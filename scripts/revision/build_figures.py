"""Regenerate the five main figures per Reviewer 1's minor comments."""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P

P.ensure_dirs()
OUT = P.RESULTS_DIR
FIG = P.FIGURE_DIR

PALETTE = {
    "blue": "#2F6F9F", "teal": "#2A9D8F", "gold": "#E9C46A",
    "red": "#C65D4E", "ink": "#263238", "gray": "#7A8691", "light": "#EEF2F5",
}
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9.5, "axes.titlesize": 11,
    "axes.labelsize": 10, "axes.edgecolor": "#9AA4AD", "grid.color": "#DDE3E8",
    "savefig.facecolor": "white", "axes.spines.top": False, "axes.spines.right": False,
})


def save(name):
    for ext in ("png", "pdf"):
        plt.savefig(FIG / f"{name}.{ext}", dpi=300, bbox_inches="tight")
    plt.close()


# ============================================================ Figure 1: flow
def figure1():
    steps = [
        ("NEISS annual archived records\nscreened, 2015-2025", "3,924,911", None),
        ("Treatment year 2015-2025", "3,924,903", "8 outside study period"),
        ("Age 10-18 years", "732,983", "3,191,920 outside age range"),
        ("Primary body part: finger", "73,419", "659,564 other body part"),
        ("Primary diagnosis:\nfracture or dislocation", "24,363", "49,056 other diagnosis"),
        ("Verified selected ball-sport code\nin Product_1 or Product_2", "16,069", "8,294 no verified\nball-sport code"),
        ("Final analytic cohort", "16,066", "3 spectator/bystander\nnarratives"),
    ]
    fig, ax = plt.subplots(figsize=(7.6, 9.9))
    ax.set_xlim(0, 10); ax.set_ylim(-6, 10 * len(steps) + 6); ax.axis("off")
    bw, bh, cx = 4.6, 6.4, 3.0
    ys = [10 * len(steps) - i * 10 for i in range(len(steps))]

    for i, ((label, count, excl), y) in enumerate(zip(steps, ys)):
        final = i == len(steps) - 1
        box = FancyBboxPatch(
            (cx - bw / 2, y - bh / 2), bw, bh,
            boxstyle="round,pad=0.25,rounding_size=0.35",
            facecolor=PALETTE["blue"] if final else PALETTE["light"],
            edgecolor=PALETTE["blue"], linewidth=1.6 if final else 1.1, zorder=3)
        ax.add_patch(box)
        tc = "white" if final else PALETTE["ink"]
        ax.text(cx, y + 1.15, label, ha="center", va="center", fontsize=9.2,
                color=tc, fontweight="bold" if final else "normal", zorder=4)
        ax.text(cx, y - 1.5, f"n = {count}", ha="center", va="center", fontsize=10.5,
                color=tc, fontweight="bold", zorder=4)
        if i < len(steps) - 1:
            ax.add_patch(FancyArrowPatch(
                (cx, y - bh / 2), (cx, ys[i + 1] + bh / 2),
                arrowstyle="-|>", mutation_scale=13, linewidth=1.3,
                color=PALETTE["gray"], zorder=2))
        if excl:
            my = y + 5.0
            ax.annotate("", xy=(cx + bw / 2 + 2.6, my), xytext=(cx, my),
                        arrowprops=dict(arrowstyle="-|>", color=PALETTE["red"],
                                        linewidth=1.1, mutation_scale=11))
            ax.text(cx + bw / 2 + 2.75, my, f"Excluded:\n{excl}", ha="left", va="center",
                    fontsize=8.2, color=PALETTE["red"])

    ax.text(cx, ys[-1] - bh / 2 - 3.6,
            "Weighted national estimate: 441,441 ED visits\n(95% CI 341,825-541,056)",
            ha="center", va="center", fontsize=9.8, color=PALETTE["ink"], fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.45", facecolor="white",
                      edgecolor=PALETTE["blue"], linewidth=1.3))
    ax.set_title("Figure 1. Cohort selection", loc="left", fontsize=12,
                 fontweight="bold", color=PALETTE["ink"], pad=14)
    save("figure_1_cohort_flow")


# ========================================================== Figure 2: annual
def figure2():
    ann = pd.read_csv(OUT / "annual_estimates_with_ci.csv")
    fig, ax = plt.subplots(figsize=(8.4, 5.0))
    ax.axvspan(2019.5, 2021.5, color=PALETTE["gold"], alpha=0.28, zorder=0)
    ax.text(2020.5, ann["ci_hi"].max() * 0.985,
            "COVID-19 pandemic\nperiod (2020-2021)", ha="center", va="top",
            fontsize=8.6, color="#8A6D0B", fontweight="bold", zorder=5)
    lo = ann["weighted_estimate"] - ann["ci_lo"]
    hi = ann["ci_hi"] - ann["weighted_estimate"]
    ax.errorbar(ann["year"], ann["weighted_estimate"], yerr=[lo, hi],
                fmt="o-", color=PALETTE["blue"], ecolor=PALETTE["blue"],
                elinewidth=1.2, capsize=3.5, markersize=5.5, linewidth=1.8, zorder=4)
    ax.set_xticks(ann["year"])
    ax.set_xlabel("Treatment year")
    ax.set_ylabel("Weighted national ED visit estimate")
    ax.set_ylim(0, ann["ci_hi"].max() * 1.08)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, p: f"{int(v):,}"))
    ax.grid(axis="y", alpha=0.6)
    ax.set_title("Figure 2. Annual weighted national estimates, 2015-2025",
                 loc="left", fontsize=12, fontweight="bold", color=PALETTE["ink"])
    ax.text(0.0, -0.185,
            "Error bars are 95% confidence intervals from standard errors estimated by Taylor linearization using the\n"
            "NEISS complex survey design. No significant linear trend across the period (-2.5%/year; 95% CI -5.0 to +0.1; p=0.064).",
            transform=ax.transAxes, fontsize=8.2, color=PALETTE["gray"], va="top")
    save("figure_2_annual_weighted_estimates")


# ===================================================== Figure 3: sport groups
def figure3():
    t1 = pd.read_csv(OUT / "table1_with_ci.csv")
    d = t1[t1.section == "Sport group"].copy()
    d["label"] = d["label"].replace({"other selected ball sports": "other selected ball\nand stick sports"})
    d = d.sort_values("weighted_estimate")
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    y = np.arange(len(d))
    ax.barh(y, d["weighted_estimate"], color=PALETTE["blue"], height=0.6, zorder=3)
    ax.errorbar(d["weighted_estimate"], y,
                xerr=[d["weighted_estimate"] - d["ci_lo"], d["ci_hi"] - d["weighted_estimate"]],
                fmt="none", ecolor=PALETTE["ink"], elinewidth=1.1, capsize=3.5, zorder=4)
    ax.set_yticks(y); ax.set_yticklabels(d["label"])
    for yi, (est, pct, hi) in enumerate(zip(d["weighted_estimate"], d["weighted_pct"], d["ci_hi"])):
        ax.text(hi + d["ci_hi"].max() * 0.015, yi, f"{int(est):,}  ({pct:.1f}%)",
                va="center", fontsize=9.2, color=PALETTE["ink"], fontweight="bold")
    ax.set_xlim(0, d["ci_hi"].max() * 1.30)
    ax.set_xlabel("Weighted national ED visit estimate")
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, p: f"{int(v):,}"))
    ax.grid(axis="x", alpha=0.6)
    ax.set_title("Figure 3. Sport-group distribution, 2015-2025",
                 loc="left", fontsize=12, fontweight="bold", color=PALETTE["ink"])
    ax.text(0.0, -0.19, "Bars show weighted national estimates with 95% confidence intervals; labels give the estimate and the\n"
                        "weighted percentage of the cohort. Estimates are ED visit burden, not participant-normalized rates.",
            transform=ax.transAxes, fontsize=8.2, color=PALETTE["gray"], va="top")
    save("figure_3_sport_group_distribution")


# ================================================== Figure 4: diagnosis by sport
def figure4():
    t2 = pd.read_csv(OUT / "table2_with_ci_and_severe_flags.csv")
    t2["sport_group"] = t2["sport_group"].replace(
        {"other selected ball sports": "other selected ball\nand stick sports"})
    d = t2.sort_values("dislocation_pct")
    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    y = np.arange(len(d))
    ax.barh(y, d["fracture_pct"], color=PALETTE["blue"], height=0.6, label="Fracture", zorder=3)
    ax.barh(y, d["dislocation_pct"], left=d["fracture_pct"], color=PALETTE["gold"],
            height=0.6, label="Dislocation", zorder=3)
    for yi, r in enumerate(d.itertuples()):
        ax.text(r.fracture_pct / 2, yi, f"{r.fracture_pct:.1f}%", ha="center", va="center",
                fontsize=9.2, color="white", fontweight="bold", zorder=5)
        ax.text(r.fracture_pct + r.dislocation_pct / 2, yi, f"{r.dislocation_pct:.1f}%",
                ha="center", va="center", fontsize=9.2, color=PALETTE["ink"],
                fontweight="bold", zorder=5)
        ax.text(102, yi, f"dislocation 95% CI {r.dislocation_ci}", va="center",
                fontsize=8.4, color=PALETTE["gray"])
    ax.set_yticks(y); ax.set_yticklabels(d["sport_group"])
    ax.set_xlim(0, 133); ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("Weighted percentage within sport group")
    ax.legend(loc="lower center", bbox_to_anchor=(0.38, -0.30), ncol=2, frameon=False)
    ax.grid(axis="x", alpha=0.5)
    ax.set_title("Figure 4. Sport-specific diagnosis pattern, 2015-2025",
                 loc="left", fontsize=12, fontweight="bold", color=PALETTE["ink"])
    ax.text(0.0, -0.36, "Percentages are weighted within sport group and sum to 100%. Dislocation intervals overlap substantially\n"
                        "across volleyball, football, and basketball; those differences are not statistically distinguishable.",
            transform=ax.transAxes, fontsize=8.2, color=PALETTE["gray"], va="top")
    save("figure_4_sport_specific_diagnosis_pattern")


# ==================================================== Figure 5: forest plot
def figure5():
    rows = [
        ("Baseball/softball", 0.66, 0.51, 0.86, "sport"),
        ("Basketball", 1.05, 0.92, 1.20, "sport"),
        ("Other ball and stick sports", 0.57, 0.41, 0.80, "sport"),
        ("Soccer", 0.82, 0.59, 1.13, "sport"),
        ("Volleyball", 1.26, 0.91, 1.75, "sport"),
        ("Age 13-15 years", 1.84, 1.59, 2.14, "age"),
        ("Age 16-18 years", 4.86, 3.94, 5.99, "age"),
        ("Sex: coded female", 0.57, 0.47, 0.70, "sex"),
        ("Treatment year, per year", 0.99, 0.96, 1.01, "year"),
    ]
    colors = {"sport": PALETTE["blue"], "age": PALETTE["teal"],
              "sex": PALETTE["red"], "year": PALETTE["gray"]}
    fig, (ax, axt) = plt.subplots(
        1, 2, figsize=(9.6, 5.2), gridspec_kw={"width_ratios": [2.5, 1.25], "wspace": 0.04})
    y = np.arange(len(rows))[::-1]
    for yi, (label, orv, lo, hi, grp) in zip(y, rows):
        ax.plot([lo, hi], [yi, yi], color=colors[grp], linewidth=2.0, zorder=3)
        ax.plot([lo, lo], [yi - 0.14, yi + 0.14], color=colors[grp], linewidth=1.6, zorder=3)
        ax.plot([hi, hi], [yi - 0.14, yi + 0.14], color=colors[grp], linewidth=1.6, zorder=3)
        ax.plot([orv], [yi], "o", color=colors[grp], markersize=7, zorder=4)
    ax.axvline(1, color=PALETTE["ink"], linestyle="--", linewidth=1.1, zorder=2)
    ax.set_xscale("log")
    ax.set_xticks([0.4, 0.6, 1, 2, 4, 6])
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.set_xlim(0.33, 7.2)
    ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows], fontsize=9.4)
    ax.set_ylim(-0.7, len(rows) - 0.3)
    ax.set_xlabel("Adjusted odds ratio (log scale)")
    ax.grid(axis="x", alpha=0.45)
    ax.text(0.42, -0.62, "← lower odds of dislocation", fontsize=8.2, color=PALETTE["gray"])
    ax.text(1.35, -0.62, "higher odds of dislocation →", fontsize=8.2, color=PALETTE["gray"])

    axt.axis("off"); axt.set_ylim(-0.7, len(rows) - 0.3)
    axt.text(0.02, len(rows) - 0.35, "OR (95% CI)", fontsize=9.4, fontweight="bold",
             color=PALETTE["ink"], va="center")
    for yi, (label, orv, lo, hi, grp) in zip(y, rows):
        axt.text(0.02, yi, f"{orv:.2f} ({lo:.2f}-{hi:.2f})", fontsize=9.3,
                 color=PALETTE["ink"], va="center")
    fig.suptitle("Figure 5. Adjusted odds of dislocation versus fracture, 2015-2025",
                 x=0.09, ha="left", fontsize=12, fontweight="bold", color=PALETTE["ink"], y=0.98)
    fig.text(0.09, -0.02,
             "Conditional case-mix odds among adolescents presenting with one of the two diagnoses — not injury-risk estimates.\n"
             "References: football, ages 10-12 years, records coded as male. Sport comparisons are exploratory; see Table 3 for Holm-adjusted p values.",
             fontsize=8.2, color=PALETTE["gray"], va="top")
    save("figure_5_forest_plot_dislocation_model")


for f in (figure1, figure2, figure3, figure4, figure5):
    f()
    print("built", f.__name__)
