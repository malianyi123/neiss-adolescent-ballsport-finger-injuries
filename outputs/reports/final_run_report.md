# Final Run Report

- Generated at pipeline runtime from local outputs.
- Years included: 2015-2025
- Final unweighted cohort size: 16,066
- Final weighted national estimate: 441,441

## Top Sport Groups

- football: 166,972 weighted ED visits (unweighted n=5,990)
- basketball: 154,526 weighted ED visits (unweighted n=5,770)
- baseball/softball: 40,297 weighted ED visits (unweighted n=1,282)
- soccer: 34,880 weighted ED visits (unweighted n=1,430)
- other selected ball sports: 27,066 weighted ED visits (unweighted n=974)

## Key Output Paths

- Main cohort: `data/processed/cohort_main.csv`
- Main tables: `outputs/tables`
- Main figures: `outputs/figures`
- Manuscript: `outputs/manuscript/manuscript.md`
- Supplement: `outputs/supplementary`
- Data inventory: `outputs/reports/data_inventory.csv`

## Warnings and Limitations

- NEISS estimates represent ED visits, not population incidence.
- Sport exposure denominators are unavailable.
- Product/activity codes indicate association, not confirmed athlete status or causality.
- Instability flags should be checked before interpreting subgroup estimates.
- Primary adjusted model generated with R survey::svydesign and survey::svyglm.
- Severe-disposition model not run. Severe events=89; approximate parameters=9; minimum sport category n=617. The prespecified sparse-event rule was not met.
