#!/usr/bin/env python
from __future__ import annotations

import warnings
import shutil
import subprocess

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

from utils import (
    ROOT,
    PROCESSED_DIR,
    REPORT_DIR,
    design_total_cv,
    ensure_dirs,
    instability_flag,
    load_config,
    weighted_total,
    write_markdown_table,
)


def read_cohort() -> pd.DataFrame:
    path = PROCESSED_DIR / "cohort_main.csv"
    if not path.exists():
        raise FileNotFoundError("Missing data/processed/cohort_main.csv. Run scripts/03_build_cohort.py.")
    df = pd.read_csv(path)
    df["treatment_date"] = pd.to_datetime(df["treatment_date"], errors="coerce")
    return df


def domain_summary(df: pd.DataFrame, mask: pd.Series, label: str, config: dict) -> dict:
    n = int(mask.sum())
    est, se, cv = design_total_cv(df, mask)
    return {
        "label": label,
        "unweighted_n": n,
        "weighted_estimate": est,
        "se": se,
        "cv": cv,
        "instability_flag": instability_flag(n, est, cv, config),
    }


def make_table1_components(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    groups = [
        ("age_group", "Age group"),
        ("sex_clean", "Sex"),
        ("calendar_period", "Calendar period"),
        ("sport_group", "Sport group"),
        ("diagnosis_group", "Diagnosis group"),
        ("disposition_group", "Disposition"),
        ("season", "Season"),
    ]
    denom = weighted_total(df)
    rows = []
    for col, section in groups:
        for val in sorted(df[col].dropna().unique(), key=lambda x: str(x)):
            mask = df[col] == val
            row = domain_summary(df, mask, str(val), config)
            row["section"] = section
            row["weighted_percent"] = row["weighted_estimate"] / denom if denom else np.nan
            rows.append(row)
    return pd.DataFrame(rows)[
        ["section", "label", "unweighted_n", "weighted_estimate", "se", "cv", "weighted_percent", "instability_flag"]
    ]


def annual_estimates(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    rows = []
    for year in sorted(df["year"].dropna().astype(int).unique()):
        row = domain_summary(df, df["year"] == year, str(year), config)
        row["year"] = year
        rows.append(row)
    return pd.DataFrame(rows)[["year", "unweighted_n", "weighted_estimate", "se", "cv", "instability_flag"]]


def annual_by_sport(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    rows = []
    for year in sorted(df["year"].dropna().astype(int).unique()):
        for sport in sorted(df["sport_group"].dropna().unique()):
            mask = (df["year"] == year) & (df["sport_group"] == sport)
            row = domain_summary(df, mask, sport, config)
            row["year"] = year
            row["sport_group"] = sport
            rows.append(row)
    return pd.DataFrame(rows)[
        ["year", "sport_group", "unweighted_n", "weighted_estimate", "se", "cv", "instability_flag"]
    ]


def sport_patterns(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    rows = []
    for sport in sorted(df["sport_group"].dropna().unique()):
        mask = df["sport_group"] == sport
        total = domain_summary(df, mask, sport, config)
        sport_est = total["weighted_estimate"]
        fracture_est = weighted_total(df, mask & (df["diagnosis_group"] == "fracture"))
        dislocation_est = weighted_total(df, mask & (df["diagnosis_group"] == "dislocation"))
        severe_nonmissing = mask & df["severe_disposition"].notna()
        severe_est = weighted_total(df, mask & (df["severe_disposition"] == 1))
        severe_denom = weighted_total(df, severe_nonmissing)
        season_est = (
            df.loc[mask]
            .groupby("season", dropna=True)["weight"]
            .sum()
            .sort_values(ascending=False)
        )
        peak_season = season_est.index[0] if len(season_est) else ""
        rows.append(
            {
                "sport_group": sport,
                "unweighted_n": total["unweighted_n"],
                "weighted_estimate": sport_est,
                "se": total["se"],
                "cv": total["cv"],
                "fracture_weighted_percent": fracture_est / sport_est if sport_est else np.nan,
                "dislocation_weighted_percent": dislocation_est / sport_est if sport_est else np.nan,
                "severe_disposition_weighted_percent": severe_est / severe_denom if severe_denom else np.nan,
                "top_season": peak_season,
                "instability_flag": total["instability_flag"],
            }
        )
    return pd.DataFrame(rows).sort_values("weighted_estimate", ascending=False)


def diagnosis_by_sport(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    rows = []
    for sport in sorted(df["sport_group"].dropna().unique()):
        denom = weighted_total(df[df["sport_group"] == sport])
        for diag in ["fracture", "dislocation"]:
            mask = (df["sport_group"] == sport) & (df["diagnosis_group"] == diag)
            row = domain_summary(df, mask, diag, config)
            row["sport_group"] = sport
            row["diagnosis_group"] = diag
            row["weighted_percent_within_sport"] = row["weighted_estimate"] / denom if denom else np.nan
            rows.append(row)
    return pd.DataFrame(rows)


def season_month_summary(df: pd.DataFrame, config: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    season_rows = []
    for season in sorted(df["season"].dropna().unique()):
        season_rows.append(domain_summary(df, df["season"] == season, season, config))
    month_rows = []
    for month in range(1, 13):
        row = domain_summary(df, df["month"] == month, str(month), config)
        row["month"] = month
        month_rows.append(row)
    return pd.DataFrame(season_rows), pd.DataFrame(month_rows)


def narrative_summary(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    d = df[df["year"].between(2019, 2025)].copy()
    rows = []
    denom = weighted_total(d) if len(d) else np.nan
    for mech in sorted(d["narrative_mechanism"].dropna().unique()):
        mask = d["narrative_mechanism"] == mech
        row = domain_summary(d, mask, mech, config)
        row["weighted_percent"] = row["weighted_estimate"] / denom if denom else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def fit_dislocation_model(df: pd.DataFrame) -> pd.DataFrame:
    d = df[df["diagnosis_group"].isin(["fracture", "dislocation"]) & df["sex_clean"].isin(["male", "female"])].copy()
    sport_order = (
        d.groupby("sport_group")["weight"].sum().sort_values(ascending=False).index.tolist()
    )
    if not sport_order:
        return pd.DataFrame()
    ref_sport = sport_order[0]
    d["sport_group"] = pd.Categorical(d["sport_group"], categories=sport_order)
    d["age_group"] = pd.Categorical(d["age_group"], categories=["10-12", "13-15", "16-18"])
    d["sex_clean"] = pd.Categorical(d["sex_clean"], categories=["male", "female"])
    d["dislocation"] = (d["diagnosis_group"] == "dislocation").astype(int)
    d["year_centered"] = d["year"] - d["year"].median()
    formula = "dislocation ~ C(sport_group, Treatment(reference='%s')) + C(age_group) + C(sex_clean) + year_centered" % ref_sport
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = smf.glm(formula=formula, data=d, family=sm.families.Binomial(), freq_weights=d["weight"])
        try:
            fit = model.fit(cov_type="cluster", cov_kwds={"groups": d["psu"].astype(str)})
            se_note = "cluster-robust by PSU; approximate with frequency weights"
        except Exception:
            fit = model.fit()
            se_note = "model-based; cluster-robust covariance unavailable"
    params = fit.params
    conf = fit.conf_int()
    rows = []
    for term, beta in params.items():
        if term == "Intercept":
            continue
        p = float(fit.pvalues.get(term, np.nan))
        lo, hi = conf.loc[term]
        rows.append(
            {
                "term": term,
                "adjusted_or": float(np.exp(beta)),
                "ci_low": float(np.exp(lo)),
                "ci_high": float(np.exp(hi)),
                "p_value": p,
                "reference": f"sport reference: {ref_sport}; outcome reference: fracture",
                "se_note": se_note,
            }
        )
    out = pd.DataFrame(rows)
    (REPORT_DIR / "model_dislocation_summary.txt").write_text(
        str(fit.summary())
        + "\n\nNote: adjusted regression excludes records with sex coded unknown/other to avoid sparse-cell separation; descriptive tables retain them.\n",
        encoding="utf-8",
    )
    return out


def maybe_fit_severe_model(df: pd.DataFrame) -> pd.DataFrame:
    d = df[df["severe_disposition"].isin([0, 1]) & df["sex_clean"].isin(["male", "female"])].copy()
    sport_counts = d.groupby("sport_group").size()
    sport_order = d.groupby("sport_group")["weight"].sum().sort_values(ascending=False).index.tolist()
    if not sport_order:
        return pd.DataFrame()
    params_count = max(1, (len(sport_order) - 1) + 2 + 1 + 1)
    severe_events = int((d["severe_disposition"] == 1).sum())
    too_sparse = severe_events < 10 * params_count or (sport_counts < 20).any()
    if too_sparse:
        msg = (
            f"Severe-disposition model not run. Severe events={severe_events}; "
            f"approximate parameters={params_count}; minimum sport category n={int(sport_counts.min()) if len(sport_counts) else 0}. "
            "The prespecified sparse-event rule was not met."
        )
        (REPORT_DIR / "severe_model_not_run.txt").write_text(msg + "\n", encoding="utf-8")
        return pd.DataFrame()
    ref_sport = sport_order[0]
    d["sport_group"] = pd.Categorical(d["sport_group"], categories=sport_order)
    d["age_group"] = pd.Categorical(d["age_group"], categories=["10-12", "13-15", "16-18"])
    d["year_centered"] = d["year"] - d["year"].median()
    formula = "severe_disposition ~ C(sport_group, Treatment(reference='%s')) + C(age_group) + C(sex_clean) + year_centered" % ref_sport
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = smf.glm(formula=formula, data=d, family=sm.families.Binomial(), freq_weights=d["weight"]).fit(
            cov_type="cluster", cov_kwds={"groups": d["psu"].astype(str)}
        )
    rows = []
    conf = fit.conf_int()
    for term, beta in fit.params.items():
        if term == "Intercept":
            continue
        lo, hi = conf.loc[term]
        rows.append(
            {
                "term": term,
                "adjusted_or": float(np.exp(beta)),
                "ci_low": float(np.exp(lo)),
                "ci_high": float(np.exp(hi)),
                "p_value": float(fit.pvalues.get(term, np.nan)),
                "reference": f"sport reference: {ref_sport}; outcome reference: treated/released",
                "se_note": "cluster-robust by PSU; approximate with frequency weights",
            }
        )
    return pd.DataFrame(rows)


def trend_summary(annual: pd.DataFrame) -> pd.DataFrame:
    d = annual.dropna(subset=["year", "weighted_estimate"]).copy()
    if len(d) < 3:
        return pd.DataFrame()
    x = d["year"].astype(float)
    y = d["weighted_estimate"].astype(float)
    slope, intercept, r, p, se = stats.linregress(x, y)
    excl = d[~d["year"].isin([2020, 2021])]
    row = {
        "model": "linear annual weighted totals, 2015-2025",
        "slope_per_year": slope,
        "p_value": p,
        "r_squared": r**2,
        "note": "descriptive trend; no sport-exposure denominator",
    }
    if len(excl) >= 3:
        x2 = excl["year"].astype(float)
        y2 = excl["weighted_estimate"].astype(float)
        slope2, intercept2, r2, p2, se2 = stats.linregress(x2, y2)
        return pd.DataFrame(
            [
                row,
                {
                    "model": "linear annual weighted totals, excluding 2020-2021",
                    "slope_per_year": slope2,
                    "p_value": p2,
                    "r_squared": r2**2,
                    "note": "descriptive sensitivity trend; pandemic years excluded",
                },
            ]
        )
    return pd.DataFrame([row])


def sensitivity_summary(config: dict) -> pd.DataFrame:
    path = PROCESSED_DIR / "cohort_sensitivity_2019_2025.csv"
    if not path.exists():
        return pd.DataFrame()
    d = pd.read_csv(path)
    rows = [
        {
            "cohort": "main restricted to 2019-2025",
            "unweighted_n": "",
            "weighted_estimate": "",
            "note": "Computed in table S4 by sport below.",
        }
    ]
    main = read_cohort()
    main19 = main[main["year"].between(2019, 2025)]
    rows[0]["unweighted_n"] = len(main19)
    rows[0]["weighted_estimate"] = weighted_total(main19)
    rows.append(
        {
            "cohort": "sensitivity 2019-2025 including secondary/product_3 variables",
            "unweighted_n": len(d),
            "weighted_estimate": weighted_total(d),
            "note": "Uses Body_Part_2, Diagnosis_2, and Product_3 when available.",
        }
    )
    return pd.DataFrame(rows)


def main() -> None:
    ensure_dirs()
    config = load_config()
    df = read_cohort()
    if df.empty:
        raise RuntimeError("Main cohort is empty; no analysis can be performed.")

    table1 = make_table1_components(df, config)
    annual = annual_estimates(df, config)
    annual_sport = annual_by_sport(df, config)
    sport = sport_patterns(df, config)
    diag_sport = diagnosis_by_sport(df, config)
    season, month = season_month_summary(df, config)
    narrative = narrative_summary(df, config)
    model = fit_dislocation_model(df)
    severe = maybe_fit_severe_model(df)
    trend = trend_summary(annual)
    sensitivity = sensitivity_summary(config)

    outputs = {
        "analysis_table1_components.csv": table1,
        "annual_estimates.csv": annual,
        "annual_by_sport.csv": annual_sport,
        "sport_patterns.csv": sport,
        "diagnosis_by_sport.csv": diag_sport,
        "season_summary.csv": season,
        "month_summary.csv": month,
        "narrative_mechanism_2019_2025.csv": narrative,
        "model_dislocation_vs_fracture.csv": model,
        "model_severe_disposition.csv": severe,
        "trend_summary.csv": trend,
        "sensitivity_summary.csv": sensitivity,
    }
    for name, data in outputs.items():
        data.to_csv(REPORT_DIR / name, index=False)
    rscript = shutil.which("Rscript")
    r_survey_script = REPORT_DIR.parents[1] / "scripts" / "04a_survey_analysis.R"
    if rscript and r_survey_script.exists():
        proc = subprocess.run([rscript, str(r_survey_script), str(ROOT)], check=False, capture_output=True, text=True)
        if proc.returncode != 0:
            (REPORT_DIR / "r_survey_status.txt").write_text(
                "R survey step did not complete; Python fallback outputs were retained.\n"
                + proc.stdout
                + "\n"
                + proc.stderr,
                encoding="utf-8",
            )
    write_markdown_table(trend, REPORT_DIR / "trend_summary.md", "Trend Summary")
    print(f"Analysis complete. Main cohort n={len(df)}, weighted={weighted_total(df):.0f}")


if __name__ == "__main__":
    main()
