"""
Module A — Data Ingestion
Reads GEOTRAN-format .xls DAQ files (tab-separated, 12-row header).
NH-71 instrumented pavement project.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional
from src.utils.config import load_config, get_logger

log = get_logger(__name__)
CFG = load_config()


GAUGE_TYPE_MAP = {
    "VER": "vertical_strain",
    "HOR": "horizontal_strain",
    "TEMP": "temperature",
    "EPC": "epc",
}


def _detect_gauge_type(col_name: str) -> str:
    col_upper = col_name.upper()
    if "VER" in col_upper or "VERTICAL" in col_upper:
        return "vertical_strain"
    if "HOR" in col_upper or "HORIZONTAL" in col_upper:
        return "horizontal_strain"
    if "TEMP" in col_upper or "°C" in col_upper:
        return "temperature"
    if "EPC" in col_upper or "PRESSURE" in col_upper or "MPA" in col_upper:
        return "epc"
    return "unknown"


def parse_geotran(filepath: str | Path, daq_type: str = "auto") -> tuple[pd.DataFrame, dict]:
    """
    Parse a GEOTRAN .xls DAQ file.

    Parameters
    ----------
    filepath : path to .xls file
    daq_type : 'VER', 'HOR', or 'auto' (inferred from filename)

    Returns
    -------
    df       : DataFrame indexed by time (seconds), columns = gauge names
    metadata : dict with sampling_rate, daq_type, gauge_types, filepath
    """
    filepath = Path(filepath)
    log.info(f"Parsing GEOTRAN file: {filepath.name}")

    if daq_type == "auto":
        name_upper = filepath.stem.upper()
        if "VER" in name_upper:
            daq_type = "VER"
        elif "HOR" in name_upper:
            daq_type = "HOR"
        else:
            daq_type = "UNKNOWN"
            log.warning("Could not auto-detect DAQ type from filename; defaulting to UNKNOWN")

    # Infer engine from file extension (None = pandas auto-detect)
    ext = filepath.suffix.lower()
    excel_kwargs = {}
    if ext == ".xlsx":
        excel_kwargs["engine"] = "openpyxl"
    elif ext == ".xls":
        pass  # let pandas auto-detect (xlrd or calamine)

    # Try reading with header skip — GEOTRAN files have 12-row header
    try:
        raw = pd.read_excel(filepath, header=None, **excel_kwargs)
    except Exception:
        # Fallback: tab-separated text disguised as xls
        try:
            raw = pd.read_csv(filepath, sep="\t", header=None, encoding="utf-8", on_bad_lines="skip")
        except Exception:
            raw = pd.read_csv(filepath, sep=",", header=None, encoding="utf-8", on_bad_lines="skip")

    # Detect actual header row (find row where column 0 == 0 or "Time")
    header_row = 0
    for i, row in raw.iterrows():
        vals = row.dropna().astype(str).str.lower().tolist()
        if "time" in vals or (len(vals) > 1 and vals[0] in ["0", "0.0"]):
            header_row = i
            break

    # Re-read with correct header
    try:
        df = pd.read_excel(filepath, skiprows=header_row, **excel_kwargs)
    except Exception:
        try:
            df = pd.read_csv(
                filepath, sep="\t", skiprows=header_row, encoding="utf-8", on_bad_lines="skip"
            )
        except Exception:
            df = pd.read_csv(
                filepath, sep=",", skiprows=header_row, encoding="utf-8", on_bad_lines="skip"
            )

    df.columns = [str(c).strip() for c in df.columns]

    # Identify time column (first column)
    time_col = df.columns[0]
    df[time_col] = pd.to_numeric(df[time_col], errors="coerce")
    df = df.dropna(subset=[time_col])
    df = df.set_index(time_col)
    df.index.name = "time_s"

    # Convert all gauge columns to numeric
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Build metadata
    fs = CFG["daq"]["sampling_rate"]
    gauge_types = {col: _detect_gauge_type(col) for col in df.columns}

    metadata = {
        "filepath": str(filepath),
        "daq_type": daq_type,
        "n_samples": len(df),
        "n_gauges": len(df.columns),
        "sampling_rate": fs,
        "duration_s": len(df) / fs,
        "gauge_types": gauge_types,
        "gauge_names": list(df.columns),
    }

    log.info(
        f"Loaded {metadata['n_samples']} samples × {metadata['n_gauges']} gauges "
        f"({metadata['duration_s']:.1f}s @ {fs}Hz)"
    )
    return df, metadata


def load_daq_session(raw_dir: str | Path) -> dict[str, tuple[pd.DataFrame, dict]]:
    """Load all GEOTRAN files from a directory. Returns dict keyed by file stem."""
    raw_dir = Path(raw_dir)
    results = {}
    for f in sorted(raw_dir.glob("*.xls")):
        try:
            df, meta = parse_geotran(f)
            results[f.stem] = (df, meta)
        except Exception as e:
            log.error(f"Failed to load {f.name}: {e}")
    return results


def save_processed(df: pd.DataFrame, name: str, out_dir: str | Path = "data/processed") -> Path:
    """Save processed DataFrame as .parquet."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{name}.parquet"
    df.to_parquet(out_path)
    log.info(f"Saved processed data → {out_path}")
    return out_path
