"""
04_generate_dataset_overview_figures.py

Dataset overview figures for the LVDC real-world datasets
(Scientific Data - Input datasets / Data overview support)

Purpose
-------
This script generates compact, paper-ready figures to support the description
of the input datasets.

It produces:

1) A raw signal overview figure showing the DC bus voltage and representative
   power-related channels over a short time window.
2) A variable-category distribution figure showing the number of variables
   grouped by broad signal type.

Why this script is included
---------------------------
The manuscript describes real-world LVDC time-series datasets. A compact visual
overview helps readers understand the structure and content of the CSV files
before the validation and usage-example sections.

The figures are descriptive only. They are not intended to provide event
detection, statistical validation, or machine learning results.

Inputs
------
- Dataset configuration from configs/datasets.yaml (A/B)
- CSV referenced by the dataset config

Outputs
-------
Writes outputs to:
  out/reporting/<run_id>/dataset_overview/

For each dataset:
  - raw_signals_<dataset_id>.svg
  - raw_signals_<dataset_id>.pdf
  - variable_distribution_<dataset_id>.svg
  - variable_distribution_<dataset_id>.pdf
  - variable_categories_<dataset_id>.csv
  - params_<dataset_id>.json

usage
-----

this script generates two types of figures for each dataset:

1) variable distribution (bar chart)
2) raw signal overview (time-series)

it is designed to be executed from run_all.sh as part of the reporting stage.


example standalone usage
------------------------

# Dataset A, intended as the upper panel in a stacked A/B figure
python3 -m scripts.reporting.04_generate_dataset_overview_figures \
  --dataset-id A \
  --run-id test_overview_A \
  --window-start-time "2025-05-02 15:15:00" \
  --window-s 600 \
  --power-cols "NRE K4 P1,NRE K6 P1" \
  --time-axis elapsed \
  --hide-xaxis-label \
  --hide-legend \
  --vbus-margin 1.0 \
  --power-margin-frac 0.10 \
  --plot-formats svg,pdf \
  --font-size 11 \
  --title-font-delta 2 \
  --tick-font-delta -1 \
  --line-width 1.4 \
  --raw-fig-width 8.0 \
  --raw-fig-height 3.3 \
  --dist-fig-width 7.0 \
  --dist-fig-height 2.2

# Dataset B, intended as the lower panel in a stacked A/B figure
python3 -m scripts.reporting.04_generate_dataset_overview_figures \
  --dataset-id B \
  --run-id test_overview_B \
  --window-start-time "2024-05-10 17:25:00" \
  --window-s 600 \
  --power-cols "NRE K4 P1,NRE K6 P1" \
  --time-axis elapsed \
  --vbus-margin 1.0 \
  --power-margin-frac 0.10 \
  --plot-formats svg,pdf \
  --font-size 11 \
  --title-font-delta 2 \
  --tick-font-delta -1 \
  --line-width 1.4 \
  --raw-fig-width 8.0 \
  --raw-fig-height 3.3 \
  --dist-fig-width 7.0 \
  --dist-fig-height 2.2


notes
-----

- the raw signal figure is intentionally compact to fit paper layouts.
- the top panel shows the DC bus voltage with a focused Y-axis range.
- the bottom panel shows representative power channels using a shared Y-axis.
- the selected time window should be representative of signal behaviour, without
  adding event annotations or detection markers.
- when A and B are stacked in the paper, Dataset A can be generated without
  x-axis labels and legend, while Dataset B keeps the relative time axis and legend.
- the elapsed time axis is relative to the beginning of each selected window.
- variable distribution excludes time and unclassified variables to improve clarity.


why
---

these figures are intended to:

- provide a clear overview of the dataset structure (variable distribution)
- illustrate the typical behaviour of key signals without focusing on specific events
- complement the event-driven analysis presented in the Usage Notes section

this separation avoids duplication between dataset description and usage examples.
"""

import argparse
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import StrMethodFormatter
import matplotlib.dates as mdates

from scripts.common.io_config import (
    ensure_dir,
    load_csv,
    load_dataset_config,
    make_run_id,
)


POWER_LABELS = {
    "NRE K1 P1": "NRE K1 P1 (W)",
    "NRE K4 P1": "NRE K4 P1 (W)",
    "NRE K6 P1": "NRE K6 P1 (W)",
    "Nachladung P": "Nachladung P (W)",
}

DEFAULT_POWER_COLS = [
    "NRE K4 P1",
    "NRE K6 P1",
]

CATEGORY_ORDER = [
    "DC-side measurements",
    "AC-side measurements",
    "Battery-related variables",
    "Status / diagnostic variables",
]

CATEGORY_COLORS = {
    "DC-side measurements": "#4C78A8",
    "AC-side measurements": "#F58518",
    "Battery-related variables": "#54A24B",
    "Status / diagnostic variables": "#B279A2",
}

def _resolve_power_columns( cfg: dict, df: pd.DataFrame, power_cols_arg: str | None = None,) -> list[str]:
    """
    Resolve representative power-related columns for the raw signal figure.
    """
    if power_cols_arg:
        cols = [c.strip() for c in power_cols_arg.split(",") if c.strip()]
    elif isinstance(cfg, dict) and cfg.get("power_cols_candidates"):
        cols = [str(c) for c in cfg["power_cols_candidates"]]
    elif isinstance(cfg, dict) and cfg.get("power_col"):
        cols = [str(cfg["power_col"])]
    else:
        cols = DEFAULT_POWER_COLS

    return [c for c in cols if c in df.columns]


def _categorize_column(col: str) -> str:
    """
    Categorize one column using explicit naming rules.

    The rules are based on the column naming conventions in the CSV headers.
    This keeps the figure reproducible and avoids manual classification.
    """
    if col == "Time":
        return "Other variables"

    if col.startswith("BAT"):
        return "Battery-related variables"

    if (
        col.startswith("NRE")
        or col.startswith("PV ")
        or col.startswith("Nachladung")
        or col.startswith("DC ")
    ):
        return "DC-side measurements"

    if (
        col.startswith("P_ges")
        or col.startswith("LF_ges")
        or col.startswith("S_ges")
        or col.startswith("I_L")
        or col.startswith("I_N")
        or col.startswith("U_L")
        or col.startswith("FQ_")
        or col.startswith("Netz")
    ):
        return "AC-side measurements"

    if (
        "Status" in col
        or "Stat" in col
        or "ISO" in col
        or "RlSt" in col
    ):
        return "Status / diagnostic variables"

    return "Other variables"


def _build_variable_category_table(columns: list[str]) -> pd.DataFrame:
    """
    Build a traceable column-level category table.

    Time and unclassified variables are excluded from the plotting categories
    to keep the overview figure focused on measured signals.
    """
    rows = []
    for col in columns:
        if col == "Time":
            continue

        category = _categorize_column(col)
        if category == "Other variables":
            continue

        rows.append({
            "column": col,
            "category": category,
        })

    return pd.DataFrame(rows)


def _select_time_window(df: pd.DataFrame, t: pd.Series, args: argparse.Namespace) -> tuple[pd.DataFrame, pd.Series]:
    """
    Select a deterministic time window for the raw signal overview.
    """
    if args.window_start_time:
        start_time = pd.to_datetime(args.window_start_time, errors="coerce")
        if pd.isna(start_time):
            raise RuntimeError(f"Invalid --window-start-time: {args.window_start_time}")
    else:
        start_time = t.iloc[0]

    end_time = start_time + pd.Timedelta(seconds=float(args.window_s))

    win_mask = (t >= start_time) & (t <= end_time)
    df_win = df.loc[win_mask].reset_index(drop=True)
    t_win = t.loc[win_mask].reset_index(drop=True)

    if len(t_win) < 3:
        raise RuntimeError(
            "Selected window has fewer than 3 samples. "
            "Try increasing --window-s or changing --window-start-time."
        )

    return df_win, t_win


def _plot_raw_signals(
    out_dir: str,
    df: pd.DataFrame,
    time_col: str,
    time_format: str,
    vbus_col: str,
    power_cols: list[str],
    dataset_id: str,
    args: argparse.Namespace,
):
    """
    Plot a compact raw signal overview for one dataset.
    """
    if vbus_col not in df.columns:
        raise RuntimeError(f"Vbus column not found: {vbus_col}")

    if not power_cols:
        raise RuntimeError(
            "No representative power columns found. "
            "Check power_cols_candidates in configs/datasets.yaml."
        )

    t = pd.to_datetime(df[time_col], format=time_format, errors="coerce")
    vbus = pd.to_numeric(df[vbus_col], errors="coerce")

    valid_rows = t.notna() & vbus.notna()
    t = t.loc[valid_rows].reset_index(drop=True)
    df = df.loc[valid_rows].reset_index(drop=True)

    if len(t) < 3:
        raise RuntimeError("Not enough valid samples after filtering invalid timestamps/values.")

    df_win, t_win = _select_time_window(df=df, t=t, args=args)

    if args.time_axis == "elapsed":
        x_values = (t_win - t_win.iloc[0]).dt.total_seconds() / 60.0
        x_label = "Relative time (min)"
    else:
        x_values = t_win
        x_label = "Time"

    # --- Font sizes ---
    base_fs = float(args.font_size)

    # Ticks
    tick_fs = base_fs + args.tick_font_delta

    # Axis labels
    label_fs = tick_fs + 3.0

    vbus_color = "#4C78A8" # blue
    power_colors = {
        "NRE K1 P1": "#B279A2",  # K1 purple
        "NRE K4 P1": "#F58518",  # K4 orange
        "NRE K6 P1": "#54A24B",  # K6 green
    }

    fig, axes = plt.subplots(
        nrows=2,
        ncols=1,
        sharex=True,
        figsize=(float(args.raw_fig_width), float(args.raw_fig_height)),
        gridspec_kw={"height_ratios": [1.0, 1.0]},
    )

    # ------------------------------------------------------------
    # Panel 1: DC bus voltage
    # ------------------------------------------------------------
    ax0 = axes[0]

    vbus_values = pd.to_numeric(df_win[vbus_col], errors="coerce")
    ax0.plot(
        x_values,
        vbus_values,
        linewidth=float(args.line_width),
        color=vbus_color,
    )

    ax0.set_ylabel("Vbus (V)", fontsize=label_fs)
    ax0.tick_params(axis="both", labelsize=tick_fs)
    ax0.grid(True, alpha=0.25)
    ax0.yaxis.set_major_formatter(StrMethodFormatter("{x:.0f}"))

    vmin = float(np.nanmin(vbus_values))
    vmax = float(np.nanmax(vbus_values))
    if np.isfinite(vmin) and np.isfinite(vmax) and vmax > vmin:
        margin = float(args.vbus_margin)
        ax0.set_ylim(vmin - margin, vmax + margin)

    # ------------------------------------------------------------
    # Panel 2: representative power channels
    # ------------------------------------------------------------
    ax1 = axes[1]

    power_values_all = []

    for idx, col in enumerate(power_cols):
        values = pd.to_numeric(df_win[col], errors="coerce")
        power_values_all.append(values.to_numpy(dtype=float))

        ax1.plot(
            x_values,
            values,
            linewidth=float(args.line_width),
            color=power_colors.get(col, None),
            label=POWER_LABELS.get(col, col),
        )

    ax1.set_ylabel("Power (W)", fontsize=label_fs)
    if args.hide_xaxis_label:
        ax1.set_xlabel("")
        ax1.tick_params(axis="x", which="both", bottom=False, labelbottom=False)
    else:
        ax1.set_xlabel(x_label, fontsize=label_fs, labelpad=7)
        ax1.tick_params(axis="both", labelsize=tick_fs)
    
    ax1.grid(True, alpha=0.25)
    ax1.yaxis.set_major_formatter(StrMethodFormatter("{x:.0f}"))

    if power_values_all:
        power_concat = np.concatenate(power_values_all)
        pmin = float(np.nanmin(power_concat))
        pmax = float(np.nanmax(power_concat))

        if np.isfinite(pmin) and np.isfinite(pmax) and pmax > pmin:
            margin = max((pmax - pmin) * float(args.power_margin_frac), 2.0)
            ax1.set_ylim(pmin - margin, pmax + margin)

    if not args.hide_legend:
        ax1.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, -0.70),
            ncol=len(power_cols),
            fontsize=tick_fs,
            frameon=False,
        )

    for ax in axes:
        ax.tick_params(axis="x", labelrotation=0, labelsize=tick_fs)

    if args.time_axis == "clock":
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        
    if args.hide_xaxis_label:
        ax1.set_xlabel("")
        ax1.tick_params(axis="x", which="both", bottom=False, labelbottom=False)

    fig.align_ylabels(axes)
    fig.tight_layout(rect=(0.0, 0.11, 1.0, 1.0))

    formats = [f.strip().lower() for f in str(args.plot_formats).split(",") if f.strip()]
    for fmt in formats:
        fig_path = os.path.join(out_dir, f"raw_signals_{dataset_id}.{fmt}")
        fig.savefig(fig_path, bbox_inches="tight")

    plt.close(fig)


def _plot_variable_distribution(
    out_dir: str,
    cat_table: pd.DataFrame,
    dataset_id: str,
    args: argparse.Namespace,
):
    """
    Plot a compact horizontal bar chart of variable categories.
    """
    counts = (
        cat_table["category"]
        .value_counts()
        .reindex(CATEGORY_ORDER)
        .dropna()
        .astype(int)
    )
    counts = counts[counts > 0]

    # --- Font sizes ---
    base_fs = float(args.font_size)

    # Ticks
    tick_fs = base_fs + args.tick_font_delta

    # Axis labels
    label_fs = tick_fs + 6.0

    fig, ax = plt.subplots( figsize=(float(args.dist_fig_width), float(args.dist_fig_height)))

    y_pos = np.arange(len(counts))
    counts_np = counts.to_numpy()
    bar_colors = [CATEGORY_COLORS.get(cat, "#9D9D9D") for cat in counts.index]
    ax.barh(y_pos, counts_np, color=bar_colors)
    
    ax.set_yticks(y_pos)
    y_label_fs = tick_fs + 4.0
    ax.set_yticklabels(counts.index, fontsize=y_label_fs)
    ax.invert_yaxis()

    ax.set_xlabel("Number of variables", fontsize=label_fs)
    ax.tick_params(axis="x", labelsize=tick_fs)
    ax.grid(True, axis="x", alpha=0.25)

    for i, value in enumerate(counts_np):
        ax.text(
            value + 0.2,
            i,
            str(value),
            va="center",
            fontsize=base_fs,
        )

    ax.set_xlim(0, max(counts_np) + 3)

    fig.tight_layout(rect=(0.0, 0.0, 1.0, 1.0))

    formats = [f.strip().lower() for f in str(args.plot_formats).split(",") if f.strip()]
    for fmt in formats:
        fig_path = os.path.join(out_dir, f"variable_distribution_{dataset_id}.{fmt}")
        fig.savefig(fig_path, bbox_inches="tight")

    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--out-root", type=str, default="out", help="Output root folder (default: out).")
    parser.add_argument(
        "--window-s",
        type=float,
        default=300.0,
        help="Time window length in seconds for the raw signal overview (default: 300).",
    )
    parser.add_argument(
        "--time-axis",
        type=str,
        default="clock",
        choices=["clock", "elapsed"],
        help="X-axis mode for raw signal plots: clock time or elapsed minutes.",
    )
    parser.add_argument(
        "--hide-xaxis-label",
        action="store_true",
        help="Hide x-axis ticks and label for stacked upper figures.",
    )
    parser.add_argument(
        "--hide-legend",
        action="store_true",
        help="Hide legend for stacked upper figures.",
    )
    parser.add_argument(
        "--plot-formats",
        type=str,
        default="svg,pdf",
        help="Comma-separated formats for generated figures (default: svg,pdf).",
    )
    parser.add_argument(
        "--font-size",
        type=float,
        default=11.0,
        help="Base font size for the plots (default: 11).",
    )
    parser.add_argument(
        "--title-font-delta",
        type=float,
        default=2.0,
        help="Kept for consistency with other plotting scripts (default: +2).",
    )
    parser.add_argument(
        "--tick-font-delta",
        type=float,
        default=-1.0,
        help="Delta added to base font size for tick labels (default: -1).",
    )
    parser.add_argument(
        "--line-width",
        type=float,
        default=1.4,
        help="Line width for plotted signals (default: 1.4).",
    )
    parser.add_argument(
        "--window-start-time",
        type=str,
        default=None,
        help="Start timestamp for the raw signal overview window.",
    )
    parser.add_argument(
        "--power-cols",
        type=str,
        default=None,
        help="Comma-separated power columns for the raw signal overview.",
    )
    parser.add_argument(
        "--vbus-margin",
        type=float,
        default=0.5,
        help="Voltage axis margin in V for the raw signal overview.",
    )
    parser.add_argument(
        "--power-margin-frac",
        type=float,
        default=0.08,
        help="Relative Y-axis margin for the power panel.",
    )
    parser.add_argument(
        "--raw-fig-width",
        type=float,
        default=8.0,
        help="Raw signal figure width in inches.",
    )
    parser.add_argument(
        "--raw-fig-height",
        type=float,
        default=3.0,
        help="Raw signal figure height in inches.",
    )
    parser.add_argument(
        "--dist-fig-width",
        type=float,
        default=7.0,
        help="Variable distribution figure width in inches.",
    )
    parser.add_argument(
        "--dist-fig-height",
        type=float,
        default=2.2,
        help="Variable distribution figure height in inches.",
    )
    args = parser.parse_args()

    # --- Load dataset ---
    cfg = load_dataset_config(args.dataset_id)
    df = load_csv(cfg)

    time_col = cfg["time_col"]
    time_format = cfg["time_format"]
    vbus_col = cfg["vbus_col"]

    # --- Output directory ---
    run_id = args.run_id if args.run_id else make_run_id()
    out_dir = os.path.join(args.out_root, "reporting", run_id, "dataset_overview")
    ensure_dir(out_dir)

    # --- Resolve representative signal columns ---
    power_cols = _resolve_power_columns( cfg=cfg, df=df, power_cols_arg=args.power_cols)

    # --- Generate raw signal overview ---
    _plot_raw_signals(
        out_dir=out_dir,
        df=df,
        time_col=time_col,
        time_format=time_format,
        vbus_col=vbus_col,
        power_cols=power_cols,
        dataset_id=args.dataset_id,
        args=args,
    )

    # --- Generate variable distribution figure ---
    cat_table = _build_variable_category_table(list(df.columns))

    cat_csv_path = os.path.join(out_dir, f"variable_categories_{args.dataset_id}.csv")
    cat_table.to_csv(cat_csv_path, index=False)

    _plot_variable_distribution(
        out_dir=out_dir,
        cat_table=cat_table,
        dataset_id=args.dataset_id,
        args=args,
    )

    # --- Save parameters ---
    params = {
        "dataset_id": args.dataset_id,
        "run_id": run_id,
        "time_col": time_col,
        "vbus_col": vbus_col,
        "power_cols": power_cols,
        "window_s": float(args.window_s),
        "time_axis": args.time_axis,
        "plot_formats": str(args.plot_formats),
        "font_size": float(args.font_size),
        "title_font_delta": float(args.title_font_delta),
        "tick_font_delta": float(args.tick_font_delta),
        "line_width": float(args.line_width),
        "category_order": CATEGORY_ORDER,
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_start_time": args.window_start_time,
        "power_cols_arg": args.power_cols,
        "vbus_margin": float(args.vbus_margin),
        "power_margin_frac": float(args.power_margin_frac),
        "raw_fig_width": float(args.raw_fig_width),
        "raw_fig_height": float(args.raw_fig_height),
        "dist_fig_width": float(args.dist_fig_width),
        "dist_fig_height": float(args.dist_fig_height),
    }

    with open(os.path.join(out_dir, f"params_{args.dataset_id}.json"), "w") as f:
        json.dump(params, f, indent=2)

    print("Dataset overview figures written to:")
    formats = [f.strip().lower() for f in str(args.plot_formats).split(",") if f.strip()]
    for fmt in formats:
        print(os.path.join(out_dir, f"raw_signals_{args.dataset_id}.{fmt}"))
        print(os.path.join(out_dir, f"variable_distribution_{args.dataset_id}.{fmt}"))

    print("Variable category table written to:")
    print(cat_csv_path)

    print("Parameters written to:")
    print(os.path.join(out_dir, f"params_{args.dataset_id}.json"))


if __name__ == "__main__":
    main()