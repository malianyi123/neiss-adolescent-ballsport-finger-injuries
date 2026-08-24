#!/usr/bin/env python
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from utils import (
    DOCS_DIR,
    PROCESSED_DIR,
    REPORT_DIR,
    design_total_cv,
    ensure_dirs,
    instability_flag,
    load_clean_years,
    load_config,
    load_mappings,
    sport_code_to_group,
    weighted_total,
)


def clean_sex(series: pd.Series, mappings: dict) -> pd.Series:
    labels = mappings.get("sex", {})
    out = []
    for val in series:
        label = labels.get(str(int(val)) if pd.notna(val) else "", "").upper()
        if "MALE" in label and "FEMALE" not in label:
            out.append("male")
        elif "FEMALE" in label:
            out.append("female")
        elif "NON-BINARY" in label or "OTHER" in label:
            out.append("unknown/other")
        else:
            out.append("unknown/other")
    return pd.Series(out, index=series.index)


def diagnosis_group(series: pd.Series, mappings: dict) -> pd.Series:
    fracture = int(mappings["diagnosis"]["fracture"]["code"])
    dislocation = int(mappings["diagnosis"]["dislocation"]["code"])
    return np.select(
        [series == fracture, series == dislocation],
        ["fracture", "dislocation"],
        default=pd.NA,
    )


def disposition_group(series: pd.Series, mappings: dict) -> pd.Series:
    labels = mappings.get("disposition", {})
    out = []
    for val in series:
        label = labels.get(str(int(val)) if pd.notna(val) else "", "").upper()
        if "TREATED" in label and ("RELEASED" in label or "EXAMINED" in label):
            out.append("treated/released")
        elif "TRANSFER" in label:
            out.append("transferred")
        elif "ADMIT" in label or "HOSPITAL" in label:
            out.append("admitted")
        elif "OBSERV" in label or "HELD" in label:
            out.append("observation")
        else:
            out.append("other/unknown")
    return pd.Series(out, index=series.index)


def severe_from_disposition(group: pd.Series) -> pd.Series:
    return np.select(
        [
            group.isin(["transferred", "admitted", "observation"]),
            group == "treated/released",
        ],
        [1, 0],
        default=np.nan,
    )


def season_from_month(month: pd.Series) -> pd.Series:
    return np.select(
        [
            month.isin([12, 1, 2]),
            month.isin([3, 4, 5]),
            month.isin([6, 7, 8]),
            month.isin([9, 10, 11]),
        ],
        ["winter", "spring", "summer", "fall"],
        default=pd.NA,
    )


def classify_mechanism(narrative: str) -> str:
    text = str(narrative).upper()
    if re.search(r"HIT BY (A )?BALL|STRUCK BY (A )?BALL|BALL HIT|BALL STRUCK|CAUGHT (THE )?BALL|CATCH(ING)? (A |THE )?BALL|ATTEMPT(ING|ED)? TO CATCH", text):
        return "ball impact/catching"
    if re.search(r"JAM(MED|MING)?|BENT BACK|HYPEREXTEND|HYPER-EXTEND", text):
        return "jamming/hyperextension"
    if re.search(r"\bFELL\b|\bFALL\b|FOOSH|FALLING", text):
        return "fall"
    if re.search(r"COLLID|TACKL|ANOTHER PLAYER|WITH PLAYER|CONTACT", text):
        return "collision/contact"
    if re.search(r"\bBAT\b|GLOVE|GOAL|STICK|EQUIPMENT", text):
        return "equipment"
    return "unclear"


def nonparticipant_mask(narrative: pd.Series) -> pd.Series:
    text = narrative.fillna("").astype(str).str.upper()
    spectator = text.str.contains(r"SPECTATOR|BYSTANDER|WATCHING .*GAME|WATCHING .*PLAY|IN (THE )?STANDS|BLEACHER|ATTENDING .*GAME", regex=True)
    participant = text.str.contains(r"PLAYING|PLAYER|PRACTICE|PRACTICING|DURING .*GAME|WHILE .*PLAY", regex=True)
    return spectator & ~participant


def assign_sport(df: pd.DataFrame, mappings: dict, include_product3: bool = False) -> pd.DataFrame:
    code_map = sport_code_to_group(mappings)
    prod_cols = ["product_1", "product_2"] + (["product_3"] if include_product3 else [])

    sport_codes = []
    sport_groups = []
    multi_flags = []
    for _, row in df[prod_cols].iterrows():
        found = []
        for col in prod_cols:
            val = row[col]
            if pd.notna(val) and int(val) in code_map:
                found.append((int(val), code_map[int(val)], col))
        if found:
            sport_codes.append(found[0][0])
            sport_groups.append(found[0][1])
            multi_flags.append(len({x[1] for x in found}) > 1)
        else:
            sport_codes.append(np.nan)
            sport_groups.append(pd.NA)
            multi_flags.append(False)
    out = df.copy()
    out["sport_code"] = sport_codes
    out["sport_group"] = sport_groups
    out["multi_selected_sport_flag"] = multi_flags
    return out


def add_derived(df: pd.DataFrame, mappings: dict) -> pd.DataFrame:
    out = df.copy()
    out["age_group"] = pd.cut(
        out["age"],
        bins=[9, 12, 15, 18],
        labels=["10-12", "13-15", "16-18"],
        include_lowest=True,
        right=True,
    ).astype(str)
    out["sex_clean"] = clean_sex(out["sex"], mappings)
    out["diagnosis_group"] = diagnosis_group(out["diagnosis"], mappings)
    out["disposition_group"] = disposition_group(out["disposition"], mappings)
    out["severe_disposition"] = severe_from_disposition(out["disposition_group"])
    out["calendar_period"] = np.select(
        [
            out["year"].between(2015, 2019),
            out["year"].between(2020, 2021),
            out["year"].between(2022, 2025),
        ],
        ["pre-pandemic", "pandemic", "post-pandemic"],
        default=pd.NA,
    )
    treatment_date = pd.to_datetime(out["treatment_date"], errors="coerce")
    out["month"] = treatment_date.dt.month
    out["season"] = season_from_month(out["month"])
    out["narrative_mechanism"] = out["narrative"].map(classify_mechanism)
    return out


def flow_row(step: str, df: pd.DataFrame, config: dict) -> dict:
    mask = np.ones(len(df), dtype=bool)
    est, se, cv = design_total_cv(df, mask) if len(df) else (0.0, None, None)
    return {
        "step": step,
        "unweighted_n": int(len(df)),
        "weighted_estimate": est,
        "se": se,
        "cv": cv,
        "instability_flag": instability_flag(int(len(df)), est, cv, config),
    }


def collapse_other_if_sparse(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    min_n = int(config["study"]["other_selected_ball_sports_min_unweighted_n"])
    out = df.copy()
    n_other = int((out["sport_group"] == "other selected ball sports").sum())
    if 0 < n_other < min_n:
        out = out[out["sport_group"] != "other selected ball sports"].copy()
    return out


def build_main(df: pd.DataFrame, config: dict, mappings: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    years = config["study"]["years"]
    finger = int(mappings["body_part"]["finger"]["code"])
    fracture = int(mappings["diagnosis"]["fracture"]["code"])
    dislocation = int(mappings["diagnosis"]["dislocation"]["code"])
    flow = []

    d0 = df.copy()
    flow.append(flow_row("All NEISS records in downloaded files", d0, config))
    d1 = d0[d0["year"].isin(years)].copy()
    flow.append(flow_row("Treatment year 2015-2025", d1, config))
    d2 = d1[d1["age"].between(config["study"]["age_min"], config["study"]["age_max"])].copy()
    flow.append(flow_row("Age 10-18 years", d2, config))
    d3 = d2[d2["body_part"] == finger].copy()
    flow.append(flow_row("Primary body part is finger", d3, config))
    d4 = d3[d3["diagnosis"].isin([fracture, dislocation])].copy()
    flow.append(flow_row("Primary diagnosis is fracture or dislocation", d4, config))
    d4 = assign_sport(d4, mappings, include_product3=False)
    d5 = d4[d4["sport_group"].notna()].copy()
    d5 = collapse_other_if_sparse(d5, config)
    flow.append(flow_row("Product_1 or Product_2 is a verified selected ball sport", d5, config))
    essential = [
        "case_id",
        "treatment_date",
        "age",
        "body_part",
        "diagnosis",
        "sport_group",
        "weight",
        "stratum",
        "psu",
    ]
    d6 = d5.dropna(subset=essential).copy()
    flow.append(flow_row("Missing essential fields excluded", d6, config))
    if config["study"].get("exclude_obvious_nonparticipants", True):
        bystander = nonparticipant_mask(d6["narrative"])
        d7 = d6[~bystander].copy()
        flow.append(flow_row("Obvious spectator/bystander narratives excluded", d7, config))
    else:
        d7 = d6.copy()
    d7 = add_derived(d7, mappings)
    return d7, pd.DataFrame(flow)


def build_sensitivity(df: pd.DataFrame, config: dict, mappings: dict) -> pd.DataFrame:
    finger = int(mappings["body_part"]["finger"]["code"])
    fracture = int(mappings["diagnosis"]["fracture"]["code"])
    dislocation = int(mappings["diagnosis"]["dislocation"]["code"])
    d = df[df["year"].between(2019, 2025) & df["age"].between(10, 18)].copy()
    body_mask = (d["body_part"] == finger) | (d["body_part_2"] == finger)
    diag_mask = d["diagnosis"].isin([fracture, dislocation]) | d["diagnosis_2"].isin([fracture, dislocation])
    d = d[body_mask & diag_mask].copy()
    d = assign_sport(d, mappings, include_product3=True)
    d = d[d["sport_group"].notna()].copy()
    if config["study"].get("exclude_obvious_nonparticipants", True):
        d = d[~nonparticipant_mask(d["narrative"])].copy()

    # For sensitivity records where only the secondary diagnosis matches, use that
    # diagnosis to define the diagnosis group.
    use_secondary = ~d["diagnosis"].isin([fracture, dislocation]) & d["diagnosis_2"].isin([fracture, dislocation])
    d.loc[use_secondary, "diagnosis"] = d.loc[use_secondary, "diagnosis_2"]
    d = d.dropna(subset=["case_id", "treatment_date", "age", "diagnosis", "sport_group", "weight"]).copy()
    d = add_derived(d, mappings)
    return d


def write_missingness(df: pd.DataFrame) -> None:
    rows = []
    for col in df.columns:
        rows.append({"variable": col, "missing_n": int(df[col].isna().sum()), "missing_percent": float(df[col].isna().mean())})
    pd.DataFrame(rows).to_csv(REPORT_DIR / "missingness_summary.csv", index=False)


def main() -> None:
    ensure_dirs()
    config = load_config()
    mappings = load_mappings()
    df = load_clean_years([int(y) for y in config["study"]["years"]])
    main_cohort, flow = build_main(df, config, mappings)
    sensitivity = build_sensitivity(df, config, mappings)

    main_cohort.to_csv(PROCESSED_DIR / "cohort_main.csv", index=False)
    sensitivity.to_csv(PROCESSED_DIR / "cohort_sensitivity_2019_2025.csv", index=False)
    flow.to_csv(REPORT_DIR / "cohort_flow.csv", index=False)
    write_missingness(main_cohort)

    analysis_decisions = [
        "# Analysis Decisions",
        "",
        "- Main cohort uses Body_Part, Diagnosis, Product_1, and Product_2 only.",
        "- Product_3, Body_Part_2, and Diagnosis_2 are used only for 2019-2025 sensitivity analysis.",
        f"- Obvious spectator/bystander exclusions enabled: {config['study'].get('exclude_obvious_nonparticipants', True)}.",
        "- Other selected ball sports are retained only as a combined category when the combined unweighted sample size meets the configured minimum.",
        "- Narrative mechanism is descriptive and not used as a primary 2015-2025 trend variable.",
        "",
        f"- Main cohort unweighted n: {len(main_cohort)}",
        f"- Main cohort weighted estimate: {weighted_total(main_cohort):.0f}",
        f"- Sensitivity cohort unweighted n: {len(sensitivity)}",
        f"- Sensitivity cohort weighted estimate: {weighted_total(sensitivity):.0f}",
    ]
    (DOCS_DIR / "analysis_decisions.md").write_text("\n".join(analysis_decisions) + "\n", encoding="utf-8")
    print(f"Main cohort written: n={len(main_cohort)}, weighted={weighted_total(main_cohort):.0f}")


if __name__ == "__main__":
    main()
