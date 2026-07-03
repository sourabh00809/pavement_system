"""
run_pipeline.py — Pavement Analysis Pipeline (CLI Entry Point)
Processes VER and HOR strain data files independently.
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
from src.ingestion.geotran_parser import join_same_type_files

log = get_logger("pipeline")
CFG = load_config()


def process_group(file_list: list[str],
                  group_name: str,
                  config_prefix: str) -> dict:
    """
    Run the full pipeline for one group (VER or HOR).
    Returns dict with all results.
    """
    log.info(f"\n{'='*60}")
    log.info(f"PROCESSING {group_name} ({len(file_list)} file(s))")
    log.info(f"{'='*60}")

    if not file_list:
        log.warning(f"No files for {group_name} — skipping")
        return {}

    log.info(f"\n[STEP 1] Data Ingestion — {group_name}")
    df_raw, meta = join_same_type_files(file_list)
    log.info(f"  Raw data: {df_raw.shape}")

    gauge_types = meta["gauge_types"]
    strain_cols = [c for c, t in gauge_types.items()
                   if t in ("vertical_strain", "horizontal_strain") and c in df_raw.columns]

    if not strain_cols:
        log.warning(f"No strain channels found in {group_name} data")
        return {
            "group": group_name,
            "df_raw": df_raw,
            "gauge_types": gauge_types,
            "strain_cols": strain_cols,
            "empty": True,
        }

    log.info(f"\n[STEP 2] Signal Preprocessing ({group_name})")
    df_filtered = preprocess_dataframe(df_raw[strain_cols], gauge_types,
                                        fs=CFG["daq"]["sampling_rate"])

    log.info(f"\n[STEP 3] Sensor Health Assessment ({group_name})")
    health_map = assess_all_gauges(df_filtered)
    for name, gh in health_map.items():
        status = "EXCLUDED" if gh.excluded else "OK"
        log.info(f"    {name:15s}  score={gh.health_score:.2f}  {status}"
                  + (f"  [{'; '.join(gh.flags)}]" if gh.flags else ""))

    healthy_gauges = get_healthy_gauges(health_map)
    gauge_weights = get_gauge_weights(health_map, healthy_gauges)
    log.info(f"\n  Healthy gauges ({len(healthy_gauges)}): {healthy_gauges}")

    log.info(f"\n[STEP 4] Vehicle Event Detection ({group_name})")
    all_events = extract_all_events(df_filtered, healthy_gauges, config_prefix=config_prefix)
    event_df = events_to_dataframe(all_events)
    total_events = len(event_df)
    log.info(f"  Total events detected: {total_events}")
    if not event_df.empty:
        vc = event_df["axle_count"].value_counts().sort_index()
        log.info(f"  By axle count: {vc.to_dict()}")

    log.info(f"\n[STEP 5] Multi-Gauge Synchronization ({group_name})")
    synced_bundles = build_synced_bundles(all_events, df_filtered, healthy_gauges)
    log.info(f"  Synchronized bundles: {len(synced_bundles)}")

    log.info(f"\n[STEP 6] Feature Engineering ({group_name})")
    features_df = build_feature_matrix(all_events, df_filtered) if not event_df.empty else pd.DataFrame()
    log.info(f"  Feature matrix: {features_df.shape}")

    log.info(f"\n[STEP 7] Collective Strain Estimation ({group_name})")
    eps_t_list, eps_v_list = [], []
    for bundle in synced_bundles[:min(100, len(synced_bundles))]:
        t_start = bundle.representative_time - 0.5
        t_end = bundle.representative_time + 1.5
        eps_t, eps_v = estimate_collective_strain(
            df_filtered, health_map, gauge_types, t_start, t_end
        )
        if eps_t > 0:
            eps_t_list.append(eps_t)
        if eps_v > 0:
            eps_v_list.append(eps_v)

    rep_eps_t = float(np.percentile(eps_t_list, 95)) if eps_t_list else 0.0
    rep_eps_v = float(np.percentile(eps_v_list, 95)) if eps_v_list else 0.0
    log.info(f"  eps_t (p95): {rep_eps_t:.1f} µε, eps_v (p95): {rep_eps_v:.1f} µε")

    log.info(f"\n[STEP 8] Life Prediction ({group_name})")
    if rep_eps_t > 0 or rep_eps_v > 0:
        result = compute_pavement_life(
            max(rep_eps_t, 1.0), max(rep_eps_v, 1.0), E_MPa=3000.0
        )
        uncertainty = compute_life_with_uncertainty(
            max(rep_eps_t, 1.0), max(rep_eps_v, 1.0),
            epsilon_t_std=max(rep_eps_t * 0.10, 0.1),
            epsilon_v_std=max(rep_eps_v * 0.10, 0.1),
        )
    else:
        result = compute_pavement_life(200.0, 300.0, E_MPa=3000.0)
        uncertainty = compute_life_with_uncertainty(200.0, 300.0, 20.0, 30.0)
        log.warning("  No strain data — using default 200/300 µε")

    log.info(f"\n  Life Results ({group_name}):")
    log.info(f"    Nf (fatigue) = {result.Nf:.3e}")
    log.info(f"    Nr (rutting) = {result.Nr:.3e}")
    log.info(f"    Governing: {result.governing_failure}")

    # Build per-gauge summary
    per_gauge = []
    for gauge in strain_cols:
        gh = health_map.get(gauge)
        n_veh = len(all_events.get(gauge, []))
        veh_ids = [ev.vehicle_id for ev in all_events.get(gauge, [])]
        series = df_filtered[gauge].dropna() if gauge in df_filtered.columns else pd.Series(dtype=float)
        peak = float(series.abs().max()) if len(series) > 0 else 0.0
        per_gauge.append({
            "gauge_id": gauge,
            "group": group_name,
            "peak_strain_microstrain": round(peak, 2),
            "n_vehicles": n_veh,
            "vehicle_ids": veh_ids,
            "health_score": round(gh.health_score, 3) if gh else 0.0,
            "excluded": gh.excluded if gh else True,
        })

    per_gauge_df = pd.DataFrame(per_gauge)

    log.info(f"\n{'='*60}")
    log.info(f"{group_name} PIPELINE COMPLETE")
    log.info(f"{'='*60}")

    return {
        "group": group_name,
        "df_raw": df_raw,
        "df_filtered": df_filtered,
        "gauge_types": gauge_types,
        "strain_cols": strain_cols,
        "health_map": health_map,
        "healthy_gauges": healthy_gauges,
        "gauge_weights": gauge_weights,
        "all_events": all_events,
        "event_df": event_df,
        "total_events": total_events,
        "synced_bundles": synced_bundles,
        "features_df": features_df,
        "rep_eps_t": rep_eps_t,
        "rep_eps_v": rep_eps_v,
        "life_result": result,
        "uncertainty": uncertainty,
        "per_gauge": per_gauge_df,
        "empty": False,
    }


def run_pipeline(ver_files: list[str] | None = None,
                 hor_files: list[str] | None = None) -> dict:
    """
    Run full pipeline for VER and/or HOR file groups.
    Returns dict with 'VER', 'HOR' group results and combined summary.
    """
    log.info("=" * 60)
    log.info("PAVEMENT ANALYSIS SYSTEM — PIPELINE START")
    log.info("=" * 60)

    ver_files = ver_files or []
    hor_files = hor_files or []

    ver_result = process_group(ver_files, "VER", "event_detection_ver") if ver_files else {}
    hor_result = process_group(hor_files, "HOR", "event_detection_hor") if hor_files else {}

    # Build combined per-gauge summary across both groups
    all_per_gauge = []
    for group_result in [ver_result, hor_result]:
        if not group_result or group_result.get("empty", True):
            continue
        pg = group_result.get("per_gauge")
        if pg is not None and not pg.empty:
            all_per_gauge.append(pg)

    per_gauge_summary = pd.concat(all_per_gauge, ignore_index=True) if all_per_gauge else pd.DataFrame()

    log.info("\n" + "=" * 60)
    log.info("PIPELINE COMPLETE — FINAL SUMMARY")
    log.info("=" * 60)
    if not per_gauge_summary.empty:
        for _, row in per_gauge_summary.iterrows():
            log.info(f"  {row['gauge_id']:10s} ({row['group']:3s}): "
                      f"peak={row['peak_strain_microstrain']:8.2f} µε, "
                      f"vehicles={row['n_vehicles']:3d}, "
                      f"health={row['health_score']:.2f}")
    else:
        log.info("  No data processed")

    out_dir = Path("data/processed")
    out_dir.mkdir(parents=True, exist_ok=True)

    for group_name, group_result in [("VER", ver_result), ("HOR", hor_result)]:
        if not group_result or group_result.get("empty", True):
            continue
        edf = group_result.get("event_df")
        if edf is not None and not edf.empty:
            edf.to_csv(out_dir / f"vehicle_events_{group_name.lower()}.csv", index=False)
            log.info(f"  Events ({group_name}) -> {out_dir / f'vehicle_events_{group_name.lower()}.csv'}")
        pg = group_result.get("per_gauge")
        if pg is not None and not pg.empty:
            pg.to_csv(out_dir / f"per_gauge_summary_{group_name.lower()}.csv", index=False)
            log.info(f"  Summary ({group_name}) -> {out_dir / f'per_gauge_summary_{group_name.lower()}.csv'}")

    if not per_gauge_summary.empty:
        per_gauge_summary.to_csv(out_dir / "per_gauge_summary_all.csv", index=False)
        log.info(f"  Combined summary -> {out_dir / 'per_gauge_summary_all.csv'}")

    return {
        "VER": ver_result,
        "HOR": hor_result,
        "per_gauge_summary": per_gauge_summary,
        "has_ver": bool(ver_files),
        "has_hor": bool(hor_files),
    }


def start_api_server():
    import uvicorn
    log.info("Starting Pavement Analysis API server...")
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=False)


def _parse_file_pairs(args_list: list[str]) -> tuple[list[str], list[str]]:
    """Parse alternating --type path arguments from CLI."""
    ver_files, hor_files = [], []
    i = 0
    while i < len(args_list):
        if args_list[i] in ("--ver", "-v") and i + 1 < len(args_list):
            ver_files.append(args_list[i + 1])
            i += 2
        elif args_list[i] in ("--hor", "-h") and i + 1 < len(args_list):
            hor_files.append(args_list[i + 1])
            i += 2
        else:
            i += 1
    return ver_files, hor_files


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pavement Analysis System Pipeline")
    parser.add_argument("--ver", type=str, action="append", default=[], help="VER GEOTRAN file path (can repeat)")
    parser.add_argument("--hor", type=str, action="append", default=[], help="HOR GEOTRAN file path (can repeat)")
    parser.add_argument("--api", action="store_true", help="Start the FastAPI web server")
    args = parser.parse_args()

    if args.api:
        start_api_server()
    else:
        results = run_pipeline(ver_files=args.ver or None, hor_files=args.hor or None)
