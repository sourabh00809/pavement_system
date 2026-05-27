"""Data visualization endpoints — returns Plotly interactive JSON instead of static images."""
from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from fastapi import APIRouter

router = APIRouter()

_cache: dict = {}

# Professional theme colors
THEME = {
    "primary": "#1e3a5f",
    "secondary": "#4a90d9",
    "accent": "#e8a838",
    "success": "#2ecc71",
    "danger": "#e74c3c",
    "warning": "#f39c12",
    "bg": "#f5f7fa",
    "card": "#ffffff",
    "text": "#333333",
}


def _layout(title: str, xlabel: str = "", ylabel: str = "", **kwargs) -> dict:
    return dict(
        title=dict(text=title, font=dict(size=16, color=THEME["primary"])),
        xaxis=dict(title=xlabel, gridcolor="#eee", zerolinecolor="#ddd"),
        yaxis=dict(title=ylabel, gridcolor="#eee", zerolinecolor="#ddd"),
        plot_bgcolor=THEME["card"],
        paper_bgcolor=THEME["bg"],
        font=dict(family="Inter, sans-serif", color=THEME["text"]),
        margin=dict(l=50, r=20, t=50, b=40),
        hovermode="closest",
        **kwargs,
    )


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

    times = df_combined.index[:5000]
    raw = df_combined[gauge].values[:5000]
    processed = df_filtered[gauge].values[:5000] if gauge in df_filtered.columns else raw

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=times, y=raw, mode="lines",
        name="Raw", line=dict(color=THEME["secondary"], width=1),
        hovertemplate="Time: %{x:.3f}s<br>Raw: %{y:.1f} µε<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=times, y=processed, mode="lines",
        name="Filtered (0.5–30 Hz)", line=dict(color=THEME["primary"], width=1.5),
        hovertemplate="Time: %{x:.3f}s<br>Filtered: %{y:.1f} µε<extra></extra>",
    ))
    fig.update_layout(**_layout(f"{gauge} — Raw vs Filtered", "Time (s)", "Strain (µε)"))

    return {
        "gauge": gauge,
        "times": times.tolist(),
        "raw": raw.tolist(),
        "filtered": processed.tolist(),
        "plot_json": fig.to_json(),
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

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=names, y=scores,
        marker_color=colors,
        text=[f"{s:.2f}" for s in scores],
        textposition="outside",
        hovertemplate="Gauge: %{x}<br>Score: %{y:.3f}<extra></extra>",
    ))
    fig.add_hline(y=0.3, line_dash="dash", line_color=THEME["danger"],
                  annotation_text="Exclusion threshold", annotation_position="bottom right")
    fig.update_layout(**_layout("Gauge Health Scores", yaxis=dict(range=[0, 1.1], title="Health Score")))

    return {"gauges": gauges_data, "plot_json": fig.to_json()}


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

    fig = go.Figure()
    if events_summary:
        strains = [e["max_strain"] for e in events_summary]
        fig.add_trace(go.Histogram(
            x=strains, nbinsx=20,
            marker_color=THEME["secondary"],
            hovertemplate="Strain: %{x:.1f} µε<br>Count: %{y}<extra></extra>",
            name="Peak Strain",
        ))
    fig.update_layout(**_layout("Peak Strain Distribution", "Max Strain (µε)", "Count"))

    fig2 = go.Figure()
    if axle_dist:
        fig2.add_trace(go.Bar(
            x=list(axle_dist.keys()), y=list(axle_dist.values()),
            marker_color=THEME["primary"],
            text=list(axle_dist.values()), textposition="outside",
            hovertemplate="%{x}-axle: %{y} vehicles<extra></extra>",
        ))
    fig2.update_layout(**_layout("Vehicles by Axle Count", "Axles", "Count"))

    return {
        "events": events_summary,
        "axle_distribution": axle_dist,
        "n_total": len(events_summary),
        "plot_json": fig.to_json(),
        "plot_json2": fig2.to_json(),
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

    fig = go.Figure(data=go.Heatmap(
        z=matrix, x=gauges, y=gauges,
        colorscale="Blues",
        hovertemplate="G1: %{x}<br>G2: %{y}<br>Shared: %{z}<extra></extra>",
    ))
    fig.update_layout(**_layout("Cross-Gauge Event Matches"))
    fig.update_xaxes(tickangle=45, tickfont=dict(size=9))
    fig.update_yaxes(tickfont=dict(size=9))

    bundles_summary = [b.to_dict() for b in bundles[:20]]

    return {
        "bundles": bundles_summary,
        "n_bundles": len(bundles),
        "matrix": matrix.tolist(),
        "gauges": gauges,
        "plot_json": fig.to_json(),
    }


@router.get("/viz/life")
async def get_life_plot():
    result = _get_pipeline_result()
    life = result["life_result"]
    uncertainty = result["uncertainty"]

    fig = go.Figure()
    labels = ["Fatigue (Nf)", "Rutting (Nr)", "Design (Nd)"]
    values = [life.Nf, life.Nr, life.Nd]
    log_vals = [np.log10(max(v, 1)) for v in values]

    fig.add_trace(go.Bar(
        x=labels, y=log_vals,
        marker_color=[THEME["secondary"], THEME["accent"], THEME["primary"]],
        text=[f"{v:.2e}" for v in values],
        textposition="outside",
        hovertemplate="%{x}<br>log₁₀ = %{y:.2f}<br>Value = %{text}<extra></extra>",
    ))
    fig.update_layout(**_layout("Pavement Life (log scale)", yaxis=dict(title="log₁₀(Repetitions)")))

    fig2 = go.Figure()
    util_labels = ["Fatigue (Nd/Nf)", "Rutting (Nd/Nr)"]
    util_vals = [life.fatigue_utilization, life.rutting_utilization]
    util_colors = [THEME["danger"] if v > 1 else THEME["success"] for v in util_vals]
    fig2.add_trace(go.Bar(
        x=util_labels, y=util_vals,
        marker_color=util_colors,
        text=[f"{v:.4f}" for v in util_vals],
        textposition="outside",
        hovertemplate="%{x}<br>Ratio: %{y:.4f}<extra></extra>",
    ))
    fig2.add_hline(y=1.0, line_dash="dash", line_color=THEME["danger"],
                   annotation_text="Failure threshold")
    fig2.update_layout(**_layout("Utilization Ratios", yaxis=dict(title="Nd / N (≤1 = adequate)")))

    return {
        "life": life.to_dict(),
        "uncertainty": uncertainty,
        "plot_json": fig.to_json(),
        "plot_json2": fig2.to_json(),
    }


@router.get("/viz/strains")
async def get_strains():
    result = _get_pipeline_result()
    dd = _get_demo_data()
    df_filtered = dd["df_filtered"]
    gauge_types = dd["gauge_types"]
    health_map = result["health_map"]
    eps_t = result["rep_eps_t"]
    eps_v = result["rep_eps_v"]

    per_gauge = []
    for gauge in df_filtered.columns:
        gh = health_map.get(gauge)
        if gh is None:
            continue
        series = df_filtered[gauge].dropna()
        peak_strain = float(series.abs().max()) if len(series) > 0 else 0
        gtype = gauge_types.get(gauge, "unknown")
        per_gauge.append({
            "gauge": gauge,
            "type": gtype,
            "peak_strain_microstrain": round(peak_strain, 1),
            "health_score": round(gh.health_score, 3),
            "excluded": gh.excluded,
        })

    # per-gauge bar chart
    fig = go.Figure()
    hor_gauges = [g for g in per_gauge if g["type"] == "horizontal_strain"]
    ver_gauges = [g for g in per_gauge if g["type"] == "vertical_strain"]
    for label, group, color in [("Horizontal", hor_gauges, THEME["accent"]),
                                  ("Vertical", ver_gauges, THEME["secondary"])]:
        if group:
            fig.add_trace(go.Bar(
                name=label,
                x=[g["gauge"] for g in group],
                y=[g["peak_strain_microstrain"] for g in group],
                marker_color=color,
                hovertemplate="Gauge: %{x}<br>Peak: %{y:.1f} µε<br>" + label + "<extra></extra>",
            ))
    fig.update_layout(**_layout("Per-Gauge Peak Strain by Type", "Gauge", "Peak Strain (µε)",
                                 barmode="group"))

    # collective strain histogram across bundles
    bundle_strains_t, bundle_strains_v = [], []
    for bundle in result["synced_bundles"][:100]:
        from src.feature_engineering.feature_engineering import estimate_collective_strain
        t_start = bundle.representative_time - 0.5
        t_end = bundle.representative_time + 1.5
        et, ev = estimate_collective_strain(df_filtered, health_map, gauge_types, t_start, t_end)
        if et > 0:
            bundle_strains_t.append(et)
        if ev > 0:
            bundle_strains_v.append(ev)

    fig2 = go.Figure()
    if bundle_strains_t:
        fig2.add_trace(go.Box(y=bundle_strains_t, name="εt (horizontal)", marker_color=THEME["accent"],
                               hovertemplate="εt: %{y:.1f} µε<extra></extra>"))
    if bundle_strains_v:
        fig2.add_trace(go.Box(y=bundle_strains_v, name="εv (vertical)", marker_color=THEME["secondary"],
                               hovertemplate="εv: %{y:.1f} µε<extra></extra>"))
    fig2.add_hline(y=eps_t, line_dash="dash", line_color=THEME["accent"],
                   annotation_text=f"p95 εt = {eps_t:.0f} µε")
    fig2.add_hline(y=eps_v, line_dash="dash", line_color=THEME["secondary"],
                   annotation_text=f"p95 εv = {eps_v:.0f} µε")
    fig2.update_layout(**_layout("Collective Strain Distribution Across Events", "Strain Type", "Strain (µε)"))

    return {
        "per_gauge": per_gauge,
        "eps_t": round(eps_t, 1),
        "eps_v": round(eps_v, 1),
        "n_gauges": len(per_gauge),
        "n_horizontal": len(hor_gauges),
        "n_vertical": len(ver_gauges),
        "plot_json": fig.to_json(),
        "plot_json2": fig2.to_json(),
    }


@router.get("/viz/temperature")
async def get_temperature(offset_ch10: float = 0, offset_ch11: float = 0):
    dd = _get_demo_data()
    df_combined = dd["df_combined"]

    ch10 = "CH10_hor"
    ch11 = "CH11_hor"

    times = df_combined.index[:5000].tolist()
    raw_ch10 = df_combined[ch10].values[:5000].tolist() if ch10 in df_combined.columns else []
    raw_ch11 = df_combined[ch11].values[:5000].tolist() if ch11 in df_combined.columns else []

    cal_ch10 = [v + offset_ch10 for v in raw_ch10] if raw_ch10 else []
    cal_ch11 = [v + offset_ch11 for v in raw_ch11] if raw_ch11 else []

    fig = go.Figure()
    if raw_ch10:
        fig.add_trace(go.Scatter(x=times, y=raw_ch10, mode="lines",
                                 name="CH10 Raw", line=dict(color=THEME["danger"], width=1),
                                 hovertemplate="Time: %{x:.3f}s<br>Raw: %{y:.1f} °C<extra></extra>"))
        fig.add_trace(go.Scatter(x=times, y=cal_ch10, mode="lines",
                                 name="CH10 Calibrated", line=dict(color=THEME["accent"], width=1.5),
                                 hovertemplate="Time: %{x:.3f}s<br>Cal: %{y:.1f} °C<extra></extra>"))
    if raw_ch11:
        fig.add_trace(go.Scatter(x=times, y=raw_ch11, mode="lines",
                                 name="CH11 Raw", line=dict(color=THEME["secondary"], width=1, dash="dot"),
                                 hovertemplate="Time: %{x:.3f}s<br>Raw: %{y:.1f} °C<extra></extra>"))
        fig.add_trace(go.Scatter(x=times, y=cal_ch11, mode="lines",
                                 name="CH11 Calibrated", line=dict(color=THEME["primary"], width=1.5, dash="dot"),
                                 hovertemplate="Time: %{x:.3f}s<br>Cal: %{y:.1f} °C<extra></extra>"))
    fig.update_layout(**_layout("Temperature Channels — Raw vs Calibrated", "Time (s)", "Temperature (°C)"))

    stats = {}
    for label, raw in [("CH10", raw_ch10), ("CH11", raw_ch11)]:
        if raw:
            stats[label] = {
                "mean": round(float(np.mean(raw)), 1),
                "min": round(float(np.min(raw)), 1),
                "max": round(float(np.max(raw)), 1),
            }

    return {
        "ch10_raw": raw_ch10,
        "ch10_calibrated": cal_ch10,
        "ch11_raw": raw_ch11,
        "ch11_calibrated": cal_ch11,
        "times": times,
        "stats": stats,
        "offset_ch10": offset_ch10,
        "offset_ch11": offset_ch11,
        "plot_json": fig.to_json(),
    }


@router.post("/refresh")
async def refresh_cache():
    _cache.clear()
    return {"status": "cache cleared"}
