#!/usr/bin/env python3
"""
01_fix_dataset_C_alignment.py

Purpose
-------
Fix column misalignment in Dataset C (700 V AFE) in a reproducible way.

Context
-------
The raw file contains 12 event-marker rows (Timestamp,CONNECTION_RESTORED). The first
14 data rows follow the header order. In the data rows after the second marker row
(file line 17), the numeric fields appear in the order poweroutput, upstreamvoltage,
upstreamcurrent, temperature, systemstate. This order was inferred from the data,
using the relation between power, voltage and current; it has not been confirmed by
the data provider. We keep the raw file unchanged and generate an aligned CSV under
data/processed/ for analysis and figure generation.

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
  Marker rows are not written. Each data row is classified from the value ranges of
  its fields (see detect_layout). Line endings are CRLF (csv module default).
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
    # Integer-like value in a broad range; the recording contains values from 25 to 28.
    v = to_float(x)
    if v is None:
        return False
    return is_int_like(x) and (10 <= v <= 60)


def looks_like_systemstate(x: str) -> bool:
    # Integer-like value in a broad range; systemstate is 3 throughout the recording.
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

    Rotated (observed in the data rows after the second marker row, file line 17):
      ts, power, volt, curr, temp, state
    """
    ts, f1, f2, f3, f4, f5 = fields_6

    # Canonical signature: temp integer-like, state small integer, volt ~ 700
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