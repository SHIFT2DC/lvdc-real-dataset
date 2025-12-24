# Data directory

This directory contains the data files associated with the LVDC real-world dataset.

## raw/

The `raw/` folder contains the original CSV files as obtained from the monitoring system. These files are kept as close as possible to the exported measurements to preserve traceability.

## processed/

The `processed/` folder contains derived versions of the dataset produced after basic preprocessing steps, such as cleaning, time alignment, and optional feature generation (for example dV/dt). Processed files should be reproducible from the raw data using the scripts provided in `scripts/`.
