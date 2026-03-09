#!/usr/bin/env python3
"""
05_data_overview_summary.py

Purpose
-------
Create one compact validation summary table for the main paper datasets.
This script does not recompute event detection or cross-signal metrics.
It only reads the existing outputs from Stage 03 and Stage 04 and merges
them into one clean dataset-level summary.

Why this script exists
----------------------
The pipeline already produces:
- detailed dV/dt event statistics (Stage 03)
- cross-signal consistency metrics (Stage 04)
- a LaTeX event table for extreme percentiles (reporting/02)

What is still missing is one small bridge artifact that consolidates the
main validation metrics per dataset in a single place. This makes the
pipeline easier to review, easier to execute end-to-end, and easier to
connect later with run_all and the manuscript tables.

What this script reads
----------------------
For each dataset, this script reads:

Stage 03
- dvdt_percentiles.csv
- event_counts_by_percentile.csv

Stage 04
- cross_signal_summary.csv

What this script writes
-----------------------
Under:

    out/reporting/<RUN_ID>/validation_summary/

Files:
- validation_summary.csv
- validation_summary.tex
- validation_summary.json
- params.json

Usage
-----
From the repository root:

python3 -m scripts.validation.05_data_overview_summary --datasets A B

Optional fixed validation run ids:

python3 -m scripts.validation.05_data_overview_summary \
  --datasets A B \
  --events-run-id 2026-03-01_1020Z_abcdef1 \
  --cross-run-id 2026-03-01_1040Z_abcdef1

Notes
-----
- This script is designed for datasets A and B in the main paper flow.
- Dataset C is intentionally left out of the main summary for now.
- Event-rate statistics by percentile are already handled by
  reporting/02_generate_latex_table_events.py, so this script focuses on:
  overview, dV/dt global statistics, and cross-signal consistency.
"""

from __future__ import annotations

import argparse
import glob
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

import pandas as pd

from scripts.common.io_config import ensure_dir, write_json, make_run_id


STAGE_NAME = "validation_summary"


def _utc_now_iso() -> str:
    """Return current UTC time in ISO-like compact format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _find_latest_file(
    pattern: str,
    required_dataset_id: Optional[str] = None,
) -> str:
    """
    Find the newest file matching a glob pattern.

    If required_dataset_id is provided, the CSV is opened and checked to ensure
    it contains at least one row with that dataset_id.
    """
    candidates = sorted(glob.glob(pattern))
    if not candidates:
        raise FileNotFoundError(f"No files found for pattern: {pattern}")

    valid_candidates: List[str] = []

    for path in candidates:
        if required_dataset_id is None:
            valid_candidates.append(path)
            continue

        try:
            df = pd.read_csv(path)
            if "dataset_id" in df.columns:
                mask = df["dataset_id"].astype(str) == str(required_dataset_id)
                if mask.any():
                    valid_candidates.append(path)
        except Exception:
            continue

    if not valid_candidates:
        raise FileNotFoundError(
            f"No valid files found for pattern: {pattern} "
            f"with dataset_id={required_dataset_id}"
        )

    valid_candidates.sort(key=lambda x: os.path.getmtime(x))
    return valid_candidates[-1]


def _find_stage03_dvdt_percentiles_csv(
    out_root: str,
    dataset_id: str,
    run_id: Optional[str],
) -> str:
    """Locate dvdt_percentiles.csv produced by Stage 03."""
    pattern = os.path.join(
        out_root,
        dataset_id,
        "*",
        "events_dvdt",
        "stats",
        "dvdt_percentiles.csv",
    )

    if run_id is not None:
        pattern = os.path.join(
            out_root,
            dataset_id,
            run_id,
            "events_dvdt",
            "stats",
            "dvdt_percentiles.csv",
        )

    return _find_latest_file(pattern, required_dataset_id=dataset_id)


def _find_stage03_event_counts_csv(
    out_root: str,
    dataset_id: str,
    run_id: Optional[str],
) -> str:
    """Locate event_counts_by_percentile.csv produced by Stage 03."""
    pattern = os.path.join(
        out_root,
        dataset_id,
        "*",
        "events_dvdt",
        "stats",
        "event_counts_by_percentile.csv",
    )

    if run_id is not None:
        pattern = os.path.join(
            out_root,
            dataset_id,
            run_id,
            "events_dvdt",
            "stats",
            "event_counts_by_percentile.csv",
        )

    return _find_latest_file(pattern, required_dataset_id=dataset_id)


def _find_stage04_cross_signal_csv(
    out_root: str,
    dataset_id: str,
    run_id: Optional[str],
) -> str:
    """Locate cross_signal_summary.csv produced by Stage 04."""
    pattern = os.path.join(
        out_root,
        dataset_id,
        "*",
        "cross_signal",
        "stats",
        "cross_signal_summary.csv",
    )

    if run_id is not None:
        pattern = os.path.join(
            out_root,
            dataset_id,
            run_id,
            "cross_signal",
            "stats",
            "cross_signal_summary.csv",
        )

    return _find_latest_file(pattern, required_dataset_id=dataset_id)

def _extract_run_id_from_stage_path(path: str, dataset_id: str, stage_name: str) -> str:
    """
    Extract run_id from a path like:

        out/<dataset_id>/<run_id>/<stage_name>/stats/<file>

    Returns
    -------
    run_id as string.

    Raises
    ------
    ValueError if the expected structure is not found.
    """
    norm = os.path.normpath(path)
    parts = norm.split(os.sep)

    try:
        ds_idx = parts.index(dataset_id)
    except ValueError as exc:
        raise ValueError(f"Could not locate dataset_id={dataset_id} in path: {path}") from exc

    if ds_idx + 2 >= len(parts):
        raise ValueError(f"Path too short to extract run_id from: {path}")

    run_id = parts[ds_idx + 1]
    stage = parts[ds_idx + 2]

    if stage != stage_name:
        raise ValueError(
            f"Unexpected stage folder in path: {path}\n"
            f"Expected stage folder: {stage_name}\n"
            f"Found: {stage}"
        )

    return run_id


def _read_single_row_csv(csv_path: str, dataset_id: str) -> pd.Series:
    """
    Read a CSV that should contain one row for the requested dataset_id.

    If multiple rows are present, keep the first matching row.
    """
    df = pd.read_csv(csv_path)
    if "dataset_id" not in df.columns:
        raise ValueError(f"Missing 'dataset_id' column in: {csv_path}")

    df["dataset_id"] = df["dataset_id"].astype(str)
    df_ds = df[df["dataset_id"] == str(dataset_id)].copy()

    if df_ds.empty:
        raise ValueError(f"No row found for dataset_id={dataset_id} in: {csv_path}")

    return df_ds.iloc[0]


def _safe_float(row: pd.Series, key: str) -> float:
    """Read one numeric value from a row, returning NaN if missing."""
    if key not in row.index:
        return float("nan")
    return float(pd.to_numeric(pd.Series([row[key]]), errors="coerce").iloc[0])


def _safe_int(row: pd.Series, key: str) -> int:
    """Read one integer value from a row, returning 0 if missing."""
    if key not in row.index:
        return 0

    val = pd.to_numeric(pd.Series([row[key]]), errors="coerce").iloc[0]
    if pd.isna(val):
        return 0
    return int(val)


def _extract_dvdt_metrics(
    dvdt_percentiles_csv: str,
    event_counts_csv: str,
    dataset_id: str,
) -> Dict[str, Any]:
    """
    Extract dataset-level metrics from Stage 03 outputs.

    We use:
    - dvdt_percentiles.csv for global |dV/dt| statistics
    - event_counts_by_percentile.csv only for recording_duration_h
    """
    dvdt_row = _read_single_row_csv(dvdt_percentiles_csv, dataset_id)
    counts_row = _read_single_row_csv(event_counts_csv, dataset_id)

    run_id_events = _extract_run_id_from_stage_path(
        dvdt_percentiles_csv,
        dataset_id=dataset_id,
        stage_name="events_dvdt",
    )

    return {
        "run_id_events_dvdt": run_id_events,
        "recording_duration_h": _safe_float(counts_row, "recording_duration_h"),
        "dvdt_count": _safe_int(dvdt_row, "dvdt_count"),
        "dvdt_abs_mean": _safe_float(dvdt_row, "dvdt_abs_mean"),
        "dvdt_abs_std": _safe_float(dvdt_row, "dvdt_abs_std"),
        "dvdt_abs_p95": _safe_float(dvdt_row, "dvdt_abs_p95"),
        "dvdt_abs_p99": _safe_float(dvdt_row, "dvdt_abs_p99"),
        "dvdt_abs_p995": _safe_float(dvdt_row, "dvdt_abs_p995"),
        "dvdt_abs_p999": _safe_float(dvdt_row, "dvdt_abs_p999"),
    }


def _extract_cross_metrics(
    cross_signal_csv: str,
    dataset_id: str,
) -> Dict[str, Any]:
    """
    Extract dataset-level metrics from Stage 04 outputs.
    """
    row = _read_single_row_csv(cross_signal_csv, dataset_id)

    run_id_cross = _extract_run_id_from_stage_path(
        cross_signal_csv,
        dataset_id=dataset_id,
        stage_name="cross_signal",
    )

    power_col_main = str(row.get("power_col", ""))
    safe_main = power_col_main.replace(" ", "_") if power_col_main else ""

    main_n_rows_used_key = f"n_rows_used_{safe_main}" if safe_main else ""
    n_rows_used_power_main = _safe_int(row, main_n_rows_used_key) if main_n_rows_used_key else 0

    out: Dict[str, Any] = {
        "run_id_cross_signal": run_id_cross,
        "power_col_main": power_col_main,
        "n_rows_raw": _safe_int(row, "n_rows_raw"),
        "n_rows_used": _safe_int(row, "n_rows_used"),
        "n_rows_used_power_main": n_rows_used_power_main,
        "spearman_vbus_power_main": _safe_float(row, "spearman_vbus_power"),
        "spearman_abs_dvdt_abs_dp_main": _safe_float(row, "spearman_abs_dvdt_abs_dp"),
        "coherent_sign_ratio_main": _safe_float(row, "coherent_sign_ratio"),
        "coherent_sign_n_main": _safe_int(row, "coherent_sign_n"),
    }

    for branch in ["NRE_K1_P1", "NRE_K4_P1", "NRE_K6_P1"]:
        out[f"n_rows_used_{branch}"] = _safe_int(row, f"n_rows_used_{branch}")
        out[f"spearman_vbus_power_{branch}"] = _safe_float(row, f"spearman_vbus_power_{branch}")
        out[f"spearman_abs_dvdt_abs_dp_{branch}"] = _safe_float(row, f"spearman_abs_dvdt_abs_dp_{branch}")
        out[f"coherent_sign_ratio_{branch}"] = _safe_float(row, f"coherent_sign_ratio_{branch}")
        out[f"coherent_sign_n_{branch}"] = _safe_int(row, f"coherent_sign_n_{branch}")

    return out


def _build_summary_row(
    out_root: str,
    dataset_id: str,
    events_run_id: Optional[str],
    cross_run_id: Optional[str],
) -> Dict[str, Any]:
    """
    Build one summary row for one dataset.
    """
    dvdt_percentiles_csv = _find_stage03_dvdt_percentiles_csv(
        out_root=out_root,
        dataset_id=dataset_id,
        run_id=events_run_id,
    )
    event_counts_csv = _find_stage03_event_counts_csv(
        out_root=out_root,
        dataset_id=dataset_id,
        run_id=events_run_id,
    )
    cross_signal_csv = _find_stage04_cross_signal_csv(
        out_root=out_root,
        dataset_id=dataset_id,
        run_id=cross_run_id,
    )

    row: Dict[str, Any] = {
        "dataset_id": dataset_id,
    }

    row.update(
        _extract_dvdt_metrics(
            dvdt_percentiles_csv=dvdt_percentiles_csv,
            event_counts_csv=event_counts_csv,
            dataset_id=dataset_id,
        )
    )

    row.update(
        _extract_cross_metrics(
            cross_signal_csv=cross_signal_csv,
            dataset_id=dataset_id,
        )
    )

    row["_source_dvdt_percentiles_csv"] = dvdt_percentiles_csv
    row["_source_event_counts_csv"] = event_counts_csv
    row["_source_cross_signal_csv"] = cross_signal_csv

    return row


def _ordered_columns() -> List[str]:
    """Column order for validation_summary.csv."""
    return [
        "dataset_id",
        "run_id_events_dvdt",
        "run_id_cross_signal",
        "recording_duration_h",
        "n_rows_raw",
        "n_rows_used",
        "dvdt_count",
        "dvdt_abs_mean",
        "dvdt_abs_std",
        "dvdt_abs_p95",
        "dvdt_abs_p99",
        "dvdt_abs_p995",
        "dvdt_abs_p999",
        "power_col_main",
        "n_rows_used_power_main",
        "spearman_vbus_power_main",
        "spearman_abs_dvdt_abs_dp_main",
        "coherent_sign_ratio_main",
        "coherent_sign_n_main",
        "n_rows_used_NRE_K1_P1",
        "spearman_vbus_power_NRE_K1_P1",
        "spearman_abs_dvdt_abs_dp_NRE_K1_P1",
        "coherent_sign_ratio_NRE_K1_P1",
        "coherent_sign_n_NRE_K1_P1",
        "n_rows_used_NRE_K4_P1",
        "spearman_vbus_power_NRE_K4_P1",
        "spearman_abs_dvdt_abs_dp_NRE_K4_P1",
        "coherent_sign_ratio_NRE_K4_P1",
        "coherent_sign_n_NRE_K4_P1",
        "n_rows_used_NRE_K6_P1",
        "spearman_vbus_power_NRE_K6_P1",
        "spearman_abs_dvdt_abs_dp_NRE_K6_P1",
        "coherent_sign_ratio_NRE_K6_P1",
        "coherent_sign_n_NRE_K6_P1",
    ]


def _format_float_for_tex(value: Any, decimals: int = 2) -> str:
    """Format one value for LaTeX output."""
    num = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(num):
        return "--"
    return f"{float(num):.{decimals}f}"


def _build_latex_table(
    df: pd.DataFrame,
    caption: str,
    label: str,
) -> str:
    """
    Build a compact LaTeX table for the main paper summary.

    The LaTeX table is intentionally compact and focuses on the main columns.
    The full machine-readable content stays in validation_summary.csv.
    """
    lines: List[str] = []
    lines.append("\\begin{table*}[t]")
    lines.append("\\centering")
    lines.append(f"\\caption{{{caption}}}")
    lines.append(f"\\label{{{label}}}")
    lines.append("\\begin{tabular}{lcccccc}")
    lines.append("\\toprule")
    lines.append(
        "Dataset & Duration (h) & Rows used & |dV/dt| p99 & "
        "$\\rho$(Vbus,P) main & Sign ratio main & Main power \\\\"
    )
    lines.append("\\midrule")

    for _, row in df.iterrows():
        ds = str(row["dataset_id"])
        duration_h = _format_float_for_tex(row["recording_duration_h"], 2)
        rows_used = str(int(pd.to_numeric(pd.Series([row["n_rows_used"]]), errors="coerce").fillna(0).iloc[0]))
        dvdt_p99 = _format_float_for_tex(row["dvdt_abs_p99"], 2)
        rho_main = _format_float_for_tex(row["spearman_vbus_power_main"], 3)
        sign_ratio = _format_float_for_tex(row["coherent_sign_ratio_main"], 3)
        main_power = str(row["power_col_main"]).replace("_", "\\_")

        lines.append(
            f"{ds} & {duration_h} & {rows_used} & {dvdt_p99} & "
            f"{rho_main} & {sign_ratio} & {main_power} \\\\"
        )

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table*}")
    lines.append("")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    p = argparse.ArgumentParser(
        description="Stage 05: Build one compact validation overview from Stage 03 and Stage 04 outputs."
    )
    p.add_argument(
        "--datasets",
        nargs="+",
        default=["A", "B"],
        help="Datasets to include in the main summary (default: A B).",
    )
    p.add_argument(
        "--validation-out-root",
        default="out",
        help="Root folder where validation outputs are stored (default: out).",
    )
    p.add_argument(
        "--reporting-out-root",
        default="out/reporting",
        help="Root folder where reporting outputs are written (default: out/reporting).",
    )
    p.add_argument(
        "--events-run-id",
        default=None,
        help="Optional fixed run id for Stage 03 inputs. If omitted, the latest run per dataset is used.",
    )
    p.add_argument(
        "--cross-run-id",
        default=None,
        help="Optional fixed run id for Stage 04 inputs. If omitted, the latest run per dataset is used.",
    )
    p.add_argument(
        "--run-id",
        default=None,
        help="Optional reporting run id for this Stage 05 output. If omitted, one is generated.",
    )
    p.add_argument(
        "--caption",
        default="Compact validation summary for the main LVDC datasets.",
        help="LaTeX caption text for validation_summary.tex",
    )
    p.add_argument(
        "--label",
        default="tab:validation_summary",
        help="LaTeX label for validation_summary.tex",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    reporting_run_id = args.run_id if args.run_id else make_run_id()
    out_dir = os.path.join(args.reporting_out_root, reporting_run_id, STAGE_NAME)
    ensure_dir(out_dir)

    rows: List[Dict[str, Any]] = []
    sources: Dict[str, Dict[str, str]] = {}

    for dataset_id in args.datasets:
        row = _build_summary_row(
            out_root=args.validation_out_root,
            dataset_id=dataset_id,
            events_run_id=args.events_run_id,
            cross_run_id=args.cross_run_id,
        )
        rows.append(row)
        sources[dataset_id] = {
            "dvdt_percentiles_csv": row["_source_dvdt_percentiles_csv"],
            "event_counts_csv": row["_source_event_counts_csv"],
            "cross_signal_csv": row["_source_cross_signal_csv"],
        }

    if not rows:
        raise RuntimeError("No datasets were processed. Check --datasets and available inputs.")

    df_all = pd.DataFrame(rows)

    # Keep source paths only in JSON, not in the main CSV
    df_csv = df_all.copy()
    source_cols = [c for c in df_csv.columns if c.startswith("_source_")]
    if source_cols:
        df_csv = df_csv.drop(columns=source_cols)

    ordered = _ordered_columns()
    missing_ordered = [c for c in ordered if c not in df_csv.columns]
    if missing_ordered:
        raise RuntimeError(
            "The summary is missing expected columns:\n"
            + "\n".join(f"- {c}" for c in missing_ordered)
        )

    df_csv = df_csv[ordered].copy()
    df_csv = df_csv.sort_values("dataset_id").reset_index(drop=True)

    csv_path = os.path.join(out_dir, "validation_summary.csv")
    df_csv.to_csv(csv_path, index=False)

    tex_path = os.path.join(out_dir, "validation_summary.tex")
    latex = _build_latex_table(
        df=df_csv,
        caption=args.caption,
        label=args.label,
    )
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(latex)

    json_path = os.path.join(out_dir, "validation_summary.json")
    json_obj: Dict[str, Any] = {
        "stage": STAGE_NAME,
        "reporting_run_id": reporting_run_id,
        "created_utc": _utc_now_iso(),
        "datasets": list(args.datasets),
        "sources": sources,
        "rows": df_csv.to_dict(orient="records"),
    }
    write_json(json_path, json_obj)

    params = {
        "stage": STAGE_NAME,
        "reporting_run_id": reporting_run_id,
        "created_utc": _utc_now_iso(),
        "datasets": list(args.datasets),
        "validation_out_root": args.validation_out_root,
        "reporting_out_root": args.reporting_out_root,
        "events_run_id": args.events_run_id,
        "cross_run_id": args.cross_run_id,
        "caption": args.caption,
        "label": args.label,
        "outputs": {
            "csv": csv_path,
            "tex": tex_path,
            "json": json_path,
        },
        "sources": sources,
    }
    write_json(os.path.join(out_dir, "params.json"), params)

    print(f"[OK] Stage 05 summary written to: {out_dir}")
    print(f"  - CSV : {csv_path}")
    print(f"  - TEX : {tex_path}")
    print(f"  - JSON: {json_path}")


if __name__ == "__main__":
    main()