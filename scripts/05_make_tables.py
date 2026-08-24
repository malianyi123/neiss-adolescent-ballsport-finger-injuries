#!/usr/bin/env python
from __future__ import annotations

import numpy as np
import pandas as pd
import re

from utils import (
    CONFIG_DIR,
    REPORT_DIR,
    SUPPLEMENT_DIR,
    TABLE_DIR,
    ensure_dirs,
    format_int,
    format_or,
    format_pct,
    load_config,
    load_mappings,
    md_table,
    safe_read_csv,
    write_docx_tables,
    write_markdown_table,
)


def fmt_estimate_table(df: pd.DataFrame, keep: list[str]) -> pd.DataFrame:
    out = df.copy()
    if "weighted_estimate" in out:
        out["weighted national estimate"] = out["weighted_estimate"].map(format_int)
    if "weighted_percent" in out:
        out["weighted %"] = out["weighted_percent"].map(format_pct)
    if "cv" in out:
        out["CV"] = out["cv"].map(lambda x: "" if pd.isna(x) else f"{float(x) * 100:.1f}%")
    rename = {"unweighted_n": "unweighted n", "instability_flag": "instability flag"}
    out = out.rename(columns=rename)
    return out[[c for c in keep if c in out.columns]]


def make_table1() -> pd.DataFrame:
    df = safe_read_csv(REPORT_DIR / "analysis_table1_components.csv")
    keep = [
        "section",
        "label",
        "unweighted n",
        "weighted national estimate",
        "weighted %",
        "CV",
        "instability flag",
    ]
    return fmt_estimate_table(df, keep)


def make_table2() -> pd.DataFrame:
    df = safe_read_csv(REPORT_DIR / "sport_patterns.csv")
    if df.empty:
        return df
    out = df.copy()
    out["weighted national estimate"] = out["weighted_estimate"].map(format_int)
    out["fracture weighted %"] = out["fracture_weighted_percent"].map(format_pct)
    out["dislocation weighted %"] = out["dislocation_weighted_percent"].map(format_pct)
    out["severe disposition weighted %"] = out["severe_disposition_weighted_percent"].map(format_pct)
    out["CV"] = out["cv"].map(lambda x: "" if pd.isna(x) else f"{float(x) * 100:.1f}%")
    out = out.rename(columns={"unweighted_n": "unweighted n", "instability_flag": "instability flag"})
    return out[
        [
            "sport_group",
            "unweighted n",
            "weighted national estimate",
            "fracture weighted %",
            "dislocation weighted %",
            "severe disposition weighted %",
            "top_season",
            "CV",
            "instability flag",
        ]
    ].rename(columns={"sport_group": "sport group", "top_season": "top season"})


def clean_model_term(term: str) -> str:
    term = str(term)
    m = re.match(r"C\(sport_group, Treatment\(reference='(.+)'\)\)\[T\.(.+)\]", term)
    if m:
        return f"sport group: {m.group(2)} vs {m.group(1)}"
    m = re.match(r"C\(age_group\)\[T\.(.+)\]", term)
    if m:
        return f"age group: {m.group(1)} vs 10-12"
    m = re.match(r"C\(sex_clean\)\[T\.(.+)\]", term)
    if m:
        return f"sex: {m.group(1)} vs male"
    term = term.replace("C(sport_group, Treatment(reference=", "sport group: ")
    term = term.replace("C(age_group)", "age group")
    term = term.replace("C(sex_clean)", "sex")
    term = term.replace("T.", "")
    term = term.replace("[", " ")
    term = term.replace("]", "")
    term = term.replace("'", "")
    term = term.replace(")", "")
    term = term.replace("year_centered", "treatment year, per year")
    return " ".join(term.split())


def make_table3() -> pd.DataFrame:
    df = safe_read_csv(REPORT_DIR / "model_dislocation_vs_fracture.csv")
    if df.empty:
        return df
    out = pd.DataFrame(
        {
            "predictor": df["term"].map(clean_model_term),
            "adjusted OR": df["adjusted_or"].map(format_or),
            "95% CI": df.apply(lambda r: f"{format_or(r['ci_low'])}-{format_or(r['ci_high'])}", axis=1),
            "p value": df["p_value"].map(lambda x: "" if pd.isna(x) else ("<0.001" if x < 0.001 else f"{x:.3f}")),
            "note": df["reference"].fillna("") + "; " + df["se_note"].fillna(""),
        }
    )
    return out


def make_table4() -> pd.DataFrame:
    df = safe_read_csv(REPORT_DIR / "model_severe_disposition.csv")
    if df.empty:
        return df
    return pd.DataFrame(
        {
            "predictor": df["term"].map(clean_model_term),
            "adjusted OR": df["adjusted_or"].map(format_or),
            "95% CI": df.apply(lambda r: f"{format_or(r['ci_low'])}-{format_or(r['ci_high'])}", axis=1),
            "p value": df["p_value"].map(lambda x: "" if pd.isna(x) else ("<0.001" if x < 0.001 else f"{x:.3f}")),
            "note": df["reference"].fillna("") + "; " + df["se_note"].fillna(""),
        }
    )


def supplementary_code_mapping(mappings: dict) -> pd.DataFrame:
    rows = []
    rows.append(
        {
            "domain": "body part",
            "group": "finger",
            "code": mappings["body_part"]["finger"]["code"],
            "official label": mappings["body_part"]["finger"]["label"],
        }
    )
    for name, meta in mappings["diagnosis"].items():
        rows.append({"domain": "diagnosis", "group": name, "code": meta["code"], "official label": meta["label"]})
    for group, meta in mappings["sport_groups"].items():
        for item in meta["codes"]:
            rows.append({"domain": "product/activity", "group": meta["label"], "code": item["code"], "official label": item["label"]})
    return pd.DataFrame(rows)


def supplementary_annual_sport() -> pd.DataFrame:
    df = safe_read_csv(REPORT_DIR / "annual_by_sport.csv")
    if df.empty:
        return df
    out = df.copy()
    out["weighted national estimate"] = out["weighted_estimate"].map(format_int)
    out["CV"] = out["cv"].map(lambda x: "" if pd.isna(x) else f"{float(x) * 100:.1f}%")
    out = out.rename(columns={"unweighted_n": "unweighted n", "instability_flag": "instability flag"})
    return out[["year", "sport_group", "unweighted n", "weighted national estimate", "CV", "instability flag"]]


def supplementary_sensitivity() -> pd.DataFrame:
    df = safe_read_csv(REPORT_DIR / "sensitivity_summary.csv")
    if df.empty:
        return df
    out = df.copy()
    out["weighted national estimate"] = out["weighted_estimate"].map(format_int)
    out = out.rename(columns={"unweighted_n": "unweighted n"})
    return out[["cohort", "unweighted n", "weighted national estimate", "note"]]


def supplementary_narrative() -> pd.DataFrame:
    df = safe_read_csv(REPORT_DIR / "narrative_mechanism_2019_2025.csv")
    if df.empty:
        return df
    out = df.copy()
    out["weighted national estimate"] = out["weighted_estimate"].map(format_int)
    out["weighted %"] = out["weighted_percent"].map(format_pct)
    out["CV"] = out["cv"].map(lambda x: "" if pd.isna(x) else f"{float(x) * 100:.1f}%")
    out = out.rename(columns={"label": "mechanism", "unweighted_n": "unweighted n", "instability_flag": "instability flag"})
    return out[["mechanism", "unweighted n", "weighted national estimate", "weighted %", "CV", "instability flag"]]


def supplementary_missingness() -> pd.DataFrame:
    df = safe_read_csv(REPORT_DIR / "missingness_summary.csv")
    if df.empty:
        return df
    out = df.copy()
    out["missing %"] = out["missing_percent"].map(format_pct)
    out = out.rename(columns={"missing_n": "missing n"})
    return out[["variable", "missing n", "missing %"]]


def instability_list() -> pd.DataFrame:
    paths = [
        ("annual estimates", REPORT_DIR / "annual_estimates.csv"),
        ("annual by sport", REPORT_DIR / "annual_by_sport.csv"),
        ("sport patterns", REPORT_DIR / "sport_patterns.csv"),
        ("narrative mechanisms", REPORT_DIR / "narrative_mechanism_2019_2025.csv"),
    ]
    rows = []
    for source, path in paths:
        df = safe_read_csv(path)
        if df.empty or "instability_flag" not in df:
            continue
        flagged = df[df["instability_flag"].fillna("") != ""].copy()
        for _, row in flagged.iterrows():
            rows.append(
                {
                    "source": source,
                    "descriptor": row.get("sport_group", row.get("label", row.get("year", ""))),
                    "year": row.get("year", ""),
                    "unweighted n": row.get("unweighted_n", ""),
                    "weighted estimate": format_int(row.get("weighted_estimate", np.nan)),
                    "flag": row.get("instability_flag", ""),
                }
            )
    return pd.DataFrame(rows)


def write_all() -> None:
    ensure_dirs()
    load_config()
    mappings = load_mappings()
    table_titles = {
        "table_1_baseline_characteristics": "Table 1. Baseline characteristics of the main analytic cohort",
        "table_2_sport_specific_patterns": "Table 2. Sport-specific injury patterns",
        "table_3_adjusted_dislocation_model": "Table 3. Survey-weighted adjusted model for dislocation versus fracture",
        "table_4_adjusted_severe_disposition_model": "Table 4. Survey-weighted adjusted model for severe disposition",
    }
    supp_titles = {
        "s1_official_code_mappings_used": "Supplementary Table S1. NEISS body-part, diagnosis, and sport/product code mapping used for cohort construction",
        "s2_cohort_flow": "Supplementary Table S2. Cohort flow for the main analytic cohort",
        "s3_annual_estimates_by_year_and_sport": "Supplementary Table S3. Annual weighted estimates by year and sport group",
        "s4_sensitivity_analysis_2019_2025": "Supplementary Table S4. Sensitivity analysis using secondary and tertiary NEISS variables, 2019-2025",
        "s5_narrative_mechanism_2019_2025": "Supplementary Table S5. Narrative mechanism classification, 2019-2025",
        "s6_missingness_summary": "Supplementary Table S6. Missingness summary for analytic variables",
        "s7_instability_flags": "Supplementary Table S7. Instability flags for generated estimates",
    }
    tables = {
        "table_1_baseline_characteristics": make_table1(),
        "table_2_sport_specific_patterns": make_table2(),
        "table_3_adjusted_dislocation_model": make_table3(),
    }
    table4 = make_table4()
    if not table4.empty:
        tables["table_4_adjusted_severe_disposition_model"] = table4

    for name, df in tables.items():
        df.to_csv(TABLE_DIR / f"{name}.csv", index=False)
        write_markdown_table(df, TABLE_DIR / f"{name}.md", table_titles.get(name, name.replace("_", " ").title()))

    write_docx_tables([(table_titles.get(name, name.replace("_", " ").title()), df) for name, df in tables.items()], TABLE_DIR / "main_tables.docx")

    supp_tables = {
        "s1_official_code_mappings_used": supplementary_code_mapping(mappings),
        "s2_cohort_flow": safe_read_csv(REPORT_DIR / "cohort_flow.csv"),
        "s3_annual_estimates_by_year_and_sport": supplementary_annual_sport(),
        "s4_sensitivity_analysis_2019_2025": supplementary_sensitivity(),
        "s5_narrative_mechanism_2019_2025": supplementary_narrative(),
        "s6_missingness_summary": supplementary_missingness(),
        "s7_instability_flags": instability_list(),
    }
    for name, df in supp_tables.items():
        df.to_csv(SUPPLEMENT_DIR / f"{name}.csv", index=False)
        write_markdown_table(df, SUPPLEMENT_DIR / f"{name}.md", supp_titles.get(name, name.replace("_", " ").upper()))
    write_docx_tables([(supp_titles.get(name, name.replace("_", " ").upper()), df) for name, df in supp_tables.items()], SUPPLEMENT_DIR / "supplementary_tables.docx")

    index_lines = ["# Tables", ""]
    for name, df in {**tables, **supp_tables}.items():
        index_lines.append(f"## {name}")
        index_lines.append("")
        index_lines.append(md_table(df))
        index_lines.append("")
    (TABLE_DIR / "all_tables.md").write_text("\n".join(index_lines), encoding="utf-8")
    print("Tables written to outputs/tables and outputs/supplementary")


if __name__ == "__main__":
    write_all()
