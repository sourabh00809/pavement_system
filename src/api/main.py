"""
FastAPI Application — Pavement AI System
BTP Phase II | IIT Tirupati | NH-71
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from src.api.routes_pipeline import router as pipeline_router
from src.api.routes_visualization import router as viz_router
from src.api.routes_life_prediction import router as life_router
from src.api.routes_export import router as export_router
from src.api.routes_upload import router as upload_router

app = FastAPI(
    title="Pavement AI System",
    description="End-to-end pavement response analysis and fatigue/rutting life prediction (IRC:37-2018)",
    version="2.0",
)

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://pavement-ai.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pipeline_router, prefix="/api")
app.include_router(viz_router, prefix="/api")
app.include_router(life_router, prefix="/api")
app.include_router(export_router, prefix="/api")
app.include_router(upload_router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok", "project": "Pavement AI System", "version": "2.0"}


# Mount static frontend in production
static_dir = Path(__file__).parent.parent.parent / "frontend" / "dist"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="frontend")
