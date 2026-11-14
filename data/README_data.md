# Data directory

This directory contains the data files associated with the LVDC dataset.

## raw/

The `raw/` folder contains the reference CSV files used in the manuscript and 
analysis pipeline. Files follow a consistent naming convention that encodes the 
voltage level, system configuration, battery state, and acquisition date.

## processed/

The `processed/` folder contains a derived version of Dataset C
(`LVDC_700V_AFE_2025_12_15_aligned.csv`), generated from
`raw/LVDC_700V_AFE_2025_12_15.csv` by the script
`scripts/preprocess/01_fix_dataset_C_alignment.py`. In the raw file, the data
rows after the second CONNECTION_RESTORED entry (file line 17) do not follow
the column order of the header. The derived file contains the 122109 data rows
in the column order of the header and omits the 12 CONNECTION_RESTORED
entries. The order of the values in the raw rows is determined from the data,
using the relation between power, voltage and current, and can be checked with
`scripts/preprocess/02_check_dataset_C_column_order.py`. The raw file is not
modified. Details are given in `metadata/Dataset_C_LVDC_700V_AFE_complementary.md`.
Datasets A and B do not require preprocessing and are used directly from
`raw/`.

## original_from_partners/

The `original_from_partners/` folder contains the original files received from 
the industrial partners, preserved without modification for traceability. These 
files use the original naming conventions and data formats as provided, and may 
differ from the reference files in `raw/` in terms of filename, structure, or 
column ordering.