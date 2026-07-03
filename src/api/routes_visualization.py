"""Data visualization endpoints — returns Plotly interactive JSON."""
from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from fastapi import APIRouter, HTTPException

router = APIRouter()

_cache: dict = {}

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


def _rangeslider_layout(start: float = 0, end: float = 10) -> dict:
    return dict(rangeslider=dict(visible=True), range=[start, end])


def _get_pipeline_data() -> dict:
    """Return cached pipeline data. Raises if no data available."""
    if "pipeline_data" not in _cache:
        raise HTTPException(400, "No data has been processed yet. Upload and process data first.")
    return _cache["pipeline_data"]


def _get_group(group_name: str) -> dict:
    """Get a specific group result (VER or HOR) or empty dict."""
    data = _get_pipeline_data()
    return data.get(group_name, {})


def _has_data(result: dict) -> bool:
    return bool(result) and not result.get("empty", True)


def set_pipeline_data(result: dict) -> None:
    _cache["pipeline_data"] = result
    _cache["_pipeline_is_demo"] = False


def set_uploaded_files(files: list[dict]) -> None:
    """Store uploaded file list (called after file upload)."""
    _cache["uploaded_files"] = files


def get_upload_status() -> dict:
    has_uploads = "uploaded_files" in _cache and len(_cache["uploaded_files"]) > 0
    has_processed = "pipeline_data" in _cache and not _cache.get("_pipeline_is_demo", True)
    files = _cache.get("uploaded_files", [])
    ver_count = sum(1 for f in files if f.get("type", "").upper() == "VER")
    hor_count = sum(1 for f in files if f.get("type", "").upper() == "HOR")
    return {
        "has_uploads": has_uploads,
        "has_processed": has_processed,
        "files": files,
        "n_ver": ver_count,
        "n_hor": hor_count,
    }


def _build_gauge_type_lists(grp: dict) -> tuple[list[str], list[str]]:
    """Return (strain_cols, healthy_cols) for a group result."""
    strain_cols = grp.get("strain_cols", [])
    healthy = grp.get("healthy_gauges", [])
    return strain_cols, healthy


# ─── Signals ──────────────────────────────────────────────────────────────────

@router.get("/viz/signals")
async def get_signals(gauge: str = "CH0", group: str = "VER"):
    grp = _get_group(group.upper())
    if not _has_data(grp):
        return {"gauge": gauge, "times": [], "raw": [], "filtered": [],
                "plot_json": None, "total_duration_s": 0}

    df_combined = grp.get("df_raw", pd.DataFrame())
    df_filtered = grp.get("df_filtered", pd.DataFrame())
    strain_cols = grp.get("strain_cols", [])

    if gauge not in df_combined.columns:
        gauge = strain_cols[0] if strain_cols else (df_combined.columns[0] if not df_combined.empty else gauge)

    if df_combined.empty or gauge not in df_combined.columns:
        return {"gauge": gauge, "times": [], "raw": [], "filtered": [],
                "plot_json": None, "total_duration_s": 0}

    times = df_combined.index.values
    raw = df_combined[gauge].values
    processed = df_filtered[gauge].values if gauge in df_filtered.columns else raw
    total_duration = float(times[-1]) if len(times) > 0 else 0.0

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=times, y=raw, mode="lines", name="Raw",
                             line=dict(color=THEME["secondary"], width=1),
                             hovertemplate="Time: %{x:.3f}s<br>Raw: %{y:.1f} µε<extra></extra>"))
    fig.add_trace(go.Scatter(x=times, y=processed, mode="lines", name="Filtered",
                             line=dict(color=THEME["primary"], width=1.5),
                             hovertemplate="Time: %{x:.3f}s<br>Filtered: %{y:.1f} µε<extra></extra>"))
    fig.update_layout(**_layout(f"{gauge} ({group}) — Raw vs Filtered", "Time (s)", "Strain (µε)"))
    fig.update_xaxes(**_rangeslider_layout(0, 10))

    return {
        "gauge": gauge, "group": group,
        "times": times.tolist(), "raw": raw.tolist(), "filtered": processed.tolist(),
        "plot_json": fig.to_json(), "total_duration_s": total_duration,
        "window_start": 0.0, "window_end": 10.0,
    }


@router.get("/viz/signals/all")
async def get_all_signals():
    data = _get_pipeline_data()

    ver_grp = data.get("VER", {})
    hor_grp = data.get("HOR", {})

    figures = {}
    for gname, grp in [("VER", ver_grp), ("HOR", hor_grp)]:
        if not _has_data(grp):
            continue
        df_filtered = grp.get("df_filtered", pd.DataFrame())
        times = df_filtered.index.values if not df_filtered.empty else []
        fig = go.Figure()
        for c in df_filtered.columns:
            fig.add_trace(go.Scatter(x=times, y=df_filtered[c].values, mode="lines",
                                     name=c, line=dict(width=1),
                                     hovertemplate="Time: %{x:.3f}s<br>%{c}: %{y:.1f} µε<extra></extra>"))
        fig.update_layout(**_layout(f"{gname} Strain Channels", "Time (s)", "Strain (µε)",
                                    legend=dict(font=dict(size=9))))
        if len(times) > 0:
            fig.update_xaxes(**_rangeslider_layout(0, 10))
        figures[gname] = fig.to_json()

    return {
        "plot_json_ver": figures.get("VER"),
        "plot_json_hor": figures.get("HOR"),
        "has_vertical": _has_data(ver_grp),
        "has_horizontal": _has_data(hor_grp),
        "n_ver_gauges": len(ver_grp.get("strain_cols", [])),
        "n_hor_gauges": len(hor_grp.get("strain_cols", [])),
    }


# ─── Health ───────────────────────────────────────────────────────────────────

@router.get("/viz/health")
async def get_health():
    data = _get_pipeline_data()
    all_gauges = []
    for gname in ("VER", "HOR"):
        grp = data.get(gname, {})
        if not _has_data(grp):
            continue
        hm = grp.get("health_map", {})
        for gh in hm.values():
            row = gh.to_dict()
            row["group"] = gname
            all_gauges.append(row)

    if not all_gauges:
        return {"gauges": [], "plot_json": None, "summary": {}}

    fig = go.Figure()
    for gname in ("VER", "HOR"):
        gg = [g for g in all_gauges if g.get("group") == gname]
        if not gg:
            continue
        names = [g["gauge"] for g in gg]
        scores = [g["health_score"] for g in gg]
        color = THEME["primary"] if gname == "VER" else THEME["accent"]
        fig.add_trace(go.Bar(name=gname, x=names, y=scores, marker_color=color,
                             text=[f"{s:.2f}" for s in scores], textposition="outside",
                             hovertemplate="Gauge: %{x}<br>Score: %{y:.3f}<extra></extra>"))
    fig.add_hline(y=0.3, line_dash="dash", line_color=THEME["danger"],
                  annotation_text="Exclusion threshold")
    fig.update_layout(**_layout("Gauge Health Scores", yaxis=dict(range=[0, 1.1], title="Health Score")))

    n_healthy = sum(1 for g in all_gauges if not g["excluded"])
    n_warning = sum(1 for g in all_gauges if 0.3 < g["health_score"] <= 0.7)
    n_excluded = sum(1 for g in all_gauges if g["excluded"])

    return {
        "gauges": all_gauges, "plot_json": fig.to_json(),
        "summary": {"total": len(all_gauges), "healthy": n_healthy, "warning": n_warning, "excluded": n_excluded},
    }


# ─── Events ───────────────────────────────────────────────────────────────────

@router.get("/viz/events")
async def get_events():
    data = _get_pipeline_data()

    events_ver, events_hor = [], []
    for gname in ("VER", "HOR"):
        grp = data.get(gname, {})
        if not _has_data(grp):
            continue
        edf = grp.get("event_df", pd.DataFrame())
        if not edf.empty:
            for _, row in edf.iterrows():
                entry = {
                    "vehicle_id": int(row.get("vehicle_id", 0)),
                    "gauge_id": str(row.get("gauge_id", "")),
                    "axle_count": int(row.get("axle_count", 0)),
                    "max_strain": float(row.get("max_strain", 0)),
                    "duration_s": float(row.get("duration_s", 0)),
                    "group": gname,
                }
                if gname == "VER":
                    events_ver.append(entry)
                else:
                    events_hor.append(entry)

    all_events = events_ver + events_hor
    n_total = len(all_events)

    # Axle distribution
    axle_dist = {}
    if all_events:
        axle_counts = [e["axle_count"] for e in all_events]
        for ac in sorted(set(axle_counts)):
            axle_dist[str(ac)] = axle_counts.count(ac)

    fig = go.Figure()
    if all_events:
        strains = [e["max_strain"] for e in all_events]
        fig.add_trace(go.Histogram(x=strains, nbinsx=20, marker_color=THEME["secondary"],
                                    hovertemplate="Strain: %{x:.1f} µε<br>Count: %{y}<extra></extra>"))
    fig.update_layout(**_layout("Peak Strain Distribution", "Max Strain (µε)", "Count"))

    fig2 = go.Figure()
    if axle_dist:
        fig2.add_trace(go.Bar(x=list(axle_dist.keys()), y=list(axle_dist.values()),
                               marker_color=THEME["primary"],
                               text=list(axle_dist.values()), textposition="outside"))
    fig2.update_layout(**_layout("Vehicles by Axle Count", "Axles", "Count"))

    return {
        "events_ver": events_ver, "events_hor": events_hor,
        "events": all_events,
        "axle_distribution": axle_dist, "n_total": n_total,
        "plot_json": fig.to_json(), "plot_json2": fig2.to_json(),
    }


# ─── Sync ─────────────────────────────────────────────────────────────────────

@router.get("/viz/sync")
async def get_sync_matrix():
    data = _get_pipeline_data()
    all_bundles = []
    all_gauges = []
    for gname in ("VER", "HOR"):
        grp = data.get(gname, {})
        if not _has_data(grp):
            continue
        bundles = grp.get("synced_bundles", [])
        hm = grp.get("health_map", {})
        gauges = list(hm.keys())
        all_gauges.extend([(g, gname) for g in gauges])
        all_bundles.extend([(b, gname) for b in bundles])

    gauges = [g for g, _ in all_gauges]
    n = len(gauges)
    matrix = np.zeros((n, n))
    for i, g1 in enumerate(gauges):
        for j, g2 in enumerate(gauges):
            shared = 0
            for bundle, _ in all_bundles:
                gnames = [m["gauge"] for m in bundle.gauge_events]
                if g1 in gnames and g2 in gnames:
                    shared += 1
            matrix[i][j] = shared

    fig = go.Figure(data=go.Heatmap(z=matrix, x=gauges, y=gauges, colorscale="Blues",
                                     hovertemplate="G1: %{x}<br>G2: %{y}<br>Shared: %{z}<extra></extra>"))
    fig.update_layout(**_layout("Cross-Gauge Event Matches"))
    fig.update_xaxes(tickangle=45, tickfont=dict(size=9))
    fig.update_yaxes(tickfont=dict(size=9))

    bundles_summary = [b.to_dict() for b, _ in all_bundles[:20]]

    return {
        "bundles": bundles_summary, "n_bundles": len(all_bundles),
        "matrix": matrix.tolist(), "gauges": gauges, "plot_json": fig.to_json(),
    }


# ─── Life ─────────────────────────────────────────────────────────────────────

@router.get("/viz/life")
async def get_life_plot():
    data = _get_pipeline_data()

    figs = {}
    life_data = {}
    for gname in ("VER", "HOR"):
        grp = data.get(gname, {})
        if not _has_data(grp):
            continue
        life = grp.get("life_result")
        uncertainty = grp.get("uncertainty", {})
        if life is None:
            continue

        fig = go.Figure()
        labels = ["Fatigue (Nf)", "Rutting (Nr)", "Design (Nd)"]
        values = [life.Nf, life.Nr, life.Nd]
        log_vals = [np.log10(max(v, 1)) for v in values]
        fig.add_trace(go.Bar(x=labels, y=log_vals,
                             marker_color=[THEME["secondary"], THEME["accent"], THEME["primary"]],
                             text=[f"{v:.2e}" for v in values], textposition="outside"))
        fig.update_layout(**_layout(f"{gname} — Pavement Life (log scale)", yaxis=dict(title="log₁₀(Repetitions)")))
        figs[gname] = fig.to_json()

        life_data[gname] = {
            "life": life.to_dict(),
            "uncertainty": uncertainty,
            "rep_eps_t": grp.get("rep_eps_t", 0),
            "rep_eps_v": grp.get("rep_eps_v", 0),
        }

    return {
        "VER": life_data.get("VER"),
        "HOR": life_data.get("HOR"),
        "plot_json_ver": figs.get("VER"),
        "plot_json_hor": figs.get("HOR"),
    }


# ─── Strains ──────────────────────────────────────────────────────────────────

@router.get("/viz/strains")
async def get_strains():
    data = _get_pipeline_data()

    per_gauge_all = []
    figs = {}

    for gname in ("VER", "HOR"):
        grp = data.get(gname, {})
        if not _has_data(grp):
            continue
        pg = grp.get("per_gauge", pd.DataFrame())
        if pg.empty:
            continue
        for _, row in pg.iterrows():
            per_gauge_all.append({
                "gauge": row["gauge_id"],
                "type": "vertical_strain" if gname == "VER" else "horizontal_strain",
                "group": gname,
                "peak_strain_microstrain": row["peak_strain_microstrain"],
                "n_vehicles": row["n_vehicles"],
                "vehicle_ids": row["vehicle_ids"],
                "health_score": row["health_score"],
                "excluded": row["excluded"],
            })
        color = THEME["secondary"] if gname == "VER" else THEME["accent"]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=list(pg["gauge_id"]), y=list(pg["peak_strain_microstrain"]),
                             marker_color=color,
                             hovertemplate=f"Gauge: %{{x}}<br>Peak: %{{y:.1f}} µε<extra></extra>"))
        fig.update_layout(**_layout(f"{gname} — Peak Strain", "Gauge", "Peak Strain (µε)"))
        figs[gname.lower()] = fig.to_json()

    return {
        "per_gauge": per_gauge_all,
        "n_gauges": len(per_gauge_all),
        "plot_json_ver": figs.get("ver"),
        "plot_json_hor": figs.get("hor"),
        "plot_json": figs.get("ver") or figs.get("hor"),
    }


# ─── Results Table ────────────────────────────────────────────────────────────

@router.get("/viz/results/table")
async def get_results_table():
    data = _get_pipeline_data()
    summary = data.get("per_gauge_summary", pd.DataFrame())
    if summary.empty:
        return {"table": [], "columns": []}

    columns = ["gauge_id", "group", "peak_strain_microstrain", "n_vehicles",
               "vehicle_ids", "health_score", "excluded"]
    table_data = summary.to_dict(orient="records")
    # Convert vehicle_ids to readable string for JSON
    for row in table_data:
        if isinstance(row.get("vehicle_ids"), list):
            row["vehicle_ids"] = [int(v) for v in row["vehicle_ids"]]

    return {"table": table_data, "columns": columns}


# ─── Temperature ──────────────────────────────────────────────────────────────

@router.get("/viz/temperature")
async def get_temperature(offset_ch10: float = 0, offset_ch11: float = 0):
    data = _get_pipeline_data()
    hor_grp = data.get("HOR", {})
    if not _has_data(hor_grp):
        return {"has_temperature": False}

    df_raw = hor_grp.get("df_raw", pd.DataFrame())
    gt = hor_grp.get("gauge_types", {})
    temp_cols = [c for c, t in gt.items() if t == "temperature"]
    temp_cols = [c for c in temp_cols if c in df_raw.columns]

    if not temp_cols:
        return {"has_temperature": False}

    times = df_raw.index.tolist()
    total_duration = float(times[-1]) if times else 0.0

    ch10_col = next((c for c in temp_cols if "CH10" in c.upper()), temp_cols[0] if temp_cols else None)
    ch11_col = next((c for c in temp_cols if "CH11" in c.upper()), None)

    raw_ch10 = df_raw[ch10_col].values.tolist() if ch10_col else []
    raw_ch11 = df_raw[ch11_col].values.tolist() if ch11_col else []

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
    fig.update_xaxes(**_rangeslider_layout(0, 10))

    stats = {}
    for label, raw in [("CH10", raw_ch10), ("CH11", raw_ch11)]:
        if raw:
            stats[label] = {
                "mean": round(float(np.mean(raw)), 1),
                "min": round(float(np.min(raw)), 1),
                "max": round(float(np.max(raw)), 1),
            }

    return {
        "ch10_raw": raw_ch10, "ch10_calibrated": cal_ch10,
        "ch11_raw": raw_ch11, "ch11_calibrated": cal_ch11,
        "times": times, "stats": stats,
        "offset_ch10": offset_ch10, "offset_ch11": offset_ch11,
        "plot_json": fig.to_json(),
        "has_temperature": True,
        "total_duration_s": total_duration,
        "window_start": 0.0, "window_end": 10.0,
    }


# ─── Cache Control ────────────────────────────────────────────────────────────

@router.post("/refresh")
async def refresh_cache():
    _cache.clear()
    return {"status": "cache cleared"}
