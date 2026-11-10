#!/usr/bin/env python3
"""
02_check_dataset_C_column_order.py

Independent check of the aligned Dataset C file.

Purpose
-------
01_fix_dataset_C_alignment.py classifies each row of the raw Dataset C file from the
value ranges of its fields and writes an aligned CSV. This script checks that file
without using those value ranges:

1) It rebuilds the aligned file by position only. The data rows before the second
   marker row (file line 17) keep the header order. In the data rows after it, the
   fields are read as poweroutput, upstreamvoltage, upstreamcurrent, temperature,
   systemstate and written in the header order. Marker rows are not written.
2) It compares the rebuilt rows with the aligned file, row by row.
3) It checks that the timestamps are the same, and in the same order, as the
   timestamps of the raw data rows.
4) It reports how many rows satisfy P = U * I / 1000 within a tolerance, in the
   aligned file and in the raw rows after the second marker row read in the header
   order, overall and for each block of rows between marker rows.

The column order is inferred from the data; it has not been confirmed by the data
provider. This script only reads the two files and writes nothing.

Usage (run from the repository root)
------------------------------------
python3 -m scripts.preprocess.02_check_dataset_C_column_order

The script exits with status 1, before step 4, if the rebuilt rows or the timestamps
do not match.
"""

from __future__ import annotations

import argparse
import csv
import sys
from typing import List, Tuple

HEADER = ["Timestamp", "temperature", "systemstate", "poweroutput", "upstreamvoltage", "upstreamcurrent"]
MARKER = "CONNECTION_RESTORED"


def _read_rows(path: str) -> List[List[str]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.reader(f))


def _power_ok(row: List[str], tol: float) -> bool:
    """P = U * I / 1000 within tol, for a row in the header order."""
    p, u, i = float(row[3]), float(row[4]), float(row[5])
    return abs(p - u * i / 1000.0) <= tol


def main() -> int:
    parser = argparse.ArgumentParser(description="Independent check of the aligned Dataset C file.")
    parser.add_argument("--raw-csv", default="data/raw/LVDC_700V_AFE_2025_12_15.csv", help="Raw Dataset C CSV.")
    parser.add_argument(
        "--aligned-csv",
        default="data/processed/LVDC_700V_AFE_2025_12_15_aligned.csv",
        help="Aligned CSV written by 01_fix_dataset_C_alignment.py.",
    )
    parser.add_argument("--tol", type=float, default=0.05, help="Tolerance for P = U * I / 1000 (default: 0.05).")
    args = parser.parse_args()

    raw = _read_rows(args.raw_csv)
    aligned = _read_rows(args.aligned_csv)

    raw_rows = raw[1:]
    marker_idx = [i for i, r in enumerate(raw_rows) if len(r) == 2 and r[1] == MARKER]
    if len(marker_idx) < 2:
        print("ERROR: fewer than two marker rows found in the raw file.", file=sys.stderr)
        return 1
    markers = set(marker_idx)
    second_marker = marker_idx[1]

    # Raw data rows with their block number (number of marker rows before them).
    data: List[Tuple[int, int, List[str]]] = []
    block = 0
    for i, r in enumerate(raw_rows):
        if i in markers:
            block += 1
            continue
        data.append((i, block, r))

    # 1) Rebuild by position only.
    rebuilt = [HEADER]
    n_header_order = 0
    n_reordered = 0
    raw_after_header_order: List[List[str]] = []
    for i, _, r in data:
        if i < second_marker:
            rebuilt.append(r)
            n_header_order += 1
        else:
            ts, p, u, c, t, s = r
            rebuilt.append([ts, t, s, p, u, c])
            raw_after_header_order.append(r)
            n_reordered += 1

    # 2) Row-by-row comparison.
    mismatching = sum(1 for a, b in zip(rebuilt, aligned) if a != b) + abs(len(rebuilt) - len(aligned))

    # 3) Timestamps.
    timestamps_ok = [r[0] for _, _, r in data] == [r[0] for r in aligned[1:]]

    print("Dataset C: independent check of the aligned file")
    print(f"Raw file:       {args.raw_csv}")
    print(f"Aligned file:   {args.aligned_csv}")
    print(f"Marker rows:    {len(marker_idx)} (first at file line {marker_idx[0] + 2}, second at file line {second_marker + 2})")
    print(f"Data rows:      {len(data)} ({n_header_order} in header order, {n_reordered} reordered); aligned file: {len(aligned) - 1}")
    print(f"Rebuilt by position vs aligned file: {mismatching} mismatching rows")
    print(f"Timestamps identical and in the same order: {timestamps_ok}")
    if mismatching != 0 or not timestamps_ok:
        print("ERROR: the aligned file does not match the positional rebuild.", file=sys.stderr)
        return 1

    # 4) Power relation, overall and per block (aligned rows follow the raw data rows one to one).
    tol = float(args.tol)
    ok_aligned = [_power_ok(r, tol) for r in aligned[1:]]
    ok_raw_header = sum(_power_ok(r, tol) for r in raw_after_header_order)
    n_aligned = len(ok_aligned)
    print(f"P = U * I / 1000 within {tol}:")
    print(f"  aligned file: {sum(ok_aligned)} of {n_aligned} rows ({100.0 * sum(ok_aligned) / n_aligned:.2f} %)")
    print(
        f"  raw rows after the second marker row, header order: {ok_raw_header} of {n_reordered} rows "
        f"({100.0 * ok_raw_header / n_reordered:.2f} %)"
    )
    print("  aligned file by block of rows between marker rows:")
    print("    first timestamp          last timestamp            rows  not satisfied")
    blocks = sorted({b for _, b, _ in data})
    for b in blocks:
        idx = [k for k, (_, bb, _) in enumerate(data) if bb == b]
        n_not = sum(1 for k in idx if not ok_aligned[k])
        first_ts, last_ts = data[idx[0]][2][0], data[idx[-1]][2][0]
        print(f"    {first_ts}  {last_ts}  {len(idx):>6}  {n_not:>6}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
