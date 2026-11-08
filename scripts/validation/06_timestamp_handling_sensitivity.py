#!/usr/bin/env python3
"""
06_timestamp_handling_sensitivity.py

Sensitivity of the coherent sign ratio (CSR) to the handling of repeated timestamps.

Purpose
-------
In Dataset B, second 53 is missing and second 54 appears twice in every minute, so the
recording contains 1440 pairs of rows with the same timestamp. The CSR reported in the
manuscript (stage 04) uses all consecutive steps, including the 1440 steps between the
two rows of each pair (zero time step, dt = 0). The |dV/dt| statistics (stage 03) exclude
these steps.

This script compares two treatments using the same CSR function as stage 04:

  all_steps        All consecutive steps, as in stage 04 and the manuscript.
  exclude_zero_dt  Steps with dt = 0 are removed before the CSR is computed. The 95th
                   percentile thresholds of |dV| and |dP| are therefore recomputed on
                   the remaining steps, and the CSR sample size is counted on them.

Both rows of each pair are kept in the data in both treatments. Only the step between
the two rows is removed in exclude_zero_dt; the steps from second 52 to the first row
and from the second row to second 55 are kept.

This script does not modify the CSV files, the pipeline method or any reported table.
Dataset A has no repeated timestamps and is included as a control: both treatments
must give the same result.

Inputs
------
- Dataset configuration from configs/datasets.yaml (A and B)
- Main power column: NRE K1 P1, as in stage 04

Outputs
-------
  out/<dataset_id>/<run_id>/timestamp_sensitivity/stats/
    - timestamp_handling_sensitivity.csv
    - timestamp_handling_sensitivity.json
    - params.json

Usage (run from the repository root)
------------------------------------
python3 -m scripts.validation.06_timestamp_handling_sensitivity --datasets A B
python3 -m scripts.validation.06_timestamp_handling_sensitivity --datasets A B --run-id check06
"""

from __future__ import annotations

import argparse
import importlib
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

import pandas as pd

from scripts.common.io_config import (
    ensure_dir,
    load_csv,
    load_dataset_config,
    make_run_id,
    validate_csv_structure,
    write_json,
)

# Stage 04 is imported to reuse exactly the same difference and CSR functions.
cross_signal = importlib.import_module("scripts.validation.04_cross_signal_consistency")


def _treatment_row(
    dataset_id: str,
    treatment: str,
    dV: pd.Series,
    dP: pd.Series,
    n_zero_dt_excluded: int,
    dv_pctl: float,
    dp_pctl: float,
) -> Dict[str, Any]:
    """Compute the CSR and its selection details for one treatment."""
    ratio, n_sel, details = cross_signal._coherent_sign_ratio(
        dV, dP, dv_pctl=float(dv_pctl), dp_pctl=float(dp_pctl)
    )
    return {
        "dataset_id": dataset_id,
        "treatment": treatment,
        "zero_dt_steps_excluded": int(n_zero_dt_excluded),
        "steps_considered": int(details["coherent_sign_steps"]),
        "dv_threshold": float(details["coherent_sign_dv_threshold"]),
        "dp_threshold": float(details["coherent_sign_dp_threshold"]),
        "dv_frac": float(details["coherent_sign_dv_frac"]),
        "dp_frac": float(details["coherent_sign_dp_frac"]),
        "coherent_sign_ratio": float(ratio),
        "coherent_sign_n": int(n_sel),
    }


def run_dataset(dataset_id: str, config_path: str, dv_pctl: float, dp_pctl: float) -> List[Dict[str, Any]]:
    """Load one dataset as stage 04 does and evaluate both treatments."""
    cfg = load_dataset_config(dataset_id, config_path=config_path)
    validate_csv_structure(cfg)

    time_col = cfg["time_col"]
    time_format = cfg["time_format"]
    vbus_col = cfg["vbus_col"]
    power_col = cfg.get("power_col", "NRE K1 P1")

    df = load_csv(cfg, usecols=[vbus_col, power_col], drop_invalid_timestamps=True)
    t = pd.to_datetime(df[time_col], format=time_format, errors="coerce")
    v = pd.to_numeric(df[vbus_col], errors="coerce")
    p = pd.to_numeric(df[power_col], errors="coerce")

    # Same row filter as stage 04 (_branch_metrics).
    valid = t.notna() & v.notna() & p.notna()
    t = t.loc[valid].reset_index(drop=True)
    v = v.loc[valid].reset_index(drop=True)
    p = p.loc[valid].reset_index(drop=True)

    dt_s, dV, dP, _ = cross_signal._compute_dvdt_and_dp(t, v, p)

    rows = [
        _treatment_row(dataset_id, "all_steps", dV, dP, 0, dv_pctl, dp_pctl),
    ]

    # Remove the zero-length steps from both series at the same positions, so that the
    # CSR function drops them together and the remaining steps stay aligned.
    keep = dt_s > 0
    n_zero = int((dt_s == 0).sum())
    rows.append(
        _treatment_row(
            dataset_id,
            "exclude_zero_dt",
            dV.where(keep),
            dP.where(keep),
            n_zero,
            dv_pctl,
            dp_pctl,
        )
    )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage 06: sensitivity of the CSR to the handling of repeated timestamps."
    )
    parser.add_argument("--datasets", nargs="+", default=["A", "B"], choices=["A", "B"], help="Datasets to evaluate.")
    parser.add_argument("--config", default="configs/datasets.yaml", help="Path to datasets.yaml.")
    parser.add_argument("--out-root", default="out", help="Output root folder (default: out).")
    parser.add_argument("--dv-pctl", type=float, default=95.0, help="Percentile for the |dV| threshold (default: 95).")
    parser.add_argument("--dp-pctl", type=float, default=95.0, help="Percentile for the |dP| threshold (default: 95).")
    parser.add_argument("--run-id", default=None, help="Optional fixed run id.")
    args = parser.parse_args()

    run_id = args.run_id if args.run_id else make_run_id()
    created_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for dataset_id in args.datasets:
        rows = run_dataset(dataset_id, args.config, args.dv_pctl, args.dp_pctl)

        stats_dir = os.path.join(args.out_root, dataset_id, run_id, "timestamp_sensitivity", "stats")
        ensure_dir(stats_dir)

        pd.DataFrame(rows).to_csv(os.path.join(stats_dir, "timestamp_handling_sensitivity.csv"), index=False)
        write_json(os.path.join(stats_dir, "timestamp_handling_sensitivity.json"), {"rows": rows})
        write_json(
            os.path.join(stats_dir, "params.json"),
            {
                "stage": "timestamp_sensitivity",
                "dataset_id": dataset_id,
                "config_path": args.config,
                "dv_pctl": float(args.dv_pctl),
                "dp_pctl": float(args.dp_pctl),
                "run_id": run_id,
                "created_utc": created_utc,
            },
        )

        print(f"Dataset {dataset_id}: outputs written to {stats_dir}")
        for r in rows:
            print(
                f"  {r['treatment']:<16} steps={r['steps_considered']:>6} "
                f"excluded_dt0={r['zero_dt_steps_excluded']:>5} "
                f"thr_dV={r['dv_threshold']:.2f} thr_dP={r['dp_threshold']:.2f} "
                f"frac_dV={r['dv_frac']:.4f} frac_dP={r['dp_frac']:.4f} "
                f"CSR={r['coherent_sign_ratio']:.4f} (n={r['coherent_sign_n']})"
            )


if __name__ == "__main__":
    main()