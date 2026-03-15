#!/bin/bash

echo "Packaging Zenodo example scripts..."

python3 -m scripts.reporting.03_package_zenodo_examples

echo "Zenodo package created:"
echo "release/zenodo_examples/lvdc_dataset_example_scripts.zip"