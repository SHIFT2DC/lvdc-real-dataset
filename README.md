# LVDC real-world datasets for event-driven monitoring and signal prioritisation

This repository contains real-world time-series measurements acquired from operational low-voltage DC (LVDC) installations with hybrid AC/DC infrastructure. The data were logged through industrial monitoring interfaces and are intended to support research on LVDC monitoring, event detection, and data-driven signal prioritisation under realistic operating conditions.

The datasets collected in this repository are being prepared in the context of a Data Descriptor manuscript and subsequent experimental validation activities.

## Dataset overview

The repository currently includes multiple real-world LVDC datasets obtained under different operating conditions and measurement contexts:

- **380 V LVDC installation without active battery operation**  
  Dataset acquired on 2 May 2025 from an operational hybrid AC/DC installation regulated using droop control. During this period, the battery energy storage system was not operational, resulting in unbuffered DC bus voltage dynamics.

- **380 V LVDC installation with active battery operation**  
  Dataset acquired on 10 May 2024 from the same installation and DC bus voltage level, during a period when the battery system was operational and actively connected to the DC bus. This dataset represents a buffered operating regime.

- **700 V LVDC AFE-related dataset (optional)**  
  Dataset acquired on 15 December 2025 from an industrial active front end (AFE) installation operating at approximately 700 V. This dataset focuses on a reduced set of electrical and state variables and is included as a complementary reference.

## Dataset characteristics

Across the different datasets, the following general characteristics apply:

- System type: hybrid AC/DC and LVDC installations
- DC bus voltage levels: 380 V and 700 V, depending on the dataset
- Sampling interval: approximately 1 s (0.5 s for the AFE-related dataset)
- Duration: from several minutes up to full-day continuous recordings
- Acquisition context: industrial LVDC installations operated by partners involved in the SHIFT2DC Horizon Europe project

## Repository scope and extensibility

The repository structure and analysis methodology are designed to support multiple LVDC datasets with different voltage levels, operating conditions, and system configurations. While the current focus is on datasets collected within the SHIFT2DC project, the repository can be extended to include additional real-world LVDC datasets from other installations or sources in the future.

## What is included

- Raw CSV files containing time-stamped electrical and system-level measurements
- Metadata describing signal names, units, and acquisition context
- Scripts for basic inspection, plotting, and exploratory analysis of voltage dynamics and events

## Repository structure

- `data/`  
  Raw and processed CSV files. See `data/README.md` for dataset-specific details.

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

A Data Descriptor manuscript is currently under preparation. A DOI and formal citation will be added once the dataset collection is released through an approved public repository.

## License and access

The final public license and release conditions will be defined prior to publication, in agreement with the data provider(s). Until then, this repository is intended for internal research, analysis, and manuscript preparation.
