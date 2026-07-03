"""Export/download endpoints."""
from __future__ import annotations
import io
import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

router = APIRouter()


def _get_pipeline_data():
    from src.api.routes_visualization import _get_pipeline_data as _get
    try:
        return _get()
    except HTTPException:
        return None


@router.get("/export/events")
async def export_events(group: str = "all"):
    data = _get_pipeline_data()
    if data is None:
        return StreamingResponse(io.StringIO(""), media_type="text/csv",
                                  headers={"Content-Disposition": "attachment; filename=events.csv"})

    parts = []
    for gname in ("VER", "HOR"):
        if group != "all" and group.upper() != gname:
            continue
        grp = data.get(gname, {})
        if grp and not grp.get("empty", True):
            edf = grp.get("event_df", pd.DataFrame())
            if not edf.empty:
                edf = edf.copy()
                edf["group"] = gname
                parts.append(edf)

    event_df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

    stream = io.StringIO()
    event_df.to_csv(stream, index=False)
    stream.seek(0)
    fname = f"vehicle_events_{group}.csv"
    return StreamingResponse(iter([stream.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename={fname}"})


@router.get("/export/results")
async def export_results():
    """Download per-gauge summary as Excel."""
    data = _get_pipeline_data()
    if data is None:
        raise HTTPException(404, "No results data available")

    summary = data.get("per_gauge_summary", pd.DataFrame())
    if summary.empty:
        raise HTTPException(404, "No results data available")

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Per-Gauge Summary", index=False)

        for gname in ("VER", "HOR"):
            grp = data.get(gname, {})
            if grp and not grp.get("empty", True):
                pg = grp.get("per_gauge", pd.DataFrame())
                if not pg.empty:
                    pg.to_excel(writer, sheet_name=f"{gname}_Gauges", index=False)

                edf = grp.get("event_df", pd.DataFrame())
                if not edf.empty:
                    edf.to_excel(writer, sheet_name=f"{gname}_Events", index=False)

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=results.xlsx"},
    )


@router.get("/export/summary")
async def export_summary():
    data = _get_pipeline_data()
    if data is None:
        return {"message": "No data"}

    result = {}
    for gname in ("VER", "HOR"):
        grp = data.get(gname, {})
        if grp and not grp.get("empty", True):
            life = grp.get("life_result")
            unc = grp.get("uncertainty", {})
            if life:
                d = life.to_dict()
                d.update(unc)
                result[gname] = d
    return result if result else {"message": "No data"}
