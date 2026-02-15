#!/usr/bin/env python3
"""
01_fix_dataset_C_alignment.py

Purpose
-------
Fix column misalignment in Dataset C (700 V AFE) in a reproducible way.

Context
-------
The raw log may contain event-marker rows (e.g., CONNECTION_RESTORED) and may switch the
ordering of numeric fields after reconnection events. We keep the raw file unchanged and
generate an aligned CSV under data/processed/ for analysis and figure generation.

How to run
----------
From the root of the repository:

python3 -m scripts.preprocess.01_fix_dataset_C_alignment \
  --in-csv data/raw/LVDC_700V_AFE_2025_12_15.csv \
  --out-csv data/processed/LVDC_700V_AFE_2025_12_15_aligned.csv

Output
------
- Aligned CSV with canonical column order:
  Timestamp,temperature,systemstate,poweroutput,upstreamvoltage,upstreamcurrent
- A short console summary with counts.
"""

from __future__ import annotations

import argparse
import csv
from typing import Optional


CANONICAL_HEADER = [
    "Timestamp",
    "temperature",
    "systemstate",
    "poweroutput",
    "upstreamvoltage",
    "upstreamcurrent",
]


def to_float(x: str) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None


def is_int_like(x: str) -> bool:
    # Accept "26" or "26.0" as int-like
    v = to_float(x)
    if v is None:
        return False
    return abs(v - round(v)) < 1e-9


def looks_like_temperature(x: str) -> bool:
    # Based on your description: 25..27, integer-like
    v = to_float(x)
    if v is None:
        return False
    return is_int_like(x) and (10 <= v <= 60)


def looks_like_systemstate(x: str) -> bool:
    # Small integer state, usually 0..10 (adjust if needed)
    v = to_float(x)
    if v is None:
        return False
    return is_int_like(x) and (0 <= v <= 20)


def looks_like_voltage_700v(x: str) -> bool:
    v = to_float(x)
    if v is None:
        return False
    return 500 <= v <= 800


def detect_layout(fields_6: list[str]) -> str:
    """
    Decide whether a 6-field row is already in canonical format or in rotated format.

    Canonical:
      ts, temp, state, power, volt, curr

    Rotated (observed after reconnection):
      ts, power, volt, curr, temp, state
    """
    ts, f1, f2, f3, f4, f5 = fields_6

    # Canonical signature: temp ~ 25..27 (int), state small int, volt ~ 700
    canonical_ok = (
        looks_like_temperature(f1)
        and looks_like_systemstate(f2)
        and looks_like_voltage_700v(f4)
    )

    # Rotated signature: volt ~ 700 appears in f2, temp in f4, state in f5
    rotated_ok = (
        looks_like_voltage_700v(f2)
        and looks_like_temperature(f4)
        and looks_like_systemstate(f5)
    )

    if canonical_ok and not rotated_ok:
        return "canonical"
    if rotated_ok and not canonical_ok:
        return "rotated"

    # If both or neither match, fall back to voltage position preference:
    if looks_like_voltage_700v(f4):
        return "canonical"
    if looks_like_voltage_700v(f2):
        return "rotated"

    return "unknown"


def reorder_to_canonical(fields_6: list[str], layout: str) -> Optional[list[str]]:
    ts, f1, f2, f3, f4, f5 = fields_6

    if layout == "canonical":
        # ts,temp,state,power,volt,curr
        return [ts, f1, f2, f3, f4, f5]

    if layout == "rotated":
        # ts,power,volt,curr,temp,state  -> ts,temp,state,power,volt,curr
        power = f1
        volt = f2
        curr = f3
        temp = f4
        state = f5
        return [ts, temp, state, power, volt, curr]

    return None


def main() -> int:
    p = argparse.ArgumentParser(description="Fix Dataset C column alignment reproducibly.")
    p.add_argument("--in-csv", required=True, help="Input raw CSV path.")
    p.add_argument("--out-csv", required=True, help="Output aligned CSV path.")
    args = p.parse_args()

    n_total = 0
    n_written = 0
    n_markers = 0
    n_canonical = 0
    n_rotated = 0
    n_unknown = 0
    n_badlen = 0

    with open(args.in_csv, "r", encoding="utf-8", newline="") as fin, open(
        args.out_csv, "w", encoding="utf-8", newline=""
    ) as fout:
        reader = csv.reader(fin)
        writer = csv.writer(fout)

        header = next(reader, None)
        if header is None:
            raise RuntimeError("Empty input file.")

        # Write canonical header
        writer.writerow(CANONICAL_HEADER)

        for row in reader:
            n_total += 1

            # Event marker rows: Timestamp,CONNECTION_RESTORED
            if len(row) == 2 and "CONNECTION_RESTORED" in row[1]:
                n_markers += 1
                continue

            if len(row) != 6:
                n_badlen += 1
                continue

            layout = detect_layout(row)

            if layout == "canonical":
                n_canonical += 1
            elif layout == "rotated":
                n_rotated += 1
            else:
                n_unknown += 1

            fixed = reorder_to_canonical(row, layout)
            if fixed is None:
                continue

            writer.writerow(fixed)
            n_written += 1

    print("Dataset C alignment fix summary")
    print(f"Input rows (excluding header): {n_total}")
    print(f"Marker rows skipped:          {n_markers}")
    print(f"Bad-length rows skipped:      {n_badlen}")
    print(f"Canonical rows:               {n_canonical}")
    print(f"Rotated rows:                 {n_rotated}")
    print(f"Unknown layout rows:          {n_unknown}")
    print(f"Rows written to output:       {n_written}")
    print(f"Output file: {args.out_csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())