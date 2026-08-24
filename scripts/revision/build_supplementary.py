"""Build revised supplementary tables, methods, checklists, and figures."""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P
import survey_lib as sv

P.ensure_dirs()
P.require_cohort()
OUT = P.RESULTS_DIR
SUPP = P.SUPPLEMENT_DIR
SFIG = P.SUPPLEMENT_FIGURE_DIR

df = pd.read_csv(P.COHORT_MAIN, low_memory=False)
df["year"] = df["year"].astype(int)
df["sport_code"] = df["sport_code"].astype(float).astype(int)
RENAME = {"other selected ball sports": "other selected ball and stick sports"}
PALETTE = {"blue": "#2F6F9F", "teal": "#2A9D8F", "gold": "#E9C46A",
           "red": "#C65D4E", "ink": "#263238", "gray": "#7A8691"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5,
                     "axes.edgecolor": "#9AA4AD", "grid.color": "#DDE3E8",
                     "savefig.facecolor": "white", "axes.spines.top": False,
                     "axes.spines.right": False})


def money(x):
    return f"{int(round(float(x))):,}" if pd.notna(x) and str(x) != "" else ""


def ci(lo, hi):
    if pd.isna(lo) or pd.isna(hi):
        return ""
    return f"{money(lo)}{' to ' if float(lo) < 0 else '-'}{money(hi)}"


# ============================================================ supplementary tables
doc = Document()
for s in doc.sections:
    s.orientation = WD_ORIENT.LANDSCAPE
    s.page_width, s.page_height = Inches(11.69), Inches(8.27)
    s.left_margin = s.right_margin = Inches(0.6)
    s.top_margin = s.bottom_margin = Inches(0.7)
doc.styles["Normal"].font.name = "Times New Roman"
doc.styles["Normal"].font.size = Pt(9)


def shade(cell, hexcolor):
    el = OxmlElement("w:shd")
    el.set(qn("w:val"), "clear"); el.set(qn("w:fill"), hexcolor)
    cell._tc.get_or_add_tcPr().append(el)


def add_table(title, frame, note, page_break=True, flagcol="flag"):
    p = doc.add_paragraph(); r = p.add_run(title)
    r.bold = True; r.font.size = Pt(10.5)
    p.paragraph_format.space_after = Pt(6)
    t = doc.add_table(rows=1, cols=len(frame.columns)); t.style = "Table Grid"
    for j, col in enumerate(frame.columns):
        c = t.rows[0].cells[j]; c.text = ""
        pp = c.paragraphs[0]; pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = pp.add_run(str(col)); run.bold = True; run.font.size = Pt(8)
        shade(c, "D9E2F3")
    for i in range(len(frame)):
        cells = t.add_row().cells
        for j, col in enumerate(frame.columns):
            raw = frame.iloc[i, j]
            v = "" if pd.isna(raw) else str(raw)
            pp = cells[j].paragraphs[0]
            pp.alignment = WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER
            run = pp.add_run(v); run.font.size = Pt(8)
            if str(col).lower().startswith(("instability", "criteria", "flag")) and v:
                run.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
            if str(frame.iloc[i, 0]).upper().startswith("TOTAL"):
                run.bold = True
    n = doc.add_paragraph(); nr = n.add_run(note)
    nr.italic = True; nr.font.size = Pt(8)
    n.paragraph_format.space_before = Pt(6)
    if page_break:
        doc.add_page_break()


# ---- S1: code mappings with weighted composition
LABELS = {
    1215: "LACROSSE (ACTIVITY, APPAREL OR EQUIPMENT)",
    1279: "ICE HOCKEY (ACTIVITY, APPAREL OR EQUIPMENT)",
    1282: "HANDBALL (ACTIVITY, APPAREL OR EQUIPMENT)",
    1295: "FIELD HOCKEY (ACTIVITY, APPAREL OR EQUIPMENT)",
    3234: "RUGBY (ACTIVITY, APPAREL OR EQUIPMENT)",
    3235: "OTHER BALL SPORTS (ACTIVITY, APPAREL OR EQUIPMENT)",
    3236: "BALL SPORTS (ACTIVITY, APPAREL OR EQUIPMENT), N.S.",
    3245: "STREET HOCKEY (ACTIVITY, APPAREL OR EQUIPMENT)",
    3272: "HOCKEY (ACTIVITY, APPAREL OR EQUIPMENT), NOT SPECIFIED",
}
other = df[df.sport_group == "other selected ball sports"]
tot_other = other["weight"].sum()
g = other.groupby("sport_code")["weight"].agg(["count", "sum"]).sort_values("sum", ascending=False)
S1 = pd.DataFrame([{
    "NEISS code": int(code),
    "Official label": LABELS.get(int(code), str(code)),
    "Unweighted n": int(row["count"]),
    "Weighted estimate": money(row["sum"]),
    "% of category": f"{row['sum']/tot_other*100:.1f}%",
} for code, row in g.iterrows()])
S1.loc[len(S1)] = ["TOTAL", "other selected ball and stick sports", int(g["count"].sum()),
                   money(tot_other), "100.0%"]
add_table(
    "Supplementary Table S1. Composition of the \"other selected ball and stick sports\" category",
    S1,
    "Core sport groups (basketball, football, baseball/softball, soccer, volleyball) were mapped from the official NEISS "
    "product/activity codes listed in the study configuration and are not reproduced here. Roller hockey (code 5032) was "
    "eligible under the a priori selection rule but contributed no records to the cohort and is therefore not listed. "
    "Generic ball-sport codes (3235 and 3236) account for 68.8% of this category; unambiguous ball sports (adding lacrosse, "
    "rugby, and handball) account for 83.9%. Puck-based codes (ice hockey and unspecified hockey) account for 11.6% of this "
    "category and 0.71% of the whole cohort; all hockey-variant codes account for 16.1% of the category and 0.99% of the "
    "cohort. Sensitivity analyses excluding these codes are reported in the Results.")

# ---- S2: cohort flow
flow = [
    ("All NEISS records in downloaded files", 3924911, 150292889, 14613593, 9.7),
    ("Treatment year 2015-2025", 3924903, 150292889, 14613593, 9.7),
    ("Age 10-18 years", 732983, 23289909, 2476321, 10.6),
    ("Primary body part is finger", 73419, 2373767, 238730, 10.1),
    ("Primary diagnosis is fracture or dislocation", 24363, 669256, 74807, 11.2),
    ("Product_1 or Product_2 is a verified selected ball sport", 16069, 441512, 50822, 11.5),
    ("Missing essential fields excluded", 16069, 441512, 50822, 11.5),
    ("Obvious spectator/bystander narratives excluded (final cohort)", 16066, 441441, 50825, 11.5),
]
S2 = pd.DataFrame([{
    "Screening step": s, "Unweighted n": f"{n:,}", "Weighted estimate": f"{e:,}",
    "SE": f"{se:,}", "CV": f"{cv:.1f}%",
    "95% CI": f"{round(e-1.96*se):,}-{round(e+1.96*se):,}",
} for s, n, e, se, cv in flow])
add_table("Supplementary Table S2. Cohort flow for the main analytic cohort", S2,
          "Weighted estimates use NEISS sample weights; standard errors were estimated by Taylor linearization using the "
          "stratified ultimate-cluster estimator with NEISS stratum and primary sampling unit variables. The final step "
          "removed 3 records (71 weighted visits, 0.02%). CI, confidence interval; CV, coefficient of variation; SE, "
          "standard error.")

# ---- S3: annual by year and sport, with CI
rows = []
for y in sorted(df.year.unique()):
    for sport in sorted(df.sport_group.unique()):
        m = ((df.year == y) & (df.sport_group == sport)).to_numpy()
        if m.sum() == 0:
            continue
        t = sv.total(df, m)
        flags = []
        if t["est"] < 1200: flags.append("estimate<1200")
        if t["n"] < 20: flags.append("n<20")
        if not pd.isna(t["cv"]) and t["cv"] > 0.33: flags.append("cv>33%")
        rows.append({"Year": int(y), "Sport group": RENAME.get(sport, sport),
                     "Unweighted n": t["n"], "Weighted estimate": money(t["est"]),
                     "95% CI": ci(t["lo"], t["hi"]), "CV": f"{t['cv']*100:.1f}%",
                     "Instability flag": "; ".join(flags)})
add_table("Supplementary Table S3a. Annual weighted estimates by year and sport group, 2015-2025",
          pd.DataFrame(rows),
          "Instability flags follow CPSC criteria. CI, confidence interval; CV, coefficient of variation.")

lin = pd.read_csv(OUT / "trend_analysis.csv"); log = pd.read_csv(OUT / "trend_analysis_loglinear.csv")
S3b = pd.DataFrame([{
    "Period": a.label, "Years": a.years,
    "Slope (visits/year)": f"{a.slope_per_year:,.0f}",
    "95% CI": f"{a.ci_lo:,.0f} to {a.ci_hi:,.0f}", "p": f"{a.p:.3f}",
    "Annual % change": f"{b.annual_pct_change:+.1f}%",
    "95% CI ": f"{b.ci_lo:+.1f} to {b.ci_hi:+.1f}", "p ": f"{b.p:.3f}",
} for a, b in zip(lin.itertuples(), log.itertuples())])
S3b.columns = ["Period", "Years", "Slope (visits/year)", "95% CI", "p", "Annual % change", "95% CI", "p"]
add_table("Supplementary Table S3b. Design-based trend models and key temporal contrasts", S3b,
          "Trend models regress annual weighted estimates on treatment year by inverse-variance weighted least squares "
          "using each year's design-based variance. Key contrasts (design-based ratios of weighted totals with Taylor-"
          "linearized variances): 2019 vs 2015, ratio 0.81 (95% CI 0.65-1.02; p=0.069); 2020 vs the 2015-2019 mean, ratio "
          "0.38 (95% CI 0.32-0.46), i.e. 61.8% lower (95% CI 54.0-68.2% lower); 2020 vs 2019, ratio 0.42 (95% CI 0.36-0.49); "
          "2022-2025 mean vs 2015-2019 mean, ratio 0.84 (95% CI 0.66-1.06). These analyses are descriptive; no causal "
          "interpretation is supported because participation and care-seeking denominators are unavailable.")

# ---- S4: sensitivity by sport + model
s4 = pd.read_csv(OUT / "s4_by_sport.csv")
S4a = pd.DataFrame([{
    "Sport group": RENAME.get(r.sport_group, r.sport_group),
    "Main cohort n": r.main_n, "Main cohort estimate": money(r.main_est), "95% CI": r.main_ci,
    "Sensitivity n": r.sens_n, "Sensitivity estimate": money(r.sens_est), "95% CI ": r.sens_ci,
    "Increase": f"{r.pct_increase:.1f}%",
} for r in s4.itertuples()])
S4a.columns = ["Sport group", "Main cohort n", "Main cohort estimate", "95% CI",
               "Sensitivity n", "Sensitivity estimate", "95% CI", "Increase"]
add_table("Supplementary Table S4a. Sensitivity analysis by sport group, 2019-2025", S4a,
          "The main cohort is restricted to 2019-2025 so that the two definitions cover the same period. The sensitivity "
          "cohort additionally uses Body_Part_2, Diagnosis_2, and Product_3, which were introduced with 2019 treatment "
          "dates. The increment is near-uniform across sport groups (2.3% to 3.1%).")

mc = pd.read_csv(OUT / "model_main_2019_2025.csv").merge(
    pd.read_csv(OUT / "model_sensitivity_2019_2025.csv"), on="term", suffixes=("_m", "_s"))
mc = mc[mc.term != "Intercept"]
S4b = pd.DataFrame([{
    "Predictor": (r.term.replace("C(sport_group, Treatment(reference='football'))[T.", "")
                  .replace("C(age_group)[T.", "").replace("C(sex_clean)[T.", "").replace("]", "")
                  .replace("other selected ball sports", "other selected ball and stick sports")),
    "Main cohort 2019-2025": f"{r.or_m:.2f} ({r.lo_m:.2f}-{r.hi_m:.2f})",
    "Expanded sensitivity cohort": f"{r.or_s:.2f} ({r.lo_s:.2f}-{r.hi_s:.2f})",
    "Relative change in OR": f"{abs(r.or_s-r.or_m)/r.or_m*100:.1f}%",
} for r in mc.itertuples()])
add_table("Supplementary Table S4b. Primary model refitted on the expanded sensitivity cohort", S4b,
          "No adjusted odds ratio changed by more than 4.6% in relative terms; all confidence intervals overlap "
          "substantially and no comparison changed direction or crossed a conventional significance threshold. "
          "OR, odds ratio.")

# ---- S5: mechanism with CI
mech = pd.read_csv(OUT / "mechanism_with_ci.csv").sort_values("est", ascending=False)
S5 = pd.DataFrame([{
    "Mechanism": r.mechanism, "Unweighted n": r.n, "Weighted estimate": money(r.est),
    "95% CI": r.ci, "CV": f"{r.cv_pct:.1f}%", "Weighted %": f"{r.pct:.1f}%",
    "95% CI for %": r.pct_ci,
} for r in mech.itertuples()])
add_table("Supplementary Table S5. Narrative mechanism classification, 2019-2025", S5,
          "Mechanism was unclassifiable in 47.6% of records, the largest single category. Classified proportions are "
          "therefore LOWER BOUNDS on each mechanism's true frequency rather than estimates of mechanism prevalence. "
          "Mechanism classification is descriptive and is restricted to 2019-2025 because maximum narrative length "
          "changed with 2019 treatment dates. CI, confidence interval; CV, coefficient of variation.")

# ---- S6: missingness, analytic variables only
ANALYTIC = ["case_id", "treatment_date", "year", "age", "sex", "body_part", "diagnosis",
            "body_part_2", "diagnosis_2", "disposition", "product_1", "product_2", "product_3",
            "narrative", "weight", "stratum", "psu", "sport_code", "sport_group", "age_group",
            "sex_clean", "diagnosis_group", "disposition_group", "severe_disposition",
            "calendar_period", "month", "season", "narrative_mechanism"]
S6 = pd.DataFrame([{
    "Analytic variable": v,
    "Missing n": f"{int(df[v].isna().sum()):,}",
    "Missing %": f"{df[v].isna().mean()*100:.1f}%",
} for v in ANALYTIC if v in df.columns])
add_table("Supplementary Table S6. Missingness summary for analytic variables", S6,
          "Race and ethnicity were extracted during data cleaning but were not used in any analysis and are therefore "
          "not tabulated; the same applies to other extracted-but-unused fields. Body_Part_2 and Diagnosis_2 are missing "
          "for 96.0% of records because they were introduced with 2019 treatment dates and are used only in the "
          "sensitivity analysis. Severe disposition is missing for 32 records (0.2%) whose disposition could not be "
          "classified as severe or nonsevere.")

# ---- S7: comprehensive instability register
s7 = pd.read_csv(OUT / "s7_comprehensive_flags.csv")
s7["descriptor"] = s7["descriptor"].str.replace("other selected ball sports",
                                                "other selected ball and stick sports", regex=False)
S7 = pd.DataFrame({"Source": s7["source"], "Estimate": s7["descriptor"],
                   "Unweighted n": s7["unweighted_n"],
                   "Weighted estimate": s7["weighted_estimate"].map(money),
                   "CV": s7["cv_pct"].map(lambda v: f"{v:.1f}%" if pd.notna(v) else ""),
                   "Criteria breached": s7["flag"]})
add_table("Supplementary Table S7. Comprehensive instability register", S7,
          "This register is exhaustive across the manuscript and supplementary material. Inclusion rule: any estimate "
          "with weighted estimate <1,200, unweighted n <20, or coefficient of variation >33%, following CPSC guidance. "
          "The six Table 2 severe-disposition sub-estimates are the reason sport-specific severe disposition is not "
          "reported in Table 2. CV, coefficient of variation.")

# ---- S8: concordance
S8 = pd.DataFrame([
    ["Coded dislocation (n=2,213)", "1,995", "2", "77", "139"],
    ["Coded fracture (n=13,853)", "2", "13,370", "196", "285"],
], columns=["Coded primary diagnosis", "Narrative: dislocation term only",
            "Narrative: fracture term only", "Narrative: both terms", "Narrative: neither term"])
add_table("Supplementary Table S8. Narrative-based diagnostic concordance assessment", S8,
          "All 16,066 cohort records. Narratives were classified by keyword for dislocation terms (dislocation, "
          "subluxation, reduction) and fracture terms (fracture, buckle, Salter, avulsion). Among the 15,369 records "
          "(95.7%) whose narrative contained exactly one diagnostic term family, the narrative agreed with the coded "
          "diagnosis in 15,365 (99.97%; Cohen's kappa 0.999). IMPORTANT: narrative and diagnosis code are abstracted from "
          "the same emergency department record, so this demonstrates internal consistency, not validation against "
          "radiographic adjudication. It excludes coding and data-entry error as a substantial source of outcome "
          "misclassification but cannot exclude misclassification at the point of clinical diagnosis.",
          page_break=False)

doc.save(SUPP / "supplementary tables.docx")
print("saved supplementary tables.docx")

# ================================================= supplementary methods + checklists
d2 = Document()
d2.styles["Normal"].font.name = "Times New Roman"
d2.styles["Normal"].font.size = Pt(10.5)


def h(text, level=1):
    p = d2.add_heading(text, level=level)
    for r in p.runs:
        r.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)
    return p


def para(text):
    p = d2.add_paragraph(text)
    p.paragraph_format.space_after = Pt(8)
    return p


h("Supplementary Methods", 0)

h("Data source and provenance")
para("The main analytic cohort used only NEISS variables available across 2015-2025: age, Treatment_Date, Body_Part, "
     "Diagnosis, Product_1, Product_2, Disposition, Sex, Narrative, Weight, Stratum, and PSU. Product_3, Body_Part_2, "
     "Diagnosis_2, Ethnicity, Alcohol_Involved, and Drug_Involved were added beginning with 2019 treatment dates and "
     "were excluded from the main cohort.")
para("Annual archived tab-delimited files were downloaded directly from the CPSC archived-data directory, which is the "
     "finalized calendar-year release rather than the interactive query system; CPSC does not apply a provisional "
     "designation to files in this series. The 2025 file was obtained from "
     "https://www.cpsc.gov/cgibin/NEISSQuery/Data/Archived%20Data/2025/neiss2025.tsv, carried a server last-modified "
     "timestamp of 6 May 2026, and was downloaded on 16 May 2026 (UTC). Source URLs, file timestamps, and download times "
     "for every annual file are recorded in the download log included in the code deposit.")
para("Official CPSC files used for validation: the NEISS Data Dictionary Excel file, and the NEISS format file "
     "neiss_fmt.txt, including body-part, diagnosis, disposition, sex, and product/activity labels.")

h("Survey design specification")
para("Survey-design analyses used survey::svydesign(ids = ~psu, strata = ~stratum, weights = ~weight, nest = TRUE). "
     "Variances for weighted totals were estimated by Taylor linearization using the stratified ultimate-cluster "
     "estimator. The analytic cohort spanned 5 NEISS strata (C, L, M, S, V) and 103 primary sampling units, with 9, 13, "
     "28, 48, and 24 primary sampling units contributing to strata C, L, M, S, and V respectively. Because no stratum "
     "contributed a single primary sampling unit, no lonely-primary-sampling-unit adjustment (for example "
     "options(survey.lonely.psu=)) was required or applied, and results are insensitive to that setting.")
para("Confidence intervals for weighted totals were computed as the estimate plus or minus 1.96 standard errors. "
     "Confidence intervals for weighted proportions and for ratios of weighted totals were computed on the log scale "
     "from the linearized ratio variance, which constrains bounds to admissible values. All weighted estimates are "
     "rounded from unrounded survey-weighted values; components may therefore not sum exactly to totals. The exact "
     "unrounded cohort total is 441,440.82. Combined estimates reported in the text are computed before rounding, which "
     "is why the football-plus-basketball estimate is 321,497 rather than the 321,498 obtained by summing the two "
     "separately rounded values.")

h("Modelling specification")
para("The primary adjusted model was fitted with survey::svyglm using a binomial family and logit link, including sport "
     "group, age group, sex, and treatment year. The estimand is conditional: the model estimates the odds that a "
     "presenting injury was coded as a dislocation rather than a fracture, among adolescents who presented to an "
     "emergency department with one of these two diagnoses. It is a comparison of diagnostic case mix among presenting "
     "patients and is not an estimate of injury risk.")
para("Treatment year was entered as a single continuous, mean-centered term to provide a parsimonious adjustment for "
     "secular drift in case mix rather than as an estimand of interest. Entering year as ten indicator variables would "
     "have consumed nine degrees of freedom in a model whose outcome comprises 2,213 unweighted events distributed "
     "across 103 primary sampling units, reducing precision for the sport, age, and sex terms the model exists to "
     "estimate. The linear year term was null (OR 0.99 per year; 95% CI 0.96-1.01; p=0.357), so the functional form "
     "imposed on year has little scope to distort the remaining estimates.")
para("The single record with sex coded unknown/other (one 2021 basketball-associated finger fracture, sample weight "
     "5.54) was excluded from the model because one observation in a three-level factor induces sparse-cell separation "
     "and unstable standard errors. It is retained in the descriptive tables so that the cohort sums to the reported "
     "total. The model's analytic n is therefore 16,065 against a descriptive cohort of 16,066; its exclusion has no "
     "effect on any estimate at the reported precision.")
para("The five sport comparisons against football were treated as a family for multiplicity adjustment and are reported "
     "with Holm-adjusted p values alongside unadjusted values; Benjamini-Hochberg values were also computed and agree "
     "in substance. Age, sex, and treatment year were prespecified adjustment variables and were not subject to "
     "multiplicity correction. Both significant sport comparisons survived Holm adjustment.")
para("Severe-disposition modelling was prespecified subject to a sparse-event rule requiring BOTH at least 10 severe "
     "events per model parameter AND at least 20 records in every sport category. The second condition was met "
     "(minimum sport-category n=617); the first was not (89 severe events against 9 model parameters, requiring 90), "
     "and the model was therefore not fitted. Consistent with that decision, sport-specific severe-disposition "
     "descriptive estimates were also found to be unreportable under CPSC criteria and are not presented.")

h("Derived variables")
para("Season was derived from the calendar month of the Treatment_Date field using the standard meteorological mapping: "
     "winter = December, January, February; spring = March, April, May; summer = June, July, August; fall = September, "
     "October, November. December is grouped with the following January and February rather than split at the "
     "calendar-year boundary.")
para("Sex reflects NEISS administrative coding rather than a measured biological attribute and is described throughout "
     "as records coded as female or male.")
para("Severe disposition was defined as admission, transfer, or observation. Records whose disposition could not be "
     "classified as severe or nonsevere (n=32; 0.2%) were excluded from severe-disposition denominators.")

h("Selected ball-sport code selection")
para("Sport/product groups were defined before cohort construction using official NEISS product/activity labels. The "
     "core sport groups were basketball, football, baseball/softball, soccer, and volleyball. These activities were "
     "selected because they are common adolescent ball-sport activities and have plausible direct finger-loading "
     "mechanisms, including catching, ball impact, jamming/hyperextension, falls, and player contact.")
para("Additional ball, puck, or stick-and-ball sports were eligible only if the official NEISS label identified a sport "
     "activity rather than a nonspecific product or equipment category. Eligible smaller activities were combined as "
     "\"other selected ball and stick sports\" when the combined unweighted sample size met the prespecified minimum. "
     "Activities were not eligible if the official label indicated a non-ball activity, water sport, wheeled sport, "
     "playground activity, fitness/exercise activity, combat sport, hunting/firearm activity, or generic equipment-only "
     "product category without a sport-activity label. The full composition of the residual category by weighted "
     "contribution is given in Supplementary Table S1.")

h("Narrative screening and mechanism classification")
para("Narratives were used for two distinct purposes. First, as a cohort-definition step applied across all study "
     "years, narratives were screened by an automated, deterministic keyword rule for terms indicating spectator or "
     "bystander circumstances; candidate records were then read individually and three were excluded. The screening "
     "rule is reproduced in full in the deposited code. Candidate exclusions were reviewed by a single author; a second "
     "reviewer and a formal agreement statistic were not employed, which is acknowledged as a limitation. The step "
     "changed the cohort estimate from 441,512 to 441,441 (71 weighted visits; 0.02%).")
para("Second, and separately, a conservative keyword-based classifier assigned records to mechanism categories. "
     "Mechanism classification was used descriptively only, and is emphasized for 2019-2025 because maximum narrative "
     "length changed with 2019 treatment dates. Mechanism was unclassifiable in 47.6% of 2019-2025 records, so "
     "classified proportions are lower bounds rather than prevalence estimates.")

h("Diagnostic concordance assessment")
para("To assess potential outcome misclassification, each narrative was classified by keyword for dislocation terms "
     "(dislocation, subluxation, reduction) and fracture terms (fracture, buckle, Salter, avulsion) and cross-tabulated "
     "against the coded primary diagnosis across all 16,066 records. Results are given in Supplementary Table S8. "
     "Because narrative and diagnosis code are abstracted from the same emergency department record, this assessment "
     "demonstrates internal consistency rather than validation against radiographic adjudication.")

d2.add_page_break()

# ---------------- STROBE
h("Supplementary File: STROBE Checklist (cross-sectional studies)", 0)
para("Page numbers refer to the revised manuscript. Items not applicable to a cross-sectional design are marked NA with "
     "the reason.")
strobe = [
    ("1a", "Title/abstract: study design in title or abstract", "Title page; Abstract — cross-sectional NEISS analysis identified"),
    ("1b", "Title/abstract: informative and balanced summary", "Abstract — now reports uncertainty for all weighted estimates and the principal adjusted result"),
    ("2", "Introduction: background/rationale", "Introduction, paragraphs 1-3"),
    ("3", "Introduction: objectives", "Introduction, final paragraph"),
    ("4", "Methods: study design", "Methods, Data Source and Study Design"),
    ("5", "Methods: setting, locations, dates", "Methods, Data Source and Study Design — NEISS hospitals; treatment years 2015-2025; file provenance and download dates stated"),
    ("6a", "Methods: eligibility criteria, sources, selection", "Methods, Cohort Definition; Figure 1"),
    ("7", "Methods: variables defined", "Methods, Variables; Supplementary Methods"),
    ("8", "Methods: data sources/measurement", "Methods, Data Source; Supplementary Methods"),
    ("9", "Methods: bias", "Methods, Cohort Definition; Limitations — ED-only capture, product association, absent denominators, diagnostic misclassification"),
    ("10", "Methods: study size", "Methods, Statistical Analysis — all eligible records; no a priori sample-size calculation"),
    ("11", "Methods: quantitative variables handling", "Methods, Variables and Statistical Analysis — age groups, season mapping, continuous year term"),
    ("12a", "Methods: statistical methods", "Methods, Statistical Analysis"),
    ("12b", "Methods: subgroups and interactions", "Methods, Statistical Analysis — sport, age, sex subgroups; multiplicity approach stated"),
    ("12c", "Methods: missing data", "Supplementary Table S6"),
    ("12d", "Methods: sampling strategy accounted for", "Methods, Statistical Analysis — svydesign specification, stratum/PSU counts, lonely-PSU statement"),
    ("12e", "Methods: sensitivity analyses", "Methods and Results, Sensitivity Analyses"),
    ("13", "Results: participants", "Results, Cohort; Figure 1; Supplementary Table S2"),
    ("14", "Results: descriptive data", "Results; Table 1"),
    ("15", "Results: outcome data", "Results; Tables 1-2"),
    ("16", "Results: main results with precision", "Results; Tables 1-3 — all estimates now with 95% CIs; unadjusted and Holm-adjusted p values"),
    ("17", "Results: other analyses", "Results, Sensitivity Analyses, Diagnostic Concordance, Narrative Mechanism"),
    ("18", "Discussion: key results", "Discussion, Principal Findings"),
    ("19", "Discussion: limitations", "Limitations"),
    ("20", "Discussion: interpretation", "Discussion — conditional estimand stated; mechanisms presented as hypotheses"),
    ("21", "Discussion: generalisability", "Discussion, Comparison With Previous Literature; Limitations"),
    ("22", "Other: funding", "Statements, Funding"),
]
t = d2.add_table(rows=1, cols=3); t.style = "Table Grid"
for j, hd in enumerate(["Item", "STROBE recommendation", "Location in revised manuscript"]):
    c = t.rows[0].cells[j]; c.text = ""
    r = c.paragraphs[0].add_run(hd); r.bold = True; r.font.size = Pt(9)
    shade(c, "D9E2F3")
for item, rec, loc in strobe:
    cells = t.add_row().cells
    for j, v in enumerate([item, rec, loc]):
        run = cells[j].paragraphs[0].add_run(v); run.font.size = Pt(9)
para("")
para("Items 6b (matching criteria), 12f (loss to follow-up), and follow-up-related sub-items are not applicable: this "
     "is a cross-sectional analysis of a repeated-cross-section surveillance sample with no longitudinal follow-up of "
     "individuals and no matching.")

d2.add_page_break()
h("Supplementary File: RECORD Checklist", 0)
record = [
    ("RECORD 1.1", "Type of data, databases, and selection of populations", "Methods, Data Source and Cohort Definition; Supplementary Methods"),
    ("RECORD 1.2", "Population selection: codes and algorithms", "Methods, Selection of Ball-Sport Product Codes; Supplementary Table S1; deposited code"),
    ("RECORD 1.3", "Validation of codes/algorithms", "Methods — official CPSC data dictionary and format file used for verification; Supplementary Methods"),
    ("RECORD 6.1", "Codes and algorithms to classify exposures, outcomes, confounders", "Methods, Variables; Supplementary Table S1; Supplementary Methods"),
    ("RECORD 6.2", "Validation of these codes", "Methods; Results, Diagnostic Concordance; Supplementary Table S8"),
    ("RECORD 6.3", "Validation studies referenced", "Limitations — no external radiographic validation available; internal concordance reported"),
    ("RECORD 7.1", "Data cleaning methods", "Methods, Cohort Definition; Supplementary Methods; Supplementary Table S6"),
    ("RECORD 11.1", "Linkage of databases", "NA — single data source; no record linkage performed"),
    ("RECORD 12.1", "Population selection flow diagram", "Figure 1; Supplementary Table S2"),
    ("RECORD 13.1", "Implications of using routinely collected data", "Limitations; Discussion, Severity and Health-System Interpretation"),
    ("RECORD 19.1", "Discussion of misclassification and unmeasured confounding", "Limitations — diagnostic misclassification; Discussion — conditional estimand and care-seeking/coding alternatives"),
    ("RECORD 22.1", "Access to protocol, raw data, programming code", "Statements, Data Availability — public repository and DOI"),
    ("RECORD 22.2", "Availability of the population base", "Statements, Data Availability — CPSC NEISS public archive"),
]
t = d2.add_table(rows=1, cols=3); t.style = "Table Grid"
for j, hd in enumerate(["Item", "RECORD recommendation", "Location in revised manuscript"]):
    c = t.rows[0].cells[j]; c.text = ""
    r = c.paragraphs[0].add_run(hd); r.bold = True; r.font.size = Pt(9)
    shade(c, "D9E2F3")
for item, rec, loc in record:
    cells = t.add_row().cells
    for j, v in enumerate([item, rec, loc]):
        run = cells[j].paragraphs[0].add_run(v); run.font.size = Pt(9)

d2.save(SUPP / "supplementary_methods_and_checklists.docx")
print("saved supplementary_methods_and_checklists.docx")


# ==================================================== supplementary figures
def sfig(name):
    for ext in ("png", "pdf"):
        plt.savefig(SFIG / f"{name}.{ext}", dpi=300, bbox_inches="tight")
    plt.close()


# S1 monthly
allm = np.ones(len(df), bool)
months = range(1, 13)
est = [sv.total(df, (df.month == m).to_numpy()) for m in months]
fig, ax = plt.subplots(figsize=(8.4, 4.4))
ax.bar(list(months), [e["est"] for e in est], color=PALETTE["blue"],
       yerr=[[e["est"] - e["lo"] for e in est], [e["hi"] - e["est"] for e in est]],
       capsize=3, ecolor=PALETTE["ink"], error_kw={"elinewidth": 1.0})
ax.set_xticks(list(months))
ax.set_xticklabels(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
ax.set_ylabel("Weighted national ED visit estimate"); ax.set_xlabel("Month of treatment date")
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, p: f"{int(v):,}"))
ax.grid(axis="y", alpha=0.6)
ax.set_title("Supplementary Figure S1. Monthly distribution (descriptive)",
             loc="left", fontsize=11.5, fontweight="bold", color=PALETTE["ink"])
ax.text(0.0, -0.20, "DESCRIPTIVE ANALYSIS. No test for monthly variation was performed. Monthly variation cannot be separated from\n"
                    "the sport calendar and school-year exposure patterns because participation denominators are unavailable in NEISS.",
        transform=ax.transAxes, fontsize=8.2, color=PALETTE["gray"], va="top")
sfig("supplementary_monthly_distribution")

# S2 seasonal
t1 = pd.read_csv(OUT / "table1_with_ci.csv")
se = t1[t1.section == "Season"].set_index("label").loc[["winter", "spring", "summer", "fall"]]
fig, ax = plt.subplots(figsize=(7.2, 4.4))
ax.bar(se.index, se["weighted_estimate"], color=PALETTE["teal"],
       yerr=[se["weighted_estimate"] - se["ci_lo"], se["ci_hi"] - se["weighted_estimate"]],
       capsize=4, ecolor=PALETTE["ink"], error_kw={"elinewidth": 1.0}, width=0.6)
for i, (v, p) in enumerate(zip(se["weighted_estimate"], se["weighted_pct"])):
    ax.text(i, se["ci_hi"].iloc[i] * 1.02, f"{int(v):,}\n({p:.1f}%)", ha="center",
            fontsize=8.8, color=PALETTE["ink"], fontweight="bold")
ax.set_ylim(0, se["ci_hi"].max() * 1.22)
ax.set_ylabel("Weighted national ED visit estimate")
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, p: f"{int(v):,}"))
ax.grid(axis="y", alpha=0.6)
ax.set_title("Supplementary Figure S2. Seasonal distribution (descriptive)",
             loc="left", fontsize=11.5, fontweight="bold", color=PALETTE["ink"])
ax.text(0.0, -0.20, "DESCRIPTIVE ANALYSIS. Season derived from treatment-date month (winter = Dec-Feb; spring = Mar-May;\n"
                    "summer = Jun-Aug; fall = Sep-Nov). No test for seasonality was performed.",
        transform=ax.transAxes, fontsize=8.2, color=PALETTE["gray"], va="top")
sfig("supplementary_seasonal_distribution")

# S3 sensitivity paired bars
s4p = s4[s4.sport_group != "TOTAL"].copy()
s4p["label"] = s4p["sport_group"].replace({"other selected ball sports": "other selected ball\nand stick sports"})
s4p = s4p.sort_values("main_est", ascending=False)
x = np.arange(len(s4p)); w = 0.38
fig, ax = plt.subplots(figsize=(9.0, 4.8))
ax.bar(x - w/2, s4p["main_est"], w, label="Main cohort definition", color=PALETTE["blue"])
ax.bar(x + w/2, s4p["sens_est"], w, label="Expanded sensitivity definition", color=PALETTE["gold"])
for xi, r in zip(x, s4p.itertuples()):
    ax.text(xi, max(r.main_est, r.sens_est) * 1.03, f"+{r.pct_increase:.1f}%", ha="center",
            fontsize=9.2, fontweight="bold", color=PALETTE["red"])
ax.set_xticks(x); ax.set_xticklabels(s4p["label"], fontsize=8.8)
ax.set_ylabel("Weighted national ED visit estimate, 2019-2025")
ax.set_ylim(0, s4p["sens_est"].max() * 1.18)
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, p: f"{int(v):,}"))
ax.legend(frameon=False, loc="upper right"); ax.grid(axis="y", alpha=0.6)
ax.set_title("Supplementary Figure S3. Sensitivity analysis: cohort definitions compared, 2019-2025",
             loc="left", fontsize=11.5, fontweight="bold", color=PALETTE["ink"])
ax.text(0.0, -0.22, "The expanded definition adds Body_Part_2, Diagnosis_2, and Product_3. It increased the weighted total by 2.6%\n"
                    "(247,727 to 254,069), with near-uniform increments across sport groups (2.3% to 3.1%).",
        transform=ax.transAxes, fontsize=8.2, color=PALETTE["gray"], va="top")
sfig("supplementary_sensitivity_2019_2025")

# S4 mechanism
mm = mech.sort_values("est")
fig, ax = plt.subplots(figsize=(8.6, 4.4))
cols = [PALETTE["gray"] if m == "unclear" else PALETTE["blue"] for m in mm["mechanism"]]
ax.barh(np.arange(len(mm)), mm["pct"], color=cols, height=0.6)
ax.set_yticks(np.arange(len(mm))); ax.set_yticklabels(mm["mechanism"])
for i, (p, c) in enumerate(zip(mm["pct"], mm["pct_ci"])):
    ax.text(p + 1.2, i, f"{p:.1f}%  (95% CI {c})", va="center", fontsize=8.8, color=PALETTE["ink"])
ax.set_xlim(0, 78); ax.set_xlabel("Weighted percentage of 2019-2025 records")
ax.grid(axis="x", alpha=0.6)
ax.set_title("Supplementary Figure S4. Narrative mechanism distribution, 2019-2025 (descriptive)",
             loc="left", fontsize=11.5, fontweight="bold", color=PALETTE["ink"])
ax.text(0.0, -0.22, "DESCRIPTIVE ANALYSIS. Mechanism was unclassifiable in 47.6% of records (shown in grey). Classified proportions\n"
                    "are lower bounds on each mechanism's true frequency, not estimates of mechanism prevalence.",
        transform=ax.transAxes, fontsize=8.2, color=PALETTE["gray"], va="top")
sfig("supplementary_narrative_mechanism_2019_2025")
print("saved supplementary figures")
