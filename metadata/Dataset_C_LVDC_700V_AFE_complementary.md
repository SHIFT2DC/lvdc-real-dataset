# Dataset C – LVDC 700 V active front end installation (optional)

## Overview

This dataset contains real-world time-series measurements acquired from an AC/DC power converter developed by an industrial partner within the context of the SHIFT2DC project. The converter is intended for integration into low-voltage direct current (LVDC) systems and was operated in this case with a nominal DC bus voltage of 700 V.

The dataset corresponds to a measurement campaign carried out between 15 December 2025 at 17:26:29 and 17 December 2025 at 17:13:31. It is provided as an optional complementary dataset and reflects a different LVDC voltage level and system architecture compared to Datasets A and B.

This dataset is intended to support cross-scenario comparison, exploratory analysis, and validation of methods across different LVDC configurations.

## Acquisition context

Measurements were acquired from an AC/DC power converter designed for deployment in LVDC demonstrators and distribution systems. In this dataset, the converter was operated with a nominal DC bus voltage of 700 V under normal operating conditions.

The dataset includes measurements related to DC-side electrical behaviour, system state information, and basic thermal monitoring. The recorded signals indicate bidirectional power flow conditions, including periods with both positive and negative power values.

All measurements reflect operational system behaviour and were not obtained through a dedicated experimental campaign designed by the authors.

## Time coverage and format

The dataset is provided as a single comma-separated values (CSV) file containing time-stamped measurements. Timestamps are expressed in a human-readable format with millisecond resolution and represent the local system time of the logging device.

The nominal sampling interval is approximately 1 second, with small timing variations typical of industrial logging systems. The recording contains four gaps longer than 1 h, totalling 14.21 h; data are available for 33.57 h of the 47.78 h span. No temporal resampling or interpolation has been applied.

The dataset is provided in its original recorded form, without filtering, smoothing, or post-processing.

## Signals included

The dataset includes a compact set of electrical and system-level variables. Table 1 summarises the signals available in the dataset, together with a short description and the corresponding physical units.

### Table 1 – Signal description for Dataset C

| Column name | Description | Unit |
|------------|------------|------|
| Timestamp | Timestamp of the measurement | – |
| temperature | Measured temperature of the system or power electronics | °C |
| systemstate | System state indicator reported by the AFE controller | – |
| poweroutput | DC-side power output of the active front end | kW |
| upstreamvoltage | DC bus voltage measured upstream of the AFE | V |
| upstreamcurrent | DC current measured upstream of the AFE | A |

In addition to numerical measurements, the dataset may include textual status entries indicating system-level events, such as connection or reconnection events.

## Column order

Only the first 14 numeric rows (2025-12-15 17:26:29.132 to 17:26:42.132) follow the column order of the header. From 2025-12-15 17:26:50.828 onwards (122095 of the 122109 numeric rows), the values are consistent with the order poweroutput, upstreamvoltage, upstreamcurrent, temperature, systemstate: in 99.54% of these rows, the first value matches the product of the second and third values divided by 1000 within 0.05. This column order is inferred from the data and has not been confirmed by the data provider. The file is provided as recorded.

## Notes on system state and event entries

Some rows in the dataset contain non-numerical entries associated with system status notifications, for example connection-related events. These entries are preserved in the dataset for traceability and reflect the original logging behaviour of the system.

Users may need to handle such entries explicitly during data parsing or preprocessing, depending on the intended analysis.

## Data quality and limitations

The dataset reflects real industrial measurements and includes the natural noise, timing irregularities, and logging artefacts expected in operational environments.

Signal descriptions are based on column names, observed value ranges, and contextual information provided with the dataset. The internal semantics of the system state variable and event messages may depend on proprietary implementation details of the AFE controller.

Due to its reduced number of signals, this dataset is not intended for standalone statistical analysis, but rather as a complementary reference for comparative and validation purposes.
