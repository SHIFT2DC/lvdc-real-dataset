# A real-world low-voltage direct current (LVDC) dataset for event-driven monitoring and signal prioritization

## Overview

This record contains a collection of real-world time-series datasets acquired from operational low-voltage direct current (LVDC) installations under normal industrial operating conditions. The datasets were collected within the context of the SHIFT2DC European project and reflect realistic voltage dynamics, load variations, and measurement noise that are typically not captured in simulation-based studies.

All data are provided in their original recorded form as time-stamped CSV files, without filtering, smoothing, resampling, or post-processing. For Dataset C, the record also includes a derived file with the columns in the order of the header (see below).

The dataset is intended to support research on LVDC monitoring, event detection, and data-driven analysis, as well as the validation of algorithms using real operational measurements.

This record also includes a self-contained Python example package that selects candidate events with a percentile threshold on |dV/dt| and reproduces the event window figure of the associated Data Descriptor.

---

## Datasets included

The record includes three datasets corresponding to different LVDC operating conditions:

- **Dataset A – LVDC 380 V, battery off**  
  Measurements acquired on 2 May 2025 from a hybrid AC/DC installation with a nominal DC bus voltage of 380 V. The battery current (`BAT I`) was 0 A throughout the recording.

- **Dataset B – LVDC 380 V, battery on**  
  Measurements acquired on 10 May 2024 from the same installation, with the battery energy storage system in operation according to the data provider. The two recordings were made on different dates and under different power conditions, so differences between Datasets A and B cannot be attributed to the battery alone.

- **Dataset C – LVDC 700 V AFE (complementary dataset)**  
  Measurements from a separate 700 V DC installation, logged by a solid-state circuit breaker (SCCB) connected next to an active front-end (AFE) converter, included as a complementary reference dataset. In the data rows after file line 17 of the CSV file, the values do not follow the column order of the header. The column order determined from the data, a derived file with the header order, and the scripts to reproduce and check it are described in the Dataset C metadata file. The derived file (`LVDC_700V_AFE_2025_12_15_aligned.csv`) is included in this record, and the scripts are in the GitHub repository listed under Related resources.

---

## File contents and structure

The dataset archive contains the following file types:

- **CSV files**  
  Raw time-series measurements, including time-stamped electrical variables from the AC and DC sides of the installations, and the derived file of Dataset C.

- **Metadata files (.md)**  
  One metadata file per dataset, providing:
  - acquisition context,
  - time coverage and sampling characteristics,
  - signal descriptions,
  - units and measurement notes.

- **Example scripts (ZIP)**  
  Self-contained Python example package that selects candidate events with a percentile threshold on |dV/dt| and reproduces the event window figure of the associated Data Descriptor. It contains the code, the requirements, the configuration of Datasets A and B and an empty `data/raw/` folder; the CSV files are downloaded separately from this record.

Each metadata file documents the corresponding CSV file. For a small number of signals, notes on data quality or reliability are included directly in the metadata files where relevant.

---

## Data format

- File format: comma-separated values (CSV)
- Time representation: human-readable timestamps (YYYY-MM-DD HH:MM:SS, with millisecond resolution in Dataset C)
- Sampling interval: approximately 1 second (with minor timing variations typical of industrial logging systems; Dataset C also contains four gaps longer than 1 h, documented in its metadata file)
- Data processing: none in the original CSV files (raw recorded data); the derived file of Dataset C only changes the column order and leaves out the 12 CONNECTION_RESTORED entries

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

Additional analysis scripts, plotting utilities, metadata, and reproducible processing workflows related to these datasets are maintained in the associated GitHub repository:

https://github.com/SHIFT2DC/lvdc-real-dataset

---

## Example scripts (ZIP)

This record also includes a self-contained example package provided as:

**lvdc_dataset_example_scripts.zip**

The example shows how candidate events can be selected in Datasets A and B with a percentile threshold on |dV/dt|. Because |dV/dt| is computed between consecutive samples, about 1 s apart, the candidate events describe voltage changes at the 1-s scale, not faster converter transients. They are not labelled or independently verified.

With the command given in the included `README_examples.md` file, the script reproduces the event window figure of the associated Data Descriptor from Dataset A. The ZIP file also contains a `requirements.txt` file, the configuration of Datasets A and B, and a `CODE_VERSION.txt` file that identifies the version of the code in the GitHub repository from which the package was generated. The CSV files are not included in the ZIP file: they are published as separate files in this record, and users download them and place them in the empty `data/raw/` folder of the package, as described in `README_examples.md`. The script can also be run on Dataset B and used as a starting point for further analysis of LVDC voltage dynamics.

## Funding

This work was supported by the European Commission under the SHIFT2DC project (Grant Agreement No. 101136131).

---

## Citation

If you use this dataset, please cite:

Arroyo-Valle, F. J., Drexler, K., Roger, S., & Saldana, J. (2026).
A real-world low-voltage direct current (LVDC) dataset for event-driven monitoring and signal prioritization [Data set].
Zenodo. https://doi.org/10.5281/zenodo.18524234


