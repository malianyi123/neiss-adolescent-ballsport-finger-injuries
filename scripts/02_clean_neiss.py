#!/usr/bin/env python
from __future__ import annotations

import pandas as pd

from utils import (
    REPORT_DIR,
    annual_raw_path,
    assert_all_years_present,
    clean_numeric_code,
    clean_year_path,
    count_lines,
    ensure_dirs,
    load_config,
    load_mappings,
    parse_treatment_date,
    read_raw_neiss,
    standardize_columns,
    to_numeric,
)


def clean_one_year(year: int) -> dict:
    raw_path = annual_raw_path(year)
    df_raw = read_raw_neiss(raw_path)
    raw_columns = list(df_raw.columns)
    df = standardize_columns(df_raw)
    df["source_year"] = int(year)
    df["treatment_date"] = parse_treatment_date(df["treatment_date"])
    df["year"] = df["treatment_date"].dt.year

    for col in [
        "age",
        "sex",
        "race",
        "hispanic",
        "body_part",
        "diagnosis",
        "body_part_2",
        "diagnosis_2",
        "disposition",
        "location",
        "product_1",
        "product_2",
        "product_3",
        "psu",
    ]:
        df[col] = clean_numeric_code(df[col])
    df["weight"] = to_numeric(df["weight"])
    df["case_id"] = df["case_id"].astype(str).str.strip()
    df["stratum"] = df["stratum"].astype(str).str.strip().replace({"": pd.NA, "nan": pd.NA})
    df["narrative"] = df["narrative"].fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip()

    cols = [
        "case_id",
        "treatment_date",
        "year",
        "source_year",
        "age",
        "sex",
        "race",
        "hispanic",
        "body_part",
        "diagnosis",
        "body_part_2",
        "diagnosis_2",
        "disposition",
        "location",
        "product_1",
        "product_2",
        "product_3",
        "narrative",
        "weight",
        "stratum",
        "psu",
    ]
    out = df[cols].copy()
    clean_path = clean_year_path(year)
    out.to_csv(clean_path, index=False)

    return {
        "year": year,
        "raw_file": str(raw_path),
        "clean_file": str(clean_path),
        "row_count_by_read": len(df_raw),
        "row_count_by_line_count": count_lines(raw_path),
        "column_count": len(raw_columns),
        "column_names": "|".join(raw_columns),
        "date_year_mismatch_n": int(((df["year"].notna()) & (df["year"] != year)).sum()),
        "missing_treatment_date_n": int(df["treatment_date"].isna().sum()),
        "missing_weight_n": int(df["weight"].isna().sum()),
        "nonpositive_weight_n": int((df["weight"].fillna(0) <= 0).sum()),
        "min_age": float(df["age"].min(skipna=True)) if df["age"].notna().any() else None,
        "max_age": float(df["age"].max(skipna=True)) if df["age"].notna().any() else None,
    }


def main() -> None:
    ensure_dirs()
    config = load_config()
    load_mappings()
    years = [int(y) for y in config["study"]["years"]]
    assert_all_years_present(years)

    rows = []
    for year in years:
        print(f"Cleaning {year}")
        rows.append(clean_one_year(year))

    inventory = pd.DataFrame(rows)
    inventory["source_url"] = inventory["year"].map(
        lambda y: config["sources"]["annual_tsv_url_template"].format(year=int(y))
    )
    inventory.to_csv(REPORT_DIR / "data_inventory.csv", index=False)
    inventory.to_csv(REPORT_DIR / "qc_cleaning.csv", index=False)

    failures = inventory[
        (inventory["date_year_mismatch_n"] > 0)
        | (inventory["missing_weight_n"] > 0)
        | (inventory["nonpositive_weight_n"] > 0)
    ]
    if not failures.empty:
        print("QC warnings found; see outputs/reports/qc_cleaning.csv")
    print("Clean annual files written to data/intermediate/")


if __name__ == "__main__":
    main()
