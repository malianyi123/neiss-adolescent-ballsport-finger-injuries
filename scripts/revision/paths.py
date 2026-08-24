"""Shared paths for the revision analyses.

All paths resolve relative to the repository root, so the scripts run from any
working directory without editing.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PROCESSED_DIR = ROOT / "data" / "processed"
COHORT_MAIN = PROCESSED_DIR / "cohort_main.csv"
COHORT_SENSITIVITY = PROCESSED_DIR / "cohort_sensitivity_2019_2025.csv"

REVISION_DIR = ROOT / "outputs" / "revision"
RESULTS_DIR = REVISION_DIR / "results"
TABLE_DIR = REVISION_DIR / "tables"
FIGURE_DIR = REVISION_DIR / "figures"
SUPPLEMENT_DIR = REVISION_DIR / "supplementary"
SUPPLEMENT_FIGURE_DIR = SUPPLEMENT_DIR / "supplementary figure"


def ensure_dirs() -> None:
    for p in (RESULTS_DIR, TABLE_DIR, FIGURE_DIR, SUPPLEMENT_DIR, SUPPLEMENT_FIGURE_DIR):
        p.mkdir(parents=True, exist_ok=True)


def require_cohort() -> None:
    missing = [str(p) for p in (COHORT_MAIN, COHORT_SENSITIVITY) if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Analytic cohort files not found:\n  "
            + "\n  ".join(missing)
            + "\n\nRun the main pipeline first:  make all\n"
              "(or at minimum: make download && make clean-data && make analysis)"
        )
