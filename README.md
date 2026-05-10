# A real-world low-voltage direct current (LVDC) dataset for event-driven monitoring and signal prioritization

This repository contains real-world time-series measurements and auxiliary analysis resources related to operational low-voltage direct current (LVDC) installations with hybrid AC/DC infrastructure. The data were logged through industrial monitoring interfaces and capture realistic voltage dynamics, measurement noise, and timing irregularities under normal operating conditions.

The datasets were curated and documented as part of the SHIFT2DC Horizon Europe project (Grant Agreement No. 101136131) and are described in an accompanying Data Descriptor manuscript.

## Dataset overview

The repository currently includes three curated reference datasets obtained under different operating conditions and measurement contexts:

### Core datasets (380 V LVDC installation)

- **LVDC_380V_hybrid_ACDC_battery_off_2025_05_02.csv**  
  Dataset acquired on 2 May 2025 from an operational hybrid AC/DC installation regulated using droop control. During this period, the battery energy storage system was not operational, resulting in unbuffered DC bus voltage dynamics.

- **LVDC_380V_hybrid_ACDC_battery_on_2024_05_10.csv**  
  Dataset acquired on 10 May 2024 from the same installation and DC bus voltage level, during a period when the battery system was operational and actively connected to the DC bus. This dataset represents a buffered operating regime and enables direct comparison with the unbuffered case.

Together, these two datasets enable controlled comparison between unbuffered and buffered LVDC operation using measurements from the same installation and voltage level.

### Complementary dataset (700 V LVDC)

- **LVDC_700V_AFE_2025_12_15.csv**  
  Dataset acquired on 15 December 2025 from an industrial active front end (AFE) installation operating at a nominal DC bus voltage of approximately 700 V. This dataset focuses on a reduced set of electrical and system state variables and is included as a complementary reference representing a different LVDC voltage level and operational context.
  The industrial partner initially provided two CSV files covering consecutive time segments. The second file already contains the complete continuous time series required for analysis. Therefore, only this file is used to generate the raw dataset stored under data/raw/.
  The original partner-provided files are preserved under data/original_from_partners/ for traceability. The validation and analysis pipeline operates exclusively on the selected consolidated dataset.

## Dataset characteristics

Across the different datasets, the following general characteristics apply:

- System type: hybrid AC/DC and LVDC installations  
- DC bus voltage levels: 380 V and 700 V, depending on the dataset  
- Sampling interval: approximately 1 s (0.5 s for the AFE-related dataset)  
- Duration: from several minutes (AFE-related dataset) up to full-day continuous recordings (380 V installation datasets)
- Acquisition context: industrial LVDC installations operated by partners involved in the SHIFT2DC project

### Data integrity notes and logging characteristics

The following observations were identified during reproducible validation of the raw datasets:

- **Dataset A (380 V, battery-off)**  
  No duplicated or invalid timestamps were detected. Approximately 30.9% of consecutive DC bus voltage samples are identical, reflecting steady-state operation and measurement quantization effects rather than data corruption.

- **Dataset B (380 V, battery-on)**  
  A total of 1,440 duplicated timestamps (1.67% of samples) were observed. These duplicates occur systematically once per minute at a fixed second offset (second 54) and are attributed to the logging mechanism. The overall temporal sequence remains monotonic and physically consistent.

- **Dataset C (700 V AFE)**  
  The original partner log includes structural markers and a field-order switch after reconnection events. A reproducible preprocessing script (`scripts/preprocess/01_fix_dataset_C_alignment.py`) is provided to restore column consistency prior to analysis. No duplicated timestamps were detected after alignment. A high proportion of identical consecutive samples reflects extended steady-state intervals typical of industrial operation.

All validation results are reproducible using the scripts under `scripts/validation/`.

## Repository scope and extensibility

The repository structure and analysis methodology are designed to support multiple LVDC datasets with different voltage levels, operating conditions, and system configurations.

## Reporting and Paper-Ready Figures

This repository includes reproducible scripts to generate publication-ready figures
based on the empirical distribution of |dV/dt| across datasets.

### Figure 1 — Stacked CCDF of |dV/dt|

The recommended figure for the manuscript is the stacked complementary cumulative
distribution function (CCDF) of |dV/dt|, including extreme-tail percentile markers
(p99.9 and p99.95).

Run from repository root:

```bash
python3 -m scripts.reporting.01_plot_dvdt_distribution \
    --datasets A B C \
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
```
This produces:
* One subplot per dataset (stacked layout)
* Log-scale on the y-axis
* Percentile thresholds (p99.9 and p99.95)
* Vector outputs (SVG and PDF) suitable for journal submission

Outputs are written to:
```console
out/reporting/<run_id>/figures/
```
### Alternative View — Histogram (Density)

A stacked histogram representation can also be generated:

```bash
python3 -m scripts.reporting.01_plot_dvdt_distribution \
    --datasets A B C \
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
```
This view is primarily intended for exploratory analysis or supplementary material.

### Design Rationale
* CCDF is preferred for manuscript presentation as it highlights extreme-tail behaviour.
* Percentile-based thresholds (p99.9, p99.95) are used for event detection.
* Typography and layout parameters are fully controllable via CLI arguments.
* Figures are generated in vector format to ensure reproducibility and publication quality.

## What is included

- Raw CSV files containing time-stamped electrical and system-level measurements  
- Metadata files describing signal names, units, and acquisition context
- Scripts for basic inspection, plotting, and exploratory analysis of voltage dynamics and events
  
Note: analysis scripts are provided in this GitHub repository for research and reproducibility purposes and are not part of the dataset archive released on Zenodo.

## Repository structure

- `data/raw/`  
  Reference CSV datasets used in the manuscript and analysis.

- `data/original_from_partners/`  
  Original files received from industrial partners, preserved for traceability.

- `metadata/`  
  Signal descriptions, units, and contextual information for each dataset.

- `scripts/`  
  Utility scripts used to inspect the datasets and generate plots.

- `figures/`  
  Selected figures used for documentation and manuscript preparation.

## Intended use

The datasets support:
- analysis of LVDC voltage dynamics and transient behaviour,  
- event-driven monitoring and detection based on voltage and derived signals such as dV/dt,  
- validation of data-driven methods under realistic measurement noise and sampling irregularities.

## Usage

A typical workflow is:
1. start from the raw CSV files in `data/raw/`,  
2. run the scripts in `scripts/` to inspect voltage behaviour and candidate events,  
3. generate processed files in `data/processed/` if required for specific analyses.

## Citation

If you use this dataset, please cite:

Arroyo-Valle, F. J., Drexler, K., Roger, S., & Saldaña, J. (2026).
A real-world low-voltage direct current (LVDC) dataset for event-driven monitoring and signal prioritization.
Zenodo. https://doi.org/10.5281/zenodo.18524234

## License and access

This repository is released under the Creative Commons Attribution 4.0 International License (CC BY 4.0). See the LICENSE file for details.
