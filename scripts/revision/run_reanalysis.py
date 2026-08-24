"""Re-analysis to support the point-by-point response to reviewers."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P
import survey_lib as sv

P.ensure_dirs()
P.require_cohort()
MAIN = P.COHORT_MAIN
SENS = P.COHORT_SENSITIVITY
OUT = P.RESULTS_DIR

df = pd.read_csv(MAIN, low_memory=False)
df["year"] = df["year"].astype(int)
results: dict = {}

# ---------------------------------------------------------------- 0. design
n_strata = df["stratum"].nunique()
psu_per_stratum = df.groupby("stratum")["psu"].nunique()
single_psu = psu_per_stratum[psu_per_stratum == 1]
w_by_stratum = df.groupby("stratum")["weight"].sum()
results["design"] = {
    "n_records": int(len(df)),
    "n_strata": int(n_strata),
    "n_psu": int(df["psu"].nunique()),
    "psu_per_stratum": {str(k): int(v) for k, v in psu_per_stratum.items()},
    "single_psu_strata": [str(s) for s in single_psu.index],
    "single_psu_weight": float(w_by_stratum.reindex(single_psu.index).sum()),
    "single_psu_weight_pct": float(w_by_stratum.reindex(single_psu.index).sum() / df["weight"].sum() * 100),
    "single_psu_n": int(df[df["stratum"].isin(single_psu.index)].shape[0]),
}

# ---------------------------------------------------------- 1. headline total
allmask = np.ones(len(df), dtype=bool)
tot = sv.total(df)
results["headline_total"] = tot

# ------------------------------------------------------------- 2. Table 1 CIs
t1_rows = []
sections = [
    ("Age group", "age_group"),
    ("Sex", "sex_clean"),
    ("Calendar period", "calendar_period"),
    ("Sport group", "sport_group"),
    ("Diagnosis group", "diagnosis_group"),
    ("Disposition", "disposition_group"),
    ("Season", "season"),
]
for section, col in sections:
    for val in sorted(df[col].dropna().unique(), key=str):
        m = (df[col] == val).to_numpy()
        t = sv.total(df, m)
        p = sv.ratio(df, m, allmask)
        flags = []
        if t["est"] < 1200:
            flags.append("estimate<1200")
        if t["n"] < 20:
            flags.append("n<20")
        if not pd.isna(t["cv"]) and t["cv"] > 0.33:
            flags.append("cv>33%")
        t1_rows.append(
            {
                "section": section,
                "label": val,
                "unweighted_n": t["n"],
                "weighted_estimate": round(t["est"]),
                "ci_lo": round(t["lo"]) if not pd.isna(t["lo"]) else None,
                "ci_hi": round(t["hi"]) if not pd.isna(t["hi"]) else None,
                "se": round(t["se"]) if not pd.isna(t["se"]) else None,
                "cv_pct": round(t["cv"] * 100, 1) if not pd.isna(t["cv"]) else None,
                "weighted_pct": round(p["est"] * 100, 1),
                "pct_ci_lo": round(p["lo"] * 100, 1) if not pd.isna(p["lo"]) else None,
                "pct_ci_hi": round(p["hi"] * 100, 1) if not pd.isna(p["hi"]) else None,
                "instability_flag": "; ".join(flags),
            }
        )
t1 = pd.DataFrame(t1_rows)
t1.to_csv(OUT / "table1_with_ci.csv", index=False)

# --------------------------------------------- 3. Table 2 with CIs + severe fix
t2_rows = []
for sport in df.groupby("sport_group")["weight"].sum().sort_values(ascending=False).index:
    sm = (df["sport_group"] == sport).to_numpy()
    t = sv.total(df, sm)
    frac = sv.ratio(df, sm & (df["diagnosis_group"] == "fracture").to_numpy(), sm)
    disl = sv.ratio(df, sm & (df["diagnosis_group"] == "dislocation").to_numpy(), sm)
    sev_mask = sm & (df["severe_disposition"] == 1).to_numpy()
    sev_n = int(sev_mask.sum())
    sev_tot = sv.total(df, sev_mask)
    sev_pct = sv.ratio(df, sev_mask, sm)
    sev_flags = []
    if sev_tot["est"] < 1200:
        sev_flags.append("estimate<1200")
    if sev_n < 20:
        sev_flags.append("n<20")
    if not pd.isna(sev_tot["cv"]) and sev_tot["cv"] > 0.33:
        sev_flags.append("cv>33%")
    season_tot = (
        df[sm].groupby("season")["weight"].sum().sort_values(ascending=False)
    )
    t2_rows.append(
        {
            "sport_group": sport,
            "unweighted_n": t["n"],
            "weighted_estimate": round(t["est"]),
            "est_ci": f"{t['lo']:,.0f}-{t['hi']:,.0f}",
            "cv_pct": round(t["cv"] * 100, 1),
            "fracture_pct": round(frac["est"] * 100, 1),
            "fracture_ci": f"{frac['lo']*100:.1f}-{frac['hi']*100:.1f}",
            "dislocation_pct": round(disl["est"] * 100, 1),
            "dislocation_ci": f"{disl['lo']*100:.1f}-{disl['hi']*100:.1f}",
            "severe_n": sev_n,
            "severe_weighted_est": round(sev_tot["est"]),
            "severe_est_ci": (
                f"{sev_tot['lo']:,.0f}-{sev_tot['hi']:,.0f}" if not pd.isna(sev_tot["lo"]) else ""
            ),
            "severe_cv_pct": round(sev_tot["cv"] * 100, 1) if not pd.isna(sev_tot["cv"]) else None,
            "severe_pct": round(sev_pct["est"] * 100, 2),
            "severe_pct_ci": (
                f"{sev_pct['lo']*100:.2f}-{sev_pct['hi']*100:.2f}" if not pd.isna(sev_pct["lo"]) else ""
            ),
            "severe_instability_flag": "; ".join(sev_flags),
            "top_season": season_tot.index[0],
        }
    )
t2 = pd.DataFrame(t2_rows)
t2.to_csv(OUT / "table2_with_ci_and_severe_flags.csv", index=False)

# overall severe events
results["severe_overall"] = {
    "n_events": int((df["severe_disposition"] == 1).sum()),
    "by_disposition": df[df["severe_disposition"] == 1]["disposition_group"].value_counts().to_dict(),
    "total": sv.total(df, (df["severe_disposition"] == 1).to_numpy()),
    "missing_severe": int(df["severe_disposition"].isna().sum()),
}

# ------------------------------------------------------- 4. annual series + CI
ann_rows = []
for y in sorted(df["year"].unique()):
    m = (df["year"] == y).to_numpy()
    t = sv.total(df, m)
    ann_rows.append(
        {
            "year": int(y),
            "unweighted_n": t["n"],
            "weighted_estimate": round(t["est"]),
            "se": round(t["se"]),
            "cv_pct": round(t["cv"] * 100, 1),
            "ci_lo": round(t["lo"]),
            "ci_hi": round(t["hi"]),
        }
    )
ann = pd.DataFrame(ann_rows)
ann.to_csv(OUT / "annual_estimates_with_ci.csv", index=False)

# ------------------------------------------- 5. trend analyses (design-based)
def wls_trend(sub: pd.DataFrame, label: str) -> dict:
    """Inverse-variance weighted least squares of annual estimate on year."""
    x = sub["year"].to_numpy(dtype=float)
    y = sub["weighted_estimate"].to_numpy(dtype=float)
    w = 1.0 / (sub["se"].to_numpy(dtype=float) ** 2)
    X = np.column_stack([np.ones_like(x), x - x.mean()])
    W = np.diag(w)
    beta = np.linalg.solve(X.T @ W @ X, X.T @ W @ y)
    cov = np.linalg.inv(X.T @ W @ X)
    se_b = math.sqrt(cov[1, 1])
    from scipy import stats

    z = beta[1] / se_b
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    return {
        "label": label,
        "years": f"{int(x.min())}-{int(x.max())}",
        "slope_per_year": beta[1],
        "se": se_b,
        "ci_lo": beta[1] - sv.Z * se_b,
        "ci_hi": beta[1] + sv.Z * se_b,
        "z": z,
        "p": p,
    }

trend = [
    wls_trend(ann, "Full study period"),
    wls_trend(ann[ann["year"] <= 2019], "Pre-pandemic"),
    wls_trend(ann[(ann["year"] >= 2022)], "Post-pandemic"),
    wls_trend(ann[~ann["year"].isin([2020, 2021])], "Excluding pandemic years"),
]
pd.DataFrame(trend).to_csv(OUT / "trend_analysis.csv", index=False)
results["trend"] = trend

# design-based log-linear trend on individual records (annual percent change)
# Fit a survey-weighted Poisson-style trend via WLS on log(estimate).
def log_trend(sub: pd.DataFrame, label: str) -> dict:
    x = sub["year"].to_numpy(dtype=float)
    y = np.log(sub["weighted_estimate"].to_numpy(dtype=float))
    rel_se = sub["se"].to_numpy(dtype=float) / sub["weighted_estimate"].to_numpy(dtype=float)
    w = 1.0 / rel_se**2
    X = np.column_stack([np.ones_like(x), x - x.mean()])
    W = np.diag(w)
    beta = np.linalg.solve(X.T @ W @ X, X.T @ W @ y)
    cov = np.linalg.inv(X.T @ W @ X)
    se_b = math.sqrt(cov[1, 1])
    from scipy import stats

    z = beta[1] / se_b
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    return {
        "label": label,
        "years": f"{int(x.min())}-{int(x.max())}",
        "annual_pct_change": (math.exp(beta[1]) - 1) * 100,
        "ci_lo": (math.exp(beta[1] - sv.Z * se_b) - 1) * 100,
        "ci_hi": (math.exp(beta[1] + sv.Z * se_b) - 1) * 100,
        "p": p,
    }

logtrend = [
    log_trend(ann, "Full study period"),
    log_trend(ann[ann["year"] <= 2019], "Pre-pandemic"),
    log_trend(ann[ann["year"] >= 2022], "Post-pandemic"),
    log_trend(ann[~ann["year"].isin([2020, 2021])], "Excluding pandemic years"),
]
pd.DataFrame(logtrend).to_csv(OUT / "trend_analysis_loglinear.csv", index=False)
results["trend_loglinear"] = logtrend

# ------------------------- 6. key contrasts: pre-pandemic decline & 2020 trough
y = df["year"].to_numpy()
pre = (y >= 2015) & (y <= 2019)
m2015, m2019, m2020 = (y == 2015), (y == 2019), (y == 2020)

contrasts = {}
contrasts["2019_vs_2015_ratio"] = sv.ratio(df, m2019, m2015)
contrasts["2019_vs_2015_diff"] = sv.difference(df, m2019, m2015)
contrasts["2020_vs_pre_mean_ratio"] = sv.ratio_of_lincom(
    df, [(m2020, 1.0)], [(pre, 0.2)]
)
contrasts["2020_vs_2019_ratio"] = sv.ratio(df, m2020, m2019)
post = (y >= 2022) & (y <= 2025)
contrasts["post_mean_vs_pre_mean_ratio"] = sv.ratio_of_lincom(
    df, [(post, 0.25)], [(pre, 0.2)]
)
contrasts["pre_mean"] = sv.lincom(df, [(pre, 0.2)])
contrasts["post_mean"] = sv.lincom(df, [(post, 0.25)])
results["contrasts"] = contrasts

# --------------------------------------------------------------- 7. the model
import statsmodels.api as smapi
import statsmodels.formula.api as smf
from scipy import stats as sstats

model_df = df[df["sex_clean"].isin(["male", "female"])].copy()
model_df["dislocation"] = (model_df["diagnosis_group"] == "dislocation").astype(int)
model_df["year_centered"] = model_df["year"] - model_df["year"].mean()


def fit_model(data: pd.DataFrame) -> pd.DataFrame:
    m = smf.glm(
        "dislocation ~ C(sport_group, Treatment(reference='football')) "
        "+ C(age_group) + C(sex_clean) + year_centered",
        data=data,
        family=smapi.families.Binomial(),
        freq_weights=data["weight"],
    ).fit(cov_type="cluster", cov_kwds={"groups": data["psu"].astype(str) + "_" + data["stratum"].astype(str)})
    out = pd.DataFrame(
        {
            "term": m.params.index,
            "or": np.exp(m.params.values),
            "lo": np.exp(m.conf_int()[0].values),
            "hi": np.exp(m.conf_int()[1].values),
            "p": m.pvalues.values,
        }
    )
    return out


main_model = fit_model(model_df)
main_model.to_csv(OUT / "model_main_refit.csv", index=False)

# multiplicity adjustment on the five sport comparisons
sport_rows = main_model[main_model["term"].str.contains("sport_group")].copy()
pvals = sport_rows["p"].to_numpy()
order = np.argsort(pvals)
m_tests = len(pvals)
holm = np.empty(m_tests)
running = 0.0
for rank, idx in enumerate(order):
    val = (m_tests - rank) * pvals[idx]
    running = max(running, val)
    holm[idx] = min(running, 1.0)
bh = np.empty(m_tests)
running = 1.0
for rank in range(m_tests - 1, -1, -1):
    idx = order[rank]
    val = m_tests / (rank + 1) * pvals[idx]
    running = min(running, val)
    bh[idx] = min(running, 1.0)
sport_rows["p_holm"] = holm
sport_rows["p_bh"] = bh
sport_rows.to_csv(OUT / "model_sport_multiplicity.csv", index=False)
results["multiplicity"] = sport_rows.to_dict(orient="records")

# model restricted to 2019-2025 (comparable window) and sensitivity cohort
main_1925 = fit_model(model_df[model_df["year"] >= 2019])
main_1925.to_csv(OUT / "model_main_2019_2025.csv", index=False)

sens = pd.read_csv(SENS, low_memory=False)
sens["year"] = sens["year"].astype(int)
sens_model_df = sens[sens["sex_clean"].isin(["male", "female"])].copy()
sens_model_df["dislocation"] = (sens_model_df["diagnosis_group"] == "dislocation").astype(int)
sens_model_df["year_centered"] = sens_model_df["year"] - sens_model_df["year"].mean()
sens_model = fit_model(sens_model_df)
sens_model.to_csv(OUT / "model_sensitivity_2019_2025.csv", index=False)

# ------------------------------------------------- 8. S4 by-sport sensitivity
s4_rows = []
main_1925_df = df[df["year"] >= 2019]
for sport in sorted(set(main_1925_df["sport_group"]) | set(sens["sport_group"])):
    mm = (main_1925_df["sport_group"] == sport).to_numpy()
    sm = (sens["sport_group"] == sport).to_numpy()
    a = sv.total(main_1925_df, mm)
    b = sv.total(sens, sm)
    s4_rows.append(
        {
            "sport_group": sport,
            "main_n": a["n"],
            "main_est": round(a["est"]),
            "main_ci": f"{a['lo']:,.0f}-{a['hi']:,.0f}",
            "sens_n": b["n"],
            "sens_est": round(b["est"]),
            "sens_ci": f"{b['lo']:,.0f}-{b['hi']:,.0f}",
            "pct_increase": round((b["est"] - a["est"]) / a["est"] * 100, 1),
        }
    )
a_all = sv.total(main_1925_df)
b_all = sv.total(sens)
s4_rows.append(
    {
        "sport_group": "TOTAL",
        "main_n": a_all["n"],
        "main_est": round(a_all["est"]),
        "main_ci": f"{a_all['lo']:,.0f}-{a_all['hi']:,.0f}",
        "sens_n": b_all["n"],
        "sens_est": round(b_all["est"]),
        "sens_ci": f"{b_all['lo']:,.0f}-{b_all['hi']:,.0f}",
        "pct_increase": round((b_all["est"] - a_all["est"]) / a_all["est"] * 100, 1),
    }
)
pd.DataFrame(s4_rows).to_csv(OUT / "s4_by_sport.csv", index=False)

# ---------------------------------------------------------- 9. rounding audit
rounding = {}
for section, col in sections:
    parts = df.groupby(col)["weight"].sum()
    rounding[section] = {
        "sum_of_rounded_parts": int(sum(round(v) for v in parts.values)),
        "rounded_total": int(round(df["weight"].sum())),
        "exact_total": float(df["weight"].sum()),
    }
fb = df[df["sport_group"].isin(["football", "basketball"])]
rounding["football_plus_basketball"] = {
    "exact": float(fb["weight"].sum()),
    "rounded_combined": int(round(fb["weight"].sum())),
    "sum_of_rounded_parts": int(
        round(df[df.sport_group == "football"]["weight"].sum())
        + round(df[df.sport_group == "basketball"]["weight"].sum())
    ),
}
results["rounding"] = rounding

# --------------------------------------- 10. season definition & month mapping
season_map = (
    df.groupby(["season", "month"]).size().reset_index(name="n").sort_values(["season", "month"])
)
season_map.to_csv(OUT / "season_month_map.csv", index=False)
results["season_month_map"] = (
    df.groupby("season")["month"].apply(lambda s: sorted(s.unique().tolist())).to_dict()
)

# ---------------------------------- 11. narrative-based concordance assessment
narr = df["narrative"].fillna("").str.upper()
disloc_kw = r"\bDISLOCAT|\bDISLOC\b|\bSUBLUX|\bDISL\b|REDUC"
fract_kw = r"\bFRACT|\bFX\b|\bFXR?\b|\bBUCKLE|\bSALTER|\bAVULS"
has_d = narr.str.contains(disloc_kw, regex=True)
has_f = narr.str.contains(fract_kw, regex=True)
coded_d = df["diagnosis_group"] == "dislocation"
conc = pd.crosstab(
    np.where(coded_d, "coded dislocation", "coded fracture"),
    np.select(
        [has_d & ~has_f, has_f & ~has_d, has_d & has_f],
        ["narrative dislocation only", "narrative fracture only", "narrative both"],
        default="narrative neither/unspecified",
    ),
)
conc.to_csv(OUT / "narrative_concordance.csv")
results["narrative_concordance"] = conc.to_dict()
# agreement among records where narrative is informative (exactly one term)
informative = (has_d ^ has_f)
agree = ((coded_d & has_d) | (~coded_d & has_f)) & informative
results["narrative_concordance_summary"] = {
    "n_total": int(len(df)),
    "n_informative": int(informative.sum()),
    "pct_informative": round(informative.sum() / len(df) * 100, 1),
    "n_agree": int(agree.sum()),
    "pct_agree_among_informative": round(agree.sum() / informative.sum() * 100, 1),
}
# Cohen's kappa on informative subset
sub = df[informative].copy()
a = (sub["diagnosis_group"] == "dislocation").astype(int)
b = has_d[informative].astype(int)
po = (a == b).mean()
pe = (a.mean() * b.mean()) + ((1 - a.mean()) * (1 - b.mean()))
results["narrative_concordance_summary"]["kappa"] = round((po - pe) / (1 - pe), 3)

# ------------------------------------------------- 12. comprehensive S7 flags
s7 = []
for r in t1_rows:
    if r["instability_flag"]:
        s7.append(
            {
                "source": "Table 1",
                "descriptor": f"{r['section']}: {r['label']}",
                "unweighted_n": r["unweighted_n"],
                "weighted_estimate": r["weighted_estimate"],
                "cv_pct": r["cv_pct"],
                "flag": r["instability_flag"],
            }
        )
for r in t2_rows:
    if r["severe_instability_flag"]:
        s7.append(
            {
                "source": "Table 2 (severe disposition)",
                "descriptor": f"{r['sport_group']}: severe disposition",
                "unweighted_n": r["severe_n"],
                "weighted_estimate": r["severe_weighted_est"],
                "cv_pct": r["severe_cv_pct"],
                "flag": r["severe_instability_flag"],
            }
        )
for yv in sorted(df["year"].unique()):
    for sport in sorted(df["sport_group"].unique()):
        m = ((df["year"] == yv) & (df["sport_group"] == sport)).to_numpy()
        if m.sum() == 0:
            continue
        t = sv.total(df, m)
        flags = []
        if t["est"] < 1200:
            flags.append("estimate<1200")
        if t["n"] < 20:
            flags.append("n<20")
        if not pd.isna(t["cv"]) and t["cv"] > 0.33:
            flags.append("cv>33%")
        if flags:
            s7.append(
                {
                    "source": "Annual by sport",
                    "descriptor": f"{sport} {int(yv)}",
                    "unweighted_n": t["n"],
                    "weighted_estimate": round(t["est"]),
                    "cv_pct": round(t["cv"] * 100, 1),
                    "flag": "; ".join(flags),
                }
            )
pd.DataFrame(s7).to_csv(OUT / "s7_comprehensive_flags.csv", index=False)
results["s7_count"] = len(s7)

# ----------------------------------------- 13. abstract-level numbers with CI
abstract = {}
for label, m in [
    ("football", (df.sport_group == "football").to_numpy()),
    ("basketball", (df.sport_group == "basketball").to_numpy()),
    ("baseball/softball", (df.sport_group == "baseball/softball").to_numpy()),
    ("football+basketball", df.sport_group.isin(["football", "basketball"]).to_numpy()),
    ("fracture", (df.diagnosis_group == "fracture").to_numpy()),
    ("dislocation", (df.diagnosis_group == "dislocation").to_numpy()),
]:
    abstract[label] = {"total": sv.total(df, m), "pct": sv.ratio(df, m, allmask)}
results["abstract"] = abstract

# --------------------------------------------- 14. "other selected ball sports"
other = df[df["sport_group"] == "other selected ball sports"]
results["other_ball_sports_composition"] = (
    other.groupby("sport_code")["weight"].agg(["count", "sum"]).sort_values("sum", ascending=False).to_dict()
)

# volleyball vs football/basketball dislocation % overlap
vb = sv.ratio(df, (df.sport_group == "volleyball").to_numpy() & (df.diagnosis_group == "dislocation").to_numpy(), (df.sport_group == "volleyball").to_numpy())
fbb = sv.ratio(df, (df.sport_group == "football").to_numpy() & (df.diagnosis_group == "dislocation").to_numpy(), (df.sport_group == "football").to_numpy())
bkb = sv.ratio(df, (df.sport_group == "basketball").to_numpy() & (df.diagnosis_group == "dislocation").to_numpy(), (df.sport_group == "basketball").to_numpy())
results["dislocation_pct_by_sport"] = {"volleyball": vb, "football": fbb, "basketball": bkb}

# unknown/other sex record
unk = df[~df["sex_clean"].isin(["male", "female"])]
results["unknown_sex"] = {
    "n": int(len(unk)),
    "weight": float(unk["weight"].sum()),
    "year": unk["year"].tolist(),
    "sport": unk["sport_group"].tolist(),
    "diagnosis": unk["diagnosis_group"].tolist(),
}


def clean(o):
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if (isinstance(o, float) and math.isnan(o)) else float(o)
    if isinstance(o, float) and math.isnan(o):
        return None
    return o


(OUT / "results.json").write_text(json.dumps(clean(results), indent=2, ensure_ascii=False))
print("DONE")
print(json.dumps(clean(results["headline_total"]), indent=2))
