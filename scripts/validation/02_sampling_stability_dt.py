#!/usr/bin/env python3
"""
02_sampling_stability_dt.py

Purpose
-------
Quantify sampling stability using inter-sample time differences (Delta t).
This script focuses on timestamp quality and sampling behaviour, not on
signal processing or model performance.

Rationale
---------
The raw CSV files are published "as provided" without resampling. To justify
this choice, we report statistics of Delta t (in seconds) and identify any
systematic patterns (e.g., duplicated timestamps or gaps).

How to run
----------
From the root of the repository:

python3 -m scripts.validation.02_sampling_stability_dt --dataset-id A
python3 -m scripts.validation.02_sampling_stability_dt --dataset-id B
python3 -m scripts.validation.02_sampling_stability_dt --dataset-id C

Optional parameters:
--out-root out
--expected-dt 1.0
--tol-ms 5
--max-gap-s 2.0

Outputs
-------
out/<dataset_id>/<run_id>/sampling_dt/stats/
  dt_summary.csv
  dt_summary.json
  dt_series.csv

out/<dataset_id>/<run_id>/sampling_dt/
  params.json

Notes
-----
- The script does not modify the original dataset.
- Delta t is computed after timestamp parsing.
- Duplicated timestamps appear as dt == 0.

Files:
- dt_series.csv
  Per-sample Delta t series (seconds) with basic flags.

- dt_summary.csv
  One-line summary with descriptive statistics and anomaly counts.

- dt_summary.json
  Same as dt_summary.csv, stored as JSON for programmatic use.

Notes
-----
- The script does not remove or alter samples. It only characterizes sampling.
- For datasets with duplicated timestamps (Delta t == 0), results are reported
  explicitly rather than corrected.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

# Import shared I/O helpers:
# - load_dataset_config: reads dataset-specific settings (A/B/C)
# - validate_csv_structure: checks CSV existence and required columns
# - load_csv: loads CSV with consistent parsing
# - make_run_id: generates reproducible run identifier
# - ensure_dir: creates output directories
# - write_json: writes structured JSON outputs

from scripts.common.io_config import (
    load_dataset_config,
    validate_csv_structure,
    load_csv,
    make_run_id,
    ensure_dir,
    write_json,
)

@dataclass
class DtSummary:
    dataset_id: str
    csv_path: str
    n_rows_used: int

    dt_count: int
    dt_mean_s: float
    dt_std_s: float
    dt_min_s: float
    dt_p01_s: float
    dt_p05_s: float
    dt_p50_s: float
    dt_p95_s: float
    dt_p99_s: float
    dt_max_s: float

    expected_dt_s: float
    tol_ms: int
    within_tol_count: int
    within_tol_pct: float

    dt_zero_count: int
    dt_negative_count: int
    dt_large_gap_count: int
    max_gap_s: float
    dt_large_gap_max_s: float


def _percentile(x: np.ndarray, q: float) -> float:
    if x.size == 0:
        return float("nan")
    return float(np.nanpercentile(x, q))


def main() -> int:
    p = argparse.ArgumentParser(description="Compute sampling stability statistics based on Delta t.")
    p.add_argument("--dataset-id", required=True, help="Dataset identifier as defined in configs/datasets.yaml (A, B, C).")
    p.add_argument("--out-root", default="out", help="Root directory for outputs (default: out).")

    p.add_argument("--expected-dt", type=float, default=1.0, help="Expected nominal sampling interval in seconds (default: 1.0).")
    p.add_argument("--tol-ms", type=int, default=5, help="Tolerance band in milliseconds for 'within tolerance' (default: 5 ms).")
    p.add_argument("--max-gap-s", type=float, default=2.0, help="Threshold in seconds for counting 'large gaps' (default: 2.0 s).")
    p.add_argument("--run-id", default=None, help="Optional run identifier. If not set, a new one is generated.")

    args = p.parse_args()

    cfg = load_dataset_config(args.dataset_id)
    dataset_id = args.dataset_id
    csv_path = cfg["csv_path"]
    time_col = cfg["time_col"]
    time_format = cfg.get("time_format", None)

    # Create run folder
    if args.run_id is None:
        rid = make_run_id()
    else:
        rid = args.run_id

    out_dir = os.path.join(args.out_root, args.dataset_id, rid)
    stats_dir = os.path.join(out_dir, "sampling_dt", "stats")
    ensure_dir(stats_dir)

    # Load only timestamp column (fast and reproducible)
    df = load_csv(cfg, usecols=[time_col])
    n_rows_used = int(len(df))

    # Parse timestamps
    if time_format:
        t = pd.to_datetime(df[time_col], format=time_format, errors="coerce")
    else:
        t = pd.to_datetime(df[time_col], errors="coerce")

    # If any timestamp cannot be parsed, we keep them as NaT and drop them for dt computation only.
    # This script characterizes sampling; it does not rewrite the dataset.
    valid_mask = t.notna()
    t_valid = t.loc[valid_mask].reset_index(drop=True)

    # Compute Delta t in seconds
    dt = t_valid.diff().dt.total_seconds().to_numpy(dtype=float)
    # First element has no previous sample
    dt = dt[1:]

    # Basic flags
    dt_zero = int(np.sum(dt == 0))
    dt_negative = int(np.sum(dt < 0))
    dt_large_gap = int(np.sum(dt > float(args.max_gap_s)))
    dt_large_gap_values = dt[dt > float(args.max_gap_s)]
    dt_large_gap_max = float(np.nanmax(dt_large_gap_values)) if dt_large_gap_values.size else 0.0

    # "Within tolerance" around expected dt (use absolute error)
    expected_dt = float(args.expected_dt)
    tol_s = float(args.tol_ms) / 1000.0
    within_tol = int(np.sum(np.abs(dt - expected_dt) <= tol_s))
    within_tol_pct = (within_tol / max(dt.size, 1)) * 100.0

    # Summary statistics
    summary = DtSummary(
        dataset_id=dataset_id,
        csv_path=csv_path,
        n_rows_used=n_rows_used,

        dt_count=int(dt.size),
        dt_mean_s=float(np.nanmean(dt)) if dt.size else float("nan"),
        dt_std_s=float(np.nanstd(dt)) if dt.size else float("nan"),
        dt_min_s=float(np.nanmin(dt)) if dt.size else float("nan"),
        dt_p01_s=_percentile(dt, 1),
        dt_p05_s=_percentile(dt, 5),
        dt_p50_s=_percentile(dt, 50),
        dt_p95_s=_percentile(dt, 95),
        dt_p99_s=_percentile(dt, 99),
        dt_max_s=float(np.nanmax(dt)) if dt.size else float("nan"),

        expected_dt_s=expected_dt,
        tol_ms=int(args.tol_ms),
        within_tol_count=int(within_tol),
        within_tol_pct=float(within_tol_pct),

        dt_zero_count=int(dt_zero),
        dt_negative_count=int(dt_negative),
        dt_large_gap_count=int(dt_large_gap),
        max_gap_s=float(args.max_gap_s),
        dt_large_gap_max_s=dt_large_gap_max,
    )

    # Save dt series (lightweight)
    dt_series_path = os.path.join(stats_dir, "dt_series.csv")
    dt_df = pd.DataFrame({
        "dt_s": dt,
        "is_zero": (dt == 0),
        "is_negative": (dt < 0),
        "is_large_gap": (dt > float(args.max_gap_s)),
        "abs_err_to_expected_s": np.abs(dt - expected_dt),
    })
    dt_df.to_csv(dt_series_path, index=False)

    # Save summary (CSV + JSON)
    dt_summary_path = os.path.join(stats_dir, "dt_summary.csv")
    pd.DataFrame([asdict(summary)]).to_csv(dt_summary_path, index=False)

    dt_summary_json_path = os.path.join(stats_dir, "dt_summary.json")
    write_json(dt_summary_json_path, asdict(summary))

    # Store run parameters for traceability
    params = {
        "dataset_id": dataset_id,
        "csv_path": csv_path,
        "time_col": time_col,
        "time_format": time_format,
        "expected_dt_s": expected_dt,
        "tol_ms": int(args.tol_ms),
        "max_gap_s": float(args.max_gap_s),
        "n_rows_used": n_rows_used,
        "run_id": rid,
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stage": "sampling_dt",
    }
    
    write_json(os.path.join(out_dir, "sampling_dt", "params.json"), params)

    print(f"OK {dataset_id}: wrote outputs to {out_dir}")
    print(f"dt_count={summary.dt_count}, mean={summary.dt_mean_s:.6f}s, "
            f"p50={summary.dt_p50_s:.6f}s, p99={summary.dt_p99_s:.6f}s, "
            f"dt_zero={summary.dt_zero_count}, dt_large_gap={summary.dt_large_gap_count}, "
            f"dt_max={summary.dt_max_s:.3f}s, dt_large_gap_max={summary.dt_large_gap_max_s:.3f}s")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())