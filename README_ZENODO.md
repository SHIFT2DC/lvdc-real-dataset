# A real-world low-voltage DC (LVDC) dataset for event-driven monitoring and signal prioritization

## Overview

This record contains a collection of real-world time-series datasets acquired from operational low-voltage DC (LVDC) installations under normal industrial operating conditions. The datasets were collected within the context of the SHIFT2DC European project and reflect realistic voltage dynamics, load variations, and measurement noise that are typically not captured in simulation-based studies.

All data are provided in their original recorded form as time-stamped CSV files, without filtering, smoothing, resampling, or post-processing.

The dataset is intended to support research on LVDC monitoring, event detection, and data-driven analysis, as well as the validation of algorithms using real operational measurements.

---

## Datasets included

The record includes three datasets corresponding to different LVDC operating conditions:

- **Dataset A – LVDC 380 V, battery off (unbuffered)**  
  Measurements acquired from a hybrid AC/DC installation operating at a nominal DC bus voltage of 380 V without active battery participation. Voltage dynamics are driven by load changes and converter operation.

- **Dataset B – LVDC 380 V, battery on (buffered)**  
  Measurements acquired from the same installation under comparable load conditions, but with an active battery energy storage system connected to the DC bus, providing voltage buffering.

- **Dataset C – LVDC 700 V AFE (optional reference dataset)**  
  Measurements acquired from a separate 700 V DC active front-end (AFE) installation, included as a complementary reference dataset.

---

## File contents and structure

The dataset archive contains the following file types:

- **CSV files**  
  Raw time-series measurements, including time-stamped electrical variables from the AC and DC sides of the installations.

- **Metadata files (.md)**  
  One metadata file per dataset, providing:
  - acquisition context,
  - time coverage and sampling characteristics,
  - signal descriptions,
  - units and measurement notes.

Each metadata file fully documents the corresponding CSV file.

---

## Data format

- File format: comma-separated values (CSV)
- Time representation: human-readable timestamps (YYYY-MM-DD HH:MM:SS)
- Sampling interval: approximately 1 second (with minor timing variations typical of industrial logging systems)
- Data processing: none (raw recorded data)

No temporal alignment, interpolation, or correction has been applied.

---

## Intended use

The datasets are suitable for:
- event-driven monitoring and detection,
- analysis of LVDC voltage dynamics under real operating conditions,
- evaluation of data-driven and machine learning-based methods,
- validation of monitoring and prioritization strategies using real industrial data.

The datasets are not intended to represent controlled laboratory experiments, but rather continuous operational behavior.

---

## Related resources

Additional analysis scripts, plotting utilities, and exploratory tools related to these datasets are maintained in a separate GitHub repository for research and reproducibility purposes:

https://github.com/fjarroyovalle/lvdc-real-dataset

Note: the GitHub repository is not part of this Zenodo archive and may have restricted access.

---

## Funding

This work was supported by the European Commission under the SHIFT2DC project (Grant Agreement No. 101136131).

---

## Citation

If you use this dataset, please cite:

Arroyo-Valle, F. J., Drexler, K., Roger, S., & Saldaña, J. (2026).
*A real-world low-voltage DC (LVDC) dataset for event-driven monitoring and signal prioritization* (v1.0) [Data set].
Zenodo. https://doi.org/10.5281/zenodo.18524235


