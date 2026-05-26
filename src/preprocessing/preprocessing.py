"""
Module B — Signal Preprocessing
Corrected bandpass filter (0.5–30 Hz), baseline correction, normalization.
Critical fix: replaces erroneous 0.1 Hz cutoff from mid-term pipeline.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import signal
from src.utils.config import load_config, get_logger

log = get_logger(__name__)
CFG = load_config()
FILT = CFG["filtering"]
FS = CFG["daq"]["sampling_rate"]


def butter_bandpass(data: np.ndarray, fs: float = FS,
                    lowcut: float = FILT["bandpass_low"],
                    highcut: float = FILT["bandpass_high"],
                    order: int = FILT["bandpass_order"]) -> np.ndarray:
    """
    4th-order zero-phase Butterworth bandpass filter.
    CRITICAL: Default 0.5–30 Hz captures highway axle events (12–25 Hz dominant).
    Previous 0.1 Hz cutoff removed all vehicle signals — now corrected.
    """
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = min(highcut / nyq, 0.99)
    b, a = signal.butter(order, [low, high], btype="bandpass")
    return signal.filtfilt(b, a, data)


def butter_highpass(data: np.ndarray, fs: float = FS,
                    cutoff: float = FILT["drift_cutoff"],
                    order: int = 3) -> np.ndarray:
    """High-pass filter for drift/DC removal only."""
    nyq = 0.5 * fs
    b, a = signal.butter(order, cutoff / nyq, btype="high")
    return signal.filtfilt(b, a, data)


def butter_lowpass(data: np.ndarray, fs: float = FS,
                   cutoff: float = FILT["temp_cutoff"],
                   order: int = 3) -> np.ndarray:
    """Low-pass filter for temperature channels (slow variation)."""
    nyq = 0.5 * fs
    b, a = signal.butter(order, cutoff / nyq, btype="low")
    return signal.filtfilt(b, a, data)


def baseline_correct(data: np.ndarray, fs: float = FS,
                     threshold_factor: float = 2.0,
                     poly_order: int = 3) -> np.ndarray:
    """
    Polynomial baseline correction.
    1. Find quiet windows (no strain events) using rolling RMS.
    2. Fit polynomial baseline through quiet-window means.
    3. Subtract baseline from full signal.
    """
    n = len(data)
    window = int(fs * 1.0)  # 1-second rolling window
    rms = np.array([
        np.sqrt(np.mean(data[max(0, i - window):i + window] ** 2))
        for i in range(0, n, window)
    ])
    rms_global = np.median(rms)
    quiet_mask_coarse = rms < threshold_factor * rms_global

    # X-coordinates for quiet windows
    x_all = np.arange(n)
    x_quiet = np.array([
        i * window + window // 2
        for i, q in enumerate(quiet_mask_coarse) if q and i * window < n
    ])
    if len(x_quiet) < poly_order + 1:
        # Fallback: subtract global mean
        return data - np.mean(data)

    y_quiet = np.array([
        np.mean(data[x:min(x + window, n)])
        for x in x_quiet
    ])
    coeffs = np.polyfit(x_quiet, y_quiet, poly_order)
    baseline = np.polyval(coeffs, x_all)
    return data - baseline


def normalize_zero_mean(data: np.ndarray, quiet_window_s: float = 30.0,
                        fs: float = FS) -> np.ndarray:
    """Zero-mean normalization using quiet baseline window at start of signal."""
    quiet_samples = int(quiet_window_s * fs)
    offset = np.mean(data[:quiet_samples])
    return data - offset


def preprocess_gauge(series: np.ndarray, gauge_type: str,
                     fs: float = FS) -> np.ndarray:
    """
    Full preprocessing pipeline for a single gauge based on its type.
    gauge_type: 'vertical_strain' | 'horizontal_strain' | 'temperature' | 'epc'
    """
    if gauge_type == "temperature":
        return butter_lowpass(series, fs)

    # Strain gauges and EPC
    corrected = baseline_correct(series, fs)
    filtered = butter_bandpass(corrected, fs)
    return filtered


def preprocess_dataframe(df: pd.DataFrame, gauge_types: dict[str, str],
                         fs: float = FS) -> pd.DataFrame:
    """
    Apply preprocessing to all gauges in a DataFrame.
    Returns a new DataFrame with processed signals, same shape.
    """
    processed = {}
    for col in df.columns:
        gtype = gauge_types.get(col, "vertical_strain")
        data = df[col].values.astype(float)
        # Replace NaN with interpolation
        mask = np.isnan(data)
        if mask.any():
            data[mask] = np.interp(np.where(mask)[0], np.where(~mask)[0], data[~mask])
        processed[col] = preprocess_gauge(data, gtype, fs)
        log.debug(f"Preprocessed {col} ({gtype})")

    result = pd.DataFrame(processed, index=df.index)
    log.info(f"Preprocessing complete: {len(result.columns)} gauges")
    return result
