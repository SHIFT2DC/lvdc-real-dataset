"""
io_config.py

Purpose
-------
This module is the single entry point to read the dataset configuration and load CSV files
in a consistent way across all validation and overview scripts.

Why this exists
---------------
During paper reviews it is common to regenerate figures and tables several times (font sizes,
axis labels, thresholds, window lengths, etc.). To keep the pipeline reproducible, we avoid
hardcoded paths and column names inside each script. Instead, scripts read a YAML file
(configs/datasets.yaml) and use the same loader and validators.

What this module provides
-------------------------
1) Load the configuration for a given dataset_id (A, B, or C).
2) Validate that the CSV exists and contains the expected columns.
3) Load the CSV with parsed timestamps, sorted time, and basic cleaning of invalid timestamps.

Typical usage
-------------
from scripts.common.io_config import (
    load_dataset_config,
    validate_csv_structure,
    load_csv,
)

cfg = load_dataset_config("A")
validate_csv_structure(cfg)        # fails early with a clear error if something is wrong
df = load_csv(cfg)                 # returns a pandas DataFrame with parsed timestamps
"""

from __future__ import annotations

import os
from typing import Dict, Any, List, Optional
import pandas as pd
import yaml
import json
import subprocess
from datetime import datetime, timezone


def load_dataset_config(dataset_id: str, config_path: str = "configs/datasets.yaml") -> Dict[str, Any]:
    """
    Load the YAML configuration and return the dictionary for one dataset.

    Parameters
    ----------
    dataset_id:
        Dataset identifier, expected values are "A", "B", or "C".
    config_path:
        Path to the YAML configuration file.

    Returns
    -------
    dataset_config:
        Dictionary with keys such as:
        - csv_path
        - time_col
        - time_format
        - vbus_col
        - columns (optional list of expected columns)

    Notes
    -----
    This function does not read the CSV. It only loads and checks the configuration.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if not isinstance(config, dict) or "datasets" not in config:
        raise ValueError(f"Invalid YAML structure in {config_path}. Expected top-level key 'datasets'.")

    datasets = config.get("datasets", {})
    if dataset_id not in datasets:
        available = sorted(list(datasets.keys()))
        raise ValueError(f"Dataset '{dataset_id}' not found in {config_path}. Available datasets: {available}")

    dataset_config = datasets[dataset_id]

    # Minimal required keys for all datasets
    required_keys = ["csv_path", "time_col", "time_format", "vbus_col"]
    missing_keys = [k for k in required_keys if k not in dataset_config]
    if missing_keys:
        raise ValueError(
            f"Dataset '{dataset_id}' in {config_path} is missing required keys: {missing_keys}"
        )

    return dataset_config


def read_csv_header(csv_path: str) -> List[str]:
    """
    Read only the CSV header (column names). This is fast and used for validation.

    Parameters
    ----------
    csv_path:
        Path to the CSV file.

    Returns
    -------
    columns:
        List of column names as stored in the CSV file.
    """
    df_header = pd.read_csv(csv_path, nrows=0)
    return list(df_header.columns)


def validate_csv_structure(dataset_config: Dict[str, Any]) -> None:
    """
    Validate that the CSV exists and contains the required columns.

    Validation rules
    ----------------
    - The CSV file must exist.
    - time_col must exist.
    - vbus_col must exist.
    - If 'columns' is provided in the YAML, all listed columns must exist as well.

    Parameters
    ----------
    dataset_config:
        Configuration dictionary for one dataset (output of load_dataset_config).

    Raises
    ------
    FileNotFoundError:
        If the CSV file does not exist.
    ValueError:
        If one or more required columns are missing.
    """
    csv_path = dataset_config["csv_path"]
    time_col = dataset_config["time_col"]
    vbus_col = dataset_config["vbus_col"]

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    csv_columns = set(read_csv_header(csv_path))

    required = {time_col, vbus_col}

    # Optional: full column list
    expected_columns = dataset_config.get("columns", None)
    if expected_columns is not None:
        if not isinstance(expected_columns, list):
            raise ValueError("Invalid type for 'columns' in YAML. Expected a list of strings.")
        required.update(expected_columns)

    missing = sorted(list(required - csv_columns))
    if missing:
        raise ValueError(
            f"CSV structure validation failed for {csv_path}. Missing columns: {missing}"
        )


def load_csv(
    dataset_config: Dict[str, Any],
    usecols: Optional[List[str]] = None,
    drop_invalid_timestamps: bool = True,
) -> pd.DataFrame:
    """
    Load a CSV file, parse the timestamp column, and sort by time.

    Parameters
    ----------
    dataset_config:
        Configuration dictionary for one dataset (output of load_dataset_config).
    usecols:
        Optional list of column names to load. If None, load all columns.
        This is useful for faster scripts (e.g., only load Time and Vbus for dV/dt).
    drop_invalid_timestamps:
        If True, rows with unparseable timestamps are removed.

    Returns
    -------
    df:
        Pandas DataFrame with:
        - timestamp column parsed as datetime
        - rows sorted by time
        - index reset to 0..N-1

    Notes
    -----
    This loader does not resample or filter the data.
    It preserves the raw sampling behavior (including jitter) as provided.
    """
    csv_path = dataset_config["csv_path"]
    time_col = dataset_config["time_col"]
    time_format = dataset_config["time_format"]

    if usecols is not None and time_col not in usecols:
        usecols = [time_col] + list(usecols)

    df = pd.read_csv(csv_path, usecols=usecols)

    df[time_col] = pd.to_datetime(df[time_col], format=time_format, errors="coerce")

    if drop_invalid_timestamps:
        df = df.dropna(subset=[time_col])

    df = df.sort_values(time_col).reset_index(drop=True)
    return df
def ensure_dir(path: str) -> None:
    """Create a directory if it does not exist."""
    os.makedirs(path, exist_ok=True)


def write_json(path: str, obj: Dict[str, Any]) -> None:
    """Write a JSON file with stable formatting for reproducibility."""
    ensure_dir(os.path.dirname(path) or ".")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)


def _git_short_sha(default: str = "nogit") -> str:
    """Return the current git short SHA (if available)."""
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL)
        return out.decode("utf-8").strip()
    except Exception:
        return default


def make_run_id() -> str:
    """
    Build a reproducible run identifier.

    Format:
      YYYY-MM-DD_HHMMZ_<gitsha>

    Example:
      2026-02-16_2015Z_d734ec
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%MZ")
    sha = _git_short_sha()
    return f"{ts}_{sha}"