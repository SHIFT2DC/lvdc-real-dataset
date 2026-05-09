# Example: LVDC transient event detection

This example script demonstrates how voltage transient events can be detected in the LVDC datasets using the |dV/dt| criterion.

The script computes the derivative of the DC bus voltage and identifies extreme events using a percentile-based threshold. A representative event window is then automatically selected and visualized.

The generated figure corresponds to the example shown in the associated Data Descriptor manuscript.

## Requirements

Python 3.x

Required packages:

- pandas
- numpy
- matplotlib

## Example usage

Dataset A (battery off):

python3 -m scripts.examples.01_event_detection_dvdt \
    --dataset-id A \
    --percentile 99.9 \
    --window-s 10 \
    --related-cols auto \
    --export-window-csv \
    --plot

## Output

The script generates:

- event_window_A.svg
- event_window_A.pdf
- window.csv

These files illustrate a representative voltage transient event detected in the dataset.