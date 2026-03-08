#!/usr/bin/env python3
"""
04_cross_signal_consistency.py

Cross-signal consistency validation (Scientific Data - Technical Validation).

Purpose
-------
This script performs physics-informed consistency checks to verify that the main
signals within each dataset are mutually coherent. The goal is data quality validation,
not model performance.

Why these metrics
-----------------
We use three lightweight indicators that are easy to reproduce and robust in real
industrial recordings:

1) Spearman correlation between DC bus voltage (Vbus) and power (P).
   - Spearman is rank-based and therefore less sensitive to non-linear behavior and
     outliers than a purely linear metric.

2) Spearman correlation between |dV/dt| and |ΔP|.
   - Voltage transients are expected to be associated with rapid changes in power,
     supporting event-driven monitoring use cases.

3) Coherent sign ratio between ΔV and ΔP on salient steps.
   - In load-driven conditions, increases in power demand (ΔP > 0) often coincide with
     decreases in Vbus (ΔV < 0). We quantify how frequently this relationship holds
     without assuming it is always true.

Inputs
------
- Dataset configuration from configs/datasets.yaml (A/B/C)
- CSV referenced by the dataset config (raw or processed)

Outputs
-------
Writes summary metrics to:
  out/<dataset_id>/<run_id>/cross_signal/stats/
    - cross_signal_summary.csv
    - cross_signal_summary.json
    - params.json

Usage examples (run from the repository root)
---------------------------------------------
# Dataset A (battery-off)
python3 -m scripts.validation.04_cross_signal_consistency --dataset-id A

# Dataset B (battery-on)
python3 -m scripts.validation.04_cross_signal_consistency --dataset-id B

# Dataset C (optional)
python3 -m scripts.validation.04_cross_signal_consistency --dataset-id C

# Use a fixed run id (useful for run_all reproducibility)
python3 -m scripts.validation.04_cross_signal_consistency --dataset-id A --run-id 2026-02-24_1955Z_demo01

# Change percentiles used for the coherent sign test
python3 -m scripts.validation.04_cross_signal_consistency --dataset-id A --dp-pctl 95 --dv-pctl 95

Notes
-----
- This script does not resample or filter signals.
- Minimal cleaning is applied: invalid timestamps and NaN in required columns are removed.
- Results are intended as consistency indicators, not causal estimates.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

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


@dataclass
class CrossSignalSummary:
    dataset_id: str
    csv_path: str
    time_col: str
    vbus_col: str
    power_col: str

    n_rows_raw: int
    n_rows_used: int

    spearman_vbus_power: float
    pearson_vbus_power: float

    spearman_abs_dvdt_abs_dp: float
    coherent_sign_ratio: float
    coherent_sign_n: int

    dp_threshold_pctl: float
    dv_threshold_pctl: float

    created_utc: str
    run_id: str
    stage: str = "cross_signal"


def _spearman(x: pd.Series, y: pd.Series) -> float:
    """Spearman correlation (rank-based)."""
    if len(x) < 3:
        return float("nan")
    return float(x.corr(y, method="spearman"))


def _pearson(x: pd.Series, y: pd.Series) -> float:
    """Pearson correlation (linear)."""
    if len(x) < 3:
        return float("nan")
    return float(x.corr(y, method="pearson"))


def _compute_dvdt_and_dp(
    t: pd.Series,
    v: pd.Series,
    p: pd.Series,
) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """
    Compute finite differences:
    - dt_s: time delta (seconds)
    - dV: voltage difference
    - dP: power difference
    - dVdt: dV/dt
    """
    dt_s = t.diff().dt.total_seconds()
    dV = v.diff()
    dP = p.diff()

    with np.errstate(divide="ignore", invalid="ignore"):
        dVdt = dV / dt_s

    return dt_s, dV, dP, dVdt


def _coherent_sign_ratio(dV: pd.Series, dP: pd.Series, dv_pctl: float, dp_pctl: float) -> Tuple[float, int]:
    """
    Coherent sign ratio on salient steps.

    We restrict the computation to samples where both |ΔV| and |ΔP| are above percentile
    thresholds to avoid counting noise-level variations.

    Coherent rule:
      sign(ΔV) == -sign(ΔP)
    """
    dV = dV.dropna()
    dP = dP.dropna()
    n = min(len(dV), len(dP))
    if n < 3:
        return float("nan"), 0

    dV = dV.iloc[-n:]
    dP = dP.iloc[-n:]

    abs_dV = dV.abs().to_numpy()
    abs_dP = dP.abs().to_numpy()

    dv_thr = float(np.percentile(abs_dV, dv_pctl))
    dp_thr = float(np.percentile(abs_dP, dp_pctl))

    mask = (np.abs(dV.to_numpy()) >= dv_thr) & (np.abs(dP.to_numpy()) >= dp_thr)
    if int(mask.sum()) == 0:
        return float("nan"), 0

    dV_sel = dV.to_numpy()[mask]
    dP_sel = dP.to_numpy()[mask]

    coh = (np.sign(dV_sel) == -np.sign(dP_sel))
    ratio = float(np.mean(coh)) if len(coh) else float("nan")
    return ratio, int(len(coh))

def _branch_metrics(
    t: pd.Series,
    v: pd.Series,
    p: pd.Series,
    dv_pctl: float,
    dp_pctl: float,
) -> Dict[str, float]:
    """
    Compute cross-signal metrics for one candidate power branch.

    Returns
    -------
    dict with:
        - spearman_vbus_power
        - pearson_vbus_power
        - spearman_abs_dvdt_abs_dp
        - coherent_sign_ratio
        - coherent_sign_n
        - n_rows_used
    """
    # Keep only rows where time, voltage and this branch are valid
    valid = t.notna() & v.notna() & p.notna()
    t1 = t.loc[valid].reset_index(drop=True)
    v1 = v.loc[valid].reset_index(drop=True)
    p1 = p.loc[valid].reset_index(drop=True)

    if len(t1) < 5:
        return {
            "spearman_vbus_power": float("nan"),
            "pearson_vbus_power": float("nan"),
            "spearman_abs_dvdt_abs_dp": float("nan"),
            "coherent_sign_ratio": float("nan"),
            "coherent_sign_n": 0,
            "n_rows_used": int(len(t1)),
        }

    # Vbus vs power
    spearman_vp = _spearman(v1, p1)
    pearson_vp = _pearson(v1, p1)

    # |dV/dt| vs |ΔP|
    _, dV, dP, dVdt = _compute_dvdt_and_dp(t1, v1, p1)
    dvdt_abs = dVdt.abs().replace([np.inf, -np.inf], np.nan)
    dp_abs = dP.abs().replace([np.inf, -np.inf], np.nan)

    mask = dvdt_abs.notna() & dp_abs.notna()
    spearman_abs = _spearman(dvdt_abs.loc[mask], dp_abs.loc[mask])

    # Coherent sign ratio
    coh_ratio, coh_n = _coherent_sign_ratio(
        dV, dP, dv_pctl=float(dv_pctl), dp_pctl=float(dp_pctl)
    )

    return {
        "spearman_vbus_power": float(spearman_vp),
        "pearson_vbus_power": float(pearson_vp),
        "spearman_abs_dvdt_abs_dp": float(spearman_abs),
        "coherent_sign_ratio": float(coh_ratio),
        "coherent_sign_n": int(coh_n),
        "n_rows_used": int(len(t1)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Stage 04: Cross-signal consistency checks (Vbus vs power, |dV/dt| vs |ΔP|)."
    )
    parser.add_argument("--dataset-id", required=True, choices=["A", "B", "C"], help="Dataset identifier.")
    parser.add_argument("--config", default="configs/datasets.yaml", help="Path to datasets.yaml.")
    parser.add_argument("--out-root", default="out", help="Output root folder (default: out).")
    parser.add_argument("--encoding", default="utf-8", help="CSV encoding (default: utf-8).")

    parser.add_argument(
        "--dp-pctl",
        type=float,
        default=95.0,
        help="Percentile for |ΔP| threshold used in coherent sign ratio (default: 95).",
    )
    parser.add_argument(
        "--dv-pctl",
        type=float,
        default=95.0,
        help="Percentile for |ΔV| threshold used in coherent sign ratio (default: 95).",
    )

    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional fixed run id. If not provided, a timestamp+gitsha id is generated.",
    )

    args = parser.parse_args()

    # Load config
    cfg = load_dataset_config(args.dataset_id, config_path=args.config)
    validate_csv_structure(cfg)

    dataset_id = args.dataset_id
    csv_path = cfg["csv_path"]
    time_col = cfg["time_col"]
    time_format = cfg["time_format"]
    vbus_col = cfg["vbus_col"]
    power_cols_candidates = cfg.get("power_cols_candidates", [])
    power_cols_sum = cfg.get("power_cols_sum", [])
    power_sum_name = cfg.get("power_sum_name", "NRE_sum")

    # Deterministic choice of power column for this paper:
    # - A/B: NRE K1 P1 (total power)
    # - C: poweroutput
    power_col = cfg.get("power_col", None)
    if power_col is None:
        power_col = "NRE K1 P1" if dataset_id in ("A", "B") else "poweroutput"

    # Run id and output folders
    run_id = args.run_id if args.run_id else make_run_id()
    out_dir = os.path.join(args.out_root, dataset_id, run_id)
    stats_dir = os.path.join(out_dir, "cross_signal", "stats")
    ensure_dir(stats_dir)

    # Load voltage, primary power column, and all candidate branch powers
    usecols = [vbus_col, power_col]
    for col in power_cols_candidates:
        if col not in usecols:
            usecols.append(col)
    for col in power_cols_sum:
        if col not in usecols:
            usecols.append(col)

    df = load_csv(cfg, usecols=usecols, drop_invalid_timestamps=True)
    
    
    n_rows_raw = int(df.shape[0])

    # Ensure types for time and voltage first
    t = pd.to_datetime(df[time_col], format=time_format, errors="coerce")
    v = pd.to_numeric(df[vbus_col], errors="coerce")

    # Keep rows where time and voltage are valid.
    # Candidate power branches will be cleaned individually when metrics are computed.
    valid = t.notna() & v.notna()
    df = df.loc[valid].reset_index(drop=True)
    t = t.loc[valid].reset_index(drop=True)
    v = v.loc[valid].reset_index(drop=True)

    n_rows_used = int(len(t))

    if n_rows_used < 5:
        raise RuntimeError(f"Not enough valid rows after cleaning for dataset {dataset_id}: n_rows_used={n_rows_used}")

    # Primary power series (legacy/main output, kept for backward compatibility)
    p = pd.to_numeric(df[power_col], errors="coerce")

    # Main/legacy metrics using the primary power column
    main_metrics = _branch_metrics(
        t=t,
        v=v,
        p=p,
        dv_pctl=float(args.dv_pctl),
        dp_pctl=float(args.dp_pctl),
    )

    spearman_vp = main_metrics["spearman_vbus_power"]
    pearson_vp = main_metrics["pearson_vbus_power"]
    spearman_abs = main_metrics["spearman_abs_dvdt_abs_dp"]
    coh_ratio = main_metrics["coherent_sign_ratio"]
    coh_n = main_metrics["coherent_sign_n"]
    
    # ------------------------------------------------------------
    # Candidate branch metrics (A/B) or optional alternative signals
    # ------------------------------------------------------------
    candidate_metrics: Dict[str, Dict[str, float]] = {}

    for col in power_cols_candidates:
        if col in df.columns:
            p_col = pd.to_numeric(df[col], errors="coerce")
            candidate_metrics[col] = _branch_metrics(
                t=t,
                v=v,
                p=p_col,
                dv_pctl=float(args.dv_pctl),
                dp_pctl=float(args.dp_pctl),
            )

    # Optional sum of branches
    if power_cols_sum and all(col in df.columns for col in power_cols_sum):
        df_sum = df[power_cols_sum].apply(pd.to_numeric, errors="coerce")
        p_sum = df_sum.sum(axis=1, min_count=len(power_cols_sum))
        candidate_metrics[power_sum_name] = _branch_metrics(
            t=t,
            v=v,
            p=p_sum,
            dv_pctl=float(args.dv_pctl),
            dp_pctl=float(args.dp_pctl),
        )

    created_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    summary: Dict[str, Any] = {
        "dataset_id": dataset_id,
        "csv_path": str(csv_path),
        "time_col": str(time_col),
        "vbus_col": str(vbus_col),
        "power_col": str(power_col),
        "n_rows_raw": int(n_rows_raw),
        "n_rows_used": int(n_rows_used),
        "spearman_vbus_power": float(spearman_vp),
        "pearson_vbus_power": float(pearson_vp),
        "spearman_abs_dvdt_abs_dp": float(spearman_abs),
        "coherent_sign_ratio": float(coh_ratio),
        "coherent_sign_n": int(coh_n),
        "dp_threshold_pctl": float(args.dp_pctl),
        "dv_threshold_pctl": float(args.dv_pctl),
        "created_utc": created_utc,
        "run_id": str(run_id),
        "stage": "cross_signal",
    }

    # Flatten candidate branch metrics into explicit columns
    for col, metrics in candidate_metrics.items():
        safe_col = col.replace(" ", "_")
        summary[f"spearman_vbus_power_{safe_col}"] = float(metrics["spearman_vbus_power"])
        summary[f"pearson_vbus_power_{safe_col}"] = float(metrics["pearson_vbus_power"])
        summary[f"spearman_abs_dvdt_abs_dp_{safe_col}"] = float(metrics["spearman_abs_dvdt_abs_dp"])
        summary[f"coherent_sign_ratio_{safe_col}"] = float(metrics["coherent_sign_ratio"])
        summary[f"coherent_sign_n_{safe_col}"] = int(metrics["coherent_sign_n"])
        summary[f"n_rows_used_{safe_col}"] = int(metrics["n_rows_used"])

    # Params for traceability
    params: Dict[str, Any] = {
        "stage": "cross_signal",
        "dataset_id": dataset_id,
        "config_path": args.config,
        "csv_path": csv_path,
        "time_col": time_col,
        "time_format": time_format,
        "vbus_col": vbus_col,
        "power_col": power_col,
        "dp_pctl": float(args.dp_pctl),
        "dv_pctl": float(args.dv_pctl),
        "encoding": args.encoding,
        "run_id": run_id,
        "created_utc": created_utc,
        "power_cols_candidates": power_cols_candidates,
        "power_cols_sum": power_cols_sum,
        "power_sum_name": power_sum_name,
    }

    # Write outputs
    csv_out = os.path.join(stats_dir, "cross_signal_summary.csv")
    json_out = os.path.join(stats_dir, "cross_signal_summary.json")
    params_out = os.path.join(stats_dir, "params.json")

    pd.DataFrame([summary]).to_csv(csv_out, index=False)
    write_json(json_out, summary)
    write_json(params_out, params)

    print(f"Cross-signal consistency completed for dataset {dataset_id}")
    print(f"Output directory: {out_dir}")
    print(f"Stats written to: {stats_dir}")
    print(
        "Key metrics: "
        f"spearman(Vbus,P)={summary['spearman_vbus_power']:.4f}, "
        f"spearman(|dV/dt|,|ΔP|)={summary['spearman_abs_dvdt_abs_dp']:.4f}, "
        f"coherent_sign_ratio={summary['coherent_sign_ratio']:.4f} "
        f"(n={summary['coherent_sign_n']})"
    )


if __name__ == "__main__":
    main()