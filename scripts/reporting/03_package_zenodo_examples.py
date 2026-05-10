"""
03_package_zenodo_examples.py

Create the Zenodo example package for the LVDC dataset.

Purpose
-------
This script packages the reproducible example used in the associated Data Descriptor
manuscript into a ZIP archive that can be uploaded to Zenodo together with
the dataset files.

The archive contains:
    - scripts/examples/01_event_detection_dvdt.py
    - scripts/examples/README_examples.md

These files provide a minimal example demonstrating how voltage transient
events can be detected using the |dV/dt| criterion and how the representative
event figure shown in the manuscript can be reproduced.

Output
------
The script generates:

    release/zenodo_examples/lvdc_dataset_example_scripts.zip

This ZIP file can be directly uploaded to the Zenodo dataset record.

Usage
-----

From the repository root:

    python3 -m scripts.reporting.03_package_zenodo_examples

After execution, upload the generated ZIP file to the Zenodo dataset page.

Notes
-----
This script is intentionally simple and only packages the example scripts
needed for reproducibility. It does not depend on the dataset processing
pipeline and can be executed independently.
"""

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

OUT_DIR = ROOT / "release" / "zenodo_examples"
EXAMPLES_DIR = ROOT / "scripts" / "examples"

ZIP_NAME = "lvdc_dataset_example_scripts"

def main():

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    tmp_dir = OUT_DIR / "examples"

    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)

    tmp_dir.mkdir()

    shutil.copy(EXAMPLES_DIR / "01_event_detection_dvdt.py", tmp_dir)
    shutil.copy(EXAMPLES_DIR / "README_examples.md", tmp_dir)

    zip_path = shutil.make_archive(
        str(OUT_DIR / ZIP_NAME),
        "zip",
        root_dir=OUT_DIR,
        base_dir="examples",
    )

    shutil.rmtree(tmp_dir)

    print("Zenodo example package created:")
    print(zip_path)


if __name__ == "__main__":
    main()