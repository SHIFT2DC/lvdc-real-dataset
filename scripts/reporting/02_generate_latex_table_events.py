"""
Script: 02_generate_latex_table_events.py

Purpose
-------
Generate a LaTeX-ready table summarizing extreme |dV/dt| event statistics
for inclusion in the Scientific Data manuscript.

This script formats the output produced by:

    python3 -m scripts.validation.03_event_counts_by_percentile --dataset-id <A|B|C>

It does not recompute events. It only reads existing CSV results and writes:
- A LaTeX table (.tex)
- A rounded CSV used to generate the table (traceability)

Inputs
------
event_counts_by_percentile.csv files located under:

    out/<DATASET_ID>/<RUN_ID>/events/stats/event_counts_by_percentile.csv

If --run-id is not provided, the script will auto-select the most recent run
per dataset by scanning the filesystem.

Outputs
-------
Written to:

    out/reporting/<RUN_ID>/tables/

Files:
- events_table.tex
- events_table_formatted.csv
- params.json

Usage (from repository root)
----------------------------
Typical (auto-discover latest runs for A, B, C):

python3 -m scripts.reporting.02_generate_latex_table_events \
  --datasets A B C

Select a specific run id (applies to all datasets, if present):

python3 -m scripts.reporting.02_generate_latex_table_events \
  --datasets A B C \
  --run-id 2026-02-21_1848Z_4800b1f

Notes
-----
- This script expects that Stage 03 has already been executed for each dataset.
- The LaTeX table focuses on the most extreme percentiles by default (99.9, 99.95).
"""

import os
import glob
import json
import argparse
from datetime import datetime, timezone
from typing import List, Optional, Dict

import pandas as pd


def utc_timestamp_compact() -> str:
    """Return a UTC timestamp string like YYYY-MM-DD_HHMMZ."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%MZ")


def ensure_dir(path: str) -> None:
    """Create directory if it does not exist."""
    os.makedirs(path, exist_ok=True)


def write_json(path: str, obj: Dict) -> None:
    """Write JSON with stable formatting for traceability."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)


def _find_event_counts_csv(out_root: str, dataset_id: str, run_id: Optional[str]) -> str:
    """
    Locate event_counts_by_percentile.csv for a given dataset.

    We only consider Stage-03 outputs, identified by a fixed folder layout:
        .../events_dvdt/stats/event_counts_by_percentile.csv

    If run_id is provided, we restrict to paths containing that run_id.
    If multiple candidates exist, we select the newest by modification time.
    As an extra guard, we verify the CSV contains the requested dataset_id.
    """
    base = os.path.join(out_root, dataset_id)

    # Stage-03 layout (current): events_dvdt/stats/...
    patterns = [
        os.path.join(base, "*", "events_dvdt", "stats", "event_counts_by_percentile.csv"),
        # Optional future compatibility (if you ever rename the folder):
        os.path.join(base, "*", "events", "stats", "event_counts_by_percentile.csv"),
    ]

    candidates = []
    for p in patterns:
        candidates.extend(glob.glob(p))

    candidates = sorted(set(candidates))

    if run_id is not None:
        candidates = [p for p in candidates if run_id in p]

    if not candidates:
        msg = (
            f"No Stage-03 event counts CSV found for dataset {dataset_id}.\n"
            f"Tried patterns:\n"
            f"  - {patterns[0]}\n"
            f"  - {patterns[1]}\n"
        )
        if run_id is not None:
            msg += f"Filtered by run_id={run_id}\n"
        msg += "Tip: run Stage 03 first for this dataset."
        raise FileNotFoundError(msg)

    # Extra guard: ensure the file belongs to dataset_id
    matching = []
    for p in candidates:
        try:
            df = pd.read_csv(p)
            if "dataset_id" in df.columns and (df["dataset_id"].astype(str) == str(dataset_id)).any():
                matching.append(p)
        except Exception:
            continue

    if matching:
        candidates = matching

    # Choose newest by modification time
    candidates.sort(key=lambda x: os.path.getmtime(x))
    return candidates[-1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a LaTeX table from dv/dt event statistics (Stage 03 outputs)."
    )

    parser.add_argument(
        "--datasets",
        nargs="+",
        default=["A", "B", "C"],
        help="Datasets to include (default: A B C).",
    )

    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Optional run id to use for all datasets (e.g., 2026-02-21_1848Z_4800b1f). "
             "If omitted, the script auto-selects the latest run per dataset.",
    )

    parser.add_argument(
        "--validation-out-root",
        type=str,
        default="out",
        help="Root folder where validation outputs are stored (default: out).",
    )

    parser.add_argument(
        "--reporting-out-root",
        type=str,
        default="out/reporting",
        help="Root folder where reporting outputs will be written (default: out/reporting).",
    )

    parser.add_argument(
        "--percentiles",
        nargs="+",
        type=float,
        default=[99.9, 99.95],
        help="Which percentile rows to include in the table (default: 99.9 99.95).",
    )

    parser.add_argument(
        "--caption",
        type=str,
        default="Extreme |dV/dt| event statistics per dataset.",
        help="LaTeX caption text.",
    )

    parser.add_argument(
        "--label",
        type=str,
        default=None,
        help="Optional LaTeX label (e.g., tab:dvdt-events). If omitted, no label is added.",
    )

    args = parser.parse_args()

    reporting_run_id = utc_timestamp_compact()
    out_dir = os.path.join(args.reporting_out_root, reporting_run_id, "tables")
    ensure_dir(out_dir)

    # -------------------------------------------------------------------------
    # Load and merge inputs from datasets
    # -------------------------------------------------------------------------
    rows = []
    sources = {}

    for ds in args.datasets:
        csv_path = _find_event_counts_csv(args.validation_out_root, ds, args.run_id)
        sources[ds] = csv_path

        df = pd.read_csv(csv_path)
        df["dataset_id"] = df["dataset_id"].astype(str)

        # Keep only requested percentiles
        df = df[df["threshold_value"].isin(args.percentiles)].copy()
        rows.append(df)

    if not rows:
        raise RuntimeError("No data loaded. Check --datasets and available Stage 03 outputs.")

    df_all = pd.concat(rows, ignore_index=True)

    # Sort for clean presentation
    df_all = df_all.sort_values(["dataset_id", "threshold_value"]).reset_index(drop=True)

    # -------------------------------------------------------------------------
    # Rounding for publication (consistent, readable)
    # -------------------------------------------------------------------------
    df_all["recording_duration_h"] = df_all["recording_duration_h"].round(2)
    df_all["threshold_vps_equivalent"] = df_all["threshold_vps_equivalent"].round(2)
    df_all["events_per_hour"] = df_all["events_per_hour"].round(2)
    df_all["samples_in_event_pct"] = df_all["samples_in_event_pct"].round(2)

    formatted_csv_path = os.path.join(out_dir, "events_table_formatted.csv")
    df_all.to_csv(formatted_csv_path, index=False)

    # -------------------------------------------------------------------------
    # Create LaTeX table
    # -------------------------------------------------------------------------
    latex_lines: List[str] = []
    latex_lines.append(r"\begin{table}[t]")
    latex_lines.append(r"\centering")
    latex_lines.append(rf"\caption{{{args.caption}}}")

    if args.label:
        latex_lines.append(rf"\label{{{args.label}}}")

    latex_lines.append(r"\begin{tabular}{lccccc}")
    latex_lines.append(r"\toprule")
    latex_lines.append(
        r"Dataset & Duration (h) & Percentile & Threshold (V/s) & Events/h & Samples (\%) \\"
    )
    latex_lines.append(r"\midrule")

    for _, row in df_all.iterrows():
        latex_lines.append(
            f"{row['dataset_id']} & "
            f"{row['recording_duration_h']} & "
            f"{row['threshold_value']} & "
            f"{row['threshold_vps_equivalent']} & "
            f"{row['events_per_hour']} & "
            f"{row['samples_in_event_pct']} \\\\"
        )

    latex_lines.append(r"\bottomrule")
    latex_lines.append(r"\end{tabular}")
    latex_lines.append(r"\end{table}")

    latex_path = os.path.join(out_dir, "events_table.tex")
    with open(latex_path, "w", encoding="utf-8") as f:
        f.write("\n".join(latex_lines))

    # -------------------------------------------------------------------------
    # Params for traceability
    # -------------------------------------------------------------------------
    params = {
        "stage": "latex_table_events",
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "datasets": args.datasets,
        "percentiles": args.percentiles,
        "validation_out_root": args.validation_out_root,
        "reporting_out_root": args.reporting_out_root,
        "run_id_requested": args.run_id,
        "sources": sources,
        "output_dir": out_dir,
    }
    write_json(os.path.join(out_dir, "params.json"), params)

    print("LaTeX table written to:")
    print(latex_path)
    print("Formatted CSV written to:")
    print(formatted_csv_path)
    print("Sources used:")
    for k, v in sources.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()