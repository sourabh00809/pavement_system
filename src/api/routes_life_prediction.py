"""Life prediction and redesign endpoints."""
from __future__ import annotations
import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class LayerInput(BaseModel):
    Layer: str
    Thickness_mm: float = Field(default=0.0, alias="Thickness (mm)")


class LifePredictionInput(BaseModel):
    epsilon_t: float = 200.0
    epsilon_v: float = 300.0
    E_MPa: float = 3000.0
    A: float = 1000.0
    D: float = 0.75
    F: float = 4.5
    r: float = 0.05
    n: int = 20
    layers: list[LayerInput] | None = None


@router.post("/life/predict")
async def predict_life(req: LifePredictionInput):
    try:
        from src.mechanistic.mechanistic import (
            compute_pavement_life,
            compute_life_with_uncertainty,
            recommend_pavement_redesign,
        )
        layers_dict = None
        if req.layers:
            layers_dict = [{"Layer": l.Layer, "Thickness (mm)": l.Thickness_mm} for l in req.layers]

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
            layers=layers_dict, A=req.A, D=req.D, F=req.F, r=req.r, n=req.n,
        )
        return {
            **result.to_dict(),
            "uncertainty": uncertainty,
            "redesign": redesign,
        }
    except Exception as e:
        raise HTTPException(500, str(e))
