"""
Module F — Feature Engineering
Extracts waveform and multi-axle features from vehicle events.
Module G — Sensor Fusion
Health-weighted collective strain estimation (εt and εv).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from src.utils.config import load_config, get_logger
from src.event_detection.event_detection import VehicleEvent
from src.sensor_health.sensor_health import GaugeHealth

log = get_logger(__name__)
CFG = load_config()
FS = CFG["daq"]["sampling_rate"]


# ─── Feature Engineering ─────────────────────────────────────────────────────

def extract_waveform_features(waveform: np.ndarray, fs: float = FS) -> dict:
    """Extract scalar features from a single event waveform."""
    if len(waveform) == 0:
        return {}
    abs_w = np.abs(waveform)
    peak = float(np.max(abs_w))
    mean = float(np.mean(abs_w))
    area = float(np.trapezoid(abs_w) if hasattr(np, "trapezoid") else np.trapz(abs_w)) / fs
    # Rise time: time from 10% to 90% of peak
    threshold_lo = 0.1 * peak
    threshold_hi = 0.9 * peak
    rise_idxs = np.where(abs_w > threshold_lo)[0]
    rise_time = float(len(rise_idxs)) / fs if len(rise_idxs) > 0 else 0.0
    # Peak-to-peak
    p2p = float(np.max(waveform) - np.min(waveform))
    # Zero-crossing rate
    zcr = float(np.sum(np.diff(np.sign(waveform)) != 0)) / len(waveform)
    return {
        "max_strain": peak,
        "mean_strain": mean,
        "area_under_curve": area,
        "peak_to_peak": p2p,
        "rise_time_s": rise_time,
        "zero_crossing_rate": zcr,
    }


def extract_event_features(event: VehicleEvent, df: pd.DataFrame) -> dict:
    """Full feature vector for one vehicle event."""
    # Waveform
    mask = (df.index >= event.start_time) & (df.index <= event.end_time)
    waveform = df.loc[mask, event.gauge_id].values if event.gauge_id in df.columns else np.array([])
    wf_features = extract_waveform_features(waveform)

    # Axle features
    axle_times = sorted(set(round(a.time_s, 3) for a in event.axles))
    axle_spacings = [axle_times[i+1] - axle_times[i] for i in range(len(axle_times)-1)]
    peak_mags = [abs(a.peak_strain) for a in event.axles]

    features = {
        "vehicle_id": event.vehicle_id,
        "gauge_id": event.gauge_id,
        "axle_count": event.axle_count,
        "duration_s": event.duration_s,
        "mean_axle_spacing_s": float(np.mean(axle_spacings)) if axle_spacings else 0.0,
        "std_axle_spacing_s": float(np.std(axle_spacings)) if axle_spacings else 0.0,
        "max_axle_peak": float(np.max(peak_mags)) if peak_mags else 0.0,
        "mean_axle_peak": float(np.mean(peak_mags)) if peak_mags else 0.0,
        "peak_strain_ratio": float(peak_mags[0] / peak_mags[-1]) if len(peak_mags) >= 2 else 1.0,
        "vehicle_type_estimate": event.vehicle_type_estimate,
    }
    features.update(wf_features)
    return features


def build_feature_matrix(all_events: dict[str, list[VehicleEvent]],
                          df: pd.DataFrame) -> pd.DataFrame:
    """Build feature matrix from all events across all gauges."""
    rows = []
    for gauge, events in all_events.items():
        for e in events:
            rows.append(extract_event_features(e, df))
    return pd.DataFrame(rows)


# ─── Sensor Fusion / Collective Strain Estimation ────────────────────────────

def estimate_collective_strain(
    df: pd.DataFrame,
    health_map: dict[str, GaugeHealth],
    gauge_types: dict[str, str],
    event_start: float,
    event_end: float,
) -> tuple[float, float]:
    """
    Estimate collective εt (horizontal tensile strain) and εv (vertical compressive strain)
    from all healthy gauges for a single vehicle event window.

    Returns
    -------
    epsilon_t : µε — representative horizontal tensile strain (for Nf)
    epsilon_v : µε — representative vertical compressive strain (for Nr)
    """
    mask = (df.index >= event_start) & (df.index <= event_end)
    if not mask.any():
        return 0.0, 0.0

    hor_peaks, hor_weights = [], []
    ver_peaks, ver_weights = [], []

    for gauge, gtype in gauge_types.items():
        if gauge not in df.columns:
            continue
        gh = health_map.get(gauge)
        if gh is None or gh.excluded:
            continue
        window = df.loc[mask, gauge].values
        if len(window) == 0:
            continue
        peak = float(np.max(np.abs(window)))
        w = gh.health_score

        if gtype == "horizontal_strain":
            hor_peaks.append(peak)
            hor_weights.append(w)
        elif gtype == "vertical_strain":
            ver_peaks.append(peak)
            ver_weights.append(w)

    # Weighted average
    def weighted_mean(values, weights):
        if not values:
            return 0.0
        wt = np.array(weights)
        wt = wt / (wt.sum() + 1e-9)
        return float(np.dot(wt, values))

    epsilon_t = weighted_mean(hor_peaks, hor_weights)
    epsilon_v = weighted_mean(ver_peaks, ver_weights)
    return epsilon_t, epsilon_v
