from __future__ import annotations


MAIN_TABLE_FIGURE_LEGENDS = """# Tables and Figure Legends

Table 1. Baseline characteristics of the main analytic cohort of adolescent NEISS records associated with selected ball-sport activities, 2015-2025. The table summarizes unweighted NEISS record counts, weighted national estimates of emergency department (ED) visits, weighted percentages, coefficients of variation (CVs), and instability flags for age group, sex, calendar period, sport group, diagnosis group, ED disposition, and season. Percentages are weighted percentages within the final analytic cohort. Calendar periods were defined descriptively as pre-pandemic (2015-2019), pandemic (2020-2021), and post-pandemic (2022-2025). Instability flags follow CPSC guidance and identify estimates with weighted estimate <1,200, unweighted n <20, or CV >33%. CPSC, U.S. Consumer Product Safety Commission; NEISS, National Electronic Injury Surveillance System.

Table 2. Sport-specific injury patterns among adolescent NEISS records for selected ball-sport-associated finger fractures and dislocations, 2015-2025. For each sport group, the table reports unweighted NEISS record counts, weighted national estimates of ED visits, weighted percentages of fracture and dislocation within sport group, weighted percentage with severe ED disposition, top season by weighted estimate, CV, and instability flag. Severe disposition was defined as admission, transfer, observation/held for observation, or fatality when present; treated-and-released visits were the reference nonsevere disposition. "Other selected ball sports" combines verified official NEISS product/activity codes with sufficient aggregate sample size, including lacrosse, hockey-related activities, handball, field hockey, rugby, and other or not-specified ball-sport codes. ED, emergency department; NEISS, National Electronic Injury Surveillance System.

Table 3. Survey-weighted adjusted model for dislocation versus fracture among adolescent NEISS records associated with selected ball-sport activities, 2015-2025. The dependent variable was diagnosis group, coded as dislocation versus fracture. Adjusted odds ratios (ORs), 95% confidence intervals (CIs), and p values were estimated using a survey-weighted logistic regression model that included sport group, age group, sex, and treatment year. Football, age 10-12 years, male sex, and fracture diagnosis served as reference categories. Treatment year was modeled per calendar-year increase and centered for model stability. Standard errors were estimated using NEISS strata, primary sampling unit, and sample weight variables when available. CI, confidence interval; NEISS, National Electronic Injury Surveillance System; OR, odds ratio.

Figure 1. Flow diagram of cohort selection. Counts in screening boxes are unweighted NEISS records. The final analytic cohort contained 16,066 unweighted NEISS records, corresponding to a weighted national estimate of 441,441 ED visits. The final national estimate was calculated using NEISS sample weights. The main cohort used Product_1 and Product_2 only because Product_3 was introduced later. ED, emergency department; NEISS, National Electronic Injury Surveillance System.

Figure 2. Annual weighted national estimates of adolescent selected ball-sport-associated finger fractures and dislocations presenting to U.S. emergency departments, 2015-2025. Points show weighted national ED visit estimates by treatment year, and vertical error bars show standard errors estimated using available NEISS design variables. The shaded interval marks the pandemic period, 2020-2021, for descriptive context. Estimates represent ED visit burden and should not be interpreted as incidence because sport participation denominators were not available. ED, emergency department; NEISS, National Electronic Injury Surveillance System.

Figure 3. Sport-group distribution of adolescent selected ball-sport-associated finger fractures and dislocations, 2015-2025. Horizontal bars show weighted national estimates of ED visits by sport group. Sport groups were assigned using verified official NEISS product/activity codes from Product_1 or Product_2. Values represent national ED visit estimates rather than participant-normalized sport-specific rates. ED, emergency department; NEISS, National Electronic Injury Surveillance System.

Figure 4. Sport-specific diagnosis pattern among adolescent selected ball-sport-associated finger fractures and dislocations, 2015-2025. Stacked horizontal bars show the weighted percentage of fracture and dislocation within each sport group. Percentages are weighted within sport group and therefore sum to 100% for each sport. ED, emergency department; NEISS, National Electronic Injury Surveillance System.

Figure 5. Adjusted odds ratios for dislocation versus fracture among adolescent NEISS records associated with selected ball-sport activities, 2015-2025. The forest plot displays adjusted ORs and 95% CIs from the survey-weighted logistic regression model shown in Table 3. The vertical reference line indicates OR = 1. Estimates to the right of the line indicate higher adjusted odds of dislocation relative to fracture; estimates to the left indicate lower adjusted odds. The treatment-year term was included in the model but omitted from the plotted forest display for readability. CI, confidence interval; NEISS, National Electronic Injury Surveillance System; OR, odds ratio.
"""


SUPPLEMENTARY_TABLE_FIGURE_LEGENDS = """# Supplementary Tables and Figure Legends

Supplementary Table S1. Official NEISS code mappings used to construct the main analytic cohort. The table lists the verified official CPSC NEISS body-part, diagnosis, and product/activity codes used to identify finger injuries, fracture and dislocation diagnoses, and selected ball-sport activity groups. Product/activity mappings were applied to Product_1 and Product_2 for the main 2015-2025 cohort. CPSC, U.S. Consumer Product Safety Commission; NEISS, National Electronic Injury Surveillance System.

Supplementary Table S2. Cohort flow for the main analytic cohort. The table shows the sequential screening steps used to construct the main cohort from annual archived NEISS records, including unweighted NEISS record counts, weighted estimates, standard errors, CVs, and instability flags where available. Screening counts are record counts and should not be interpreted as unique persons. CV, coefficient of variation; NEISS, National Electronic Injury Surveillance System.

Supplementary Table S3. Annual weighted estimates by treatment year and sport group, 2015-2025. The table reports unweighted NEISS record counts, weighted national ED visit estimates, CVs, and instability flags for each year-by-sport stratum. Estimates flagged as unstable should be interpreted cautiously and not overemphasized in sport-specific annual comparisons. CV, coefficient of variation; ED, emergency department; NEISS, National Electronic Injury Surveillance System.

Supplementary Table S4. Sensitivity analysis for the 2019-2025 cohort using secondary and tertiary NEISS variables. The sensitivity cohort allowed Body_Part_2, Diagnosis_2, and Product_3 when available and is compared with the main-cohort definition restricted to 2019-2025. Because these additional variables were introduced later, sensitivity estimates are not directly comparable with the primary 2015-2025 trend analysis.

Supplementary Table S5. Narrative mechanism classification among main-cohort records from 2019-2025. Mechanisms were assigned using a conservative keyword-based approach and are reported as unweighted NEISS record counts, weighted national estimates, weighted percentages, CVs, and instability flags. Mechanism categories are descriptive only because NEISS narratives are brief clinical summaries and narrative length increased beginning in 2019. CV, coefficient of variation; NEISS, National Electronic Injury Surveillance System.

Supplementary Table S6. Missingness summary for analytic variables in the final main cohort. The table reports the number and percentage of missing values for standardized and derived variables used in cohort construction, descriptive analyses, models, and sensitivity analyses. Variables introduced in 2019, including Body_Part_2 and Diagnosis_2, are expected to be missing for earlier years and were not used in the primary 2015-2025 cohort definition.

Supplementary Table S7. Instability flags for generated estimates. The table lists generated estimates that met at least one CPSC instability criterion: weighted estimate <1,200, unweighted n <20, or CV >33%. Flagged estimates were retained for transparency but should be interpreted cautiously. CPSC, U.S. Consumer Product Safety Commission; CV, coefficient of variation.

Supplementary Figure S1. Seasonal distribution of adolescent selected ball-sport-associated finger fractures and dislocations, 2015-2025. Bars show weighted national ED visit estimates by season of treatment date. Seasons were derived from treatment month and are descriptive. ED, emergency department; NEISS, National Electronic Injury Surveillance System.

Supplementary Figure S2. Monthly distribution of adolescent selected ball-sport-associated finger fractures and dislocations, 2015-2025. Points show weighted national ED visit estimates by treatment month. The figure is descriptive and does not account for sport-specific exposure or participation schedules. ED, emergency department; NEISS, National Electronic Injury Surveillance System.

Supplementary Figure S3. Sensitivity analysis comparing the main 2019-2025 cohort definition with an expanded 2019-2025 definition that allowed Body_Part_2, Diagnosis_2, and Product_3 when available. Bars show weighted national ED visit estimates. This sensitivity analysis evaluates capture using variables introduced later and should not be used as the primary 2015-2025 trend definition. ED, emergency department; NEISS, National Electronic Injury Surveillance System.

Supplementary Figure S4. Narrative mechanism distribution among main-cohort records from 2019-2025. Horizontal bars show weighted national ED visit estimates by conservative keyword-based mechanism category. Mechanism estimates are descriptive only because NEISS narratives are brief and because narrative length changed beginning in 2019. ED, emergency department; NEISS, National Electronic Injury Surveillance System.
"""


ALL_TABLE_FIGURE_LEGENDS = (
    MAIN_TABLE_FIGURE_LEGENDS.rstrip()
    + "\n\n"
    + SUPPLEMENTARY_TABLE_FIGURE_LEGENDS.rstrip()
    + "\n"
)
