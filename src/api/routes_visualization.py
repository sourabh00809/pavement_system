"""Data visualization endpoints — with in-memory caching to avoid re-running full pipeline on every request."""
from __future__ import annotations
import io
import base64
import functools
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from fastapi import APIRouter

router = APIRouter()

plt.rcParams.update({
    "figure.facecolor": "#f5f7fa",
    "axes.facecolor": "#ffffff",
    "axes.edgecolor": "#e0e0e0",
    "axes.grid": True,
    "grid.alpha": 0.3,
})

_cache: dict = {}


def _fig_to_b64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def _get_pipeline_result():
    if "pipeline" not in _cache:
        from run_pipeline import run_pipeline
        _cache["pipeline"] = run_pipeline(demo=True)
    return _cache["pipeline"]


def _get_demo_data():
    if "demo_data" not in _cache:
        from run_pipeline import generate_demo_data
        from src.preprocessing.preprocessing import preprocess_dataframe
        df_ver, df_hor = generate_demo_data()
        gauge_types = {}
        for c in df_ver.columns:
            gauge_types[c] = "vertical_strain" if int(c[2:]) <= 12 else "horizontal_strain"
        for c in df_hor.columns:
            key = f"{c}_hor"
            idx = int(c[2:])
            gauge_types[key] = "horizontal_strain" if idx <= 9 else ("temperature" if idx <= 11 else "epc")
        df_combined = pd.concat([df_ver, df_hor.rename(columns={c: f"{c}_hor" for c in df_hor.columns})], axis=1)
        strain_cols = [c for c, t in gauge_types.items() if t in ("vertical_strain", "horizontal_strain") and c in df_combined.columns]
        df_filtered = preprocess_dataframe(df_combined[strain_cols], gauge_types)
        _cache["demo_data"] = {
            "df_combined": df_combined,
            "df_filtered": df_filtered,
            "gauge_types": gauge_types,
            "strain_cols": strain_cols,
        }
    return _cache["demo_data"]


@router.get("/viz/signals")
async def get_signals(gauge: str = "CH0"):
    dd = _get_demo_data()
    df_combined = dd["df_combined"]
    df_filtered = dd["df_filtered"]
    strain_cols = dd["strain_cols"]

    if gauge not in df_combined.columns:
        gauge = strain_cols[0] if strain_cols else df_combined.columns[0]

    raw = df_combined[gauge].values[:5000]
    times = df_combined.index[:5000]
    processed = df_filtered[gauge].values[:5000] if gauge in df_filtered.columns else raw

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 5), sharex=True)
    ax1.plot(times, raw, color="#4a90d9", linewidth=0.5)
    ax1.set_title(f"{gauge} — Raw Signal", fontweight="bold")
    ax1.set_ylabel("Strain (µε)")
    ax2.plot(times, processed, color="#1e3a5f", linewidth=0.5)
    ax2.set_title(f"{gauge} — Filtered (0.5–30 Hz bandpass)", fontweight="bold")
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Strain (µε)")
    fig.tight_layout()

    return {
        "gauge": gauge,
        "times": times.tolist(),
        "raw": raw.tolist(),
        "filtered": processed.tolist(),
        "plot": _fig_to_b64(fig),
    }


@router.get("/viz/health")
async def get_health():
    from src.sensor_health.sensor_health import assess_all_gauges

    dd = _get_demo_data()
    df_filtered = dd["df_filtered"]

    health_map = assess_all_gauges(df_filtered)
    gauges_data = [gh.to_dict() for gh in health_map.values()]

    names = [g["gauge"] for g in gauges_data]
    scores = [g["health_score"] for g in gauges_data]
    colors = ["#2ecc71" if s > 0.7 else ("#f39c12" if s > 0.3 else "#e74c3c") for s in scores]

    fig, ax = plt.subplots(figsize=(10, 4))
    bars = ax.bar(names, scores, color=colors, edgecolor="white", linewidth=0.5)
    ax.axhline(y=0.3, color="#e74c3c", linestyle="--", alpha=0.6, label="Exclusion threshold")
    ax.set_ylim(0, 1.1)
    ax.set_title("Gauge Health Scores", fontweight="bold")
    ax.set_ylabel("Health Score")
    ax.legend()
    for bar, s in zip(bars, scores):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f"{s:.2f}", ha="center", va="bottom", fontsize=7)
    fig.tight_layout()

    return {"gauges": gauges_data, "plot": _fig_to_b64(fig)}


@router.get("/viz/events")
async def get_events():
    result = _get_pipeline_result()
    event_df = result["event_df"]

    events_summary = []
    if not event_df.empty:
        for _, row in event_df.iterrows():
            events_summary.append({
                "vehicle_id": int(row.get("vehicle_id", 0)),
                "gauge_id": str(row.get("gauge_id", "")),
                "axle_count": int(row.get("axle_count", 0)),
                "max_strain": float(row.get("max_strain", 0)),
                "duration_s": float(row.get("duration_s", 0)),
            })

    axle_dist = {}
    if not event_df.empty and "axle_count" in event_df.columns:
        axle_dist = event_df["axle_count"].value_counts().sort_index().to_dict()
        axle_dist = {str(k): int(v) for k, v in axle_dist.items()}

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    if events_summary:
        strains = [e["max_strain"] for e in events_summary]
        ax1.hist(strains, bins=20, color="#4a90d9", edgecolor="white")
        ax1.set_title("Peak Strain Distribution", fontweight="bold")
        ax1.set_xlabel("Max Strain (µε)")
        ax1.set_ylabel("Count")
    if axle_dist:
        ax2.bar(list(axle_dist.keys()), list(axle_dist.values()), color="#1e3a5f", edgecolor="white")
        ax2.set_title("Vehicles by Axle Count", fontweight="bold")
        ax2.set_xlabel("Axles")
        ax2.set_ylabel("Count")
    fig.tight_layout()

    return {
        "events": events_summary,
        "axle_distribution": axle_dist,
        "n_total": len(events_summary),
        "plot": _fig_to_b64(fig),
    }


@router.get("/viz/sync")
async def get_sync_matrix():
    result = _get_pipeline_result()
    bundles = result["synced_bundles"]
    health_map = result["health_map"]
    gauges = list(health_map.keys())

    matrix = np.zeros((len(gauges), len(gauges)))
    for i, g1 in enumerate(gauges):
        for j, g2 in enumerate(gauges):
            shared = 0
            for b in bundles:
                gnames = [m["gauge"] for m in b.gauge_events]
                if g1 in gnames and g2 in gnames:
                    shared += 1
            matrix[i][j] = shared

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(matrix, cmap="Blues", aspect="auto")
    ax.set_xticks(range(len(gauges)))
    ax.set_yticks(range(len(gauges)))
    ax.set_xticklabels(gauges, rotation=45, ha="right", fontsize=7)
    ax.set_yticklabels(gauges, fontsize=7)
    ax.set_title("Cross-Gauge Event Matches", fontweight="bold")
    plt.colorbar(im, ax=ax, label="Shared events")
    fig.tight_layout()

    bundles_summary = [b.to_dict() for b in bundles[:20]]

    return {
        "bundles": bundles_summary,
        "n_bundles": len(bundles),
        "matrix": matrix.tolist(),
        "gauges": gauges,
        "plot": _fig_to_b64(fig),
    }


@router.get("/viz/life")
async def get_life_plot():
    result = _get_pipeline_result()
    life = result["life_result"]
    uncertainty = result["uncertainty"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    labels = ["Nf\n(Fatigue)", "Nr\n(Rutting)", "Nd\n(Design)"]
    values = [life.Nf, life.Nr, life.Nd]
    bars = ax1.bar(labels, [np.log10(max(v, 1)) for v in values],
                   color=["#4a90d9", "#e8a838", "#1e3a5f"], edgecolor="white")
    for bar, v in zip(bars, values):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                 f"{v:.1e}", ha="center", va="bottom", fontsize=9)
    ax1.set_title("Pavement Life (log scale)", fontweight="bold")
    ax1.set_ylabel("log₁₀(Repetitions)")

    util_labels = ["Fatigue\n(Nd/Nf)", "Rutting\n(Nd/Nr)"]
    util_values = [life.fatigue_utilization, life.rutting_utilization]
    util_colors = ["#e74c3c" if v > 1 else "#2ecc71" for v in util_values]
    ax2.bar(util_labels, util_values, color=util_colors, edgecolor="white", width=0.5)
    ax2.axhline(y=1.0, color="#e74c3c", linestyle="--", alpha=0.7, label="Failure threshold")
    ax2.set_title("Utilization Ratios", fontweight="bold")
    ax2.set_ylabel("Nd / N (≤1 = adequate)")
    for i, v in enumerate(util_values):
        ax2.text(i, v + 0.02, f"{v:.4f}", ha="center", va="bottom", fontsize=9)
    ax2.legend(fontsize=8)
    fig.tight_layout()

    return {
        "life": life.to_dict(),
        "uncertainty": uncertainty,
        "plot": _fig_to_b64(fig),
    }


@router.post("/refresh")
async def refresh_cache():
    _cache.clear()
    return {"status": "cache cleared"}
