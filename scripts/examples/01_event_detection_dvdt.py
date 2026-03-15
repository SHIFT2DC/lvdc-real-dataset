"""
01_event_detection_dvdt.py

Minimal transient event detection and visualization example based on |dV/dt|
(Scientific Data - Usage Example / Functional Validation)

Purpose
-------
This script provides a minimal, fully reproducible example illustrating how
extreme voltage transients can be programmatically detected and inspected
in the LVDC datasets.

It demonstrates:

1) Computation of dV/dt from DC bus voltage.
2) Definition of an "extreme" threshold using a percentile of |dV/dt|.
3) Detection of contiguous transient events.
4) Automatic selection of a representative event (maximum |dV/dt| peak).
5) Export of a time-aligned window around that event.
6) Optional generation of a vector figure (SVG/PDF) showing:
   - Vbus around the event
   - A related signal (e.g., power) for contextual interpretation.

Why this example is included
----------------------------
Scientific Data manuscripts typically focus on dataset description and validation.
However, providing a small, concrete example of dataset usage improves clarity and
demonstrates practical applicability without introducing ML models.

This script serves as:

- A reproducible usage example.
- A sanity-check of event detectability.
- A Zenodo-ready demonstration artifact.
- An appendix-level example for the manuscript.

Inputs
------
- Dataset configuration from configs/datasets.yaml (A/B/C)
- CSV referenced by the dataset config (raw or processed)

Outputs
-------
Writes outputs to:
  out/<dataset_id>/<run_id>/examples/dvdt_event_example/

Always:
  - selected_event.json   (selected event metadata and window definition)
  - params.json           (run parameters for traceability)

If --export-window-csv is enabled:
  - window.csv            (time-aligned window around the selected event)

If --plot is enabled:
  - event_window.svg
  - event_window.pdf

Recommended main example (includes power trace)
-----------------------------------------------

# Dataset A (battery-off)
python3 -m scripts.examples.01_event_detection_dvdt \
    --dataset-id A \
    --percentile 99.9 \
    --window-s 10 \
    --related-cols auto \
    --export-window-csv \
    --plot

# Dataset B (battery-on)
python3 -m scripts.examples.01_event_detection_dvdt \
    --dataset-id B \
    --percentile 99.9 \
    --window-s 10 \
    --related-cols auto \
    --export-window-csv \
    --plot

# Dataset C (700 V AFE)
python3 -m scripts.examples.01_event_detection_dvdt \
    --dataset-id C \
    --percentile 99.9 \
    --window-s 10 \
    --power-col "poweroutput" \
    --export-window-csv \
    --plot

Additional examples
-------------------

# Custom plot styling
python3 -m scripts.examples.01_event_detection_dvdt \
    --dataset-id A \
    --percentile 99.9 \
    --window-s 10 \
    --power-col "NRE K1 P1" \
    --plot \
    --font-size 11 \
    --title-font-delta 2 \
    --tick-font-delta -1 \
    --line-width 1.4

# Use automatic power column from YAML (if defined)
python3 -m scripts.examples.01_event_detection_dvdt \
    --dataset-id A \
    --percentile 99.9 \
    --window-s 10 \
    --power-col auto \
    --plot

# Fixed run id (useful for run_all reproducibility)
python3 -m scripts.examples.01_event_detection_dvdt \
    --dataset-id A \
    --percentile 99.9 \
    --window-s 10 \
    --run-id 2026-02-28_demo \
    --plot

Notes
-----
- This script does not resample or filter signals.
- Minimal cleaning is applied: invalid timestamps and NaN values are removed.
- The event threshold is percentile-based unless explicitly changed.
- The generated figure is intended for inspection and illustration,
  not for statistical inference.
- No machine learning is used in this example.
"""

import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter
from matplotlib.ticker import StrMethodFormatter
import matplotlib.dates as mdates

from scripts.common.io_config import (
    ensure_dir,
    load_csv,
    load_dataset_config,
    make_run_id,
)


@dataclass
class DvdtStats:
    n_samples: int
    dvdt_abs_pctl_threshold: float
    dvdt_abs_max: float


def compute_dvdt(t: pd.Series, v: pd.Series) -> pd.Series:
    """
    Compute dV/dt (V/s) using forward differences in time.
    """
    dt = t.diff().dt.total_seconds()
    dv = v.diff()
    dvdt = dv / dt
    return dvdt


def detect_contiguous_events(mask: pd.Series):
    """
    Convert a boolean mask into contiguous (start_idx, end_idx) event segments.
    """
    events = []
    in_event = False
    start = None

    for i, flag in enumerate(mask):
        if flag and not in_event:
            in_event = True
            start = i
        elif not flag and in_event:
            in_event = False
            events.append((start, i - 1))

    if in_event and start is not None:
        events.append((start, len(mask) - 1))

    return events


def _resolve_related_signal_columns(
    cfg: dict,
    args_related_cols: str,
    args_power_col: str,
) -> list[str]:
    """
    Resolve the related signal columns to plot alongside Vbus.

    Priority
    --------
    1) If --related-cols is not 'auto', use the explicit comma-separated list.
    2) Else, if --power-col is not 'auto', use it as a single-column fallback.
    3) Else, use cfg['power_cols_candidates'] if present.
    4) Else, fall back to cfg['power_col'] if present.

    Returns
    -------
    list[str]
        List of related signal columns to plot.
    """
    # Explicit list wins
    if args_related_cols and str(args_related_cols).lower() != "auto":
        return [c.strip() for c in str(args_related_cols).split(",") if c.strip()]

    # Backward-compatible single-column fallback
    if args_power_col and str(args_power_col).lower() != "auto":
        return [str(args_power_col)]

    # YAML candidates for A/B
    if isinstance(cfg, dict) and cfg.get("power_cols_candidates"):
        return [str(c) for c in cfg["power_cols_candidates"]]

    # Legacy primary power column
    if isinstance(cfg, dict) and cfg.get("power_col"):
        return [str(cfg["power_col"])]

    return []

POWER_LABELS = {
    "NRE K1 P1": "NRE K1 P1 (W)",
    "NRE K4 P1": "NRE K4 P1 (W)",
    "NRE K6 P1": "NRE K6 P1 (W)",
}

def _plot_event_window(
    out_dir: str,
    df_win: pd.DataFrame,
    time_col: str,
    vbus_col: str,
    related_cols: list[str],
    peak_time: pd.Timestamp,
    peak_abs_dvdt: float,
    window_start: pd.Timestamp,
    window_end: pd.Timestamp,
    dataset_id: str,
    args: argparse.Namespace,
):
    """
    Plot a time-aligned window around the selected event.

    The plot is intended to be paper-ready (vector formats) and easy to
    re-style via command-line parameters (font sizes, line widths, etc.).
    """
    # --- Font sizes ---
    base_fs = float(args.font_size)

    # Ticks
    tick_fs = base_fs + args.tick_font_delta  # e.g. base 11 + (-1) = 10

    # Axis labels (Time, NRE DCbus U, etc.)
    label_fs = tick_fs + 3.0  # 2 pt larger than ticks

    # Title
    title_fs = label_fs + 2.0  # slightly larger than axis labels

    vbus_color = "tab:blue"
    power_color = "tab:orange"
    marker_color = "0.25"

    t = df_win[time_col]

    # Only keep columns that really exist in the selected window dataframe
    related_cols_present = [c for c in related_cols if c in df_win.columns]

    # One subplot for Vbus + one subplot per related signal
    nrows = 1 + len(related_cols_present)

    fig, axes = plt.subplots(
        nrows=nrows,
        ncols=1,
        sharex=True,
        figsize=(8.0, 2.6 * nrows),
    )
    if nrows == 1:
        axes = [axes]

    # ------------------------------------------------------------
    # Panel 1: Vbus
    # ------------------------------------------------------------
    ax0 = axes[0]
    ax0.plot(t, df_win[vbus_col], linewidth=float(args.line_width), color=vbus_color)
    ax0.axvline(peak_time, linestyle="--", linewidth=1.0, color=marker_color)
    #ax0.set_ylabel(vbus_col, fontsize=label_fs)
    ax0.set_ylabel(f"{vbus_col} (V)", fontsize=label_fs)
    ax0.tick_params(axis="both", labelsize=tick_fs)
    ax0.grid(True, alpha=0.25)
    ax0.set_xlim(window_start, window_end)
    ax0.yaxis.set_major_formatter(StrMethodFormatter("{x:.0f}"))

    # Annotate the selected |dV/dt| peak inside the voltage panel
    ax0.text(
        0.98,
        0.92,
        f"|dV/dt| peak = {peak_abs_dvdt:.2f} V/s",
        transform=ax0.transAxes,
        ha="right",
        va="top",
        fontsize=base_fs,
    )

    # ------------------------------------------------------------
    # Additional panels: related power/current signals
    # ------------------------------------------------------------
    for i, col in enumerate(related_cols_present, start=1):
        ax = axes[i]
        plot_label = POWER_LABELS.get(col, col)
        ax.plot(t, df_win[col], linewidth=float(args.line_width), color=power_color)
        ax.axvline(peak_time, linestyle="--", linewidth=1.0, color=marker_color)
        ax.set_ylabel(plot_label, fontsize=label_fs)
        ax.tick_params(axis="both", labelsize=tick_fs)
        ax.grid(True, alpha=0.25)
        ax.set_xlim(window_start, window_end)
        ax.yaxis.set_major_formatter(StrMethodFormatter("{x:.0f}"))

    axes[-1].set_xlabel("Time", fontsize=label_fs + 2.0)

    # Rotate x tick labels and increase size
    for ax in axes:
        ax.tick_params(axis="x", labelrotation=30, labelsize=tick_fs + 2)

    # Format time axis
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))

    # Align y-labels across panels
    fig.align_ylabels(axes)

    fig.suptitle(
        f"Representative LVDC voltage transient event ({dataset_id})",
        fontsize=title_fs,
        y=0.96,
    )

    # Reduce extra whitespace while keeping room for title
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.97))

    formats = [f.strip().lower() for f in str(args.plot_formats).split(",") if f.strip()]
    for fmt in formats:
        fig_path = os.path.join(out_dir, f"event_window_{dataset_id}.{fmt}")
        fig.savefig(fig_path, bbox_inches="tight")

    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--percentile", type=float, default=99.95)
    parser.add_argument("--window-s", type=float, default=10.0)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--out-root", type=str, default="out", help="Output root folder (default: out).")
    parser.add_argument(
        "--plot",
        action="store_true",
        help="If set, generate a vector figure (PDF/SVG) for the selected event window.",
    )
    parser.add_argument(
        "--plot-formats",
        type=str,
        default="svg,pdf",
        help="Comma-separated formats for the event window plot (default: svg,pdf).",
    )
    parser.add_argument(
        "--power-col",
        type=str,
        default="auto",
        help="Column to plot as the related power/current signal. Use 'auto' to use the dataset config.",
    )
    parser.add_argument(
        "--related-cols",
        type=str,
        default="auto",
        help=(
            "Comma-separated list of related signal columns to plot. "
            "Use 'auto' to use YAML power_cols_candidates if available."
        ),
    )
    parser.add_argument(
        "--export-window-csv",
        action="store_true",
        help="If set, export the selected time window to window.csv.",
    )
    parser.add_argument(
        "--font-size",
        type=float,
        default=11.0,
        help="Base font size for the plot (default: 11).",
    )
    parser.add_argument(
        "--title-font-delta",
        type=float,
        default=2.0,
        help="Delta added to base font size for the title (default: +2).",
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
    args = parser.parse_args()

    # --- Load dataset ---
    cfg = load_dataset_config(args.dataset_id)
    df = load_csv(cfg)

    time_col = cfg["time_col"]
    vbus_col = cfg["vbus_col"]

    t = pd.to_datetime(df[time_col], format=cfg["time_format"], errors="coerce")
    v = pd.to_numeric(df[vbus_col], errors="coerce")

    # Drop invalid time or voltage
    valid_rows = t.notna() & v.notna()
    t = t.loc[valid_rows].reset_index(drop=True)
    v = v.loc[valid_rows].reset_index(drop=True)
    df = df.loc[valid_rows].reset_index(drop=True)

    if len(t) < 3:
        raise RuntimeError("Not enough valid samples after filtering invalid timestamps/values.")

    # --- Compute dV/dt ---
    dvdt = compute_dvdt(t, v)
    dvdt_abs = dvdt.abs()

    # Build a single aligned mask (same index length as t/v/df/dvdt_abs)
    # - drop the first sample (diff produces NaN)
    # - remove non-finite values (inf/-inf), which can occur when dt == 0 (duplicate timestamps)
    finite_mask = pd.Series(np.isfinite(dvdt_abs.to_numpy()), index=dvdt_abs.index)
    valid_mask = dvdt_abs.notna() & finite_mask

    # Apply the same mask to all series/dataframes to keep perfect alignment
    dvdt_abs = dvdt_abs.loc[valid_mask].reset_index(drop=True)
    t = t.loc[valid_mask].reset_index(drop=True)
    v = v.loc[valid_mask].reset_index(drop=True)
    df = df.loc[valid_mask].reset_index(drop=True)

    # --- Threshold by percentile ---
    threshold = float(np.percentile(dvdt_abs.to_numpy(), args.percentile))
    event_mask = dvdt_abs >= threshold

    # --- Detect contiguous events ---
    events = detect_contiguous_events(event_mask)

    if len(events) == 0:
        raise RuntimeError(
            "No events found with the current threshold settings. Try lowering --percentile."
        )

    # --- Select representative event (max |dV/dt| peak) ---
    max_peak = -np.inf
    selected_event = None

    for start, end in events:
        peak_val = dvdt_abs.iloc[start:end + 1].max()
        if peak_val > max_peak:
            max_peak = peak_val
            selected_event = (start, end)

    if selected_event is None:
        raise RuntimeError(
            "No events found with the current threshold settings. Try lowering --percentile."
        )

    start_idx, end_idx = selected_event
    peak_idx = dvdt_abs.iloc[start_idx:end_idx + 1].idxmax()

    
    # Peak time for the plot marker
    # ------------------------------------------------------------
    # The maximum |dV/dt| may occur on either edge (drop or recovery).
    # For clearer figures, mark the most "extreme" V point inside the
    # selected event segment:
    # - if signed dV/dt at the peak is negative -> mark min(V) in the event
    # - if signed dV/dt at the peak is positive -> mark max(V) in the event
    # - fallback -> mark the max-|dV/dt| instant

    dvdt_seg_signed = dvdt.loc[start_idx:end_idx].astype(float)
    v_seg = v.loc[start_idx:end_idx].astype(float)

    dominant_sign = float(np.sign(dvdt_seg_signed.loc[peak_idx]))
    
    # Guardrail: if V hardly changes inside the event (flat segment),
    # idxmin/idxmax is not meaningful -> use the dv/dt peak instead.
    v_span = float(v_seg.max() - v_seg.min())
    if not np.isfinite(v_span) or v_span < 1e-6:
        idx_mark = int(peak_idx)
    else:
        if dominant_sign < 0:
            idx_mark = int(v_seg.idxmin())
        elif dominant_sign > 0:
            idx_mark = int(v_seg.idxmax())
        else:
            idx_mark = int(peak_idx)

    peak_time = t.loc[idx_mark]
    
    # Build a symmetric window centered on peak_time
    # args.window_s now represents TOTAL window length (not half)
    half_window = float(args.window_s) / 2.0
    window_start = peak_time - timedelta(seconds=half_window)
    window_end = peak_time + timedelta(seconds=half_window)

    # --- Output directory ---
    run_id = args.run_id if args.run_id else make_run_id()
    out_dir = os.path.join(args.out_root, args.dataset_id, run_id, "examples", "dvdt_event_example")
    ensure_dir(out_dir)

    # --- Build selected time window (for CSV export and plotting) ---
    related_cols = _resolve_related_signal_columns(cfg=cfg, args_related_cols=args.related_cols, args_power_col=args.power_col)

    # Keep only columns that really exist in the dataframe
    related_cols = [c for c in related_cols if c in df.columns]

    win_mask = (t >= window_start) & (t <= window_end)
    df_win = pd.DataFrame({
        time_col: t.loc[win_mask].reset_index(drop=True),
        vbus_col: v.loc[win_mask].reset_index(drop=True),
        "abs_dvdt_v_per_s": dvdt_abs.loc[win_mask].reset_index(drop=True),
    })

    # Add all requested related signals to the exported/plot dataframe
    for col in related_cols:
        df_win[col] = df.loc[win_mask, col].reset_index(drop=True)

    
    if args.export_window_csv:
        window_csv_path = os.path.join(out_dir, "window.csv")
        df_win.to_csv(window_csv_path, index=False)

    if args.plot:
        _plot_event_window(
            out_dir=out_dir,
            df_win=df_win,
            time_col=time_col,
            vbus_col=vbus_col,
            related_cols=related_cols,
            peak_time=peak_time,
            peak_abs_dvdt=float(max_peak),
            window_start=window_start,
            window_end=window_end,
            dataset_id=args.dataset_id,
            args=args,
        )

    # --- Save results ---
    result = {
        "dataset_id": args.dataset_id,
        "percentile": args.percentile,
        "threshold_v_per_s": float(threshold),
        "event_start_time": str(t.iloc[start_idx]),
        "event_peak_time": str(peak_time),
        "event_end_time": str(t.iloc[end_idx]),
        "window_start_time": str(window_start),
        "window_end_time": str(window_end),
        "window_seconds": args.window_s,
        "peak_abs_dvdt": float(max_peak),
        "related_cols": related_cols,
        "export_window_csv": bool(args.export_window_csv),
        "plot_enabled": bool(args.plot),
        "plot_formats": str(args.plot_formats),
    }

    params = {
        "dataset_id": args.dataset_id,
        "percentile": args.percentile,
        "window_s": args.window_s,
        "vbus_col": vbus_col,
        "time_col": time_col,
        "run_id": run_id,
        "related_cols": related_cols,
        "export_window_csv": bool(args.export_window_csv),
        "plot_enabled": bool(args.plot),
        "plot_formats": str(args.plot_formats),
        "font_size": float(args.font_size),
        "title_font_delta": float(args.title_font_delta),
        "tick_font_delta": float(args.tick_font_delta),
        "line_width": float(args.line_width),
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    with open(os.path.join(out_dir, "selected_event.json"), "w") as f:
        json.dump(result, f, indent=2)

    with open(os.path.join(out_dir, "params.json"), "w") as f:
        json.dump(params, f, indent=2)

    print("Selected event written to:")
    print(os.path.join(out_dir, "selected_event.json"))

    if args.export_window_csv:
        print("Window CSV written to:")
        print(os.path.join(out_dir, "window.csv"))

    if args.plot:
        print("Event window figure written to:")
        formats = [f.strip().lower() for f in str(args.plot_formats).split(",") if f.strip()]
        for fmt in formats:
            print(os.path.join(out_dir, f"event_window_{args.dataset_id}.{fmt}"))


if __name__ == "__main__":
    main()