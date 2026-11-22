#!/usr/bin/env python3
"""
07_signal_changes_autocorrelation.py

Changes between consecutive recorded values and autocorrelation of the main signals.

Purpose
-------
This stage describes two properties of the recordings of Datasets A and B:

1) Changes between consecutive rows, for every variable of the CSV file:
   - the percentage of steps in which the recorded value changes;
   - the median length of the runs without change.
2) Autocorrelation of the DC bus voltage and of the branch powers listed in
   power_cols_candidates (K1, K4 and K6), at lags given in rows, and the
   autocorrelation of the voltage difference between consecutive rows at a lag
   of one step.

These are descriptive properties of the recorded values. They do not separate
sensor noise from the electrical behaviour, they are not the update rate of the
measuring devices, and they do not evaluate any detection or prioritization method.

Definitions
-----------
Rows and steps
  The CSV file is loaded with the common loader (scripts.common.io_config.load_csv).
  The rows are kept in the order of the file. Before loading, the script stops with an
  error if any timestamp cannot be parsed (the loader would otherwise drop that row) or
  if the timestamps decrease (the stable sort of the loader would then reorder rows).
  No row is removed, no duplicate is dropped and nothing is interpolated.
  A step is the pair of consecutive rows (i-1, i); dt_i = t_i - t_(i-1).
  All differences are computed on the full sequence of rows first; masks are
  applied afterwards, so no artificial step is created between rows that are not
  consecutive in the file.

Steps with dt = 0
  In Dataset B, second 53 is missing and second 54 appears twice in every minute,
  which gives 1440 steps with dt = 0. As for |dV/dt| (stage 03), these steps are
  excluded from the percentage of steps with a change. Their number and the number
  of changes within them are exported separately.

Change
  A step has a change when both values are present and the recorded value of row i
  differs from that of row i-1 (exact comparison of the values read from the CSV).

Runs without change
  A run is a maximal sequence of consecutive rows with the same recorded value,
  containing at least two rows. Runs are defined on rows, so they include the
  steps with dt = 0. Their length is reported in steps (rows - 1) and in seconds
  (timestamp of the last row minus timestamp of the first row). A variable that
  never changes forms a single run covering the whole file and is flagged as
  constant. A variable that changes at every step has no runs.

Autocorrelation
  For a signal x and a lag of k rows, the autocorrelation is the Pearson
  correlation between x_i and x_(i+k) over all pairs of rows in which both values
  are present (pandas Series.autocorr). Lags are counted in rows, not in seconds.
  In Dataset A, 86397 of the 86398 steps are 1 s long, so k rows correspond to k s
  except across the first step. In Dataset B, the pattern of seconds 53 and 54 makes
  k rows correspond to k s with a difference of at most 1 s; the minimum, median and
  maximum time between the paired rows are exported for each lag.
  For the voltage difference dV_i = V_i - V_(i-1), the lag-1 autocorrelation uses
  the pairs (dV_i, dV_(i+1)) in which both steps have dt > 0. Pairs that contain a
  step with dt = 0 are excluded and counted. The value with all steps is exported
  as well.
  A constant signal has no defined autocorrelation (NaN).

Inputs
------
- Dataset configuration from configs/datasets.yaml (A and B)
- All variables of the CSV file for the changes; vbus_col and power_cols_candidates
  for the autocorrelation

Outputs
-------
  out/<dataset_id>/<run_id>/signal_changes/stats/
    - signal_changes.csv     one row per variable
    - autocorrelation.csv    one row per signal and lag
    - signal_changes_summary.json
    - params.json

Usage (run from the repository root)
------------------------------------
python3 -m scripts.validation.07_signal_changes_autocorrelation --dataset-id A
python3 -m scripts.validation.07_signal_changes_autocorrelation --dataset-id B --run-id check07
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from scripts.common.io_config import (
    ensure_dir,
    load_csv,
    load_dataset_config,
    make_run_id,
    validate_csv_structure,
    write_json,
)

STAGE_NAME = "signal_changes"


def _check_file_order(cfg: Dict[str, Any]) -> Dict[str, int]:
    """
    Fail if any timestamp cannot be parsed or if the timestamps decrease.

    In both cases the common loader would change the rows (by dropping or reordering
    them), so this stage stops instead of computing results on modified rows.
    """
    raw = pd.read_csv(cfg["csv_path"], usecols=[cfg["time_col"]])
    t = pd.to_datetime(raw[cfg["time_col"]], format=cfg["time_format"], errors="coerce")
    n_invalid = int(t.isna().sum())
    if n_invalid > 0:
        first_line = int(t.index[t.isna()][0]) + 2  # file line, counting the header as line 1
        raise RuntimeError(
            f"{n_invalid} timestamp(s) in {cfg['csv_path']} cannot be parsed with format "
            f"{cfg['time_format']!r} (first at file line {first_line}); stage 07 keeps all "
            f"rows and does not drop them."
        )
    if (t.diff().dt.total_seconds() < 0).any():
        raise RuntimeError(
            f"Timestamps decrease in {cfg['csv_path']}; the loader would change the row order."
        )
    return {"n_rows_file": int(len(t))}


def _runs_without_change(values: pd.Series, t_s: np.ndarray) -> Dict[str, Any]:
    """Maximal runs of consecutive rows with the same value (at least two rows)."""
    x = values.to_numpy()
    present = ~pd.isna(x)
    same = np.zeros(len(x), dtype=bool)  # same[i]: row i equal to row i-1
    same[1:] = present[1:] & present[:-1] & (x[1:] == x[:-1])

    lengths_steps: List[int] = []
    lengths_s: List[float] = []
    i = 1
    n = len(x)
    while i < n:
        if same[i]:
            start = i - 1
            while i < n and same[i]:
                i += 1
            end = i - 1
            lengths_steps.append(end - start)
            lengths_s.append(float(t_s[end] - t_s[start]))
        else:
            i += 1

    return {
        "n_runs": len(lengths_steps),
        "run_median_steps": float(np.median(lengths_steps)) if lengths_steps else float("nan"),
        "run_median_s": float(np.median(lengths_s)) if lengths_s else float("nan"),
        "run_max_steps": int(max(lengths_steps)) if lengths_steps else 0,
    }


def _signal_changes(df: pd.DataFrame, time_col: str, dt_s: pd.Series, t_s: np.ndarray, dataset_id: str) -> pd.DataFrame:
    """Percentage of steps with a change and runs without change, for every variable."""
    pos_dt = (dt_s > 0).to_numpy()
    zero_dt = (dt_s == 0).to_numpy()
    rows: List[Dict[str, Any]] = []

    for col in [c for c in df.columns if c != time_col]:
        x = pd.to_numeric(df[col], errors="coerce")
        x_np = x.to_numpy()
        both = np.zeros(len(x_np), dtype=bool)
        both[1:] = ~np.isnan(x_np[1:]) & ~np.isnan(x_np[:-1])
        changed = np.zeros(len(x_np), dtype=bool)
        changed[1:] = both[1:] & (x_np[1:] != x_np[:-1])

        valid = both & pos_dt
        n_valid = int(valid.sum())
        n_changed = int((changed & valid).sum())
        n_dt0 = int((both & zero_dt).sum())
        n_changed_dt0 = int((changed & zero_dt).sum())
        n_missing = int(np.isnan(x_np).sum())
        is_constant = bool(np.nanmin(x_np) == np.nanmax(x_np)) if (~np.isnan(x_np)).any() else True

        row = {
            "dataset_id": dataset_id,
            "variable": col,
            "n_rows": int(len(x_np)),
            "n_missing_values": n_missing,
            "n_steps_dt_pos": n_valid,
            "n_steps_changed": n_changed,
            "pct_steps_changed": float(100.0 * n_changed / n_valid) if n_valid else float("nan"),
            "n_steps_dt0_excluded": n_dt0,
            "n_changes_within_dt0_steps": n_changed_dt0,
            "constant": is_constant,
        }
        row.update(_runs_without_change(x, t_s))
        rows.append(row)

    return pd.DataFrame(rows)


def _autocorrelation(
    df: pd.DataFrame,
    signals: List[str],
    vbus_col: str,
    dt_s: pd.Series,
    t_s: np.ndarray,
    lags: List[int],
    dataset_id: str,
) -> pd.DataFrame:
    """Autocorrelation of the signals at lags in rows, and lag-1 autocorrelation of dV."""
    rows: List[Dict[str, Any]] = []
    t = pd.Series(t_s)

    for col in signals:
        x = pd.to_numeric(df[col], errors="coerce")
        constant = bool(x.nunique(dropna=True) <= 1)
        for k in lags:
            pair_ok = x.notna() & x.shift(-k).notna()
            gap = (t.shift(-k) - t)[pair_ok]
            r = float("nan") if constant else float(x.autocorr(lag=k))
            rows.append({
                "dataset_id": dataset_id,
                "signal": col,
                "quantity": "value",
                "lag_rows": int(k),
                "n_pairs": int(pair_ok.sum()),
                "n_pairs_excluded_dt0": 0,
                "lag_time_s_min": float(gap.min()),
                "lag_time_s_median": float(gap.median()),
                "lag_time_s_max": float(gap.max()),
                "autocorr": r,
                "autocorr_all_steps": r,
            })

    # Voltage difference between consecutive rows, computed on the full row sequence.
    v = pd.to_numeric(df[vbus_col], errors="coerce")
    dv = v.diff()
    dv_pos = dv.where(dt_s > 0)
    pair_all = dv.notna() & dv.shift(-1).notna()
    pair_pos = dv_pos.notna() & dv_pos.shift(-1).notna()
    gap = (t.shift(-1) - t)[pair_pos]
    rows.append({
        "dataset_id": dataset_id,
        "signal": vbus_col,
        "quantity": "difference_between_consecutive_rows",
        "lag_rows": 1,
        "n_pairs": int(pair_pos.sum()),
        "n_pairs_excluded_dt0": int(pair_all.sum() - pair_pos.sum()),
        "lag_time_s_min": float(gap.min()),
        "lag_time_s_median": float(gap.median()),
        "lag_time_s_max": float(gap.max()),
        "autocorr": float(dv_pos.autocorr(lag=1)),
        "autocorr_all_steps": float(dv.autocorr(lag=1)),
    })
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage 07: changes between consecutive recorded values and autocorrelation of the main signals."
    )
    parser.add_argument("--dataset-id", required=True, choices=["A", "B"], help="Dataset identifier.")
    parser.add_argument("--config", default="configs/datasets.yaml", help="Path to datasets.yaml.")
    parser.add_argument("--out-root", default="out", help="Output root folder (default: out).")
    parser.add_argument("--lags", default="1,10,60,600", help="Comma-separated lags in rows (default: 1,10,60,600).")
    parser.add_argument("--run-id", default=None, help="Optional fixed run id. If not set, one is generated.")
    args = parser.parse_args()

    cfg = load_dataset_config(args.dataset_id, config_path=args.config)
    validate_csv_structure(cfg)
    file_info = _check_file_order(cfg)

    dataset_id = args.dataset_id
    time_col = cfg["time_col"]
    vbus_col = cfg["vbus_col"]
    signals = [vbus_col] + [c for c in cfg.get("power_cols_candidates", []) if c != vbus_col]
    lags = [int(x.strip()) for x in args.lags.split(",") if x.strip()]

    run_id = args.run_id if args.run_id else make_run_id()
    stats_dir = os.path.join(args.out_root, dataset_id, run_id, STAGE_NAME, "stats")
    ensure_dir(stats_dir)

    # All columns, rows in file order. All timestamps are valid and non-decreasing
    # (checked above), so the loader keeps every row in the order of the file.
    df = load_csv(cfg, drop_invalid_timestamps=False)
    if len(df) != file_info["n_rows_file"]:
        raise RuntimeError("The number of loaded rows differs from the number of rows in the file.")
    t = df[time_col]
    t_s = (t - t.iloc[0]).dt.total_seconds().to_numpy(dtype=float)
    dt_s = t.diff().dt.total_seconds()

    changes = _signal_changes(df, time_col, dt_s, t_s, dataset_id)
    acf = _autocorrelation(df, signals, vbus_col, dt_s, t_s, lags, dataset_id)

    changes.to_csv(os.path.join(stats_dir, "signal_changes.csv"), index=False)
    acf.to_csv(os.path.join(stats_dir, "autocorrelation.csv"), index=False)

    summary = {
        "dataset_id": dataset_id,
        "n_rows_file": file_info["n_rows_file"],
        "n_rows": int(len(df)),
        "n_steps": int(len(df) - 1),
        "n_steps_dt_pos": int((dt_s > 0).sum()),
        "n_steps_dt0": int((dt_s == 0).sum()),
        "n_variables": int(len(changes)),
        "n_constant_variables": int(changes["constant"].sum()),
        "signals_autocorrelation": signals,
        "lags_rows": lags,
    }
    write_json(os.path.join(stats_dir, "signal_changes_summary.json"), summary)
    write_json(
        os.path.join(stats_dir, "params.json"),
        {
            "stage": STAGE_NAME,
            "dataset_id": dataset_id,
            "config_path": args.config,
            "csv_path": cfg["csv_path"],
            "lags_rows": lags,
            "run_id": run_id,
            "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )

    print(f"Dataset {dataset_id}: outputs written to {stats_dir}")
    print(
        f"  rows={summary['n_rows']} steps={summary['n_steps']} dt>0={summary['n_steps_dt_pos']} "
        f"dt=0={summary['n_steps_dt0']} variables={summary['n_variables']} "
        f"constant={summary['n_constant_variables']}"
    )
    for col in signals:
        r = changes.loc[changes["variable"] == col].iloc[0]
        a = acf.loc[(acf["signal"] == col) & (acf["quantity"] == "value")]
        acf_txt = " ".join(f"r{int(k)}={v:.3f}" for k, v in zip(a["lag_rows"], a["autocorr"]))
        print(
            f"  {col:<12} changed={r['pct_steps_changed']:.2f}% "
            f"median_run={r['run_median_steps']:.0f} steps ({r['run_median_s']:.0f} s)  {acf_txt}"
        )
    d = acf.loc[acf["quantity"] != "value"].iloc[0]
    print(f"  dV lag-1 autocorrelation={d['autocorr']:.3f} (pairs={int(d['n_pairs'])}, "
          f"excluded with dt=0: {int(d['n_pairs_excluded_dt0'])})")


if __name__ == "__main__":
    main()
