"""Pipeline execution endpoints — runs pipeline in background thread to avoid HF proxy timeout."""
from __future__ import annotations
import io
import base64
import uuid
from pathlib import Path
from threading import Thread
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

plt.rcParams.update({
    "figure.facecolor": "#f5f7fa",
    "axes.facecolor": "#ffffff",
    "axes.edgecolor": "#e0e0e0",
    "axes.grid": True,
    "grid.alpha": 0.3,
    "font.family": "sans-serif",
})

_task_store: dict = {}


class PipelineRequest(BaseModel):
    files: list[dict] = []  # [{"path": "...", "type": "VER"}, ...]


class LifePredictionInput(BaseModel):
    epsilon_t: float = 200.0
    epsilon_v: float = 300.0
    E_MPa: float = 3000.0
    A: float = 1000.0
    D: float = 0.75
    F: float = 4.5
    r: float = 0.05
    n: int = 20
    layers: list[dict] | None = None


@router.post("/pipeline/run")
async def run_pipeline_endpoint(req: PipelineRequest):
    # Group files by type
    ver_files = [f["path"] for f in req.files if f.get("type", "").upper() == "VER"]
    hor_files = [f["path"] for f in req.files if f.get("type", "").upper() == "HOR"]

    task_id = uuid.uuid4().hex[:8]
    _task_store[task_id] = {"status": "running"}

    def _run():
        try:
            from run_pipeline import run_pipeline as run_full_pipeline
            result = run_full_pipeline(
                ver_files=ver_files or None,
                hor_files=hor_files or None,
            )
            from src.api.routes_visualization import set_pipeline_data
            set_pipeline_data(result)
            _task_store[task_id] = {"status": "done", "result": result}
        except Exception as e:
            import traceback
            _task_store[task_id] = {"status": "error", "error": f"{e}\n{traceback.format_exc()}"}

    Thread(target=_run, daemon=True).start()
    return {"task_id": task_id, "status": "running", "n_ver": len(ver_files), "n_hor": len(hor_files)}


@router.get("/pipeline/status/{task_id}")
async def get_pipeline_status(task_id: str):
    task = _task_store.get(task_id)
    if task is None:
        raise HTTPException(404, "Task not found")
    if task["status"] == "running":
        return {"status": "running"}
    if task["status"] == "error":
        return {"status": "error", "error": task["error"]}

    result = task["result"]
    ver = result.get("VER", {})
    hor = result.get("HOR", {})

    def group_summary(grp):
        if not grp or grp.get("empty", True):
            return {"has_data": False}
        life = grp.get("life_result")
        return {
            "has_data": True,
            "n_events": len(grp.get("event_df", pd.DataFrame())),
            "n_healthy_gauges": len(grp.get("healthy_gauges", [])),
            "n_synced_bundles": len(grp.get("synced_bundles", [])),
            "rep_eps_t": grp.get("rep_eps_t", 0),
            "rep_eps_v": grp.get("rep_eps_v", 0),
            "life": life.to_dict() if life else None,
            "n_gauges": len(grp.get("per_gauge", pd.DataFrame())),
        }

    return {
        "status": "success",
        "has_ver": result.get("has_ver", False),
        "has_hor": result.get("has_hor", False),
        "VER": group_summary(ver),
        "HOR": group_summary(hor),
    }


@router.post("/pipeline/predict")
async def predict_life(req: LifePredictionInput):
    try:
        from src.mechanistic.mechanistic import (
            compute_pavement_life,
            compute_life_with_uncertainty,
            recommend_pavement_redesign,
        )
        result = compute_pavement_life(
            req.epsilon_t, req.epsilon_v, req.E_MPa,
            A=req.A, D=req.D, F=req.F, r=req.r, n=req.n,
        )
        uncertainty = compute_life_with_uncertainty(
            req.epsilon_t, req.epsilon_v,
            epsilon_t_std=req.epsilon_t * 0.10,
            epsilon_v_std=req.epsilon_v * 0.10,
        )
        redesign = recommend_pavement_redesign(
            req.epsilon_t, req.epsilon_v, req.E_MPa,
            layers=req.layers, A=req.A, D=req.D, F=req.F, r=req.r, n=req.n,
        )
        return {
            **result.to_dict(),
            "uncertainty": uncertainty,
            "redesign": redesign,
        }
    except Exception as e:
        raise HTTPException(500, str(e))
