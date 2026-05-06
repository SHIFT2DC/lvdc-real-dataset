# Dataset A – LVDC 380 V installation without battery operation

## Overview

This dataset contains real-world time-series measurements acquired from an operational hybrid AC/DC electrical installation with a nominal low-voltage DC (LVDC) bus of 380 V. The data were collected within the context of the SHIFT2DC project and reflect normal operation of the installation during an extended continuous period.

The dataset corresponds to a measurement campaign carried out on 2 May 2025. During this period, the battery energy storage system connected to the DC bus was present but not operational due to a reported fault condition. As a result, the recorded DC bus behaviour represents an unbuffered operating regime, where voltage variations are mainly driven by load changes and power electronic converter operation.

This dataset is intended to support research on LVDC monitoring, event detection, and data-driven analysis under realistic operating conditions.

## Acquisition context

Measurements were acquired from an industrial hybrid AC/DC installation operated by an industrial partner involved in the SHIFT2DC project. The system includes an AC grid connection, multiple AC and DC loads, and a DC distribution network regulated using droop control.

The nominal DC bus voltage is 380 V, with typical operating values observed between approximately 370 V and 400 V. During the recording period, no active battery buffering was present, allowing natural voltage variations to appear in response to load dynamics.

All measurements reflect normal operation of the installation and were not obtained through a dedicated experimental campaign designed by the authors.

## Time coverage and format

The dataset is provided as a single comma-separated values (CSV) file containing time-stamped measurements. Timestamps are expressed in a human-readable format (YYYY-MM-DD HH:MM:SS) and represent the local system time of the logging device.

The nominal sampling interval is approximately 1 second, with minor timing variations typical of industrial logging systems. No temporal resampling or interpolation has been applied.

The dataset is provided in its original recorded form, without filtering, smoothing, or post-processing.

## Signals included

The dataset includes electrical measurements from both the AC and DC sides of the installation, as well as system status and diagnostic variables. Table 1 summarises the signals available in the dataset, together with a short description and the corresponding physical units.

| Column name | Description | Unit |
|------------|------------|------|
| Time | Timestamp of the measurement | – |
| P_ges | Total active power of the installation | W |
| LF_ges | Likely the global power factor of the installation as reported by the monitoring system. Exact definition depends on the internal implementation and could not be independently confirmed | – |
| S_ges | Apparent power of the installation as reported by the monitoring system. This signal was consistently recorded as zero during the acquisition period; its reliability cannot be confirmed | VA |
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
| NRE K1 P1 | Power of DC/DC converter branch K1. In this dataset, values are consistently negative, indicating power consumption from the DC bus (load-side operation) | W |
| NRE K4 P1 | Power of DC/DC converter branch K4, associated with a vertical PV installation | W |
| NRE K6 P1 | Power of DC/DC converter branch K6, associated with a vertical PV installation | W |
| Nachladung P | AC/DC infeed active power reported by the monitoring system (see note below) | W |
| Nachladung I | AC/DC infeed current reported by the monitoring system (see note below) | A |
| DC Status | DC system status indicator | – |
| DC ISO R | DC insulation resistance | Ω |
| AC ISO R | AC insulation resistance. This signal was consistently recorded as zero during the acquisition period; its reliability cannot be confirmed | Ω |
| BAT SoP | Battery state of power indicator | % |
| BAT SoC | Battery state of charge indicator | % |
| BAT SoCP | Processed battery state of charge indicator | % |
| BAT SoOP | Battery operational state indicator | – |
| BAT U | Battery voltage | V |
| BAT I | Battery current | A |
| BAT T | Battery temperature | °C |
| BAT Stat | Battery status indicator | – |
| BAT RlSt | Battery relay state indicator | – |
| NetzL1_H1 | Harmonic component indicator H1 on phase L1. Physical unit and exact definition depend on the internal implementation of the monitoring system and could not be independently confirmed | – |
| NetzL1_H3 | Harmonic component indicator H3 on phase L1. Physical unit and exact definition depend on the internal implementation of the monitoring system and could not be independently confirmed | – |
| NetzL1_H6 | Harmonic component indicator H6 on phase L1. Physical unit and exact definition depend on the internal implementation of the monitoring system and could not be independently confirmed | – |
| NetzL2_H1 | Harmonic component indicator H1 on phase L2. Physical unit and exact definition depend on the internal implementation of the monitoring system and could not be independently confirmed | – |
| NetzL2_H3 | Harmonic component indicator H3 on phase L2. Physical unit and exact definition depend on the internal implementation of the monitoring system and could not be independently confirmed | – |
| NetzL2_H6 | Harmonic component indicator H6 on phase L2. Physical unit and exact definition depend on the internal implementation of the monitoring system and could not be independently confirmed | – |
| NetzL3_H1 | Harmonic component indicator H1 on phase L3. Physical unit and exact definition depend on the internal implementation of the monitoring system and could not be independently confirmed | – |
| NetzL3_H3 | Harmonic component indicator H3 on phase L3. Physical unit and exact definition depend on the internal implementation of the monitoring system and could not be independently confirmed | – |
| NetzL3_H6 | Harmonic component indicator H6 on phase L3. Physical unit and exact definition depend on the internal implementation of the monitoring system and could not be independently confirmed | – |

## Notes on battery-related signals

Although battery-related variables are included in the dataset, the battery system was not operational during the acquisition period. These signals therefore reflect static or inactive states and should not be interpreted as active battery participation in the LVDC control.

The presence of these variables allows structural consistency with other datasets acquired from the same installation under different operating conditions.

The signals `Nachladung P` and `Nachladung I` were originally labelled as battery charging power and current. Based on observed values during the acquisition period, when the battery was inactive (`BAT I` = 0 A throughout), these signals are interpreted as the active power and current of the AC/DC infeed. This interpretation is consistent with information provided by the system operator and should be considered when using these signals.

## Data quality and limitations

The dataset reflects real industrial measurements and includes the natural noise, small timing irregularities, and variability expected in operational environments. No explicit data cleaning or validation beyond basic integrity checks has been applied.

Signal descriptions are based on variable naming conventions, observed value ranges, and contextual information provided with the dataset. The detailed internal semantics of selected diagnostic or status indicators may depend on the specific implementation of the industrial monitoring system.

Users are encouraged to apply their own preprocessing, filtering, or resampling strategies depending on the intended application.
