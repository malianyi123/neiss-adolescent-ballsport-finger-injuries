#!/usr/bin/env python
from __future__ import annotations

import textwrap
import subprocess
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from utils import FIGURE_DIR, REPORT_DIR, ROOT, SUPPLEMENT_DIR, ensure_dirs, format_int, safe_read_csv


PALETTE = {
    "blue": "#2F6F9F",
    "teal": "#2A9D8F",
    "gold": "#E9C46A",
    "red": "#C65D4E",
    "ink": "#263238",
    "gray": "#7A8691",
    "light": "#EEF2F5",
}


def savefig(name: str, supplementary: bool = False) -> None:
    outdir = SUPPLEMENT_DIR / "supplementary_figures" if supplementary else FIGURE_DIR
    outdir.mkdir(parents=True, exist_ok=True)
    for ext in ["png", "pdf"]:
        plt.savefig(outdir / f"{name}.{ext}", dpi=300, bbox_inches="tight")
    plt.close()


def style() -> None:
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "ggplot")
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "figure.titlesize": 13,
            "axes.edgecolor": "#9AA4AD",
            "grid.color": "#DDE3E8",
            "savefig.facecolor": "white",
        }
    )


def figure_flow() -> None:
    script = ROOT / "scripts" / "06a_make_figure1_cohort_flow.py"
    subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True)


def figure_annual() -> None:
    annual = safe_read_csv(REPORT_DIR / "annual_estimates.csv")
    if annual.empty:
        return
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.axvspan(2020 - 0.5, 2021 + 0.5, color=PALETTE["gold"], alpha=0.25, label="2020-2021")
    yerr = annual["se"] if "se" in annual else None
    ax.errorbar(
        annual["year"],
        annual["weighted_estimate"],
        yerr=yerr,
        color=PALETTE["blue"],
        marker="o",
        linewidth=2,
        capsize=3,
    )
    ax.set_xlabel("Treatment year")
    ax.set_ylabel("Weighted national ED visits")
    ax.set_title("Figure 2. Annual weighted national estimates, 2015-2025")
    ax.yaxis.set_major_formatter(lambda x, pos: f"{x:,.0f}")
    ax.set_xticks(annual["year"].astype(int))
    ax.tick_params(axis="x", rotation=45)
    ax.legend(frameon=False)
    savefig("figure_2_annual_weighted_estimates")


def figure_sport_distribution() -> None:
    sport = safe_read_csv(REPORT_DIR / "sport_patterns.csv")
    if sport.empty:
        return
    sport = sport.sort_values("weighted_estimate")
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.barh(sport["sport_group"], sport["weighted_estimate"], color=PALETTE["teal"])
    ax.set_xlabel("Weighted national ED visits")
    ax.set_ylabel("")
    ax.set_title("Figure 3. Sport-group distribution")
    ax.xaxis.set_major_formatter(lambda x, pos: f"{x:,.0f}")
    for i, val in enumerate(sport["weighted_estimate"]):
        ax.text(val, i, f" {val:,.0f}", va="center", fontsize=9)
    savefig("figure_3_sport_group_distribution")


def figure_diagnosis_pattern() -> None:
    diag = safe_read_csv(REPORT_DIR / "diagnosis_by_sport.csv")
    if diag.empty:
        return
    pivot = diag.pivot(index="sport_group", columns="diagnosis_group", values="weighted_percent_within_sport").fillna(0)
    for col in ["fracture", "dislocation"]:
        if col not in pivot:
            pivot[col] = 0
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    left = np.zeros(len(pivot))
    colors = {"fracture": PALETTE["blue"], "dislocation": PALETTE["red"]}
    for col in ["fracture", "dislocation"]:
        ax.barh(pivot.index, pivot[col], left=left, label=col, color=colors[col])
        left += pivot[col].to_numpy()
    ax.set_xlim(0, 1)
    ax.set_xlabel("Weighted percentage within sport")
    ax.set_ylabel("")
    ax.set_title("Figure 4. Sport-specific diagnosis pattern")
    ax.xaxis.set_major_formatter(lambda x, pos: f"{x * 100:.0f}%")
    ax.legend(frameon=False, loc="lower right")
    savefig("figure_4_sport_specific_diagnosis_pattern")


def figure_forest() -> None:
    model = safe_read_csv(REPORT_DIR / "model_dislocation_vs_fracture.csv")
    if model.empty:
        return
    model = model[~model["term"].astype(str).str.contains("year_centered", regex=False)].copy()
    if model.empty:
        return
    labels = model["term"].astype(str).str.replace("C\\(|\\)|T\\.|\\[|\\]", "", regex=True)
    y = np.arange(len(model))
    fig, ax = plt.subplots(figsize=(8, max(4, len(model) * 0.32)))
    ax.errorbar(
        model["adjusted_or"],
        y,
        xerr=[model["adjusted_or"] - model["ci_low"], model["ci_high"] - model["adjusted_or"]],
        fmt="o",
        color=PALETTE["blue"],
        ecolor=PALETTE["gray"],
        capsize=3,
    )
    ax.axvline(1, color=PALETTE["red"], linestyle="--", linewidth=1)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xscale("log")
    ax.set_xlabel("Adjusted odds ratio for dislocation vs fracture")
    ax.set_title("Figure 5. Adjusted model for dislocation vs fracture")
    savefig("figure_5_forest_plot_dislocation_model")


def supplementary_season() -> None:
    season = safe_read_csv(REPORT_DIR / "season_summary.csv")
    month = safe_read_csv(REPORT_DIR / "month_summary.csv")
    if not season.empty:
        fig, ax = plt.subplots(figsize=(6, 4))
        order = ["winter", "spring", "summer", "fall"]
        season = season.set_index("label").reindex(order).dropna(subset=["weighted_estimate"]).reset_index()
        ax.bar(season["label"], season["weighted_estimate"], color=PALETTE["gold"])
        ax.set_xlabel("Season")
        ax.set_ylabel("Weighted national ED visits")
        ax.set_title("Supplementary Figure. Seasonal distribution")
        ax.yaxis.set_major_formatter(lambda x, pos: f"{x:,.0f}")
        savefig("supplementary_seasonal_distribution", supplementary=True)
    if not month.empty:
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot(month["month"], month["weighted_estimate"], marker="o", color=PALETTE["blue"])
        ax.set_xticks(range(1, 13))
        ax.set_xlabel("Treatment month")
        ax.set_ylabel("Weighted national ED visits")
        ax.set_title("Supplementary Figure. Monthly distribution")
        ax.yaxis.set_major_formatter(lambda x, pos: f"{x:,.0f}")
        savefig("supplementary_monthly_distribution", supplementary=True)


def supplementary_narrative() -> None:
    narr = safe_read_csv(REPORT_DIR / "narrative_mechanism_2019_2025.csv")
    if narr.empty:
        return
    narr = narr.sort_values("weighted_estimate")
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.barh(narr["label"], narr["weighted_estimate"], color=PALETTE["teal"])
    ax.set_xlabel("Weighted national ED visits, 2019-2025")
    ax.set_ylabel("")
    ax.set_title("Supplementary Figure. Narrative mechanism distribution")
    ax.xaxis.set_major_formatter(lambda x, pos: f"{x:,.0f}")
    savefig("supplementary_narrative_mechanism_2019_2025", supplementary=True)


def supplementary_sensitivity() -> None:
    sens = safe_read_csv(REPORT_DIR / "sensitivity_summary.csv")
    if sens.empty:
        return
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.barh(sens["cohort"], sens["weighted_estimate"], color=[PALETTE["blue"], PALETTE["red"]][: len(sens)])
    ax.set_xlabel("Weighted national ED visits")
    ax.set_ylabel("")
    ax.set_title("Supplementary Figure. 2019-2025 sensitivity cohort")
    ax.xaxis.set_major_formatter(lambda x, pos: f"{x:,.0f}")
    savefig("supplementary_sensitivity_2019_2025", supplementary=True)


def main() -> None:
    ensure_dirs()
    style()
    figure_flow()
    figure_annual()
    figure_sport_distribution()
    figure_diagnosis_pattern()
    figure_forest()
    supplementary_season()
    supplementary_narrative()
    supplementary_sensitivity()
    print("Figures written to outputs/figures and outputs/supplementary/supplementary_figures")


if __name__ == "__main__":
    main()
