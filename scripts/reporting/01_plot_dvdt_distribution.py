"""
01_plot_dvdt_distribution.py

Generate distribution figures for |dV/dt| (absolute voltage slope) for one or more datasets.

Why this exists
---------------
In Technical Validation we want to:
- Show the empirical distribution of |dV/dt| derived from real timestamps.
- Justify percentile-based thresholds used for simple transient detection.
- Compare unbuffered (A) vs buffered (B) operation, and optionally dataset C.

Two plot modes are supported:
- hist: histogram (density) plotted as step lines (clean in PDF/SVG)
- ccdf: complementary CDF, P(|dV/dt| >= x), which is robust and highlights tails

Important notes
---------------
- dV/dt uses the raw sampling (no resampling).
- If dt = 0 (duplicate timestamps), dV/dt becomes inf. We filter non-finite values.
- For visualization, we clip the x-axis to a high percentile to avoid outliers
  compressing the plot. This does not change computed percentiles; it only
  changes the displayed range.

Usage examples (run from repository root)
-----------------------------------------
Stacked CCDF (recommended for the paper), log-y, with percentile legend:
    python3 -m scripts.reporting.01_plot_dvdt_distribution \
        --datasets A B \
        --mode ccdf \
        --log-y \
        --font-size 11 \
        --title-font-delta 2 \
        --tick-font-delta -1 \
        --line-width 1.4 \
        --marker-line-width 1.6 \
        --legend \
        --legend-font-delta -1 \
        --legend-bbox 0.5,-0.01

Stacked histogram (density), log-y, with percentile legend:
    python3 -m scripts.reporting.01_plot_dvdt_distribution \
        --datasets A B \
        --mode hist \
        --log-y \
        --bins 200 \
        --font-size 11 \
        --title-font-delta 2 \
        --tick-font-delta -1 \
        --line-width 1.4 \
        --marker-line-width 1.6 \
        --legend \
        --legend-font-delta -1 \
        --legend-bbox 0.5,-0.01

Outputs:
- out/reporting/<run_id>/figures/dvdt_distribution_hist_stacked.svg
- out/reporting/<run_id>/figures/dvdt_distribution_hist_stacked.pdf
- out/reporting/<run_id>/figures/dvdt_distribution_ccdf_stacked.svg
- out/reporting/<run_id>/figures/dvdt_distribution_ccdf_stacked.pdf
"""

import os
import argparse
from datetime import datetime, timezone
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from scripts.common.io_config import load_dataset_config, load_csv


# -----------------------------------------------------------------------------
# Filesystem helpers
# -----------------------------------------------------------------------------

def ensure_dir(path: str) -> None:
    """
    Create a directory if it does not exist.

    We keep this small helper local so the script remains self-contained.
    """
    if not os.path.exists(path):
        os.makedirs(path)


def utc_timestamp_compact() -> str:
    """
    Compact UTC timestamp used as run identifier prefix.
    Example: 2026-02-22_2034Z
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%MZ")


# -----------------------------------------------------------------------------
# Signal processing helpers
# -----------------------------------------------------------------------------

def compute_dvdt_abs(df: pd.DataFrame, time_col: str, v_col: str) -> np.ndarray:
    """
    Compute |dV/dt| from a dataframe using real timestamp differences.

    Parameters
    ----------
    df:
        DataFrame that contains at least time_col and v_col.
    time_col:
        Timestamp column name (already parsed to datetime by load_csv()).
    v_col:
        Voltage column name.

    Returns
    -------
    dvdt_abs:
        Numpy array of finite |dV/dt| values (V/s).

    Notes
    -----
    - dt is computed from consecutive timestamps.
    - If dt == 0, dv/dt becomes inf; we remove non-finite values.
    - No filtering, smoothing, or resampling is applied.
    """
    # Timestamps should already be datetime due to load_csv(), but we keep a safe conversion.
    t = pd.to_datetime(df[time_col], errors="coerce")

    # Voltage may be numeric already, but coercion avoids silent issues if the CSV has strings.
    v = pd.to_numeric(df[v_col], errors="coerce")

    # dV and dt between consecutive samples
    dt = t.diff().dt.total_seconds()
    dv = v.diff()

    dvdt = dv / dt
    dvdt_abs = dvdt.abs()

    # Convert to numpy and keep only finite values (remove NaN/inf)
    arr = dvdt_abs.to_numpy(dtype=float)
    arr = arr[np.isfinite(arr)]

    return arr


def compute_ccdf(x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute CCDF: P(X >= x) for sorted sample values.

    This representation is often easier to compare tails than histograms because it
    does not require choosing bins.

    Parameters
    ----------
    x:
        1D numpy array of samples (already finite).

    Returns
    -------
    xs:
        Sorted x values.
    ccdf:
        CCDF values in [0, 1], same length as xs.
    """
    xs = np.sort(x)
    n = len(xs)
    # For each sorted point i: proportion of samples >= xs[i]
    ccdf = (n - np.arange(n)) / float(n)
    return xs, ccdf


# -----------------------------------------------------------------------------
# Plot helpers
# -----------------------------------------------------------------------------

def compute_thresholds(
    dvdt_by_ds: Dict[str, np.ndarray],
    percentiles_to_mark: List[float],
) -> Dict[str, Dict[float, float]]:
    """
    Compute percentile thresholds for each dataset for later annotation.

    Returns
    -------
    thr_by_ds:
        Mapping: dataset_id -> {percentile -> threshold_value}
    """
    thr_by_ds: Dict[str, Dict[float, float]] = {}
    for dataset_id, x in dvdt_by_ds.items():
        thr_by_ds[dataset_id] = {}
        for p in percentiles_to_mark:
            thr_by_ds[dataset_id][p] = float(np.percentile(x, p))
    return thr_by_ds


def compute_common_xmax(
    dvdt_by_ds: Dict[str, np.ndarray],
    x_max_percentile: float,
) -> float:
    """
    Choose a common x-axis upper bound for visualization.

    We use a high percentile per dataset and then take the maximum across datasets.
    This avoids outliers (rare extreme values) making the plot unreadable.

    This is a visualization choice only; it does not change the data or thresholds.
    """
    xmax_candidates: List[float] = []
    for _, x in dvdt_by_ds.items():
        xmax_candidates.append(float(np.percentile(x, x_max_percentile)))
    x_max = max(xmax_candidates) * 1.05
    return x_max


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main() -> None:

    parser = argparse.ArgumentParser()

    parser.add_argument("--datasets", nargs="+", required=True,
                        help="List of dataset IDs to include, e.g., A B C")

    parser.add_argument("--mode", choices=["hist", "ccdf"], default="hist",
                        help="Plot mode: 'hist' (histogram density) or 'ccdf'")

    parser.add_argument("--bins", type=int, default=150,
                        help="Number of bins for histogram mode")

    parser.add_argument("--x-max-percentile", type=float, default=99.95,
                        help="Percentile used to clip the x-axis for visualization")

    parser.add_argument("--font-size", type=int, default=11)
    parser.add_argument("--fig-width", type=float, default=7.0)
    parser.add_argument("--fig-height", type=float, default=7.0)

    # For distribution tails this is typically needed; we keep it optional.
    parser.add_argument("--log-y", action="store_true",
                        help="Use log scale on y-axis")
    
    parser.add_argument("--legend", action="store_true",
                    help="Add a global legend for percentile markers")

    parser.add_argument("--legend-fontsize", type=int, default=10,
                        help="Legend font size")

    parser.add_argument("--legend-loc", type=str, default="lower center",
                        help="Legend location (matplotlib loc string)")

    parser.add_argument("--legend-bbox", type=str, default="0.5,-0.01",
                        help="Legend bbox_to_anchor as 'x,y'")
    
    parser.add_argument("--line-width", type=float, default=1.4,
                    help="Main curve line width")

    parser.add_argument("--marker-line-width", type=float, default=1.6,
                        help="Percentile marker line width")

    parser.add_argument("--title-font-delta", type=int, default=2,
                        help="Title fontsize = font_size + delta")

    parser.add_argument("--tick-font-delta", type=int, default=-1,
                        help="Tick fontsize = font_size + delta")

    parser.add_argument("--legend-font-delta", type=int, default=-1,
                        help="Legend fontsize = font_size + delta")

    args = parser.parse_args()

    # Output folder (one run folder for all datasets plotted together)
    run_id = utc_timestamp_compact()
    out_dir = os.path.join("out", "reporting", run_id, "figures")
    ensure_dir(out_dir)

    # Consistent styling for reproducibility across runs
    plt.rcParams.update({"font.size": args.font_size})

    # Percentiles shown as vertical lines
    #percentiles_to_mark = [99.0, 99.5, 99.9, 99.95]
    percentiles_to_mark = [99.9, 99.95]
    
    # Dataset curve styling (fixed colors for reproducibility)
    dataset_style = {
        "A": {"color": "#0072B2", "label": "Dataset A"},
        "B": {"color": "#D55E00", "label": "Dataset B"},
        "C": {"color": "#009E73", "label": "Dataset C"},
    }
    # Compact subplot titles for paper-ready figures
    panel_title = {
        "A": "(a) battery OFF",
        "B": "(b) battery ON",
        "C": "(c) complementary",
    }
    # Percentile marker styling (fixed colors for reproducibility)
    percentile_style = {
        99.9: {"color": "#CC79A7", "label": "p99.9"},
        99.95: {"color": "#000000", "label": "p99.95"},
    }

    # -------------------------------------------------------------------------
    # Load data and compute |dV/dt|
    # -------------------------------------------------------------------------
    dvdt_by_ds: Dict[str, np.ndarray] = {}

    for dataset_id in args.datasets:
        cfg = load_dataset_config(dataset_id)
        df = load_csv(cfg)

        dvdt_abs = compute_dvdt_abs(df, cfg["time_col"], cfg["vbus_col"])
        dvdt_by_ds[dataset_id] = dvdt_abs

        # Optional console trace: shows how many samples are finite after filtering
        total_pairs = max(len(df) - 1, 0)
        print(f"{dataset_id}: dvdt samples total={total_pairs}, finite={len(dvdt_abs)}")

    # Thresholds and common x-axis limit for clean visualization
    thr_by_ds = compute_thresholds(dvdt_by_ds, percentiles_to_mark)
    x_max = compute_common_xmax(dvdt_by_ds, float(args.x_max_percentile))

    # -------------------------------------------------------------------------
    # Create stacked figure (one subplot per dataset)
    # -------------------------------------------------------------------------
    fig, axes = plt.subplots(
        nrows=len(args.datasets),
        ncols=1,
        sharex=True,
        figsize=(args.fig_width, args.fig_height),
    )

    # When only one dataset is plotted, axes is not a list; normalize it.
    if len(args.datasets) == 1:
        axes = [axes]

    # -------------------------------------------------------------------------
    # Plot per dataset
    # -------------------------------------------------------------------------
    for ax, dataset_id in zip(axes, args.datasets):

        x = dvdt_by_ds[dataset_id]
        # Clip only for visualization
        x_vis = x[(x >= 0) & (x <= x_max)]

        if args.mode == "hist":
            # Step histogram is clean in vector formats and does not hide tails
            style_ds = dataset_style.get(dataset_id, {})
            ax.hist(
                x_vis,
                bins=int(args.bins),
                density=True,
                histtype="step",
                linewidth=1.0,
                color=style_ds.get("color", None),
            )
            ax.set_ylabel("Density", fontsize=int(args.font_size) + 1)


        else:
            xs, ccdf = compute_ccdf(x_vis)
            style_ds = dataset_style.get(dataset_id, {})
            ax.plot(
                xs,
                ccdf,
                linewidth=1.0,
                color=style_ds.get("color", None),
            )
            ax.set_ylabel("P(|dV/dt| ≥ x)", fontsize=int(args.font_size) + 1)

        # Percentile markers (p99.9 and p99.95) with distinct colors
        for p in percentiles_to_mark:
            thr = thr_by_ds[dataset_id][p]
            style_p = percentile_style.get(p, {})

            # Visual hierarchy:
            # p99.95 = main extreme threshold (thicker)
            # p99.9  = secondary extreme threshold (thinner)
            if p == 99.95:
                lw = float(args.marker_line_width) + 0.6
                alpha_val = 1.0
            else:
                lw = float(args.marker_line_width) - 0.6
                alpha_val = 0.8

            ax.axvline(
                thr,
                linestyle="--",
                linewidth=lw,
                color=style_p.get("color", "black"),
                alpha=alpha_val,
                label=style_p.get("label", f"p{p}") if args.legend else None,
            )

        # Compact panel label inside each subplot (paper-style)
        ax.text(
            0.08,
            0.96,
            panel_title.get(dataset_id, dataset_id),
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=int(args.font_size) + int(args.title_font_delta) - 1,
        )
        # Tick label size slightly smaller than axis labels
        tick_fs = int(args.font_size) + int(args.tick_font_delta)
        ax.tick_params(axis="both", labelsize=tick_fs)

        if args.log_y:
            ax.set_yscale("log")

    axes[-1].set_xlabel("|dV/dt| (V/s)", fontsize=int(args.font_size) + 1)
    axes[-1].set_xlim(left=0.0, right=x_max)

    # Global figure title
    if args.mode == "ccdf":
        fig.text(
            0.5,
            0.925,
            "Empirical |dV/dt| tail distribution",
            ha="center",
            va="bottom",
            fontsize=int(args.font_size) + int(args.title_font_delta) + 2,
        )
    else:
        fig.text(
            0.5,
            0.925,
            "Empirical |dV/dt| distribution",
            ha="center",
            va="bottom",
            fontsize=int(args.font_size) + int(args.title_font_delta) + 2,
        )

    fig.tight_layout(rect=(0.0, 0.02, 1.0, 0.90))
    fig.subplots_adjust(hspace=0.16)

    if args.legend:
        handles, labels = [], []
        for ax in axes:
            h, l = ax.get_legend_handles_labels()
            handles.extend(h)
            labels.extend(l)

        # Deduplicate labels keeping first occurrence
        seen = set()
        uniq_handles, uniq_labels = [], []
        for h, l in zip(handles, labels):
            if l and (l not in seen):
                uniq_handles.append(h)
                uniq_labels.append(l)
                seen.add(l)

        # Only reserve space and draw legend if we actually have labels
        if len(uniq_labels) > 0:
            # Leave a small margin for the legend
            fig.subplots_adjust(bottom=0.12)

            # bbox "x,y"
            try:
                bx, by = args.legend_bbox.split(",")
                bbox = (float(bx), float(by))
            except Exception:
                bbox = (0.5, -0.02)

            fig.legend(
                uniq_handles,
                uniq_labels,
                loc=args.legend_loc,
                bbox_to_anchor=bbox,
                ncol=len(uniq_labels),
                frameon=False,
                fontsize=int(args.font_size) + 1,
            )

    # -------------------------------------------------------------------------
    # Save outputs
    # -------------------------------------------------------------------------
    suffix = "hist" if args.mode == "hist" else "ccdf"
    svg_path = os.path.join(out_dir, f"dvdt_distribution_{suffix}_stacked.svg")
    pdf_path = os.path.join(out_dir, f"dvdt_distribution_{suffix}_stacked.pdf")

    plt.savefig(svg_path)
    plt.savefig(pdf_path)

    print("Figure written to:")
    print(svg_path)
    print(pdf_path)


if __name__ == "__main__":
    main()