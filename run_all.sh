#!/usr/bin/env bash
#
# run_all.sh
#
# Purpose
# -------
# Run the main reproducible validation and reporting pipeline for the
# Scientific Data LVDC dataset paper.
#
# This script uses one shared RUN_ID so that all outputs from the same
# pipeline execution are grouped consistently across:
# - validation stages
# - reporting stages
# - summary artifacts
#
# Main paper scope
# ----------------
# - Datasets A and B are the main datasets in the current paper flow.
# - Dataset C is intentionally excluded from the main reproducible flow
#   for now because its timing characteristics are not directly comparable
#   with A/B for the current dV/dt event analysis.
#
# What this script runs
# ---------------------
# 1) validation/01_sanity_checks.py
# 2) validation/02_sampling_stability_dt.py
# 3) validation/03_event_characterization_dvdt.py
# 4) validation/04_cross_signal_consistency.py
# 5) validation/05_data_overview_summary.py
# 6) reporting/01_plot_dvdt_distribution.py
# 7) reporting/02_generate_latex_table_events.py
# 8) reporting/04_generate_dataset_overview_figures.py
# 9) examples/01_event_detection_dvdt.py
#
# Notes
# -----
# - The example script scripts/examples/01_event_detection_dvdt.py is not part
#   of the core validation pipeline. It is left as an optional block below.
# - This script should be executed from the repository root.
# - It assumes the individual stage scripts are already working when called
#   directly on their own.
#
# Usage
# -----
# From the repository root:
#
#   bash run_all.sh
#
# Optional custom run id:
#
#   RUN_ID="2026-03-09_2200Z_manual" bash run_all.sh
#
# Optional custom datasets for the main flow:
#
#   DATASETS="A B" bash run_all.sh
#

set -euo pipefail

# Resolve repository root from this script location and execute from there.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# Main datasets for the current paper flow.
DATASETS="${DATASETS:-A B}"

# One shared run id for the whole pipeline execution.
# If RUN_ID is not provided externally, create one in UTC.
RUN_ID="${RUN_ID:-$(date -u +'%Y-%m-%d_%H%MZ')}"

# Event table caption and label are passed explicitly for reproducible LaTeX output.
EVENTS_TABLE_CAPTION="Extreme \$|dV/dt|\$ event statistics per dataset (recording duration: 24~h)."
EVENTS_TABLE_LABEL="tab:dvdt_events"

echo "=============================================="
echo "Reproducible LVDC pipeline"
echo "Repository root : $REPO_ROOT"
echo "Datasets        : $DATASETS"
echo "RUN_ID          : $RUN_ID"
echo "=============================================="
echo

# ---------------------------------------------------------------------------
# Stage 01
# Basic sanity checks for structure, timestamps, missingness, and ranges.
# Reuses the shared RUN_ID so all dataset-level outputs stay grouped.
# ---------------------------------------------------------------------------
echo "[1/9] Running validation stage 01: sanity checks"
for DS in $DATASETS; do
  echo "  -> Dataset $DS"
  python3 -m scripts.validation.01_sanity_checks \
    --dataset-id "$DS" \
    --run-id "$RUN_ID"
done
echo

# ---------------------------------------------------------------------------
# Stage 02
# Sampling stability and delta-t behavior for the same main datasets.
# This stage provides the timing validation context for later event analysis.
# ---------------------------------------------------------------------------
echo "[2/9] Running validation stage 02: sampling stability"
for DS in $DATASETS; do
  echo "  -> Dataset $DS"
  python3 -m scripts.validation.02_sampling_stability_dt \
    --dataset-id "$DS" \
    --run-id "$RUN_ID"
done
echo
# ---------------------------------------------------------------------------
# Stage 03
# dV/dt event characterization for the main paper datasets (A/B).
# This stage produces percentiles, event counts, and event-level artifacts.
# ---------------------------------------------------------------------------
echo "[3/9] Running validation stage 03: event characterization by dV/dt"
for DS in $DATASETS; do
  echo "  -> Dataset $DS"
  python3 -m scripts.validation.03_event_characterization_dvdt \
    --dataset-id "$DS" \
    --run-id "$RUN_ID"
done
echo

# ---------------------------------------------------------------------------
# Stage 04
# Cross-signal consistency between Vbus and power-related signals.
# This stage uses the same RUN_ID to stay aligned with Stage 03.
# ---------------------------------------------------------------------------
echo "[4/9] Running validation stage 04: cross-signal consistency"
for DS in $DATASETS; do
  echo "  -> Dataset $DS"
  python3 -m scripts.validation.04_cross_signal_consistency \
    --dataset-id "$DS" \
    --run-id "$RUN_ID"
done

echo

# ---------------------------------------------------------------------------
# Stage 05
# Compact validation summary that consolidates Stage 03 and Stage 04 results.
# We pass the same Stage 03 / Stage 04 run ids explicitly to avoid ambiguity.
# ---------------------------------------------------------------------------
echo "[5/9] Running validation stage 05: compact validation summary"
python3 -m scripts.validation.05_data_overview_summary \
  --datasets $DATASETS \
  --events-run-id "$RUN_ID" \
  --cross-run-id "$RUN_ID" \
  --run-id "$RUN_ID"

echo

# ---------------------------------------------------------------------------
# Reporting 01
# Main paper-ready stacked CCDF figure for |dV/dt| in datasets A and B.
# This call follows the script recommended settings for the manuscript.
# ---------------------------------------------------------------------------
echo "[6/9] Running reporting stage 01: dV/dt tail distribution figure"
python3 -m scripts.reporting.01_plot_dvdt_distribution \
  --datasets $DATASETS \
  --run-id "$RUN_ID" \
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

echo

# ---------------------------------------------------------------------------
# Reporting 02
# Paper-ready LaTeX table for extreme |dV/dt| event statistics.
# Caption and label are passed explicitly for consistent manuscript output.
# This stage reads the Stage 03 outputs identified by the shared RUN_ID.
# ---------------------------------------------------------------------------
echo "[7/9] Running reporting stage 02: LaTeX event table"
python3 -m scripts.reporting.02_generate_latex_table_events \
  --datasets $DATASETS \
  --run-id "$RUN_ID" \
  --caption "$EVENTS_TABLE_CAPTION" \
  --label "$EVENTS_TABLE_LABEL"

echo

# ---------------------------------------------------------------------------
# Reporting 04
# Paper-ready dataset overview figures for the input datasets.
# This stage generates:
# - raw signal overview figures
# - variable-category distribution figures
# ---------------------------------------------------------------------------
echo "[8/9] Running reporting stage 04: dataset overview figures"

for DS in $DATASETS; do
  echo "  -> Dataset $DS"

  if [ "$DS" = "A" ]; then
    WINDOW_ARGS=(--window-start-time "2025-05-02 15:15:00" --window-s 600)
    POWER_ARGS=(--power-cols "NRE K4 P1,NRE K6 P1")
    #STACK_ARGS=(--hide-xaxis-label --hide-legend)
  elif [ "$DS" = "B" ]; then
    WINDOW_ARGS=(--window-start-time "2024-05-10 17:25:00" --window-s 600)
    POWER_ARGS=(--power-cols "NRE K4 P1,NRE K6 P1")
    STACK_ARGS=()
  else
    WINDOW_ARGS=(--window-s 600)
    POWER_ARGS=(--power-cols "NRE K4 P1,NRE K6 P1")
    STACK_ARGS=()
  fi

  python3 -m scripts.reporting.04_generate_dataset_overview_figures \
    --dataset-id "$DS" \
    --run-id "$RUN_ID" \
    "${WINDOW_ARGS[@]}" \
    "${POWER_ARGS[@]}" \
    "${STACK_ARGS[@]}" \
    --time-axis elapsed \
    --vbus-margin 1.0 \
    --power-margin-frac 0.10 \
    --plot-formats svg,pdf \
    --font-size 11 \
    --title-font-delta 2 \
    --tick-font-delta -1 \
    --line-width 1.4 \
    --raw-fig-width 8.0 \
    --raw-fig-height 3.8 \
    --dist-fig-width 7.0 \
    --dist-fig-height 2.2

done

echo "[8/9] Done"

# ---------------------------------------------------------------------------
# Stage 09
# Reproducible example of event detection and aligned window export.
# This demonstrates practical dataset usage on the main paper datasets.
# For each dataset, this stage generates:
# - selected_event.json
# - params.json
# - window.csv
# - vector figure (SVG/PDF)
# ---------------------------------------------------------------------------
echo "[9/9] Running examples stage 01: event detection example"
for DS in $DATASETS; do
  echo "  -> Dataset $DS"
  python3 -m scripts.examples.01_event_detection_dvdt \
    --dataset-id "$DS" \
    --percentile 99.9 \
    --window-s 60 \
    --run-id "$RUN_ID" \
    --plot \
    --related-cols auto \
    --export-window-csv
done
echo

echo "=============================================="
echo "[OK] Pipeline finished successfully."
echo "Shared RUN_ID : $RUN_ID"
echo
echo "Main output roots:"
echo "  - Validation datasets : out/<DATASET>/$RUN_ID/"
echo "  - Reporting outputs   : out/reporting/$RUN_ID/"
echo "=============================================="