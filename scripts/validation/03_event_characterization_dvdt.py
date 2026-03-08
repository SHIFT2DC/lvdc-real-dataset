#!/usr/bin/env python3
"""
03_event_characterization_dvdt.py

Purpose
-------
Detect representative DC-bus voltage transients using a simple |dV/dt| trigger.
This script is designed for Technical Validation (data quality and usability),
not for machine learning performance.

Key outputs
-----------
- dV/dt distribution statistics (percentiles and extremes)
- Event counts per threshold (percentile-based and optional absolute threshold)
- Event-level summary metrics (duration, peak |dV/dt|, delta V)
- Top-N most severe events (for later plotting and paper figures)
- Optional extraction of aligned event windows (CSV)

How to run
----------
Always run from the repository root using the -m module syntax:

  # Dataset A (battery-off)
  python3 -m scripts.validation.03_event_characterization_dvdt --dataset-id A

  # Dataset B (battery-on)
  python3 -m scripts.validation.03_event_characterization_dvdt --dataset-id B

  # Dataset C (optional 700 V)
  python3 -m scripts.validation.03_event_characterization_dvdt --dataset-id C

Notes
-----
- dV/dt is computed using the real time step dt from timestamps.
- Rows with dt <= 0 are excluded from dV/dt statistics and event detection.
- In Dataset B, duplicated timestamps may produce dt = 0; these are ignored for dV/dt.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Import shared I/O helpers:
# - load_dataset_config: reads dataset-specific settings (A/B/C)
# - validate_csv_structure: checks CSV existence and required columns
# - load_csv: loads the CSV into a pandas DataFrame
# - ensure_dir: creates directories if needed
# - write_json: writes JSON with stable formatting
# - make_run_id: creates a compact run identifier for traceability
from scripts.common.io_config import (
    load_dataset_config,
    validate_csv_structure,
    load_csv,
    ensure_dir,
    write_json,
    make_run_id,
)


STAGE_NAME = "events_dvdt"


@dataclass
class DvdtPercentiles:
    dataset_id: str
    dvdt_abs_p50: float
    dvdt_abs_p90: float
    dvdt_abs_p95: float
    dvdt_abs_p99: float
    dvdt_abs_p995: float
    dvdt_abs_p999: float
    dvdt_abs_max: float
    dvdt_abs_mean: float
    dvdt_abs_std: float
    dvdt_count: int


@dataclass
class ThresholdEventCount:
    dataset_id: str
    recording_duration_h: float
    threshold_type: str  # "percentile" or "absolute"
    threshold_value: float
    threshold_unit: str  # "%" for percentiles, "V/s" for absolute
    threshold_vps_equivalent: float
    n_events: int
    events_per_hour: float
    samples_in_event: int
    samples_in_event_pct: float


@dataclass
class EventRecord:
    event_id: int
    start_time: str
    end_time: str
    duration_s: float
    peak_abs_dvdt: float
    peak_signed_dvdt: float
    dominant_sign: str  # "positive" or "negative"
    v_start: float
    v_end: float
    v_min: float
    v_max: float
    delta_v_end_start: float
    delta_v_peak_to_peak: float
    best_power_col: str
    best_power_abs_deltaP: float
    deltaP_NRE_K1_P1: float
    abs_deltaP_NRE_K1_P1: float
    deltaP_NRE_K4_P1: float
    abs_deltaP_NRE_K4_P1: float
    deltaP_NRE_K6_P1: float
    abs_deltaP_NRE_K6_P1: float
    deltaP_NRE_sum: float
    abs_deltaP_NRE_sum: float


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Event characterization using |dV/dt| on Vbus.")
    p.add_argument("--dataset-id", required=True, choices=["A", "B", "C"], help="Dataset identifier.")
    p.add_argument("--config", default="configs/datasets.yaml", help="Path to datasets.yaml")
    p.add_argument("--out-root", default="out", help="Output root folder.")
    p.add_argument("--run-id", default=None, help="Optional run id. If not set, one is generated.")
    p.add_argument("--encoding", default="utf-8", help="CSV encoding.")

    # Threshold configuration
    p.add_argument("--mode", choices=["percentile", "absolute"], default="percentile",
                   help="Threshold mode used for top events extraction.")
    p.add_argument("--percentile", type=float, default=99.9,
                   help="Percentile for |dV/dt| threshold (used when mode=percentile).")
    p.add_argument("--threshold-vps", type=float, default=None,
                   help="Absolute threshold in V/s (used when mode=absolute).")

    # Default percentile list for event-rate reporting (paper-friendly summary)
    p.add_argument("--percentile-list", default="99.0,99.5,99.9,99.95",
                   help="Comma-separated list of percentiles for event counts.")

    # Event extraction options
    p.add_argument("--min-event-samples", type=int, default=1,
                   help="Minimum number of consecutive samples to keep an event.")
    p.add_argument("--top-n", type=int, default=20,
                   help="Number of top events (by peak |dV/dt|) to store for later plotting.")
    p.add_argument("--window-s", type=float, default=10.0,
                   help="Window half-width in seconds for optional window extraction.")
    p.add_argument("--export-windows", action="store_true",
                   help="If set, export event windows for top events as a single CSV.")
    return p.parse_args()


def compute_dvdt(time_s: np.ndarray, v: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute dt, dv, and dv/dt using real time steps.

    Returns
    -------
    dt : np.ndarray
        Time difference between samples (seconds), length N-1.
    dv : np.ndarray
        Voltage difference between samples (volts), length N-1.
    dvdt : np.ndarray
        dV/dt in V/s, length N-1. Entries where dt <= 0 are set to NaN.
    """
    dt = np.diff(time_s)
    dv = np.diff(v)
    dvdt = np.full_like(dv, fill_value=np.nan, dtype=float)

    valid = dt > 0
    dvdt[valid] = dv[valid] / dt[valid]
    return dt, dv, dvdt


def contiguous_true_segments(mask: np.ndarray) -> List[Tuple[int, int]]:
    """
    Convert a boolean mask into a list of contiguous True segments [start, end] (inclusive).

    The mask corresponds to dvdt indices (length N-1). Segment indices refer to dvdt positions.
    """
    segments: List[Tuple[int, int]] = []
    if mask.size == 0:
        return segments

    in_seg = False
    start = 0
    for i, flag in enumerate(mask):
        if flag and not in_seg:
            in_seg = True
            start = i
        elif not flag and in_seg:
            segments.append((start, i - 1))
            in_seg = False

    if in_seg:
        segments.append((start, mask.size - 1))
    return segments


def build_event_records(
    t: pd.Series,
    v: pd.Series,
    dvdt: np.ndarray,
    segments: List[Tuple[int, int]],
    min_event_samples: int,
    df_power: Optional[pd.DataFrame] = None,
) -> List[EventRecord]:
    """
    Build event records from dvdt segments.

    Notes
    -----
    - dvdt index i corresponds to transition from sample i -> i+1 in the original time series.
    - For a segment [s, e] in dvdt indices:
      - start sample index = s
      - end sample index = e + 1
    """
    records: List[EventRecord] = []
    event_id = 0

    for (s, e) in segments:
        n_samples = (e - s + 1)
        if n_samples < min_event_samples:
            continue

        start_idx = s
        end_idx = e + 1

        t_start = t.iloc[start_idx]
        t_end = t.iloc[end_idx]

        v_slice = v.iloc[start_idx:end_idx + 1]
        dvdt_slice = dvdt[s:e + 1]

        peak_abs = float(np.nanmax(np.abs(dvdt_slice)))
        # peak signed dvdt is the dvdt value at the maximum abs position
        peak_pos = int(np.nanargmax(np.abs(dvdt_slice)))
        peak_signed = float(dvdt_slice[peak_pos])

        dominant_sign = "positive" if peak_signed >= 0 else "negative"

        v_start = float(v.iloc[start_idx])
        v_end = float(v.iloc[end_idx])
        v_min = float(v_slice.min())
        v_max = float(v_slice.max())
        
                # ------------------------------------------------------------
        # Power-branch characterization for this event
        # ------------------------------------------------------------
        # We compute delta P for each candidate branch and for the optional sum.
        # The "best" branch is the one with the largest absolute delta P.
        deltaP_NRE_K1_P1 = float("nan")
        abs_deltaP_NRE_K1_P1 = float("nan")
        deltaP_NRE_K4_P1 = float("nan")
        abs_deltaP_NRE_K4_P1 = float("nan")
        deltaP_NRE_K6_P1 = float("nan")
        abs_deltaP_NRE_K6_P1 = float("nan")
        deltaP_NRE_sum = float("nan")
        abs_deltaP_NRE_sum = float("nan")

        best_power_col = ""
        best_power_abs_deltaP = float("nan")

        if df_power is not None:
            abs_dp_map: Dict[str, float] = {}

            # K1
            if "NRE K1 P1" in df_power.columns:
                p0 = float(df_power.iloc[start_idx]["NRE K1 P1"])
                p1 = float(df_power.iloc[end_idx]["NRE K1 P1"])
                deltaP_NRE_K1_P1 = p1 - p0
                abs_deltaP_NRE_K1_P1 = abs(deltaP_NRE_K1_P1)
                abs_dp_map["NRE K1 P1"] = abs_deltaP_NRE_K1_P1

            # K4
            if "NRE K4 P1" in df_power.columns:
                p0 = float(df_power.iloc[start_idx]["NRE K4 P1"])
                p1 = float(df_power.iloc[end_idx]["NRE K4 P1"])
                deltaP_NRE_K4_P1 = p1 - p0
                abs_deltaP_NRE_K4_P1 = abs(deltaP_NRE_K4_P1)
                abs_dp_map["NRE K4 P1"] = abs_deltaP_NRE_K4_P1

            # K6
            if "NRE K6 P1" in df_power.columns:
                p0 = float(df_power.iloc[start_idx]["NRE K6 P1"])
                p1 = float(df_power.iloc[end_idx]["NRE K6 P1"])
                deltaP_NRE_K6_P1 = p1 - p0
                abs_deltaP_NRE_K6_P1 = abs(deltaP_NRE_K6_P1)
                abs_dp_map["NRE K6 P1"] = abs_deltaP_NRE_K6_P1

            # Sum of branches
            sum_cols = ["NRE K1 P1", "NRE K4 P1", "NRE K6 P1"]
            if all(col in df_power.columns for col in sum_cols):
                p0 = float(df_power.iloc[start_idx][sum_cols].sum())
                p1 = float(df_power.iloc[end_idx][sum_cols].sum())
                deltaP_NRE_sum = p1 - p0
                abs_deltaP_NRE_sum = abs(deltaP_NRE_sum)
                abs_dp_map["NRE_sum"] = abs_deltaP_NRE_sum

            if abs_dp_map:
                best_power_col = max(abs_dp_map.items(), key=lambda kv: kv[1])[0]
                best_power_abs_deltaP = float(abs_dp_map[best_power_col])

        rec = EventRecord(
            event_id=event_id,
            start_time=str(t_start),
            end_time=str(t_end),
            duration_s=float((pd.to_datetime(t_end) - pd.to_datetime(t_start)).total_seconds()),
            peak_abs_dvdt=peak_abs,
            peak_signed_dvdt=peak_signed,
            dominant_sign=dominant_sign,
            v_start=v_start,
            v_end=v_end,
            v_min=v_min,
            v_max=v_max,
            delta_v_end_start=float(v_end - v_start),
            delta_v_peak_to_peak=float(v_max - v_min),
            best_power_col=best_power_col,
            best_power_abs_deltaP=best_power_abs_deltaP,
            deltaP_NRE_K1_P1=deltaP_NRE_K1_P1,
            abs_deltaP_NRE_K1_P1=abs_deltaP_NRE_K1_P1,
            deltaP_NRE_K4_P1=deltaP_NRE_K4_P1,
            abs_deltaP_NRE_K4_P1=abs_deltaP_NRE_K4_P1,
            deltaP_NRE_K6_P1=deltaP_NRE_K6_P1,
            abs_deltaP_NRE_K6_P1=abs_deltaP_NRE_K6_P1,
            deltaP_NRE_sum=deltaP_NRE_sum,
            abs_deltaP_NRE_sum=abs_deltaP_NRE_sum,
        )
        records.append(rec)
        event_id += 1

    return records


def duration_hours(t: pd.Series) -> float:
    t0 = pd.to_datetime(t.iloc[0])
    t1 = pd.to_datetime(t.iloc[-1])
    seconds = (t1 - t0).total_seconds()
    return float(seconds / 3600.0) if seconds > 0 else 0.0


def main() -> None:
    args = parse_args()

    cfg = load_dataset_config(args.dataset_id, config_path=args.config)
    validate_csv_structure(cfg)

    dataset_id = args.dataset_id
    csv_path = cfg["csv_path"]
    time_col = cfg["time_col"]
    time_format = cfg.get("time_format", None)
    vbus_col = cfg["vbus_col"]

    # Run id and output folders
    rid = args.run_id if args.run_id is not None else make_run_id()
    out_dir = os.path.join(args.out_root, dataset_id, rid)
    stage_dir = os.path.join(out_dir, STAGE_NAME)
    stats_dir = os.path.join(stage_dir, "stats")
    windows_dir = os.path.join(stage_dir, "windows")

    ensure_dir(stats_dir)
    ensure_dir(windows_dir)

    # Store run parameters for traceability
    params = {
        "dataset_id": dataset_id,
        "config_path": args.config,
        "csv_path": csv_path,
        "time_col": time_col,
        "time_format": time_format,
        "vbus_col": vbus_col,
        "mode": args.mode,
        "percentile": float(args.percentile),
        "threshold_vps": None if args.threshold_vps is None else float(args.threshold_vps),
        "percentile_list": args.percentile_list,
        "min_event_samples": int(args.min_event_samples),
        "top_n": int(args.top_n),
        "window_s": float(args.window_s),
        "export_windows": bool(args.export_windows),
        "encoding": args.encoding,
        "stage": STAGE_NAME,
        "run_id": rid,
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    write_json(os.path.join(stage_dir, "params.json"), params)

    # Load voltage plus candidate power branches (if available in config)
    power_cols_candidates = cfg.get("power_cols_candidates", [])
    power_cols_sum = cfg.get("power_cols_sum", [])

    usecols = [time_col, vbus_col]
    for col in power_cols_candidates:
        if col not in usecols:
            usecols.append(col)
    for col in power_cols_sum:
        if col not in usecols:
            usecols.append(col)

    df = load_csv(cfg, usecols=usecols, drop_invalid_timestamps=True)

    # Parse timestamps and main voltage
    t = df[time_col]
    v = pd.to_numeric(df[vbus_col], errors="coerce")

    # Candidate power dataframe (may contain NaN if some branch is unavailable)
    power_cols_present = [c for c in usecols if c not in [time_col, vbus_col]]
    df_power = df[power_cols_present].copy() if power_cols_present else None

    # Drop rows with invalid time or voltage
    valid_rows = t.notna() & v.notna()
    t = t.loc[valid_rows].reset_index(drop=True)
    v = v.loc[valid_rows].reset_index(drop=True)
    df = df.loc[valid_rows].reset_index(drop=True)

    if df_power is not None:
        df_power = df_power.loc[valid_rows].reset_index(drop=True)
    
    # Recording duration (seconds and hours), used to normalize event rates
    if len(t) > 1:
        recording_duration_s = float((t.iloc[-1] - t.iloc[0]).total_seconds())
    else:
        recording_duration_s = 0.0

    recording_duration_h = float(recording_duration_s / 3600.0) if recording_duration_s > 0 else 0.0
    

    if len(t) < 3:
        raise RuntimeError("Not enough valid samples after cleaning to compute dV/dt.")

    # Convert timestamps to seconds from start for stable numeric dt
    t0 = t.iloc[0]
    time_s = (t - t0).dt.total_seconds().to_numpy(dtype=float)
    v_np = v.to_numpy(dtype=float)

    dt, dv, dvdt = compute_dvdt(time_s, v_np)

    # Build dvdt absolute series for stats (exclude NaNs)
    dvdt_abs = np.abs(dvdt)
    dvdt_abs_valid = dvdt_abs[~np.isnan(dvdt_abs)]

    # Percentile stats
    pct = lambda p: float(np.percentile(dvdt_abs_valid, p)) if dvdt_abs_valid.size else float("nan")
    dvdt_stats = DvdtPercentiles(
        dataset_id=dataset_id,
        dvdt_abs_p50=pct(50),
        dvdt_abs_p90=pct(90),
        dvdt_abs_p95=pct(95),
        dvdt_abs_p99=pct(99),
        dvdt_abs_p995=pct(99.5),
        dvdt_abs_p999=pct(99.9),
        dvdt_abs_max=float(np.nanmax(dvdt_abs_valid)) if dvdt_abs_valid.size else float("nan"),
        dvdt_abs_mean=float(np.nanmean(dvdt_abs_valid)) if dvdt_abs_valid.size else float("nan"),
        dvdt_abs_std=float(np.nanstd(dvdt_abs_valid)) if dvdt_abs_valid.size else float("nan"),
        dvdt_count=int(dvdt_abs_valid.size),
    )
    pd.DataFrame([asdict(dvdt_stats)]).to_csv(os.path.join(stats_dir, "dvdt_percentiles.csv"), index=False)

    # Event counts for the default percentile list (summary for paper and for ML feasibility checks)
    #dur_h = duration_hours(t)
    dur_h = recording_duration_h
    percentiles = [float(x.strip()) for x in args.percentile_list.split(",") if x.strip()]
    count_rows: List[Dict[str, object]] = []

    for p in percentiles:
        thr_vps = pct(p)

        mask = (dvdt_abs >= thr_vps) & (~np.isnan(dvdt_abs))
        segments = contiguous_true_segments(mask)
        events = build_event_records(t, v, dvdt, segments, min_event_samples=args.min_event_samples, df_power=df_power)

        samples_in_event = int(np.sum(mask))
        samples_pct = float(100.0 * samples_in_event / mask.size) if mask.size else 0.0
        eph = float(len(events) / dur_h) if dur_h > 0 else 0.0

        row = asdict(ThresholdEventCount(
            dataset_id=dataset_id,
            recording_duration_h=dur_h,
            threshold_type="percentile",
            threshold_value=float(p),
            threshold_unit="%",
            threshold_vps_equivalent=float(thr_vps),
            n_events=len(events),
            events_per_hour=eph,
            samples_in_event=samples_in_event,
            samples_in_event_pct=samples_pct,
        ))
        count_rows.append(row)

    pd.DataFrame(count_rows).to_csv(os.path.join(stats_dir, "event_counts_by_percentile.csv"), index=False)

    # Threshold used for selecting top events
    if args.mode == "percentile":
        thr_main = pct(float(args.percentile))
    else:
        if args.threshold_vps is None:
            raise ValueError("--threshold-vps must be provided when --mode absolute is used.")
        thr_main = float(args.threshold_vps)

    mask_main = (dvdt_abs >= thr_main) & (~np.isnan(dvdt_abs))
    segments_main = contiguous_true_segments(mask_main)
    events_main = build_event_records(t, v, dvdt, segments_main, min_event_samples=args.min_event_samples, df_power=df_power)

    # Sort by peak |dV/dt|
    events_sorted = sorted(events_main, key=lambda e: e.peak_abs_dvdt, reverse=True)
    top_events = events_sorted[: int(args.top_n)]

    pd.DataFrame([asdict(e) for e in top_events]).to_csv(os.path.join(stats_dir, "events_top.csv"), index=False)

    # Summary for the main threshold
    samples_in_event_main = int(np.sum(mask_main))
    samples_pct_main = float(100.0 * samples_in_event_main / mask_main.size) if mask_main.size else 0.0
    eph_main = float(len(events_main) / dur_h) if dur_h > 0 else 0.0

    summary_main = asdict(ThresholdEventCount(
        dataset_id=dataset_id,
        recording_duration_h=dur_h,
        threshold_type=("percentile" if args.mode == "percentile" else "absolute"),
        threshold_value=(float(args.percentile) if args.mode == "percentile" else float(thr_main)),
        threshold_unit=("%" if args.mode == "percentile" else "V/s"),
        threshold_vps_equivalent=float(thr_main),
        n_events=len(events_main),
        events_per_hour=eph_main,
        samples_in_event=samples_in_event_main,
        samples_in_event_pct=samples_pct_main,
    ))
    write_json(os.path.join(stats_dir, "event_summary_main.json"), summary_main)

    # Optional: export windows for top events (single long CSV, easy to plot later)
    if args.export_windows and top_events:
        rows: List[Dict[str, object]] = []
        for ev in top_events:
            t_center = pd.to_datetime(ev.start_time)
            t_start = t_center - pd.Timedelta(seconds=float(args.window_s))
            t_end = t_center + pd.Timedelta(seconds=float(args.window_s))

            sel = (pd.to_datetime(t) >= t_start) & (pd.to_datetime(t) <= t_end)
            w_t = pd.to_datetime(t[sel])
            w_v = v[sel].astype(float).to_numpy()

            if len(w_t) < 2:
                continue

            # Recompute dvdt inside the window (stable and self-contained)
            w_time_s = (w_t - w_t.iloc[0]).dt.total_seconds().to_numpy(dtype=float)
            _, _, w_dvdt = compute_dvdt(w_time_s, w_v)

            # Align dvdt to sample timestamps (dvdt is length N-1)
            for i in range(len(w_t)):
                row = {
                    "event_id": ev.event_id,
                    "t": w_t.iloc[i].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] if "." in str(w_t.iloc[i]) else str(w_t.iloc[i]),
                    "vbus_v": float(w_v[i]),
                    "dvdt_vps": float(w_dvdt[i - 1]) if i > 0 else float("nan"),
                }
                rows.append(row)

        if rows:
            out_windows = os.path.join(windows_dir, "windows_topN.csv")
            pd.DataFrame(rows).to_csv(out_windows, index=False)

    print(f"OK {dataset_id}: wrote outputs to {stage_dir}")
    print(f"dvdt_count={dvdt_stats.dvdt_count}, p99.9={dvdt_stats.dvdt_abs_p999:.6f} V/s, max={dvdt_stats.dvdt_abs_max:.6f} V/s")
    # Print a compact event-rate line for quick comparison
    df_counts = pd.DataFrame(count_rows)
    line = ", ".join([f"p{r['threshold_value']}: {r['events_per_hour']:.2f}/h" for _, r in df_counts.iterrows()])
    print(f"events_per_hour_by_percentile: {line}")


if __name__ == "__main__":
    main()