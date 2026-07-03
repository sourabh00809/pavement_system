"""
Module A — Data Ingestion
Reads GEOTRAN-format .xls DAQ files (tab-separated, variable header rows).
Supports joining multiple same-type files by timestamp.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional
from src.utils.config import load_config, get_logger

log = get_logger(__name__)
CFG = load_config()


def _detect_gauge_type(col_name: str) -> str:
    col_upper = col_name.upper()
    if "VER" in col_upper or "VERTICAL" in col_upper:
        return "vertical_strain"
    if "HOR" in col_upper or "HORIZONTAL" in col_upper:
        return "horizontal_strain"
    if "TEMP" in col_upper or "°C" in col_upper or "TEMPERATURE" in col_upper:
        return "temperature"
    if "EPC" in col_upper or "PRESSURE" in col_upper or "MPA" in col_upper:
        return "epc"
    return "unknown"


def _find_header_row(raw: pd.DataFrame) -> int:
    """Scan first 15 rows for the actual header (contains 'time' or numeric first column)."""
    for i, row in raw.iterrows():
        if i > 15:
            break
        vals = row.dropna().astype(str).str.lower().tolist()
        if not vals:
            continue
        first_val = vals[0].strip()
        if "time" in first_val or "timestamp" in first_val:
            return i
        try:
            float(first_val)
            return i
        except ValueError:
            continue
    return 0


def parse_geotran(filepath: str | Path) -> tuple[pd.DataFrame, dict]:
    """
    Parse a GEOTRAN .xls DAQ file.

    Returns
    -------
    df       : DataFrame indexed by time (seconds), columns = gauge names
    metadata : dict with sampling_rate, daq_type, gauge_types, filepath
    """
    filepath = Path(filepath)
    log.info(f"Parsing GEOTRAN file: {filepath.name}")

    ext = filepath.suffix.lower()
    excel_kwargs = {}
    if ext == ".xlsx":
        excel_kwargs["engine"] = "openpyxl"

    try:
        raw = pd.read_excel(filepath, header=None, **excel_kwargs)
    except Exception:
        try:
            raw = pd.read_csv(filepath, sep="\t", header=None, encoding="utf-8", on_bad_lines="skip")
        except Exception:
            raw = pd.read_csv(filepath, sep=",", header=None, encoding="utf-8", on_bad_lines="skip")

    header_row = _find_header_row(raw)

    try:
        df = pd.read_excel(filepath, skiprows=header_row, **excel_kwargs)
    except Exception:
        try:
            df = pd.read_csv(filepath, sep="\t", skiprows=header_row, encoding="utf-8", on_bad_lines="skip")
        except Exception:
            df = pd.read_csv(filepath, sep=",", skiprows=header_row, encoding="utf-8", on_bad_lines="skip")

    df.columns = [str(c).strip() for c in df.columns]

    time_col = df.columns[0]
    df[time_col] = pd.to_numeric(df[time_col], errors="coerce")
    df = df.dropna(subset=[time_col])
    df = df.set_index(time_col)
    df.index.name = "time_s"

    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    fs = CFG["daq"]["sampling_rate"]
    gauge_types = {col: _detect_gauge_type(col) for col in df.columns}

    metadata = {
        "filepath": str(filepath),
        "n_samples": len(df),
        "n_gauges": len(df.columns),
        "sampling_rate": fs,
        "duration_s": len(df) / fs if fs > 0 else 0.0,
        "gauge_types": gauge_types,
        "gauge_names": list(df.columns),
    }

    log.info(
        f"Loaded {metadata['n_samples']} samples × {metadata['n_gauges']} gauges "
        f"({metadata['duration_s']:.1f}s @ {fs}Hz)"
    )
    return df, metadata


def join_same_type_files(file_list: list[str | Path]) -> tuple[pd.DataFrame, dict]:
    """
    Parse multiple files of the same DAQ type and join them by timestamp.

    Reindexes all files to a common time axis (union of all timestamps)
    and concatenates gauge columns side-by-side.
    """
    if not file_list:
        raise ValueError("No files provided")

    parsed = []
    all_times = []
    for fp in file_list:
        df, meta = parse_geotran(fp)
        parsed.append(df)
        all_times.append(df.index)

    common_time = np.sort(np.unique(np.concatenate([t.values for t in all_times])))
    common_time = common_time[~np.isnan(common_time)]

    if len(common_time) == 0:
        raise ValueError("No valid timestamps across files")

    joined = pd.DataFrame(index=common_time)
    joined.index.name = "time_s"

    for i, df in enumerate(parsed):
        # Reindex to common time grid, forward-fill small gaps
        reindexed = df.reindex(common_time, method="nearest", tolerance=0.01)
        joined = pd.concat([joined, reindexed], axis=1)

    joined.index = joined.index.astype(float)
    joined = joined.dropna(how="all", axis=1)

    fs = CFG["daq"]["sampling_rate"]
    gauge_types = {}
    for col in joined.columns:
        gtype = "unknown"
        for df in parsed:
            if col in df.columns:
                gtype = "horizontal_strain"  # reasonable default for joined file
                break
        gauge_types[col] = _detect_gauge_type(col) if gtype == "unknown" else gtype

    metadata = {
        "filepaths": [str(p) for p in file_list],
        "n_samples": len(joined),
        "n_gauges": len(joined.columns),
        "sampling_rate": fs,
        "duration_s": len(joined) / fs if fs > 0 else 0.0,
        "gauge_types": gauge_types,
        "gauge_names": list(joined.columns),
    }

    durations = ", ".join(f"{Path(f).stem}: {len(df)/fs:.0f}s" for f, df in zip(file_list, parsed))
    log.info(f"Joined {len(file_list)} files -> {len(joined)} samples × {len(joined.columns)} gauges ({durations})")
    return joined, metadata


def load_daq_session(raw_dir: str | Path) -> dict[str, tuple[pd.DataFrame, dict]]:
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
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{name}.parquet"
    df.to_parquet(out_path)
    log.info(f"Saved processed data -> {out_path}")
    return out_path
