"""
Module D — Vehicle Event Detection
Adaptive peak detection, axle grouping, vehicle event extraction.
Parameters tuned for NH-71 highway data at 500 Hz.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from scipy import signal as sig
from src.utils.config import load_config, get_logger

log = get_logger(__name__)
CFG = load_config()
ED = CFG["event_detection"]
FS = CFG["daq"]["sampling_rate"]


@dataclass
class AxleEvent:
    time_s: float
    peak_strain: float
    sample_idx: int


@dataclass
class VehicleEvent:
    vehicle_id: int
    gauge_id: str
    start_time: float
    end_time: float
    axle_count: int
    axles: list[AxleEvent]
    vehicle_type_estimate: int   # number of axles → IRC class
    peak_strains: list[float] = field(default_factory=list)
    max_strain: float = 0.0
    mean_strain: float = 0.0
    duration_s: float = 0.0

    def to_dict(self) -> dict:
        return {
            "vehicle_id": self.vehicle_id,
            "gauge_id": self.gauge_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_s": self.duration_s,
            "axle_count": self.axle_count,
            "vehicle_type_estimate": self.vehicle_type_estimate,
            "max_strain": self.max_strain,
            "mean_strain": self.mean_strain,
            "peak_strains": self.peak_strains,
        }


def compute_adaptive_threshold(data: np.ndarray, fs: float = FS,
                                baseline_window_s: float = 5.0,
                                factor: float = ED["threshold_factor"]) -> float:
    """
    Compute adaptive detection threshold = factor × RMS of quiet baseline window.
    Uses start of signal as baseline (assumed vehicle-free).
    """
    n_baseline = int(baseline_window_s * fs)
    baseline = data[:n_baseline]
    rms = np.sqrt(np.mean(baseline ** 2))
    return max(factor * rms, ED["min_prominence_microstrain"])


def detect_peaks(data: np.ndarray, fs: float = FS) -> tuple[np.ndarray, np.ndarray]:
    """
    Detect strain peaks in preprocessed gauge signal.
    Returns (peak_indices, peak_heights).
    """
    threshold = compute_adaptive_threshold(data, fs)
    distance = ED["min_peak_distance_samples"]
    prominence = ED["min_prominence_microstrain"]

    peaks, props = sig.find_peaks(
        np.abs(data),
        height=threshold,
        distance=distance,
        prominence=prominence,
    )
    heights = np.abs(data[peaks])
    return peaks, heights


def group_axles(peaks: np.ndarray, times: np.ndarray,
                axle_window: float = ED["axle_grouping_window"],
                vehicle_window: float = ED["vehicle_grouping_window"]) -> list[list[int]]:
    """
    Group detected peaks into vehicle events.
    1. Peaks within axle_window → same axle cluster
    2. Clusters within vehicle_window → same vehicle
    Returns list of peak index lists, one list per vehicle.
    """
    if len(peaks) == 0:
        return []

    # Step 1: merge closely spaced peaks into axle clusters
    axle_groups = []
    current = [peaks[0]]
    for i in range(1, len(peaks)):
        dt = times[peaks[i]] - times[peaks[i - 1]]
        if dt <= axle_window:
            current.append(peaks[i])
        else:
            axle_groups.append(current)
            current = [peaks[i]]
    axle_groups.append(current)

    # Step 2: merge axle clusters into vehicles
    vehicles = []
    current_vehicle = [axle_groups[0]]
    for i in range(1, len(axle_groups)):
        # Time between last peak of previous cluster and first of current
        last_t = times[axle_groups[i - 1][-1]]
        next_t = times[axle_groups[i][0]]
        if next_t - last_t <= vehicle_window:
            current_vehicle.append(axle_groups[i])
        else:
            vehicles.append(current_vehicle)
            current_vehicle = [axle_groups[i]]
    vehicles.append(current_vehicle)

    # Flatten: vehicle → flat list of peak indices
    return [[p for axle in v for p in axle] for v in vehicles]


def extract_events(gauge_data: pd.Series, gauge_id: str,
                   fs: float = FS,
                   vehicle_id_start: int = 0) -> list[VehicleEvent]:
    """
    Full event extraction pipeline for one gauge.
    Returns list of VehicleEvent objects.
    """
    data = gauge_data.values.astype(float)
    times = gauge_data.index.values.astype(float)

    peaks, heights = detect_peaks(data, fs)
    if len(peaks) == 0:
        log.debug(f"No peaks detected in gauge {gauge_id}")
        return []

    vehicle_peak_groups = group_axles(peaks, times)

    events = []
    for vid_offset, peak_group in enumerate(vehicle_peak_groups):
        if not peak_group:
            continue

        axles = [
            AxleEvent(
                time_s=float(times[p]),
                peak_strain=float(data[p]),
                sample_idx=int(p),
            )
            for p in peak_group
        ]
        # Estimate axle count (unique axle times within spacing)
        unique_times = sorted(set(round(a.time_s, 2) for a in axles))
        axle_count = max(1, len(unique_times))
        axle_count = min(axle_count, ED["max_axles"])

        if axle_count < ED["min_axles"]:
            continue

        peak_strains = [a.peak_strain for a in axles]
        start_t = float(times[max(0, peak_group[0] - int(0.1 * fs))])
        end_t = float(times[min(len(times) - 1, peak_group[-1] + int(0.1 * fs))])

        event = VehicleEvent(
            vehicle_id=vehicle_id_start + vid_offset,
            gauge_id=gauge_id,
            start_time=start_t,
            end_time=end_t,
            axle_count=axle_count,
            axles=axles,
            vehicle_type_estimate=axle_count,
            peak_strains=peak_strains,
            max_strain=float(np.max(np.abs(peak_strains))),
            mean_strain=float(np.mean(np.abs(peak_strains))),
            duration_s=end_t - start_t,
        )
        events.append(event)

    log.info(f"Gauge {gauge_id}: {len(events)} vehicle events detected")
    return events


def extract_all_events(df: pd.DataFrame,
                       healthy_gauges: list[str]) -> dict[str, list[VehicleEvent]]:
    """Extract events from all healthy gauges."""
    all_events = {}
    vid_counter = 0
    for gauge in healthy_gauges:
        if gauge not in df.columns:
            continue
        events = extract_events(df[gauge], gauge, vehicle_id_start=vid_counter)
        all_events[gauge] = events
        vid_counter += len(events)
    total = sum(len(v) for v in all_events.values())
    log.info(f"Total vehicle events detected across {len(healthy_gauges)} gauges: {total}")
    return all_events


def events_to_dataframe(all_events: dict[str, list[VehicleEvent]]) -> pd.DataFrame:
    """Convert all events to a flat DataFrame for storage/analysis."""
    rows = []
    for gauge, events in all_events.items():
        for e in events:
            rows.append(e.to_dict())
    return pd.DataFrame(rows)
