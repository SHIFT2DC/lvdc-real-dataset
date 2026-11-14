# Dataset B – LVDC 380 V installation with battery operation

## Overview

This dataset contains real-world time-series measurements acquired from an operational hybrid AC/DC electrical installation with a nominal low-voltage direct current (LVDC) bus of 380 V. The data were collected within the context of the SHIFT2DC project and reflect normal operation of the installation during a continuous measurement period.

The dataset corresponds to a measurement campaign carried out on 10 May 2024. According to the data provider, the battery energy storage system of the installation was in operation at that time. The battery current (`BAT I`) is non-zero in 56528 of the 86399 samples (65.43%), with values from -3.9 A to 9.8 A. Dataset A was recorded on 2 May 2025 under different power conditions, so differences between the two recordings cannot be attributed to the battery alone.

This dataset is intended to support research on LVDC monitoring, event detection, and data-driven analysis under realistic operating conditions. It can be compared with Dataset A, taking into account the different recording dates and power conditions.

## Acquisition context

Measurements were acquired from an industrial hybrid AC/DC installation operated by an industrial partner of the SHIFT2DC project. The system includes an AC grid connection, multiple AC and DC loads, photovoltaic generation units, a battery energy storage system, and a DC distribution network regulated using droop control.

The nominal DC bus voltage is 380 V. In this recording, `NRE DCbus U` ranges from 348.1 V to 398.0 V, and 39129 of 86399 samples (45.29%) are below 370 V, the lower limit of the droop-control range given by the data provider for Dataset A.

All measurements reflect normal operational conditions of the installation and were not obtained through a dedicated experimental campaign designed by the authors.

## Time coverage and format

The dataset is provided as a single comma-separated values (CSV) file containing time-stamped measurements. Timestamps are expressed in a human-readable format (YYYY-MM-DD HH:MM:SS). The time zone and the clock source of the logging device have not been documented by the data provider.

The nominal sampling interval is approximately 1 second. In every minute of the recording, second :53 is missing and second :54 appears twice, giving 1440 pairs of rows with the same timestamp; the two rows of each pair are not identical. No temporal resampling or interpolation has been applied.

The dataset is provided in its original recorded form, without filtering, smoothing, or post-processing.

## Signals included

The dataset includes electrical measurements from both the AC and DC sides of the installation, as well as system status, battery-related variables, and diagnostic indicators. Table 1 summarises the signals available in the dataset, together with a short description and the corresponding physical units.

### Table 1 – Signal description for Dataset B

| Column name | Description | Unit |
|------------|------------|------|
| Time | Timestamp of the measurement | – |
| P_ges | Total active power of the installation | W |
| LF_ges | Global power factor of the installation. Recorded values range from -0.92 to 1.58; 742 of the 86399 samples (0.86%) exceed 1 in absolute value, which is not consistent with a power factor. The cause could not be determined from the information available | – |
| S_ges | Apparent power of the installation. This signal was consistently recorded as zero throughout the full recording period | VA |
| I_L1 | AC phase L1 current | A |
| I_L2 | AC phase L2 current | A |
| I_L3 | AC phase L3 current | A |
| I_N | Neutral current | A |
| U_L1_N | AC phase L1 to neutral voltage | V |
| U_L2_N | AC phase L2 to neutral voltage | V |
| U_L3_N | AC phase L3 to neutral voltage | V |
| FQ_L1 | AC frequency measured on phase L1 | Hz |
| FQ_L2 | AC frequency measured on phase L2 | Hz |
| FQ_L3 | AC frequency measured on phase L3 | Hz |
| Diffstrom Status | Differential current status indicator reported by the system | – |
| PV Carport Pges | Active power from PV carport installation | W |
| PV Werkstatt Pges | Active power from PV workshop installation | W |
| NRE DCbus U | DC bus voltage at the main LVDC node | V |
| NRE K1 P1 | Power of DC/DC converter branch K1. In this dataset, values range from -3329 to 1517; 66628 samples (77.12%) are positive, 14778 (17.10%) negative and 4993 (5.78%) zero. The sign convention has not been documented by the data provider | W |
| NRE K4 P1 | Power of DC/DC converter branch K4, associated with a vertical PV installation | W |
| NRE K6 P1 | Power of DC/DC converter branch K6, associated with a vertical PV installation | W |
| Nachladung P | AC/DC infeed active power reported by the monitoring system (see note below) | W |
| Nachladung I | AC/DC infeed current reported by the monitoring system (see note below) | A |
| DC Status | DC system status indicator | – |
| DC ISO R | DC insulation resistance | Ω |
| AC ISO R | AC insulation resistance. According to the system operator, this measurement point may not be connected | Ω |
| BAT SoP | Battery state of power indicator | W |
| BAT SoC | Battery state of charge indicator | % |
| BAT SoCP | Processed battery state of charge indicator | % |
| BAT SoOP | Battery operational state indicator | – |
| BAT U | Battery voltage | V |
| BAT I | Battery current | A |
| BAT T | Battery temperature | °C |
| BAT Stat | Battery status indicator | – |
| BAT RlSt | Battery relay state indicator | – |
| NetzL1_H1 | Harmonic component H1 on phase L1 | – |
| NetzL1_H3 | Harmonic component H3 on phase L1 | – |
| NetzL1_H6 | Harmonic component H6 on phase L1 | – |
| NetzL2_H1 | Harmonic component H1 on phase L2 | – |
| NetzL2_H3 | Harmonic component H3 on phase L2 | – |
| NetzL2_H6 | Harmonic component H6 on phase L2 | – |
| NetzL3_H1 | Harmonic component H1 on phase L3 | – |
| NetzL3_H3 | Harmonic component H3 on phase L3 | – |
| NetzL3_H6 | Harmonic component H6 on phase L3 | – |

## Notes on battery-related signals

In contrast to Dataset A, where `BAT I` and `BAT SoP` are 0 throughout, the battery current (`BAT I`) in this dataset takes both positive and negative values and `BAT SoC` ranges from 22% to 73%. The sign convention of `BAT I` has not been documented by the data provider.

The exact internal control logic of the battery system is not described in this dataset and may depend on proprietary implementation details of the industrial installation.

The signals `Nachladung P` and `Nachladung I` are interpreted as the active power and current of the AC/DC infeed, based on information provided by the system operator. The original naming convention of the logging system may suggest a different interpretation and should be considered when working with these signals.

## Data quality and limitations

The dataset reflects real industrial measurements and includes the natural noise, small timing irregularities, and variability expected in operational environments. No explicit data cleaning or validation beyond basic integrity checks has been applied.

Signal descriptions are based on variable naming conventions, observed value ranges, and contextual information provided with the dataset. The detailed internal semantics of selected diagnostic or status indicators may depend on the specific implementation of the industrial monitoring system.

Users are encouraged to apply their own preprocessing, filtering, or resampling strategies depending on the intended application.
