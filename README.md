# LVDC real-world dataset for event-driven monitoring and signal prioritisation

This repository contains real-world time-series measurements acquired from an operational low-voltage DC (LVDC) installation with hybrid AC/DC infrastructure. The data were logged through industrial monitoring interfaces and are intended to support research on LVDC monitoring, event detection, and data-driven signal prioritisation.

## Dataset summary (current reference dataset)

The following characteristics describe the main reference dataset currently used for analysis and methodological development in this repository.

- System type: hybrid AC/DC and LVDC installation
- Nominal DC bus voltage: 380 V (typical operating range approximately 370–400 V)
- Sampling interval: 1 s
- Duration: up to 24 hours of continuous recording (depending on the file)
- Acquisition context: industrial LVDC installation operated by a partner involved in the SHIFT2DC Horizon Europe project

## Repository scope and extensibility

While the repository currently focuses on a primary real-world LVDC dataset operating at a nominal DC bus voltage of 380 V, its structure and analysis methodology are designed to support additional datasets with different voltage levels, operating conditions, and system configurations.

In particular, the repository is intended to accommodate other real-world LVDC datasets collected within the SHIFT2DC project, including installations operating at higher DC voltage levels (for example around 700 V), as well as potential datasets from external sources in the future.


## What is included

- DC bus voltage measurements and related electrical variables
- Optional signals depending on the file (for example power, current, and state indicators), as documented in the metadata.
- Scripts for basic inspection, plotting, and event exploration

## Repository structure

- `data/`  
  Raw and processed CSV files. See `data/README.md` for details.

- `metadata/`  
  Signal descriptions, units, and acquisition context.

- `scripts/`  
  Utility scripts used to inspect the dataset and generate plots.

- `figures/`  
  Selected figures that are relevant for documentation and manuscript preparation.

## Intended use

This dataset supports:
- analysis of LVDC voltage dynamics and transient behaviour,
- event-driven monitoring and detection based on voltage and dV/dt,
- validation of data-driven methods under realistic measurement noise and sampling irregularities.

## Usage

A typical workflow is:
1. start from the raw CSV files in `data/raw/`,
2. run the scripts in `scripts/` to inspect voltage, dV/dt, and candidate events,
3. produce processed files in `data/processed/` if needed.

## Citation

A data descriptor manuscript is being prepared. A DOI will be added once the dataset is released through an approved public repository.

## License and access

The final public license and release conditions will be defined prior to publication, in agreement with the data provider(s). Until then, this repository is intended for internal research and manuscript preparation.
