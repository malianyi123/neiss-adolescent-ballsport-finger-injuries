#!/usr/bin/env python
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from utils import (
    CONFIG_DIR,
    DOCS_DIR,
    RAW_DIR,
    REPORT_DIR,
    curl_download,
    ensure_dirs,
    load_config,
    now_utc,
    write_yaml,
)


def parse_format_file(path: Path) -> dict[str, dict[str, str]]:
    df = pd.read_csv(path, sep="\t", dtype=str)
    fmt_col = "Format name"
    start_col = "Starting value for format"
    label_col = "Format value label"
    out: dict[str, dict[str, str]] = {}
    for _, row in df.iterrows():
        fmt = str(row.get(fmt_col, "")).strip().upper()
        code = str(row.get(start_col, "")).strip()
        label = str(row.get(label_col, "")).strip()
        if not fmt or not code or code == "." or not re.match(r"^-?\d+$", code):
            continue
        out.setdefault(fmt, {})[str(int(code))] = label
    return out


def dictionary_mentions(path: Path, pattern: str) -> list[str]:
    hits: list[str] = []
    xl = pd.ExcelFile(path)
    for sheet in xl.sheet_names:
        df = pd.read_excel(path, sheet_name=sheet, header=None, dtype=str)
        for _, row in df.iterrows():
            text = " | ".join("" if pd.isna(x) else str(x) for x in row)
            if re.search(pattern, text, re.I):
                hits.append(f"{sheet}: {text}")
    return hits


def validate_label(label: str, contains: str | None = None, contains_any: list[str] | None = None) -> bool:
    upper = label.upper()
    if contains:
        return contains.upper() in upper
    if contains_any:
        return any(x.upper() in upper for x in contains_any)
    return bool(label)


def main() -> None:
    ensure_dirs()
    config = load_config()
    dict_path = RAW_DIR / "DataDictionary042022.xlsx"
    fmt_path = RAW_DIR / "neiss_fmt.txt"
    if not dict_path.exists():
        ok, msg = curl_download(config["sources"]["data_dictionary_url"], dict_path)
        if not ok:
            raise FileNotFoundError(f"Could not download official data dictionary: {msg}")
    if not fmt_path.exists():
        ok, msg = curl_download(config["sources"]["format_file_url"], fmt_path)
        if not ok:
            raise FileNotFoundError(f"Could not download NEISS format file: {msg}")

    formats = parse_format_file(fmt_path)
    validation_rows = []
    errors = []

    body_part = {}
    for name, spec in config["official_codes_to_validate"]["body_part"].items():
        code = str(spec["code"])
        label = formats.get("BDYPT", {}).get(code, "")
        ok = validate_label(label, contains=spec.get("expected_label_contains"))
        validation_rows.append(
            {"domain": "body_part", "name": name, "code": code, "label": label, "validated": ok}
        )
        if not ok:
            errors.append(f"Body-part code {code} for {name} not verified. Label: {label}")
        body_part[name] = {"code": int(code), "label": label}

    diagnosis = {}
    for name, spec in config["official_codes_to_validate"]["diagnosis"].items():
        code = str(spec["code"])
        label = formats.get("DIAG", {}).get(code, "")
        ok = validate_label(label, contains=spec.get("expected_label_contains"))
        validation_rows.append(
            {"domain": "diagnosis", "name": name, "code": code, "label": label, "validated": ok}
        )
        if not ok:
            errors.append(f"Diagnosis code {code} for {name} not verified. Label: {label}")
        diagnosis[name] = {"code": int(code), "label": label}

    sport_groups = {}
    for group, spec in config["sport_code_candidates"].items():
        label = spec.get("label", group.replace("_", " "))
        entries = []
        for code_int in spec["codes"]:
            code = str(int(code_int))
            prod_label = formats.get("PROD", {}).get(code, "")
            ok = validate_label(
                prod_label,
                contains=spec.get("expected_label_contains"),
                contains_any=spec.get("expected_label_contains_any"),
            )
            validation_rows.append(
                {
                    "domain": "product",
                    "name": group,
                    "code": code,
                    "label": prod_label,
                    "validated": ok,
                }
            )
            if not ok:
                errors.append(f"Product code {code} for {group} not verified. Label: {prod_label}")
            entries.append({"code": int(code), "label": prod_label})
        sport_groups[group] = {"label": label, "codes": entries}

    for family, fmt in [
        ("sex", "SEX"),
        ("race", "RACE"),
        ("hispanic", "HISPANIC"),
        ("disposition", "DISP"),
        ("location", "LOC"),
    ]:
        if fmt in formats:
            for code, label in formats[fmt].items():
                validation_rows.append(
                    {"domain": family, "name": family, "code": code, "label": label, "validated": True}
                )

    pd.DataFrame(validation_rows).to_csv(REPORT_DIR / "code_mapping_validation.csv", index=False)
    if errors:
        report = "# Validation Report\n\nOfficial-code validation failed.\n\n" + "\n".join(
            f"- {e}" for e in errors
        )
        (DOCS_DIR / "validation_report.md").write_text(report + "\n", encoding="utf-8")
        raise SystemExit(report)

    mappings = {
        "validated": True,
        "validated_utc": now_utc(),
        "sources": {
            "data_dictionary_file": str(dict_path),
            "format_file": str(fmt_path),
            "data_dictionary_url": config["sources"]["data_dictionary_url"],
            "format_file_url": config["sources"]["format_file_url"],
        },
        "body_part": body_part,
        "diagnosis": diagnosis,
        "sport_groups": sport_groups,
        "sex": formats.get("SEX", {}),
        "race": formats.get("RACE", {}),
        "hispanic": formats.get("HISPANIC", {}),
        "disposition": formats.get("DISP", {}),
        "location": formats.get("LOC", {}),
        "all_product_labels": formats.get("PROD", {}),
    }
    write_yaml(mappings, CONFIG_DIR / "code_mappings_reviewed.yml")

    hits = {
        "finger": dictionary_mentions(dict_path, r"92\s*-\s*Finger"),
        "fracture": dictionary_mentions(dict_path, r"57\s*-\s*Fracture"),
        "dislocation": dictionary_mentions(dict_path, r"55\s*-\s*Dislocation"),
        "2019_additions": dictionary_mentions(dict_path, r"2019|Product_3|Diagnosis_2|Body_Part_2"),
    }
    report_lines = [
        "# Validation Report",
        "",
        "Official CPSC NEISS dictionary and format-file validation completed successfully.",
        "",
        f"- Validation timestamp UTC: {now_utc()}",
        f"- Data dictionary: `{dict_path}`",
        f"- Format file: `{fmt_path}`",
        "",
        "## Core Codes",
        "",
        f"- Finger body-part code: `{body_part['finger']['code']}` ({body_part['finger']['label']})",
        f"- Fracture diagnosis code: `{diagnosis['fracture']['code']}` ({diagnosis['fracture']['label']})",
        f"- Dislocation diagnosis code: `{diagnosis['dislocation']['code']}` ({diagnosis['dislocation']['label']})",
        "",
        "## Selected Sport Product Codes",
        "",
    ]
    for group, meta in sport_groups.items():
        report_lines.append(f"### {meta['label']}")
        for item in meta["codes"]:
            report_lines.append(f"- `{item['code']}`: {item['label']}")
        report_lines.append("")
    report_lines.extend(
        [
            "## Dictionary Mentions Used for Validation",
            "",
        ]
    )
    for key, values in hits.items():
        report_lines.append(f"### {key}")
        for v in values:
            report_lines.append(f"- {v}")
        report_lines.append("")
    report_lines.append("No unverified code or label was used in cohort construction.")
    (DOCS_DIR / "validation_report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    codebook_lines = ["# Codebook Used", ""]
    for row in validation_rows:
        if row["domain"] in {"body_part", "diagnosis", "product", "sex", "race", "hispanic", "disposition", "location"}:
            codebook_lines.append(
                f"- {row['domain']} / {row['name']} / `{row['code']}`: {row['label']}"
            )
    (DOCS_DIR / "codebook_used.md").write_text("\n".join(codebook_lines) + "\n", encoding="utf-8")
    print("Official code mappings validated and written to config/code_mappings_reviewed.yml")


if __name__ == "__main__":
    main()
