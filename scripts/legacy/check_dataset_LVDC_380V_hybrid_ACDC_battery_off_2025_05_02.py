#!/usr/bin/env python3
"""
check_dataset_LVDC_380V_hybrid_ACDC_battery_off_2025_05_02.py

Purpose
-------
Legacy exploratory script used during early inspection of the
original LVDC 380 V hybrid AC/DC dataset with the battery off (Dataset A).

This script scans the raw CSV, identifies relevant dV/dt excursions,
and generates diagnostic plots for manual inspection.

This script is kept for historical reference only.
It is NOT part of the reproducible Scientific Data pipeline
and is NOT called from run_all.sh.

Outputs
-------
If --save-figs is enabled, all generated outputs are written under:

    ../../out/legacy/lvdc_380v_battery_off_check/<RUN_ID>/

Usage
-----
From the script directory:

# Default configuration reproducing the original exploratory run
python3 check_dataset_LVDC_380V_hybrid_ACDC_battery_off_2025_05_02.py \
  ../../data/raw/LVDC_380V_hybrid_ACDC_battery_off_2025_05_02.csv \
  --dvdt-th 0.5 \
  --plot-top 10 \
  --window-s 300 \
  --save-figs

# Using the built-in default CSV path
python3 check_dataset_LVDC_380V_hybrid_ACDC_battery_off_2025_05_02.py \
  --dvdt-th 0.5 \
  --plot-top 10 \
  --window-s 300 \
  --save-figs

Notes
-----
- Default CSV path:
  ../../data/raw/LVDC_380V_hybrid_ACDC_battery_off_2025_05_02.csv
- Default parameters reproduce the original exploratory run.
- This script remains outside the main validation pipeline.
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import numpy as np
import pandas as pd


DEFAULT_CSV_PATH = "../../data/raw/LVDC_380V_hybrid_ACDC_battery_off_2025_05_02.csv"


def utc_timestamp_compact() -> str:
    """Return a compact UTC timestamp for output folders."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%MZ")


def _save_or_show(fig: Figure, out_path: str | None, save_figs: bool) -> None:
    """
    Save a figure if requested, otherwise keep it open for plt.show().
    """
    if save_figs:
        if out_path is None:
            raise ValueError("out_path is required when save_figs=True")
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Legacy exploratory check for the original LVDC 380 V battery-off dataset. "
            "It computes dV/dt, prints basic statistics, and optionally saves zoom plots."
        )
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        default=DEFAULT_CSV_PATH,
        help=(
            "Path to the CSV file "
            f"(default: {DEFAULT_CSV_PATH})."
        ),
    )
    parser.add_argument(
        "--time-col",
        default="Time",
        help="Time column name.",
    )
    parser.add_argument(
        "--v-col",
        default="NRE DCbus U",
        help="DC bus voltage column name.",
    )
    parser.add_argument(
        "--p-col",
        default="Nachladung P",
        help="Optional power column name.",
    )
    parser.add_argument(
        "--sep",
        default=",",
        help="CSV separator.",
    )
    parser.add_argument(
        "--dvdt-th",
        type=float,
        default=0.5,
        help="Event threshold in V/s used on |dV/dt| (default: 0.5).",
    )
    parser.add_argument(
        "--plot-top",
        type=int,
        default=10,
        help="Number of top events by |dV/dt| to inspect with zoom plots (default: 10).",
    )
    parser.add_argument(
        "--window-s",
        type=int,
        default=300,
        help="Half-window size in seconds around each selected event (default: 300).",
    )
    parser.add_argument(
        "--save-figs",
        action="store_true",
        help=(
            "If set, save figures under "
            "../../out/legacy/lvdc_380v_battery_off_check/<RUN_ID>/"
        ),
    )
    parser.add_argument(
        "--max-zoom-plots",
        type=int,
        default=20,
        help="Maximum number of zoom plots to generate (default: 20).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    out_dir: str | None = None
    if args.save_figs:
        run_id = utc_timestamp_compact()
        # Derive dataset name from CSV filename (without extension)
        csv_name = os.path.splitext(os.path.basename(args.csv_path))[0]

        # Resolve repository root based on this script location
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

        out_dir = os.path.join(repo_root, "out", "legacy", csv_name, run_id)
        os.makedirs(out_dir, exist_ok=True)

    df = pd.read_csv(args.csv_path, sep=args.sep)

    if args.time_col not in df.columns:
        raise ValueError(
            f"Could not find time column: {args.time_col}. "
            f"Available columns: {list(df.columns)}"
        )

    df[args.time_col] = pd.to_datetime(df[args.time_col], errors="coerce")
    df = df.dropna(subset=[args.time_col]).sort_values(args.time_col).reset_index(drop=True)

    if args.v_col not in df.columns:
        raise ValueError(
            f"Could not find voltage column: {args.v_col}. "
            f"Available columns: {list(df.columns)}"
        )

    v = pd.to_numeric(df[args.v_col], errors="coerce")
    t = df[args.time_col]

    dt = t.diff().dt.total_seconds()
    dv = v.diff()
    dvdt = dv / dt.replace(0, np.nan)

    df["dv_V"] = dv
    df["dt_s"] = dt
    df["dvdt_Vps"] = dvdt

    v_clean = v.dropna()
    dvdt_clean = dvdt.dropna()

    print("=== Voltage summary (V) ===")
    print(f"Samples: {len(v_clean)}")
    print(f"Min: {v_clean.min():.3f}  Max: {v_clean.max():.3f}  P2P: {(v_clean.max() - v_clean.min()):.3f}")
    print(f"Mean: {v_clean.mean():.3f}  Std: {v_clean.std():.3f}")

    print("\n=== dV/dt summary (V/s) ===")
    print(f"dV/dt samples: {len(dvdt_clean)}")
    print(f"Min: {dvdt_clean.min():.6f}  Max: {dvdt_clean.max():.6f}")
    print(f"Mean: {dvdt_clean.mean():.6f}  Std: {dvdt_clean.std():.6f}")
    print(f"P95(|dV/dt|): {np.percentile(np.abs(dvdt_clean), 95):.6f}")
    print(f"P99(|dV/dt|): {np.percentile(np.abs(dvdt_clean), 99):.6f}")

    events = df.index[np.abs(df["dvdt_Vps"]) >= args.dvdt_th].to_list()
    print(f"\n=== Events with |dV/dt| >= {args.dvdt_th} V/s ===")
    print(f"Count: {len(events)}")
    if events:
        print("First events:")
        for i in events[:10]:
            print(
                f"  {df.loc[i, args.time_col]}  "
                f"V={df.loc[i, args.v_col]:.3f}  "
                f"dV/dt={df.loc[i, 'dvdt_Vps']:.3f}"
            )

    if events:
        df_events = df.loc[events].copy()
        df_events["abs_dvdt"] = np.abs(df_events["dvdt_Vps"])
        df_top = df_events.sort_values("abs_dvdt", ascending=False).head(args.plot_top)

        print("\n=== Events with largest |dV/dt| ===")
        for _, row in df_top.iterrows():
            print(
                f"  {row[args.time_col]}  "
                f"V={row[args.v_col]:.3f}  "
                f"dV/dt={row['dvdt_Vps']:.3f}"
            )

        for k, (_, row) in enumerate(df_top.iterrows(), start=1):
            if k > args.max_zoom_plots:
                break

            t0 = row[args.time_col]
            t_start = t0 - pd.Timedelta(seconds=args.window_s)
            t_end = t0 + pd.Timedelta(seconds=args.window_s)

            w = df[(df[args.time_col] >= t_start) & (df[args.time_col] <= t_end)].copy()
            if w.empty:
                continue

            fig, ax = plt.subplots()
            ax.plot(w[args.time_col], pd.to_numeric(w[args.v_col], errors="coerce"), label=args.v_col)
            ax.axvline(t0, linestyle="--", label="event")
            ax.set_title(f"Zoom V around event #{k} ({t0})")
            ax.set_xlabel("Time")
            ax.set_ylabel("Voltage (V)")
            ax.grid(True)
            ax.legend()

            out_path = os.path.join(out_dir, f"zoom_{k:02d}_V.png") if args.save_figs and out_dir else None
            _save_or_show(fig, out_path, args.save_figs)

            fig, ax = plt.subplots()
            ax.plot(w[args.time_col], w["dvdt_Vps"], label="dV/dt (V/s)")
            ax.axhline(args.dvdt_th, linestyle="--", label="threshold")
            ax.axhline(-args.dvdt_th, linestyle="--")
            ax.axvline(t0, linestyle="--", label="event")
            ax.set_title(f"Zoom dV/dt around event #{k} ({t0})")
            ax.set_xlabel("Time")
            ax.set_ylabel("dV/dt (V/s)")
            ax.grid(True)
            ax.legend()

            out_path = os.path.join(out_dir, f"zoom_{k:02d}_dvdt.png") if args.save_figs and out_dir else None
            _save_or_show(fig, out_path, args.save_figs)

            if args.p_col in df.columns:
                pwr = pd.to_numeric(w[args.p_col], errors="coerce")
                fig, ax = plt.subplots()
                ax.plot(w[args.time_col], pwr, label=args.p_col)
                ax.axvline(t0, linestyle="--", label="event")
                ax.set_title(f"Zoom Power around event #{k} ({t0})")
                ax.set_xlabel("Time")
                ax.set_ylabel("Power")
                ax.grid(True)
                ax.legend()

                out_path = (
                    os.path.join(out_dir, f"zoom_{k:02d}_power.png") if args.save_figs and out_dir else None
                )
                _save_or_show(fig, out_path, args.save_figs)

    if not args.save_figs:
        fig, ax = plt.subplots()
        ax.plot(t, v, label=args.v_col)
        ax.set_title("DC bus voltage")
        ax.set_xlabel("Time")
        ax.set_ylabel("Voltage (V)")
        ax.grid(True)
        ax.legend()

        fig, ax = plt.subplots()
        ax.plot(t, dvdt, label="dV/dt (V/s)")
        ax.axhline(args.dvdt_th, linestyle="--", label="threshold")
        ax.axhline(-args.dvdt_th, linestyle="--")
        ax.set_title("Voltage derivative")
        ax.set_xlabel("Time")
        ax.set_ylabel("dV/dt (V/s)")
        ax.grid(True)
        ax.legend()

        if args.p_col in df.columns:
            pwr = pd.to_numeric(df[args.p_col], errors="coerce")
            fig, ax = plt.subplots()
            ax.plot(t, pwr, label=args.p_col)
            ax.set_title("Power (reference)")
            ax.set_xlabel("Time")
            ax.set_ylabel("Power")
            ax.grid(True)
            ax.legend()

        plt.show()

    if args.save_figs and out_dir:
        print(f"\nSaved plots to: {out_dir}")


if __name__ == "__main__":
    main()
