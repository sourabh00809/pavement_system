"""Export/download endpoints."""
from __future__ import annotations
import io
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()


@router.get("/export/events")
async def export_events():
    from run_pipeline import run_pipeline
    result = run_pipeline(demo=True)
    event_df = result["event_df"]

    if event_df.empty:
        return StreamingResponse(io.StringIO(""), media_type="text/csv",
                                  headers={"Content-Disposition": "attachment; filename=events.csv"})

    stream = io.StringIO()
    event_df.to_csv(stream, index=False)
    stream.seek(0)
    return StreamingResponse(iter([stream.getvalue()]), media_type="text/csv",
                              headers={"Content-Disposition": "attachment; filename=events.csv"})


@router.get("/export/summary")
async def export_summary():
    from run_pipeline import run_pipeline
    result = run_pipeline(demo=True)
    life = result["life_result"]
    d = life.to_dict()
    d.update(result["uncertainty"])
    return d


# Config export removed to prevent leaking internal parameters
