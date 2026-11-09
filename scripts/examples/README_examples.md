# Example: LVDC transient event detection

This example shows how voltage transient events can be detected in Datasets A and B using the |dV/dt| criterion. The script computes |dV/dt| of the DC bus voltage, selects the samples at or above a percentile threshold, groups contiguous samples into candidate events and plots a window around the event with the largest |dV/dt|.

With the command given below, the script reproduces the event window shown in Figure 5 of the associated Data Descriptor.

## Contents

```
lvdc_dataset_example_scripts/
├── README_examples.md
├── CODE_VERSION.txt
├── requirements.txt
├── configs/
│   └── datasets.yaml
├── data/
│   └── raw/            (place the CSV files here)
└── scripts/
    ├── common/
    │   └── io_config.py
    └── examples/
        └── 01_event_detection_dvdt.py
```

The `scripts` folders also contain empty `__init__.py` files. `CODE_VERSION.txt` identifies the version of the code in the SHIFT2DC GitHub repository from which this package was generated. In that repository, the same files are in the same places, and the commands below are run from the repository root.

## Requirements

Python 3.11 or later (tested with Python 3.11 and 3.13). The package versions are listed in `requirements.txt`.

```bash
cd lvdc_dataset_example_scripts
python3 -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Data

Download `LVDC_380V_hybrid_ACDC_battery_off_2025_05_02.csv` (Dataset A) from the Zenodo record https://doi.org/10.5281/zenodo.18524234 and place it in `data/raw/` without renaming it. Its MD5 checksum is `ce964445186e1b55f93c2818f39885b6`.

To run the example on Dataset B, also place `LVDC_380V_hybrid_ACDC_battery_on_2024_05_10.csv` in `data/raw/` (MD5 `80ac7995a64d52a9646039c882eb7df7`).

## Reproducing Figure 5

Run from the folder that contains `scripts/`:

```bash
python3 -m scripts.examples.01_event_detection_dvdt \
    --dataset-id A \
    --percentile 99.9 \
    --window-s 60 \
    --related-cols auto \
    --export-window-csv \
    --plot \
    --run-id fig5
```

## Expected output

The files are written to `out/A/fig5/examples/dvdt_event_example/`:

- `selected_event.json`: selected event and analysis window
- `params.json`: run parameters
- `window.csv`: samples in the 60 s window
- `event_window_A.svg` and `event_window_A.pdf`: event window figure

The selected event starts at 2025-05-02 15:19:14 and ends at 15:19:15, with a peak |dV/dt| of approximately 19.8 V/s. The dashed line in the figure marks the sample with the largest |dV/dt|, at 2025-05-02 15:19:15 (`event_peak_time` in `selected_event.json`), and the window spans 15:18:45 to 15:19:45.

The |dV/dt| value of a sample is computed from the change with respect to the previous sample. The values therefore describe changes at the sampling interval of the recording (approximately 1 s), not faster converter transients. The detected events are candidate events selected by a percentile threshold; they are not labelled or independently verified.

## Dataset B

Replace `--dataset-id A` with `--dataset-id B`. The files are written to `out/B/fig5/examples/dvdt_event_example/`. The selected event is the sample at 2024-05-10 16:47:04, with a peak |dV/dt| of approximately 26.5 V/s, and the window spans 16:46:34 to 16:47:34.
