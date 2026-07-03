"""
Module D — Vehicle Event Detection
Adaptive peak detection, axle grouping, vehicle event extraction.
Supports type-specific config: event_detection_ver / event_detection_hor.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from scipy import signal as sig
from src.utils.config import load_config, get_logger

log = get_logger(__name__)
CFG = load_config()
FS = CFG["daq"]["sampling_rate"]


def _get_ed_config(config_prefix: str = "event_detection_ver") -> dict:
    """Load the right event detection config block."""
    if config_prefix in CFG:
        return CFG[config_prefix]
    # fallback
    return CFG.get("event_detection_ver", {})


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
    vehicle_type_estimate: int
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
                                config_prefix: str = "event_detection_ver") -> float:
    ED = _get_ed_config(config_prefix)
    baseline_window_s = 5.0
    factor = ED["threshold_factor"]
    n_baseline = int(baseline_window_s * fs)
    baseline = data[:n_baseline]
    rms = np.sqrt(np.mean(baseline ** 2))
    return max(factor * rms, ED["min_prominence_microstrain"])


def detect_peaks(data: np.ndarray, fs: float = FS,
                 config_prefix: str = "event_detection_ver") -> tuple[np.ndarray, np.ndarray]:
    ED = _get_ed_config(config_prefix)
    threshold = compute_adaptive_threshold(data, fs, config_prefix)
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
                config_prefix: str = "event_detection_ver") -> list[list[int]]:
    ED = _get_ed_config(config_prefix)
    axle_window = ED["axle_grouping_window"]
    vehicle_window = ED["vehicle_grouping_window"]

    if len(peaks) == 0:
        return []

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

    vehicles = []
    current_vehicle = [axle_groups[0]]
    for i in range(1, len(axle_groups)):
        last_t = times[axle_groups[i - 1][-1]]
        next_t = times[axle_groups[i][0]]
        if next_t - last_t <= vehicle_window:
            current_vehicle.append(axle_groups[i])
        else:
            vehicles.append(current_vehicle)
            current_vehicle = [axle_groups[i]]
    vehicles.append(current_vehicle)

    return [[p for axle in v for p in axle] for v in vehicles]


def extract_events(gauge_data: pd.Series, gauge_id: str,
                   fs: float = FS,
                   vehicle_id_start: int = 0,
                   config_prefix: str = "event_detection_ver") -> list[VehicleEvent]:
    ED = _get_ed_config(config_prefix)
    data = gauge_data.values.astype(float)
    times = gauge_data.index.values.astype(float)

    peaks, heights = detect_peaks(data, fs, config_prefix)
    if len(peaks) == 0:
        log.debug(f"No peaks detected in gauge {gauge_id} ({config_prefix})")
        return []

    vehicle_peak_groups = group_axles(peaks, times, config_prefix)

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

        def _make_event(axle_list, offset) -> VehicleEvent | None:
            unique_times = sorted(set(round(a.time_s, 2) for a in axle_list))
            cnt = max(1, len(unique_times))
            if cnt < ED["min_axles"] or cnt > ED["max_axles"]:
                return None
            peak_vals = [a.peak_strain for a in axle_list]
            first_idx = min(a.sample_idx for a in axle_list)
            last_idx = max(a.sample_idx for a in axle_list)
            st = float(times[max(0, first_idx - int(0.1 * fs))])
            et = float(times[min(len(times) - 1, last_idx + int(0.1 * fs))])
            return VehicleEvent(
                vehicle_id=vehicle_id_start + offset,
                gauge_id=gauge_id,
                start_time=st, end_time=et,
                axle_count=cnt, axles=axle_list,
                vehicle_type_estimate=cnt,
                peak_strains=peak_vals,
                max_strain=float(np.max(np.abs(peak_vals))),
                mean_strain=float(np.mean(np.abs(peak_vals))),
                duration_s=et - st,
            )

        unique_times = sorted(set(round(a.time_s, 2) for a in axles))
        axle_count = max(1, len(unique_times))

        if axle_count < ED["min_axles"] and events:
            last = events[-1]
            last.axles.extend(axles)
            last.peak_strains = [a.peak_strain for a in last.axles]
            last.max_strain = float(np.max(np.abs(last.peak_strains)))
            last.mean_strain = float(np.mean(np.abs(last.peak_strains)))
            last.end_time = float(times[min(len(times) - 1, max(a.sample_idx for a in axles) + int(0.1 * fs))])
            last.duration_s = last.end_time - last.start_time
            unique_times = sorted(set(round(a.time_s, 2) for a in last.axles))
            last.axle_count = min(max(1, len(unique_times)), ED["max_axles"])
            last.vehicle_type_estimate = last.axle_count
            continue
        elif axle_count < ED["min_axles"]:
            continue

        if axle_count > ED["max_axles"]:
            mid = len(axles) // 2
            first = _make_event(axles[:mid], len(events))
            second = _make_event(axles[mid:], len(events) + 1)
            if first:
                events.append(first)
            if second:
                events.append(second)
        else:
            ev = _make_event(axles, len(events))
            if ev:
                events.append(ev)

    log.info(f"Gauge {gauge_id} ({config_prefix}): {len(events)} vehicle events detected")
    return events


def extract_all_events(df: pd.DataFrame,
                       healthy_gauges: list[str],
                       config_prefix: str = "event_detection_ver") -> dict[str, list[VehicleEvent]]:
    all_events = {}
    vid_counter = 0
    for gauge in healthy_gauges:
        if gauge not in df.columns:
            continue
        events = extract_events(df[gauge], gauge, vehicle_id_start=vid_counter, config_prefix=config_prefix)
        all_events[gauge] = events
        vid_counter += len(events)
    total = sum(len(v) for v in all_events.values())
    log.info(f"Total vehicle events detected ({config_prefix}): {total}")
    return all_events


def events_to_dataframe(all_events: dict[str, list[VehicleEvent]]) -> pd.DataFrame:
    rows = []
    for gauge, events in all_events.items():
        for e in events:
            rows.append(e.to_dict())
    return pd.DataFrame(rows)
