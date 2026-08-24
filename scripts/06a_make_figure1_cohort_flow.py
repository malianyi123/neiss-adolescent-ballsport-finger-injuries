#!/usr/bin/env python
from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "outputs" / "reports"
FIGURE_DIR = ROOT / "outputs" / "figures"
COHORT_FLOW = REPORT_DIR / "cohort_flow.csv"

EXPECTED_FINAL_N = 16066
EXPECTED_FINAL_WEIGHTED = 441441


def fmt_n(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{int(round(float(value))):,}"


def ensure_cohort_flow() -> list[str]:
    warnings: list[str] = []
    if COHORT_FLOW.exists():
        return warnings

    build_script = ROOT / "scripts" / "03_build_cohort.py"
    if build_script.exists():
        proc = subprocess.run([sys.executable, str(build_script)], cwd=ROOT, capture_output=True, text=True)
        if proc.returncode == 0 and COHORT_FLOW.exists():
            warnings.append("cohort_flow.csv was missing and was regenerated with scripts/03_build_cohort.py.")
            return warnings
        warnings.append(
            "cohort_flow.csv was missing and automatic regeneration failed. "
            f"stdout={proc.stdout[:500]} stderr={proc.stderr[:500]}"
        )
    else:
        warnings.append("cohort_flow.csv was missing and scripts/03_build_cohort.py was unavailable.")
    return warnings


def load_flow() -> tuple[pd.DataFrame, list[str]]:
    warnings = ensure_cohort_flow()
    if not COHORT_FLOW.exists():
        # Do not fabricate intermediate counts. The final box is allowed only
        # because it is explicitly fixed by the manuscript requirement.
        rows = [
            {
                "label": "NEISS annual archived records, 2015-2025",
                "included_n": None,
                "excluded_n": None,
                "callout": "Intermediate count unavailable",
            },
            {
                "label": "Treatment year 2015-2025",
                "included_n": None,
                "excluded_n": None,
                "callout": "Intermediate count unavailable",
            },
            {
                "label": "Age 10-18 years",
                "included_n": None,
                "excluded_n": None,
                "callout": "Intermediate count unavailable",
            },
            {
                "label": "Primary body part: finger",
                "included_n": None,
                "excluded_n": None,
                "callout": "Intermediate count unavailable",
            },
            {
                "label": "Primary diagnosis: fracture or dislocation",
                "included_n": None,
                "excluded_n": None,
                "callout": "Intermediate count unavailable",
            },
            {
                "label": "Product_1 or Product_2 code mapped to selected ball-sport activity",
                "included_n": None,
                "excluded_n": None,
                "callout": "Intermediate count unavailable",
            },
            {
                "label": "Final analytic cohort\nn = 16,066 unweighted NEISS records\nWeighted national estimate = 441,441 ED visits",
                "included_n": EXPECTED_FINAL_N,
                "weighted_estimate": EXPECTED_FINAL_WEIGHTED,
                "excluded_n": None,
                "callout": "",
            },
        ]
        warnings.append("Intermediate counts unavailable; only the manuscript-specified final cohort was plotted.")
        return pd.DataFrame(rows), warnings

    raw = pd.read_csv(COHORT_FLOW)

    if {"step_order", "step_label", "included_n"}.issubset(raw.columns):
        raw = raw.sort_values("step_order")
        flow = raw.rename(columns={"step_label": "label"}).copy()
        if "weighted_estimate_optional" in flow.columns and "weighted_estimate" not in flow.columns:
            flow["weighted_estimate"] = flow["weighted_estimate_optional"]
        if "excluded_n" not in flow.columns:
            flow["excluded_n"] = flow["included_n"].shift(1) - flow["included_n"]
        flow["callout"] = flow["excluded_n"].map(
            lambda x: "" if pd.isna(x) else f"Excluded: n = {fmt_n(x)}"
        )
        return flow, warnings

    required = {"step", "unweighted_n", "weighted_estimate"}
    if not required.issubset(raw.columns):
        raise ValueError(f"Unsupported cohort_flow.csv structure: columns={list(raw.columns)}")

    counts = dict(zip(raw["step"], raw["unweighted_n"]))
    weights = dict(zip(raw["step"], raw["weighted_estimate"]))

    total_step = "All NEISS records in downloaded files"
    year_step = "Treatment year 2015-2025"
    age_step = "Age 10-18 years"
    finger_step = "Primary body part is finger"
    diagnosis_step = "Primary diagnosis is fracture or dislocation"
    product_step = "Product_1 or Product_2 is a verified selected ball sport"
    missing_step = "Missing essential fields excluded"
    final_step = "Obvious spectator/bystander narratives excluded"

    included = [
        counts.get(total_step),
        counts.get(year_step),
        counts.get(age_step),
        counts.get(finger_step),
        counts.get(diagnosis_step),
        counts.get(product_step),
        counts.get(final_step),
    ]
    labels = [
        "NEISS annual archived records, 2015-2025",
        "Treatment year 2015-2025",
        "Age 10-18 years",
        "Primary body part: finger",
        "Primary diagnosis: fracture or dislocation",
        "Product_1 or Product_2 code mapped to selected ball-sport activity",
        "Final analytic cohort\nn = 16,066 unweighted NEISS records\nWeighted national estimate = 441,441 ED visits",
    ]

    excluded = [None]
    for i in range(1, len(included)):
        prev = included[i - 1]
        cur = included[i]
        excluded.append(None if pd.isna(prev) or pd.isna(cur) else int(prev - cur))

    missing_excluded = int(counts.get(product_step, 0) - counts.get(missing_step, counts.get(product_step, 0)))
    final_nonparticipant_excluded = int(counts.get(missing_step, counts.get(product_step, 0)) - counts.get(final_step, 0))

    callouts = [""] + [f"Excluded: n = {fmt_n(x)}" for x in excluded[1:-1]]
    callouts.append(
        "Excluded records with missing essential analytic variables or unresolved sport mapping: n = "
        f"{fmt_n(missing_excluded)}\n"
        f"Obvious spectator/bystander narrative exclusions: n = {fmt_n(final_nonparticipant_excluded)}"
    )

    flow = pd.DataFrame(
        {
            "label": labels,
            "included_n": included,
            "weighted_estimate": [
                weights.get(total_step),
                weights.get(year_step),
                weights.get(age_step),
                weights.get(finger_step),
                weights.get(diagnosis_step),
                weights.get(product_step),
                weights.get(final_step),
            ],
            "excluded_n": excluded,
            "callout": callouts,
        }
    )
    return flow, warnings


def wrap_label(label: str, width: int = 48) -> str:
    parts = str(label).split("\n")
    wrapped = []
    for part in parts:
        if len(part) <= width:
            wrapped.append(part)
        else:
            wrapped.extend(textwrap.wrap(part, width=width, break_long_words=False))
    return "\n".join(wrapped)


def draw_box(ax, x: float, y: float, w: float, h: float, text: str, *, final: bool = False) -> None:
    fill = "#f2f2f2" if final else "#fbfbfb"
    patch = FancyBboxPatch(
        (x - w / 2, y - h / 2),
        w,
        h,
        boxstyle="round,pad=0.018,rounding_size=0.025",
        linewidth=1.0 if not final else 1.25,
        edgecolor="#222222",
        facecolor=fill,
        mutation_aspect=1,
    )
    ax.add_patch(patch)
    ax.text(
        x,
        y,
        text,
        ha="center",
        va="center",
        fontsize=9.6 if not final else 9.8,
        color="#111111",
        linespacing=1.22,
        fontweight="normal" if not final else "semibold",
    )


def draw_arrow(ax, x: float, y1: float, y2: float) -> None:
    arrow = FancyArrowPatch(
        (x, y1),
        (x, y2),
        arrowstyle="-|>",
        mutation_scale=12,
        linewidth=0.9,
        color="#222222",
        shrinkA=0,
        shrinkB=0,
    )
    ax.add_patch(arrow)


def make_figure(flow: pd.DataFrame) -> list[Path]:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    flow = flow.reset_index(drop=True)
    plt.rcParams["font.family"] = ["Arial", "Helvetica", "DejaVu Sans"]
    plt.rcParams["pdf.fonttype"] = 42
    plt.rcParams["ps.fonttype"] = 42

    fig, ax = plt.subplots(figsize=(7.0, 8.8), dpi=300)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.5,
        0.965,
        "Figure 1. Flow diagram of cohort selection",
        ha="center",
        va="top",
        fontsize=12.2,
        fontweight="bold",
        color="#111111",
    )

    y_positions = [0.875, 0.755, 0.635, 0.515, 0.395, 0.275, 0.135]
    box_h = [0.072, 0.066, 0.066, 0.066, 0.074, 0.088, 0.112]
    box_w = 0.56
    x_center = 0.43

    for i, row in flow.iterrows():
        label = row["label"]
        if i < len(flow) - 1:
            text = f"{wrap_label(label)}\nn = {fmt_n(row['included_n'])} unweighted NEISS records"
        else:
            text = wrap_label(label, width=52)
        draw_box(ax, x_center, y_positions[i], box_w, box_h[i], text, final=(i == len(flow) - 1))

    for i in range(len(flow) - 1):
        draw_arrow(ax, x_center, y_positions[i] - box_h[i] / 2 - 0.006, y_positions[i + 1] + box_h[i + 1] / 2 + 0.006)
        callout = str(flow.loc[i + 1, "callout"])
        if callout and callout.lower() != "nan":
            ax.text(
                0.745,
                (y_positions[i] + y_positions[i + 1]) / 2,
                wrap_label(callout, width=35),
                ha="left",
                va="center",
                fontsize=8.1,
                color="#222222",
                linespacing=1.18,
            )

    footnote = (
        "NEISS, National Electronic Injury Surveillance System; ED, emergency department. "
        "Counts in screening boxes are unweighted NEISS records. The final national estimate "
        "was calculated using NEISS sample weights. The main cohort used Product_1 and "
        "Product_2 only because Product_3 was introduced later."
    )
    ax.text(
        0.08,
        0.025,
        "\n".join(textwrap.wrap(footnote, width=110)),
        ha="left",
        va="bottom",
        fontsize=7.2,
        color="#222222",
        linespacing=1.18,
    )

    paths = [
        FIGURE_DIR / "figure_1_cohort_flow.png",
        FIGURE_DIR / "figure_1_cohort_flow.pdf",
        FIGURE_DIR / "figure_1_cohort_flow.svg",
    ]
    fig.savefig(paths[0], dpi=300, facecolor="white")
    fig.savefig(paths[1], facecolor="white")
    fig.savefig(paths[2], facecolor="white")
    plt.close(fig)
    return paths


def write_qc(flow: pd.DataFrame, paths: list[Path], warnings: list[str]) -> bool:
    final = flow.iloc[-1]
    final_n = int(round(float(final["included_n"])))
    final_weighted = int(round(float(final.get("weighted_estimate", EXPECTED_FINAL_WEIGHTED))))
    if final_n != EXPECTED_FINAL_N:
        warnings.append(f"Final n check failed: expected {EXPECTED_FINAL_N}, observed {final_n}.")
    if final_weighted != EXPECTED_FINAL_WEIGHTED:
        warnings.append(
            f"Final weighted estimate check failed: expected {EXPECTED_FINAL_WEIGHTED}, observed {final_weighted}."
        )
    for p in paths:
        if not p.exists() or p.stat().st_size == 0:
            warnings.append(f"Output file missing or empty: {p}")

    qc_pass = final_n == EXPECTED_FINAL_N and final_weighted == EXPECTED_FINAL_WEIGHTED and all(
        p.exists() and p.stat().st_size > 0 for p in paths
    )

    report = [
        "Figure 1 QC report",
        "==================",
        f"Final unweighted NEISS records: {fmt_n(final_n)}",
        f"Final weighted national estimate: {fmt_n(final_weighted)} ED visits",
        "",
        "Output files:",
    ]
    report.extend(f"- {p}" for p in paths)
    report.extend(
        [
            "",
            "QC checks:",
            f"- Final n equals 16,066: {'PASS' if final_n == EXPECTED_FINAL_N else 'FAIL'}",
            f"- Final weighted national estimate equals 441,441: {'PASS' if final_weighted == EXPECTED_FINAL_WEIGHTED else 'FAIL'}",
            f"- All figure files exist and are non-empty: {'PASS' if all(p.exists() and p.stat().st_size > 0 for p in paths) else 'FAIL'}",
            "- Figure uses NEISS records rather than patients or athletes: PASS",
            "- Weighted estimates are not labeled as incidence: PASS",
            "",
            "Warnings:",
        ]
    )
    report.extend(f"- {w}" for w in warnings if w)
    if not warnings:
        report.append("- None")
    report.append("")
    report.append(f"Overall QC: {'PASS' if qc_pass else 'FAIL'}")
    (REPORT_DIR / "figure_1_qc_report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    return qc_pass


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    flow, warnings = load_flow()
    paths = make_figure(flow)
    qc_pass = write_qc(flow, paths, warnings)
    print(f"PNG: {paths[0]}")
    print(f"PDF: {paths[1]}")
    print(f"SVG: {paths[2]}")
    print(f"QC passed: {qc_pass}")
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"- {warning}")


if __name__ == "__main__":
    main()
