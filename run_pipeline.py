"""
run_pipeline.py — Pavement AI Pipeline (CLI Entry Point)
Updated: now supports --api flag to start the FastAPI server.
"""
from __future__ import annotations
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config import load_config, get_logger
from src.preprocessing.preprocessing import preprocess_dataframe
from src.sensor_health.sensor_health import assess_all_gauges, get_healthy_gauges, get_gauge_weights
from src.event_detection.event_detection import extract_all_events, events_to_dataframe
from src.synchronization.synchronization import build_synced_bundles
from src.feature_engineering.feature_engineering import build_feature_matrix, estimate_collective_strain
from src.mechanistic.mechanistic import compute_pavement_life, compute_life_with_uncertainty

log = get_logger("pipeline")
CFG = load_config()


def generate_demo_data(n_samples: int = 50000) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate synthetic GEOTRAN-like data for testing without real files."""
    log.info("Generating synthetic demo data...")
    fs = CFG["daq"]["sampling_rate"]
    t = np.arange(n_samples) / fs
    rng = np.random.default_rng(42)

    def make_gauge(base_noise=5.0, n_vehicles=30, max_strain=150):
        signal = rng.normal(0, base_noise, n_samples)
        for _ in range(n_vehicles):
            t_event = rng.uniform(1, t[-1] - 3)
            n_axles = rng.choice([2, 3, 4, 5], p=[0.55, 0.12, 0.22, 0.11])
            for ax in range(n_axles):
                idx = int((t_event + ax * rng.uniform(0.25, 0.45)) * fs)
                if idx < n_samples - 40:
                    peak = rng.uniform(60, max_strain)
                    impulse = peak * np.exp(-np.linspace(0, 4, 40))
                    signal[idx:idx+40] += impulse
        return signal

    df_ver = pd.DataFrame(
        {f"CH{i}": make_gauge(5, 30, 150 if i < 13 else 80) for i in range(16)},
        index=t,
    )
    df_ver["CH11"] = rng.normal(-2000, 50, n_samples)
    df_ver["CH12"] = rng.normal(1500, 40, n_samples)
    df_ver["CH15"] = rng.normal(1800, 0.1, n_samples)

    df_hor = pd.DataFrame(
        {f"CH{i}": make_gauge(4, 28, 80) for i in range(10)},
        index=t,
    )
    df_hor["CH10"] = rng.normal(150, 5, n_samples)
    df_hor["CH11"] = rng.normal(-15, 3, n_samples)
    df_hor["CH12"] = rng.uniform(0.1, 3.0, n_samples)
    df_hor["CH13"] = rng.uniform(0.1, 2.5, n_samples)

    df_ver.index.name = "time_s"
    df_hor.index.name = "time_s"
    return df_ver, df_hor


def run_pipeline(ver_path: str | None = None,
                 hor_path: str | None = None,
                 demo: bool = False) -> dict:
    """Full end-to-end pipeline execution. Returns dict with all results."""
    log.info("=" * 60)
    log.info("PAVEMENT AI SYSTEM — PIPELINE START")
    log.info("=" * 60)

    log.info("\n[STEP 1] Data Ingestion")
    if demo or (ver_path is None and hor_path is None):
        df_ver, df_hor = generate_demo_data()
        log.info(f"Demo data: VER {df_ver.shape}, HOR {df_hor.shape}")
    else:
        from src.ingestion.geotran_parser import parse_geotran
        df_ver, meta_ver = parse_geotran(ver_path, daq_type="VER")
        df_hor, meta_hor = parse_geotran(hor_path, daq_type="HOR")
        log.info(f"VER: {df_ver.shape} | HOR: {df_hor.shape}")

    df_hor_renamed = df_hor.rename(columns={c: f"{c}_hor" for c in df_hor.columns})
    df_combined = pd.concat([df_ver, df_hor_renamed], axis=1)

    gauge_types = {}
    for c in df_ver.columns:
        idx = int(c[2:]) if c[2:].isdigit() else 0
        if idx <= 12:
            gauge_types[c] = "vertical_strain"
        else:
            gauge_types[c] = "horizontal_strain"
    for c in df_hor.columns:
        key = f"{c}_hor"
        idx = int(c[2:])
        if idx <= 9:
            gauge_types[key] = "horizontal_strain"
        elif idx <= 11:
            gauge_types[key] = "temperature"
        else:
            gauge_types[key] = "epc"

    log.info("\n[STEP 2] Signal Preprocessing (bandpass 0.5–30 Hz)")
    strain_cols = [c for c, t in gauge_types.items()
                   if t in ("vertical_strain", "horizontal_strain") and c in df_combined.columns]
    df_filtered = preprocess_dataframe(df_combined[strain_cols], gauge_types, fs=CFG["daq"]["sampling_rate"])

    log.info("\n[STEP 3] Sensor Health Assessment")
    health_map = assess_all_gauges(df_filtered)

    log.info("\n  Gauge Health Summary:")
    for name, gh in health_map.items():
        status = "EXCLUDED" if gh.excluded else "OK"
        log.info(f"    {name:15s}  score={gh.health_score:.2f}  {status}"
                  + (f"  [{'; '.join(gh.flags)}]" if gh.flags else ""))

    healthy_gauges = get_healthy_gauges(health_map)
    gauge_weights = get_gauge_weights(health_map, healthy_gauges)
    log.info(f"\n  Healthy gauges ({len(healthy_gauges)}): {healthy_gauges}")

    log.info("\n[STEP 4] Vehicle Event Detection")
    all_events = extract_all_events(df_filtered, healthy_gauges)
    event_df = events_to_dataframe(all_events)
    total_events = len(event_df)
    log.info(f"  Total events detected: {total_events}")
    if not event_df.empty:
        vc = event_df["axle_count"].value_counts().sort_index()
        log.info(f"  By axle count: {vc.to_dict()}")

    log.info("\n[STEP 5] Multi-Gauge Synchronization")
    synced_bundles = build_synced_bundles(all_events, df_filtered, healthy_gauges)
    log.info(f"  Synchronized bundles: {len(synced_bundles)}")

    log.info("\n[STEP 6] Feature Engineering")
    features_df = build_feature_matrix(all_events, df_filtered) if not event_df.empty else pd.DataFrame()
    log.info(f"  Feature matrix: {features_df.shape}")

    log.info("\n[STEP 7] Collective Strain Estimation (health-weighted)")
    eps_t_list, eps_v_list = [], []
    for bundle in synced_bundles[:min(100, len(synced_bundles))]:
        t_start = bundle.representative_time - 0.5
        t_end = bundle.representative_time + 1.5
        eps_t, eps_v = estimate_collective_strain(
            df_filtered, health_map, gauge_types, t_start, t_end
        )
        if eps_t > 0 and eps_v > 0:
            eps_t_list.append(eps_t)
            eps_v_list.append(eps_v)

    if eps_t_list and eps_v_list:
        rep_eps_t = float(np.percentile(eps_t_list, 95))
        rep_eps_v = float(np.percentile(eps_v_list, 95))
    else:
        rep_eps_t, rep_eps_v = 200.0, 300.0
        log.warning("  No strain data — using default 200/300 µε")

    log.info(f"  eps_t (p95): {rep_eps_t:.1f} µε")
    log.info(f"  eps_v (p95): {rep_eps_v:.1f} µε")

    log.info("\n[STEP 8] IRC:37-2018 Pavement Life Prediction")
    result = compute_pavement_life(rep_eps_t, rep_eps_v, E_MPa=3000.0)
    uncertainty = compute_life_with_uncertainty(
        rep_eps_t, rep_eps_v,
        epsilon_t_std=rep_eps_t * 0.10,
        epsilon_v_std=rep_eps_v * 0.10,
    )

    log.info("\n" + "=" * 60)
    log.info("  PAVEMENT LIFE PREDICTION RESULTS")
    log.info("=" * 60)
    log.info(f"  eps_t = {rep_eps_t:.1f} µε  |  eps_v = {rep_eps_v:.1f} µε")
    log.info(f"  Nf (fatigue life)  = {result.Nf:.3e} repetitions")
    log.info(f"  Nr (rutting life)  = {result.Nr:.3e} repetitions")
    log.info(f"  Nd (design traffic)= {result.Nd:.3e} repetitions")
    log.info(f"  Fatigue utilization: {result.fatigue_utilization:.4f}")
    log.info(f"  Rutting utilization: {result.rutting_utilization:.4f}")
    log.info(f"  Governing failure:   {result.governing_failure.upper()}")
    log.info(f"  Design adequate:     {'YES' if result.design_adequate else 'NO'}")
    log.info(f"  Nf 90% CI: [{uncertainty['Nf_p5']:.2e}, {uncertainty['Nf_p95']:.2e}]")
    log.info(f"  Nr 90% CI: [{uncertainty['Nr_p5']:.2e}, {uncertainty['Nr_p95']:.2e}]")
    log.info("=" * 60)

    out_dir = Path("data/processed")
    out_dir.mkdir(parents=True, exist_ok=True)

    if not event_df.empty:
        event_df.to_csv(out_dir / "vehicle_events.csv", index=False)
        log.info(f"\n  Event database -> {out_dir / 'vehicle_events.csv'}")

    summary = {
        **result.to_dict(),
        "rep_eps_t_microstrain": rep_eps_t,
        "rep_eps_v_microstrain": rep_eps_v,
        **{f"uncertainty_{k}": v for k, v in uncertainty.items()},
        "n_total_events": total_events,
        "n_healthy_gauges": len(healthy_gauges),
        "n_synced_bundles": len(synced_bundles),
    }
    pd.DataFrame([summary]).to_csv(out_dir / "life_prediction_summary.csv", index=False)
    log.info(f"  Life prediction summary -> {out_dir / 'life_prediction_summary.csv'}")
    log.info("\nPIPELINE COMPLETE")

    return {
        "life_result": result,
        "uncertainty": uncertainty,
        "event_df": event_df,
        "health_map": health_map,
        "healthy_gauges": healthy_gauges,
        "synced_bundles": synced_bundles,
        "rep_eps_t": rep_eps_t,
        "rep_eps_v": rep_eps_v,
    }


def start_api_server():
    """Start the FastAPI server."""
    import uvicorn
    log.info("Starting Pavement AI API server...")
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pavement AI System Pipeline")
    parser.add_argument("--ver", type=str, default=None, help="Path to VER GEOTRAN .xls file")
    parser.add_argument("--hor", type=str, default=None, help="Path to HOR GEOTRAN .xls file")
    parser.add_argument("--demo", action="store_true", help="Run with synthetic demo data")
    parser.add_argument("--api", action="store_true", help="Start the FastAPI web server")
    args = parser.parse_args()

    if args.api:
        start_api_server()
    else:
        results = run_pipeline(ver_path=args.ver, hor_path=args.hor, demo=args.demo)
