"""Pipeline execution endpoints."""
from __future__ import annotations
import io
import base64
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


class PipelineRequest(BaseModel):
    ver_path: str | None = None
    hor_path: str | None = None
    demo: bool = True


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
    try:
        from run_pipeline import run_pipeline as run_full_pipeline
        result = run_full_pipeline(
            ver_path=req.ver_path or None,
            hor_path=req.hor_path or None,
            demo=req.demo,
        )
        # Store in visualization cache so viz endpoints pick up real data
        from src.api.routes_visualization import set_pipeline_data
        set_pipeline_data(result)

        life = result["life_result"]
        return {
            "status": "success",
            "life_result": life.to_dict(),
            "uncertainty": result["uncertainty"],
            "n_events": len(result["event_df"]) if not result["event_df"].empty else 0,
            "n_healthy_gauges": len(result["healthy_gauges"]),
            "n_synced_bundles": len(result["synced_bundles"]),
            "rep_eps_t": result["rep_eps_t"],
            "rep_eps_v": result["rep_eps_v"],
        }
    except Exception as e:
        raise HTTPException(500, str(e))


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
