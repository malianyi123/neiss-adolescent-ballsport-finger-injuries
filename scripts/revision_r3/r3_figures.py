"""R3 figures: Figure 1 (cohort flow, split records rejoined) and Figure 2 (annual estimates, year-specific 95% CIs).
Usage: python scripts/revision_r3/r3_figures.py <repo_root> [out_dir]  (run r3_design_analysis.py first)"""
import json, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from pathlib import Path
import sys
Z=1.959963984540054
ROOT=Path(sys.argv[1]) if len(sys.argv)>1 else Path(".")
OUT=Path(sys.argv[2]) if len(sys.argv)>2 else ROOT/"outputs"/"figures"; OUT.mkdir(parents=True, exist_ok=True)
res=json.load(open(ROOT/"outputs"/"reports"/"r3"/"r3_results.json"))
YRS=[str(y) for y in range(2015,2026)]
est=np.array([res["annual_estimates"][y] for y in YRS]); se=np.array([res["se_year_specific"][y] for y in YRS])
years=np.arange(2015,2026)
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"axes.spines.top":False,"axes.spines.right":False,"savefig.facecolor":"white"})
BLUE="#2e6e9e"; GOLD="#e9c46a"
# ---------------- Figure 2 ----------------
fig,ax=plt.subplots(figsize=(7.8,4.9))
ax.axvspan(2019.5,2021.5,color=GOLD,alpha=0.28,lw=0)
ax.text(2020.5,69500,"COVID-19 pandemic\nperiod (2020-2021)",ha="center",va="top",fontsize=9,fontweight="bold",color="#7a5c00")
ax.axvline(2023.5,color="#555555",ls=(0,(4,3)),lw=1.1)
ax.text(2023.62,69500,"NEISS hospital\nsample redesign\n(from 2024)",ha="left",va="top",fontsize=8.5,color="#333333")
ax.errorbar(years,est,yerr=Z*se,fmt="o-",color=BLUE,ecolor=BLUE,elinewidth=1.4,capsize=4,ms=6.5,lw=2)
ax.set_xticks(years); ax.set_xlim(2014.5,2025.5); ax.set_ylim(0,72000)
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v,p:f"{v:,.0f}"))
ax.grid(axis="y",color="#e5e5e5",lw=0.8); ax.set_axisbelow(True)
ax.set_xlabel("Treatment year"); ax.set_ylabel("Weighted national ED visit estimate")
ax.set_title("Figure 2. Annual weighted national estimates, 2015-2025",loc="left",fontsize=12.5,fontweight="bold",color="#22313f")
fig.text(0.11,-0.015,"Error bars are 95% confidence intervals from Taylor-linearized standard errors estimated under each year's own NEISS sample design\n(stratum, primary sampling unit, and sample weight).",fontsize=8.3,color="#6b7785",ha="left",va="top")
for ext in ("pdf","png"): fig.savefig(OUT/f"figure_2_annual_weighted_estimates.{ext}",dpi=300,bbox_inches="tight")
plt.close(fig)
# ---------------- Figure 1 ----------------
fig=plt.figure(figsize=(6.6,7.0)); ax=fig.add_axes([0,0,1,1]); ax.set_xlim(0,100); ax.set_ylim(2.5,100); ax.axis("off")
steps=[("NEISS annual archived records,\n2015-2025","3,924,903"),("Age 10-18 years","732,983"),("Primary body part: finger","73,419"),
       ("Primary diagnosis:\nfracture or dislocation","24,363"),("Verified selected ball and stick\nsport code in Product_1 or Product_2","16,069"),("Final analytic cohort","16,066")]
excl=["3,191,920 outside age range","659,564 other body part","49,056 other diagnosis","8,294 no verified ball and stick\nsport code","3 spectator/bystander\nnarratives"]
x0,w,h=5,45,8.6; top=89; gap=13.6
ax.text(1,97.5,"Figure 1. Cohort selection",fontsize=12.5,fontweight="bold",color="#22313f",va="center")
for i,(lab,n) in enumerate(steps):
    y=top-i*gap; final=(i==len(steps)-1)
    ax.add_patch(FancyBboxPatch((x0,y-h/2),w,h,boxstyle="round,pad=0.25,rounding_size=1.2",fc=BLUE if final else "#edf1f5",ec=BLUE,lw=1.2))
    c="white" if final else "#22313f"
    ax.text(x0+w/2,y+1.4,lab,ha="center",va="center",fontsize=8.6,color=c,fontweight="bold" if final else "normal",linespacing=1.15)
    ax.text(x0+w/2,y-2.6,f"n = {n}",ha="center",va="center",fontsize=10.5,fontweight="bold",color=c)
    if i<len(steps)-1:
        ax.annotate("",xy=(x0+w/2,y-gap+h/2+0.5),xytext=(x0+w/2,y-h/2-0.3),arrowprops=dict(arrowstyle="-|>",color="#7f8c99",lw=1.2))
        ym=y-gap/2
        ax.annotate("",xy=(70,ym),xytext=(x0+w/2,ym),arrowprops=dict(arrowstyle="-|>",color="#c0392b",lw=1.1))
        ax.text(71.5,ym,"Excluded:\n"+excl[i],ha="left",va="center",fontsize=8.2,color="#c0392b",linespacing=1.15)
yb=top-(len(steps)-1)*gap-h/2-5.2
ax.add_patch(FancyBboxPatch((0.8,yb-3.6),53.4,7.2,boxstyle="round,pad=0.25,rounding_size=1.0",fc="white",ec=BLUE,lw=1.4))
ax.text(27.5,yb,"Weighted national estimate: 441,441 ED visits\n(95% CI 341,825-541,056)",ha="center",va="center",fontsize=9.2,fontweight="bold",color="#22313f")
for ext in ("pdf","png"): fig.savefig(OUT/f"figure_1_cohort_flow.{ext}",dpi=300,bbox_inches="tight")
print("ok")
