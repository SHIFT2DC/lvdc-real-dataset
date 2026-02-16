#!/usr/bin/env python3
"""
01_sanity_checks.py

Purpose
-------
Basic sanity checks focused on data integrity and consistency. The goal is to produce
objective, reproducible evidence for the Technical Validation section of a Scientific Data
Data Descriptor. This script does not evaluate any ML model and does not modify the data.

How to run
----------
Always run this script as a module from the root of the repository.

Dataset A:
python3 -m scripts.validation.01_sanity_checks --dataset-id A --timestamp-drop-invalid

Dataset B:
python3 -m scripts.validation.01_sanity_checks --dataset-id B --timestamp-drop-invalid

Dataset C:
python3 -m scripts.validation.01_sanity_checks --dataset-id C --timestamp-drop-invalid

This ensures that the "scripts" package is correctly resolved by Python.

Outputs are created under:
out/<dataset_id>/<run_id>/

What it checks
--------------
1) CSV structure and presence of expected columns (via io_config.py).
2) Timestamp parsing:
   - invalid timestamps count
   - duplicate timestamps count
   - non-monotonic steps count
   - start and end time
3) Missing values per column (count and percentage).
4) Basic stats of the main LVDC bus voltage:
   - min, max, mean, std

Outputs
-------
out/<dataset_id>/<run_id>/sanity/stats/
  sanity_summary.csv
  missingness.csv
  timestamp_checks.json
out/<dataset_id>/<run_id>/sanity/
  params.json

Notes
-----
- No resampling, filtering, or interpolation is applied.
- If the CSV contains non-standard rows (e.g., event markers with fewer columns),
  they are skipped when reading the CSV (on_bad_lines="skip").
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any

import pandas as pd

# Import shared I/O helpers:
# - load_dataset_config: reads dataset-specific settings (A/B/C)
# - validate_csv_structure: checks CSV existence and required columns
from scripts.common.io_config import load_dataset_config, validate_csv_structure


def utc_timestamp_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%MZ")


def short_hash_from_params(params: Dict[str, Any], length: int = 6) -> str:
    payload = json.dumps(params, sort_keys=True).encode("utf-8")
    h = hashlib.sha1(payload).hexdigest()
    return h[:length]


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def save_params_json(params: Dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(params, f, indent=2, sort_keys=True)


def read_csv_safe(csv_path: str, encoding: str) -> pd.DataFrame:
    """
    Read CSV robustly. If there are malformed rows with a different number of columns,
    they are skipped (useful for Dataset C examples with event markers).
    """
    return pd.read_csv(
        csv_path,
        encoding=encoding,
        on_bad_lines="skip",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sanity checks for LVDC datasets (Scientific Data validation pipeline)."
    )
    parser.add_argument(
        "--dataset-id",
        required=True,
        choices=["A", "B", "C"],
        help="Dataset identifier as defined in configs/datasets.yaml.",
    )
    parser.add_argument(
        "--config",
        default="configs/datasets.yaml",
        help="Path to datasets.yaml.",
    )
    parser.add_argument(
        "--out-root",
        default="out",
        help="Root output directory. Default: out/",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional run_id. If not provided, it will be generated.",
    )
    parser.add_argument(
        "--timestamp-drop-invalid",
        action="store_true",
        help="If set, rows with invalid timestamps will be dropped for time integrity checks.",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="CSV file encoding. Default: utf-8.",
    )

    args = parser.parse_args()

    cfg = load_dataset_config(args.dataset_id, config_path=args.config)
    validate_csv_structure(cfg)

    csv_path = cfg["csv_path"]
    time_col = cfg["time_col"]
    time_format = cfg["time_format"]
    vbus_col = cfg["vbus_col"]

    params = {
        "dataset_id": args.dataset_id,
        "config_path": args.config,
        "csv_path": csv_path,
        "time_col": time_col,
        "time_format": time_format,
        "vbus_col": vbus_col,
        "timestamp_drop_invalid": bool(args.timestamp_drop_invalid),
        "encoding": args.encoding,
    }

    if args.run_id is None:
        rid = utc_timestamp_compact() + "_" + short_hash_from_params(params, length=6)
    else:
        rid = args.run_id
    # Add run metadata for traceability (consistent with other validation stages)
    params["run_id"] = rid
    params["created_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    params["stage"] = "sanity"

    out_dir = os.path.join(args.out_root, args.dataset_id, rid)
    #stats_dir = os.path.join(out_dir, "stats")
    stats_dir = os.path.join(out_dir, "sanity", "stats")
    ensure_dir(stats_dir)

    save_params_json(params, os.path.join(out_dir, "sanity", "params.json"))

    df = read_csv_safe(csv_path, encoding=args.encoding)
    n_rows_raw = int(df.shape[0])

    # Timestamp parsing
    ts = pd.to_datetime(df[time_col], format=time_format, errors="coerce")
    invalid_ts_count = int(ts.isna().sum())

    df[time_col] = ts

    if args.timestamp_drop_invalid:
        df = df.dropna(subset=[time_col]).reset_index(drop=True)

    n_rows_used = int(df.shape[0])

    # Missingness per column
    missing_counts = df.isna().sum()
    missing_pct = (missing_counts / max(n_rows_used, 1)) * 100.0

    missingness_df = pd.DataFrame(
        {
            "column": missing_counts.index,
            "missing_count": missing_counts.values.astype(int),
            "missing_pct": missing_pct.values,
        }
    ).sort_values("missing_pct", ascending=False)

    missingness_df.to_csv(os.path.join(stats_dir, "missingness.csv"), index=False)

    # Time integrity checks
    timestamp_checks: Dict[str, Any] = {
        "n_rows_raw": n_rows_raw,
        "n_rows_used": n_rows_used,
        "invalid_timestamp_rows": invalid_ts_count,
        "timestamp_drop_invalid": bool(args.timestamp_drop_invalid),
    }

    if n_rows_used > 0 and df[time_col].notna().all():
        dup_ts_count = int(df[time_col].duplicated().sum())
        diffs = df[time_col].diff()
        non_monotonic_count = int((diffs < pd.Timedelta(0)).sum())

        t_start = df[time_col].iloc[0]
        t_end = df[time_col].iloc[-1]

        timestamp_checks.update(
            {
                "t_start": t_start.isoformat(),
                "t_end": t_end.isoformat(),
                "duplicate_timestamps": dup_ts_count,
                "non_monotonic_steps": non_monotonic_count,
            }
        )
    else:
        timestamp_checks.update(
            {
                "t_start": None,
                "t_end": None,
                "duplicate_timestamps": None,
                "non_monotonic_steps": None,
            }
        )

    with open(os.path.join(stats_dir, "timestamp_checks.json"), "w", encoding="utf-8") as f:
        json.dump(timestamp_checks, f, indent=2, sort_keys=True)

    # ---------------------------------------------------------------------
    # Repetition checks (values repeated across samples)
    # These are not necessarily errors in industrial logs, but we quantify them.
    # ---------------------------------------------------------------------

    # Duplicate timestamps (already computed above if timestamps are valid)
    dup_timestamps_count = timestamp_checks.get("duplicate_timestamps")
    if dup_timestamps_count is None:
        dup_timestamps_count = int(df[time_col].duplicated().sum())

    # Exact duplicate rows excluding the timestamp column
    value_cols = [c for c in df.columns if c != time_col]
    if len(value_cols) > 0:
        dup_value_rows_excl_time_count = int(df.duplicated(subset=value_cols).sum())
        dup_value_rows_excl_time_pct = (dup_value_rows_excl_time_count / max(n_rows_used, 1)) * 100.0
    else:
        dup_value_rows_excl_time_count = 0
        dup_value_rows_excl_time_pct = 0.0

    # Consecutive repeats for key signals
    # Always include the LVDC bus voltage column configured in the YAML.
    repetition_signals = []
    if vbus_col in df.columns:
        repetition_signals.append(vbus_col)

    # Add a few common fields for Dataset C when available (safe for A/B too)
    for extra in ["poweroutput", "upstreamcurrent"]:
        if extra in df.columns and extra not in repetition_signals:
            repetition_signals.append(extra)

    consecutive_equal_counts = {}
    consecutive_equal_pcts = {}
    for sig in repetition_signals:
        s = pd.to_numeric(df[sig], errors="coerce")
        # Compare consecutive samples; NaN diffs are ignored
        eq = (s.diff() == 0)
        count = int(eq.sum(skipna=True))
        consecutive_equal_counts[sig] = count
        consecutive_equal_pcts[sig] = (count / max(n_rows_used - 1, 1)) * 100.0

    # Basic stats for Vbus
    vbus_stats: Dict[str, Any] = {}
    if vbus_col in df.columns:
        vbus_series = pd.to_numeric(df[vbus_col], errors="coerce")
        vbus_valid = vbus_series.dropna()
        if len(vbus_valid) > 0:
            vbus_stats = {
                "vbus_min": float(vbus_valid.min()),
                "vbus_max": float(vbus_valid.max()),
                "vbus_mean": float(vbus_valid.mean()),
                "vbus_std": float(vbus_valid.std(ddof=1)),
            }
        else:
            vbus_stats = {"vbus_min": None, "vbus_max": None, "vbus_mean": None, "vbus_std": None}

    summary = {
        "dataset_id": args.dataset_id,
        "csv_path": csv_path,
        "n_rows_raw": n_rows_raw,
        "n_rows_used": n_rows_used,
        "invalid_timestamp_rows": invalid_ts_count,
        "timestamp_drop_invalid": bool(args.timestamp_drop_invalid),
        "dup_timestamps_count": int(dup_timestamps_count),
        "dup_value_rows_excl_time_count": int(dup_value_rows_excl_time_count),
        "dup_value_rows_excl_time_pct": float(dup_value_rows_excl_time_pct),
    }
    summary.update(vbus_stats)

    # Add consecutive repeat metrics using stable column names in the summary
    # We normalize keys to keep filenames and CSV headers simple.
    for sig in repetition_signals:
        key = sig.lower().replace(" ", "_").replace(".", "_")
        summary[f"consecutive_equal_{key}_count"] = int(consecutive_equal_counts[sig])
        summary[f"consecutive_equal_{key}_pct"] = float(consecutive_equal_pcts[sig])

    pd.DataFrame([summary]).to_csv(os.path.join(stats_dir, "sanity_summary.csv"), index=False)

    print(f"Sanity checks completed for dataset {args.dataset_id}")
    print(f"Output directory: {out_dir}")
    print(f"Stats written to: {stats_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())