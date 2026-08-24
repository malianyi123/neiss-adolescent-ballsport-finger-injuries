#!/usr/bin/env python
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from utils import ROOT


STEPS = [
    "00_download_neiss.py",
    "01_parse_dictionary.py",
    "02_clean_neiss.py",
    "03_build_cohort.py",
    "04_analysis.py",
    "05_make_tables.py",
    "06_make_figures.py",
    "07_make_manuscript.py",
    "08_make_table_figure_legends.py",
]


def main() -> None:
    for step in STEPS:
        path = ROOT / "scripts" / step
        print(f"\n=== Running {step} ===", flush=True)
        proc = subprocess.run([sys.executable, str(path)], cwd=ROOT)
        if proc.returncode != 0:
            raise SystemExit(f"Pipeline stopped at {step} with exit code {proc.returncode}")
    print("\nPipeline complete. See outputs/reports/final_run_report.md")


if __name__ == "__main__":
    main()
