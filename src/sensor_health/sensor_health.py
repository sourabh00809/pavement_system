"""
Module C — Sensor Health Monitor
Detects dead, saturated, and drifting gauges.
Computes health score 0–1 per gauge.
Supports autoencoder-based anomaly detection.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional
try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
from src.utils.config import load_config, get_logger

log = get_logger(__name__)
CFG = load_config()
SH = CFG["sensor_health"]
FS = CFG["daq"]["sampling_rate"]


@dataclass
class GaugeHealth:
    gauge_name: str
    health_score: float       # 0 (dead) → 1 (healthy)
    is_dead: bool
    is_saturated: bool
    mean_offset: float
    std_dev: float
    flags: list[str] = field(default_factory=list)
    excluded: bool = False    # Set True if score < threshold or manual override

    def to_dict(self) -> dict:
        return {
            "gauge": self.gauge_name,
            "health_score": round(self.health_score, 3),
            "is_dead": self.is_dead,
            "is_saturated": self.is_saturated,
            "mean_offset": round(self.mean_offset, 2),
            "std_dev": round(self.std_dev, 2),
            "flags": self.flags,
            "excluded": self.excluded,
        }


def check_gauge_health(series: np.ndarray, gauge_name: str,
                       window_s: float = SH["health_score_window"],
                       fs: float = FS,
                       exclude_threshold: float = SH["exclude_threshold"]) -> GaugeHealth:
    """
    Compute health score for a single gauge time series.
    Checks for dead gauge, saturation, and large offset.
    """
    flags = []
    window = int(window_s * fs)
    # Use first quiet window (30 seconds into signal)
    segment = series[:window] if len(series) >= window else series

    std_dev = float(np.std(segment))
    mean_offset = float(np.mean(segment))
    abs_offset = abs(mean_offset)

    # Dead gauge check (variance too low)
    is_dead = std_dev < SH["dead_gauge_std_threshold"]
    if is_dead:
        flags.append(f"DEAD: std={std_dev:.3f} µε < threshold {SH['dead_gauge_std_threshold']}")

    # Saturation / damage check (large constant offset)
    is_saturated = abs_offset > SH["saturated_offset_threshold"]
    if is_saturated:
        flags.append(f"SATURATED: |mean|={abs_offset:.1f} µε > {SH['saturated_offset_threshold']}")

    # Additional: check for NaN ratio
    nan_ratio = float(np.isnan(series).mean())
    if nan_ratio > 0.1:
        flags.append(f"HIGH_NAN: {nan_ratio*100:.1f}% missing")

    # Check for clipping (too many identical values)
    vals, counts = np.unique(np.round(segment, 0), return_counts=True)
    if len(counts) > 0 and counts.max() / len(segment) > 0.5:
        flags.append("CLIPPING: >50% samples have same value")

    # Compute health score (0–1)
    score = 1.0
    if is_dead:
        score -= 0.6
    if is_saturated:
        score -= 0.4
    if nan_ratio > 0.1:
        score -= 0.2
    score = max(0.0, min(1.0, score))

    excluded = score < exclude_threshold

    gh = GaugeHealth(
        gauge_name=gauge_name,
        health_score=score,
        is_dead=is_dead,
        is_saturated=is_saturated,
        mean_offset=mean_offset,
        std_dev=std_dev,
        flags=flags,
        excluded=excluded,
    )
    if flags:
        log.warning(f"Gauge {gauge_name} health={score:.2f}: {'; '.join(flags)}")
    return gh


def assess_all_gauges(df: pd.DataFrame,
                      exclude_threshold: float = SH["exclude_threshold"]) -> dict[str, GaugeHealth]:
    """Run health check on all gauges. Returns dict gauge_name → GaugeHealth."""
    results = {}
    for col in df.columns:
        gh = check_gauge_health(df[col].values, col, exclude_threshold=exclude_threshold)
        results[col] = gh
    healthy = sum(1 for g in results.values() if not g.excluded)
    log.info(f"Sensor health: {healthy}/{len(results)} gauges healthy")
    return results


def get_healthy_gauges(health_map: dict[str, GaugeHealth],
                       manual_overrides: dict[str, bool] = None) -> list[str]:
    """
    Return list of gauge names to include in Nf/Nr estimation.
    manual_overrides: {gauge_name: True/False} — True = force include, False = force exclude.
    """
    overrides = manual_overrides or {}
    healthy = []
    for name, gh in health_map.items():
        if name in overrides:
            if overrides[name]:
                healthy.append(name)
        elif not gh.excluded:
            healthy.append(name)
    return healthy


def get_gauge_weights(health_map: dict[str, GaugeHealth],
                      gauge_list: list[str]) -> dict[str, float]:
    """
    Return normalized health-score weights for each gauge in gauge_list.
    Used for weighted averaging in collective strain estimation.
    """
    scores = {g: health_map[g].health_score for g in gauge_list}
    total = sum(scores.values())
    if total == 0:
        return {g: 1.0 / len(gauge_list) for g in gauge_list}
    return {g: s / total for g, s in scores.items()}


# ─── Autoencoder Anomaly Detector ────────────────────────────────────────────

if not TORCH_AVAILABLE:
    class _DummyModule:
        pass
    nn = type("nn", (), {"Module": _DummyModule})()

class GaugeAutoencoder(nn.Module):
    """Dense autoencoder for sensor anomaly detection."""
    def __init__(self, input_dim: int = 128, latent_dim: int = 16):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 64), nn.ReLU(),
            nn.Linear(64, 32), nn.ReLU(),
            nn.Linear(32, latent_dim),
        )
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 32), nn.ReLU(),
            nn.Linear(32, 64), nn.ReLU(),
            nn.Linear(64, input_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.decoder(self.encoder(x))

    def reconstruction_error(self, x: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            recon = self(x)
            return torch.mean((x - recon) ** 2, dim=1)


def train_autoencoder(baseline_windows: np.ndarray,
                      epochs: int = 50,
                      batch_size: int = 64,
                      lr: float = 1e-3) -> tuple[GaugeAutoencoder, float]:
    """
    Train autoencoder on baseline (vehicle-free) windows.
    Returns trained model and 99th-percentile error threshold.
    """
    input_dim = baseline_windows.shape[1]
    model = GaugeAutoencoder(input_dim=input_dim, latent_dim=CFG["ml"]["autoencoder_latent"])
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()

    X = torch.tensor(baseline_windows, dtype=torch.float32)
    dataset = torch.utils.data.TensorDataset(X)
    loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)

    model.train()
    for epoch in range(epochs):
        total_loss = 0.0
        for (batch,) in loader:
            optimizer.zero_grad()
            loss = criterion(model(batch), batch)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        if (epoch + 1) % 10 == 0:
            log.info(f"  AE Epoch {epoch+1}/{epochs}  loss={total_loss/len(loader):.6f}")

    # Compute threshold from training errors
    model.eval()
    errors = model.reconstruction_error(X).numpy()
    threshold = float(np.percentile(errors, 99))
    log.info(f"Autoencoder trained. Anomaly threshold (p99): {threshold:.6f}")
    return model, threshold
