.PHONY: install download clean-data analysis tables figures manuscript legends supplement revision all clean-outputs clean-revision

PYTHON ?= python

install:
	$(PYTHON) -m pip install -r requirements.txt

download:
	$(PYTHON) scripts/00_download_neiss.py
	$(PYTHON) scripts/01_parse_dictionary.py

clean-data:
	$(PYTHON) scripts/02_clean_neiss.py
	$(PYTHON) scripts/03_build_cohort.py

analysis:
	$(PYTHON) scripts/04_analysis.py

tables:
	$(PYTHON) scripts/05_make_tables.py

figures:
	$(PYTHON) scripts/06_make_figures.py

manuscript:
	$(PYTHON) scripts/07_make_manuscript.py

legends:
	$(PYTHON) scripts/08_make_table_figure_legends.py

supplement: tables figures manuscript legends

# Revision analyses (2026 peer review): design-based confidence intervals, survey-weighted
# trend analysis, multiplicity adjustment, severe-disposition instability assessment,
# narrative diagnostic concordance, and the revised tables, figures and supplementary files.
# Requires data/processed/cohort_main.csv, i.e. run `make all` (or at least
# `make download clean-data analysis`) first.
revision:
	$(PYTHON) scripts/revision/run_reanalysis.py
	$(PYTHON) scripts/revision/run_extra.py
	$(PYTHON) scripts/revision/build_tables_docx.py
	$(PYTHON) scripts/revision/build_figures.py
	$(PYTHON) scripts/revision/build_supplementary.py

all:
	$(PYTHON) scripts/run_all.py

clean-outputs:
	rm -rf data/intermediate/* data/processed/* outputs/tables/* outputs/figures/* outputs/supplementary/* outputs/manuscript/* outputs/reports/*

clean-revision:
	rm -rf outputs/revision/*
