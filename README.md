# Adolescent ball-sport finger fractures and dislocations (NEISS, 2015–2025)

Reproducible analysis pipeline for the manuscript:

> **Adolescent finger fractures and dislocations associated with selected ball sports: national emergency department burden and case mix, 2015–2025**

[![DOI](https://zenodo.org/badge/DOI/XX.XXXX/zenodo.XXXXXXX.svg)](https://doi.org/XX.XXXX/zenodo.XXXXXXX)
<!-- TODO: replace the badge above with the one Zenodo gives you after the first release -->

Every table, figure and supplementary file in the manuscript is generated from the official
public CPSC data by the code in this repository. No numbers are entered by hand.

---

## What this study does

Using the public [NEISS](https://www.cpsc.gov/Research--Statistics/NEISS-Injury-Data) annual
archived files for treatment years 2015–2025, the pipeline identifies emergency department
visits by adolescents aged 10–18 years with a primary finger injury coded as fracture or
dislocation and a verified selected ball-sport product/activity code, then estimates the
national burden and diagnostic case mix using the NEISS complex survey design.

Headline result: **441,441 estimated ED visits (95% CI 341,825–541,056)** from 16,066
unweighted records.

---

## Requirements

- Python 3.10 or later
- R with the `survey` package (optional; used for the `survey::svyglm` cross-check in
  `scripts/04a_survey_analysis.R`. The Python path produces the same estimates.)
- ~2 GB free disk for the downloaded source files
- LibreOffice (optional; only for rendering `.docx` output to PDF during QC)

```bash
make install          # pip install -r requirements.txt
# or:  conda env create -f environment.yml
```

---

## Reproduce the analysis

```bash
make all              # download → clean → cohort → analysis → tables → figures → manuscript
make revision         # the revision analyses (see below); requires `make all` first
```

Stage by stage, if you prefer:

```bash
make download         # fetch official NEISS files + data dictionary, verify code mappings
make clean-data       # standardise columns, build the analytic cohort
make analysis         # weighted estimates, instability flags, adjusted model
make tables figures   # tables and figures
make manuscript       # manuscript draft and legends
```

### Source data is not stored in this repository

The raw annual files total roughly 1.4 GB and are public CPSC products, so they are **not**
committed here. `make download` fetches them from the official archive into
`data/raw/neiss/`. If CPSC blocks automated download, follow
[`data/raw/README_download.md`](data/raw/README_download.md) to place the files manually and
re-run `make all`.

**Data vintage is recorded, not assumed.** `outputs/reports/download_log.csv` records the
source URL, server last-modified timestamp and download time for every annual file, so the
exact vintage analysed in the paper can be verified. The 2025 file was obtained from the
CPSC *archived annual* directory (the finalised calendar-year release, not the interactive
query system), with a server timestamp of 6 May 2026, downloaded 16 May 2026 UTC.

---

## Repository layout

```
config/
  study_config.yml              study parameters, instability criteria, sparse-event rule
  code_mappings_reviewed.yml    product/activity, body-part and diagnosis code mappings,
                                verified against the official CPSC dictionary
scripts/
  00_download_neiss.py          fetch official source files; write download log
  01_parse_dictionary.py        parse and validate the official CPSC dictionary/format file
  02_clean_neiss.py             standardise columns across annual files
  03_build_cohort.py            apply inclusion criteria; build main + sensitivity cohorts
  04_analysis.py                weighted estimates, CVs, instability flags, adjusted model
  04a_survey_analysis.R         R survey::svydesign / svyglm cross-check
  05_make_tables.py             main and supplementary tables
  06_make_figures.py            figures 2–5 and supplementary figures
  06a_make_figure1_cohort_flow.py   cohort flow diagram
  07_make_manuscript.py         manuscript assembly
  08_make_table_figure_legends.py   table and figure legends
  utils.py                      survey estimator, instability flags, shared I/O
  revision/                     revision analyses — see below
docs/                           analysis plan, codebook, variable definitions,
                                validation report, limitations and assumptions
outputs/
  tables/  figures/  supplementary/  manuscript/  reports/
  revision/                     output of `make revision`
data/
  raw/  intermediate/  processed/    (all gitignored except download instructions)
```

---

## Revision analyses (`make revision`)

`scripts/revision/` contains the analyses added during peer review. They read the analytic
cohort produced by the main pipeline and write to `outputs/revision/`.

| Script | What it produces |
|---|---|
| `survey_lib.py` | Design-based estimator library: weighted totals, ratios, differences and linear combinations with Taylor-linearised variances, matching the estimator in `utils.py` |
| `run_reanalysis.py` | 95% CIs for every weighted estimate; survey-weighted trend models; design-based temporal contrasts; sport-specific severe-disposition instability; multiplicity adjustment; by-sport sensitivity breakdown; rounding reconciliation; narrative diagnostic concordance; comprehensive instability register |
| `run_extra.py` | Composition of the residual sport category; model refits excluding puck and hockey codes; volleyball dislocation-proportion contrasts; mechanism distribution with CIs |
| `build_tables_docx.py` | Revised Tables 1–3 |
| `build_figures.py` | Revised Figures 1–5 |
| `build_supplementary.py` | Supplementary Tables S1–S8, Supplementary Methods, STROBE and RECORD checklists, supplementary figures |

Statistical notes:

- **Variance** uses the stratified ultimate-cluster (Taylor linearisation) estimator on
  NEISS `stratum` / `psu` / `weight`. The cohort spans 5 strata and 103 PSUs, with 9–48 PSUs
  per stratum; no stratum contributes a single PSU, so no lonely-PSU adjustment is needed.
- **Intervals** for totals are estimate ± 1.96 SE; intervals for proportions and ratios are
  computed on the log scale from the linearised ratio variance.
- **Trend** models regress annual weighted estimates on year by inverse-variance weighted
  least squares using each year's design-based variance, on additive and multiplicative scales.
- **Multiplicity**: the five sport comparisons against football are treated as a family and
  reported with Holm-adjusted p values alongside unadjusted ones.

The pipeline reproduces the published cohort total exactly: 441,440.82 weighted visits,
SE 50,825.19, CV 11.51%.

---

## Citing

Please cite the manuscript, and cite this repository via the version DOI shown in the badge
above (see `CITATION.cff`).

## Licence

Analysis code: MIT (see [`LICENSE`](LICENSE)). NEISS data is a public product of the U.S.
Consumer Product Safety Commission and is not redistributed here.
