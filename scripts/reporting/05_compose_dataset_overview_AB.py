"""
05_compose_dataset_overview_AB.py

Compose the two raw signal overview figures (Datasets A and B) into one figure file.

Purpose
-------
The journal asks for one file per figure, with the parts labelled a and b.
The raw signal overview of each dataset is generated separately by
04_generate_dataset_overview_figures.py (raw_signals_A.pdf and raw_signals_B.pdf).
This script places the two PDF pages one above the other on a new page and adds
the labels "(a)" and "(b)", with the letters in bold. The individual figures are
only read; they are not modified or regenerated.

The composition works on the PDF drawing instructions, so the result keeps the
vector content of the individual figures. No part is converted to an image; the
script checks this and stops with an error if the output contains an image.

Inputs
------
    out/reporting/<run_id>/dataset_overview/raw_signals_A.pdf
    out/reporting/<run_id>/dataset_overview/raw_signals_B.pdf

Output
------
    out/reporting/<run_id>/dataset_overview/raw_signals_AB.pdf

Usage
-----
From the repository root, after running 04_generate_dataset_overview_figures.py
for Datasets A and B with the same run id:

    python3 -m scripts.reporting.05_compose_dataset_overview_AB --run-id <run_id>
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from pypdf import PageObject, PdfReader, PdfWriter, Transformation  # noqa: E402


def _count_images(xobjects: Any) -> int:
    """Count image objects in a PDF XObject dictionary, including nested forms."""
    count = 0
    for ref in xobjects.values():
        obj = ref.get_object()
        subtype = obj.get("/Subtype")
        if subtype == "/Image":
            count += 1
        elif subtype == "/Form":
            resources = obj.get("/Resources")
            if resources is not None and "/XObject" in resources:
                count += _count_images(resources["/XObject"].get_object())
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Compose raw_signals_A.pdf and raw_signals_B.pdf into one figure.")
    parser.add_argument("--run-id", required=True, help="Run id used for the dataset overview figures.")
    parser.add_argument("--out-root", type=str, default="out", help="Output root folder (default: out).")
    parser.add_argument("--label-font-size", type=float, default=13.0, help="Font size of the labels in pt (default: 13).")
    parser.add_argument("--label-strip", type=float, default=20.0, help="Height in pt of the space above each part for its label (default: 20).")
    parser.add_argument("--gap", type=float, default=6.0, help="Vertical space in pt between the two parts (default: 6).")
    args = parser.parse_args()

    fig_dir = os.path.join(args.out_root, "reporting", args.run_id, "dataset_overview")
    path_a = os.path.join(fig_dir, "raw_signals_A.pdf")
    path_b = os.path.join(fig_dir, "raw_signals_B.pdf")
    out_path = os.path.join(fig_dir, "raw_signals_AB.pdf")

    for path in (path_a, path_b):
        if not os.path.exists(path):
            print(f"ERROR: input figure not found: {path}", file=sys.stderr)
            return 1

    page_a = PdfReader(path_a).pages[0]
    page_b = PdfReader(path_b).pages[0]
    width_a, height_a = float(page_a.mediabox.width), float(page_a.mediabox.height)
    width_b, height_b = float(page_b.mediabox.width), float(page_b.mediabox.height)

    strip = float(args.label_strip)
    gap = float(args.gap)
    width = max(width_a, width_b)
    height = strip + height_a + gap + strip + height_b

    # Part b at the bottom, part a above it. Each part keeps its original size.
    page = PageObject.create_blank_page(width=width, height=height)
    page.merge_transformed_page(page_b, Transformation().translate(0, 0))
    page.merge_transformed_page(page_a, Transformation().translate(0, height_b + gap + strip))

    # Labels drawn on a transparent page of the same size and merged on top.
    fig = plt.figure(figsize=(width / 72.0, height / 72.0))
    fig.patch.set_alpha(0.0)
    labels = (("a", height), ("b", height_b + strip))
    for letter, strip_top in labels:
        fig.text(
            4.0 / width,
            (strip_top - strip / 2.0) / height,
            rf"($\mathbf{{{letter}}}$)",
            ha="left",
            va="center",
            fontsize=float(args.label_font_size),
        )
    buffer = io.BytesIO()
    fig.savefig(buffer, format="pdf", transparent=True, metadata={"CreationDate": None})
    plt.close(fig)
    page.merge_page(PdfReader(buffer).pages[0])

    writer = PdfWriter()
    writer.add_page(page)
    with open(out_path, "wb") as f:
        writer.write(f)

    # Check that the output is still vector only.
    out_page = PdfReader(out_path).pages[0]
    resources = out_page.get("/Resources")
    n_images = 0
    if resources is not None and "/XObject" in resources:
        n_images = _count_images(resources["/XObject"].get_object())

    print("Composed figure written to:")
    print(out_path)
    print(f"Page size: {width:.1f} x {height:.1f} pt; images in PDF: {n_images}")
    if n_images > 0:
        print("ERROR: the composed figure contains images.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
