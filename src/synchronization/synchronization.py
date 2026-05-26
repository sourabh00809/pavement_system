"""
Module E — Multi-Gauge Synchronization
Cross-correlation, DTW matching, DBSCAN temporal clustering.
Links the same vehicle event across multiple gauges with time-lag correction.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from scipy import signal as sig
from src.utils.config import load_config, get_logger
from src.event_detection.event_detection import VehicleEvent

log = get_logger(__name__)
CFG = load_config()
SYNC = CFG["synchronization"]
FS = CFG["daq"]["sampling_rate"]


@dataclass
class SyncedEventBundle:
    """A single vehicle event matched across multiple gauges."""
    bundle_id: int
    representative_time: float          # centroid timestamp
    gauge_events: list[dict]            # [{gauge, start, end, peak, lag}]
    confidence: float                   # mean DTW similarity
    axle_count: int
    gauges_matched: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "bundle_id": self.bundle_id,
            "representative_time": self.representative_time,
            "confidence": round(self.confidence, 3),
            "axle_count": self.axle_count,
            "n_gauges_matched": len(self.gauge_events),
            "gauges_matched": self.gauges_matched,
            "gauge_events": self.gauge_events,
        }


def xcorr_lag(sig_a: np.ndarray, sig_b: np.ndarray, fs: float = FS) -> tuple[float, float]:
    """
    Compute cross-correlation lag between two signal windows.
    Returns (lag_seconds, normalized_correlation_peak).
    """
    n = max(len(sig_a), len(sig_b))
    # Zero-pad to equal length
    a = np.zeros(n); a[:len(sig_a)] = sig_a
    b = np.zeros(n); b[:len(sig_b)] = sig_b
    corr = sig.correlate(a - a.mean(), b - b.mean(), mode="full")
    lags = sig.correlation_lags(len(a), len(b), mode="full")
    best = int(np.argmax(np.abs(corr)))
    lag_s = lags[best] / fs
    norm = float(corr[best] / (np.std(a) * np.std(b) * n + 1e-9))
    return lag_s, norm


def _resample_for_dtw(values: np.ndarray, max_points: int = 800) -> np.ndarray:
    """Limit DTW work for long DAQ windows while preserving waveform shape."""
    values = np.asarray(values, dtype=float)
    if len(values) <= max_points:
        return values
    x_old = np.linspace(0.0, 1.0, len(values))
    x_new = np.linspace(0.0, 1.0, max_points)
    return np.interp(x_new, x_old, values)


def dtw_distance(a: np.ndarray, b: np.ndarray, max_points: int = 800) -> float:
    """
    Memory-bounded DTW distance between two sequences.
    Returns normalized distance (0 = identical, higher = more different).
    """
    a = _resample_for_dtw(a, max_points=max_points)
    b = _resample_for_dtw(b, max_points=max_points)
    n, m = len(a), len(b)
    if n == 0 or m == 0:
        return float("inf")

    prev = np.full(m + 1, np.inf)
    curr = np.full(m + 1, np.inf)
    prev[0] = 0.0
    for i in range(1, n + 1):
        curr[0] = np.inf
        for j in range(1, m + 1):
            cost = abs(float(a[i - 1]) - float(b[j - 1]))
            curr[j] = cost + min(prev[j], curr[j - 1], prev[j - 1])
        prev, curr = curr, prev
    denom = (np.std(a) + np.std(b)) * max(n, m) + 1e-9
    return float(prev[m] / denom)


def extract_window(df: pd.DataFrame, gauge: str,
                   t_start: float, t_end: float) -> np.ndarray:
    """Extract signal window for a gauge between t_start and t_end."""
    mask = (df.index >= t_start) & (df.index <= t_end)
    return df.loc[mask, gauge].values.astype(float)


def sync_event_across_gauges(primary_event: VehicleEvent,
                              df: pd.DataFrame,
                              gauges: list[str],
                              search_window: float = SYNC["search_window"],
                              dtw_threshold: float = SYNC["dtw_threshold"]) -> list[dict]:
    """
    Given a primary event, find and align the same event on all other gauges.
    Returns list of dicts: [{gauge, start, end, lag_s, xcorr, dtw_dist, peak}]
    """
    matched = []
    primary_window = extract_window(df, primary_event.gauge_id,
                                    primary_event.start_time, primary_event.end_time)
    if len(primary_window) == 0:
        return matched

    for gauge in gauges:
        if gauge == primary_event.gauge_id:
            matched.append({
                "gauge": gauge,
                "start": primary_event.start_time,
                "end": primary_event.end_time,
                "lag_s": 0.0,
                "xcorr": 1.0,
                "dtw_dist": 0.0,
                "peak": primary_event.max_strain,
                "primary": True,
            })
            continue

        # Search window around primary event
        search_start = primary_event.start_time - search_window
        search_end = primary_event.end_time + search_window
        candidate_window = extract_window(df, gauge, search_start, search_end)

        if len(candidate_window) < 5:
            continue

        lag_s, xcorr = xcorr_lag(primary_window, candidate_window)

        # Trim candidate to matched region
        aligned_start = primary_event.start_time + lag_s
        aligned_end = primary_event.end_time + lag_s
        aligned_window = extract_window(df, gauge, aligned_start, aligned_end)

        if len(aligned_window) < 5:
            continue

        # Compute DTW similarity on aligned windows
        len_min = min(len(primary_window), len(aligned_window))
        dist = dtw_distance(primary_window[:len_min], aligned_window[:len_min])

        if dist < dtw_threshold or abs(xcorr) > 0.5:
            matched.append({
                "gauge": gauge,
                "start": aligned_start,
                "end": aligned_end,
                "lag_s": lag_s,
                "xcorr": float(xcorr),
                "dtw_dist": float(dist),
                "peak": float(np.max(np.abs(aligned_window))),
                "primary": False,
            })

    return matched


def build_synced_bundles(all_events: dict[str, list[VehicleEvent]],
                          df: pd.DataFrame,
                          healthy_gauges: list[str]) -> list[SyncedEventBundle]:
    """
    Build synchronized event bundles from all gauge events.
    Uses temporal DBSCAN to cluster events from different gauges that
    correspond to the same physical vehicle passage.
    """
    # Collect all events with their timestamps
    flat_events = []
    for gauge, events in all_events.items():
        for e in events:
            flat_events.append((e.start_time, gauge, e))

    if not flat_events:
        return []

    # Sort by time
    flat_events.sort(key=lambda x: x[0])
    times = np.array([x[0] for x in flat_events])

    # Simple temporal grouping (DBSCAN equivalent)
    eps = SYNC["dbscan_eps"]
    bundles = []
    visited = set()
    bundle_id = 0

    for i, (t, gauge, event) in enumerate(flat_events):
        if i in visited:
            continue
        # Find all events within eps seconds
        cluster_idxs = [j for j, tj in enumerate(times) if abs(tj - t) <= eps]
        visited.update(cluster_idxs)

        # Only keep one event per gauge in cluster (highest peak)
        gauge_best = {}
        for j in cluster_idxs:
            _, g, ev = flat_events[j]
            if g not in gauge_best or ev.max_strain > gauge_best[g].max_strain:
                gauge_best[g] = ev

        if not gauge_best:
            continue

        # Sync the primary event across all healthy gauges
        primary_gauge = max(gauge_best, key=lambda g: gauge_best[g].max_strain)
        primary_ev = gauge_best[primary_gauge]

        gauge_matches = sync_event_across_gauges(
            primary_ev, df, list(gauge_best.keys())
        )

        if len(gauge_matches) == 0:
            continue

        confidence = float(np.mean([m["xcorr"] for m in gauge_matches]))
        axle_count = primary_ev.axle_count
        rep_time = float(np.mean([m["start"] for m in gauge_matches]))

        bundle = SyncedEventBundle(
            bundle_id=bundle_id,
            representative_time=rep_time,
            gauge_events=gauge_matches,
            confidence=confidence,
            axle_count=axle_count,
            gauges_matched=[m["gauge"] for m in gauge_matches],
        )
        bundles.append(bundle)
        bundle_id += 1

    log.info(f"Built {len(bundles)} synchronized event bundles")
    return bundles
