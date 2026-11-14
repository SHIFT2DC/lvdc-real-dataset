# Dataset C – LVDC 700 V active front end installation (optional)

## Overview

This dataset contains real-world time-series measurements from a low-voltage direct current (LVDC) installation of an industrial partner within the context of the SHIFT2DC project, with a nominal DC bus voltage of 700 V. The data were logged by a solid-state circuit breaker (SCCB) connected next to an AC/DC active front end (AFE) converter, not by the AFE itself. According to the data provider, the voltage and current at the SCCB can be taken as identical to those at the AFE terminals.

The dataset corresponds to a measurement campaign carried out between 15 December 2025 at 17:26:29 and 17 December 2025 at 17:13:31. It is provided as an optional complementary dataset and reflects a different LVDC voltage level and system architecture compared to Datasets A and B.

This dataset is intended to support cross-scenario comparison, exploratory analysis, and validation of methods across different LVDC configurations.

## Acquisition context

The AFE is an AC/DC power converter designed for deployment in LVDC demonstrators and distribution systems. During this recording, it was operated with a nominal DC bus voltage of 700 V under normal operating conditions, and the measurements were logged by the SCCB described above.

The dataset includes measurements related to DC-side electrical behaviour, system state information, and basic thermal monitoring. The recorded signals indicate bidirectional power flow conditions, including periods with both positive and negative power values.

All measurements reflect operational system behaviour and were not obtained through a dedicated experimental campaign designed by the authors.

## Time coverage and format

The dataset is provided as a single comma-separated values (CSV) file containing time-stamped measurements. Timestamps are expressed in a human-readable format with millisecond resolution. The time zone and the clock source of the logging device have not been documented by the data provider.

The nominal sampling interval is approximately 1 second, with small timing variations typical of industrial logging systems. The recording contains four gaps longer than 1 h, totalling 14.21 h; data are available for 33.57 h of the 47.78 h span. No temporal resampling or interpolation has been applied.

The CSV file is provided in its original recorded form, without filtering, smoothing, or post-processing. A derived file with all data rows in the column order of the header is described in the section Column order.

## Signals included

The dataset includes a compact set of electrical and system-level variables. Table 1 summarises the signals available in the dataset, together with a short description and the corresponding physical units.

### Table 1 – Signal description for Dataset C

| Column name | Description | Unit |
|------------|------------|------|
| Timestamp | Timestamp of the measurement | – |
| temperature | Measured temperature of the system or power electronics | °C |
| systemstate | System state indicator in the SCCB log (see Notes on system state and event entries) | – |
| poweroutput | DC power at the SCCB next to the AFE | kW |
| upstreamvoltage | DC voltage measured at the SCCB next to the AFE | V |
| upstreamcurrent | DC current measured at the SCCB next to the AFE | A |

In addition to numerical measurements, the file contains 12 text entries (CONNECTION_RESTORED); see the section Notes on system state and event entries.

## Column order

The header lists the columns in the order Timestamp, temperature, systemstate, poweroutput, upstreamvoltage, upstreamcurrent. Only the first 14 data rows (file lines 3 to 16; 2025-12-15 17:26:29.132 to 17:26:42.132) follow this order. In the data rows after the second CONNECTION_RESTORED entry (file line 17, 2025-12-15 17:26:50.827), that is 122095 of the 122109 data rows, the values are consistent with the order poweroutput, upstreamvoltage, upstreamcurrent, temperature, systemstate. With this order, the power equals the product of voltage and current divided by 1000 within 0.05 in 121545 of the 122109 data rows (99.54%). Read in the header order, none of the 122095 rows after file line 17 satisfies this relation. The 564 rows that do not satisfy it are kept in both files. The column mapping used to create the derived file was determined from these checks on the raw data. The CSV file is provided as recorded.

The code repository (https://github.com/SHIFT2DC/lvdc-real-dataset) contains:

- `data/raw/LVDC_700V_AFE_2025_12_15.csv`: the CSV file of this dataset, unchanged (MD5 `2b1b4d6761c3db3982aa9f64f290e75c`).
- `data/processed/LVDC_700V_AFE_2025_12_15_aligned.csv`: a derived file with the 122109 data rows in the column order of the header, without the 12 CONNECTION_RESTORED entries (CRLF line endings; MD5 `ef034ac03190baec099ce310dd81021d`).
- `scripts/preprocess/01_fix_dataset_C_alignment.py`: the script that generates the derived file.
- `scripts/preprocess/02_check_dataset_C_column_order.py`: an independent check. It rebuilds the derived file by position only, compares it row by row and checks the timestamps, and reports the relation between power, voltage and current, overall and for each block of rows between CONNECTION_RESTORED entries.

To reproduce and check the derived file, run from the repository root:

```
python3 -m scripts.preprocess.01_fix_dataset_C_alignment --in-csv data/raw/LVDC_700V_AFE_2025_12_15.csv --out-csv data/processed/LVDC_700V_AFE_2025_12_15_aligned.csv
python3 -m scripts.preprocess.02_check_dataset_C_column_order
```

## Notes on system state and event entries

The systemstate column has the value 3 in all data rows. The data provider listed the possible states as off, standby, connecting, on and tripped/failed, in this order, but did not give their numeric codes. If the list is numbered from zero, the value 3 would correspond to on.

The file contains 12 rows in which the timestamp is followed only by the text CONNECTION_RESTORED. The meaning of these entries has not been documented by the data provider. They are preserved in the CSV file as recorded; the derived file in the code repository does not include them.

Users may need to handle such entries explicitly during data parsing or preprocessing, depending on the intended analysis.

## Data quality and limitations

The dataset reflects real industrial measurements and includes the natural noise, timing irregularities, and logging artefacts expected in operational environments.

Signal descriptions are based on column names, observed value ranges, and information from the data provider (logging at the SCCB next to the AFE).

Due to its reduced number of signals, this dataset is not intended for standalone statistical analysis, but rather as a complementary reference for comparative and validation purposes.
