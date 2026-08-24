# Statistical Analysis Plan

## Study Design

Retrospective cross-sectional descriptive and trend analysis of public CPSC NEISS annual archived data, 2015-2025.

## Population

Adolescents aged 10-18 years with emergency department visits for finger fracture or dislocation associated with selected ball-sport product/activity codes.

## Main Cohort

The main cohort uses variables available across the full study period:

- `Body_Part` equal to official finger code.
- `Diagnosis` equal to official fracture or dislocation code.
- `Product_1` or `Product_2` matching verified selected ball-sport product codes.

Variables added for 2019 and later (`Body_Part_2`, `Diagnosis_2`, `Product_3`) are excluded from the main cohort and evaluated only in a sensitivity cohort.

## Estimates

All national burden estimates are weighted using NEISS sample weights. Raw sample counts are reported only as unweighted NEISS sample counts and are not interpreted as national burden.

## Instability Flags

CPSC instability criteria are applied:

- weighted estimate < 1,200
- unweighted n < 20
- CV > 33%, if CV can be estimated from design variables

## Models

Primary model: adjusted odds of dislocation versus fracture, with fracture as the reference outcome. Predictors include sport group, age group, sex, and treatment year.

Secondary model: severe disposition versus treated/released, only if sparse-event rules are satisfied.

## Trend Analysis

Annual weighted national estimates are plotted for 2015-2025. Pandemic years 2020-2021 are labeled descriptively. Trend modeling is interpreted cautiously because NEISS does not include sport exposure denominators.
