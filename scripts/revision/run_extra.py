"""Additional analyses: hockey-exclusion sensitivity, volleyball contrast, mechanism CIs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as smapi
import statsmodels.formula.api as smf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths as P
import survey_lib as sv

P.ensure_dirs(); P.require_cohort()
df = pd.read_csv(P.COHORT_MAIN, low_memory=False)
df["year"] = df["year"].astype(int)
df["sport_code"] = df["sport_code"].astype(float).astype(int)
out = {}

HOCKEY = {1279, 3272, 3245, 5032}          # ice / unspecified / street / roller hockey
STICK_PUCK_STRICT = {1279, 3272}            # sports played with a puck
FIELD_HOCKEY = {1295}

# --- composition of "other selected ball sports"
other = df[df.sport_group == "other selected ball sports"]
tot_other = other["weight"].sum()
out["other_group"] = {
    "n": int(len(other)),
    "weighted": float(tot_other),
    "hockey_variants_pct": float(other[other.sport_code.isin(HOCKEY | FIELD_HOCKEY)]["weight"].sum() / tot_other * 100),
    "puck_only_pct": float(other[other.sport_code.isin(STICK_PUCK_STRICT)]["weight"].sum() / tot_other * 100),
    "generic_ball_pct": float(other[other.sport_code.isin({3235, 3236})]["weight"].sum() / tot_other * 100),
    "puck_share_of_whole_cohort_pct": float(
        other[other.sport_code.isin(STICK_PUCK_STRICT)]["weight"].sum() / df["weight"].sum() * 100
    ),
    "hockey_share_of_whole_cohort_pct": float(
        other[other.sport_code.isin(HOCKEY | FIELD_HOCKEY)]["weight"].sum() / df["weight"].sum() * 100
    ),
}

# --- refit the model excluding puck sports from the "other" group
def fit(data: pd.DataFrame):
    data = data[data["sex_clean"].isin(["male", "female"])].copy()
    data["dislocation"] = (data["diagnosis_group"] == "dislocation").astype(int)
    data["year_centered"] = data["year"] - data["year"].mean()
    m = smf.glm(
        "dislocation ~ C(sport_group, Treatment(reference='football')) "
        "+ C(age_group) + C(sex_clean) + year_centered",
        data=data,
        family=smapi.families.Binomial(),
        freq_weights=data["weight"],
    ).fit(cov_type="cluster", cov_kwds={"groups": data["psu"].astype(str) + "_" + data["stratum"].astype(str)})
    res = pd.DataFrame(
        {"term": m.params.index, "or": np.exp(m.params.values),
         "lo": np.exp(m.conf_int()[0].values), "hi": np.exp(m.conf_int()[1].values), "p": m.pvalues.values}
    )
    res["term"] = (res["term"].str.replace("C(sport_group, Treatment(reference='football'))[T.", "", regex=False)
                   .str.replace("C(age_group)[T.", "", regex=False)
                   .str.replace("C(sex_clean)[T.", "", regex=False).str.replace("]", "", regex=False))
    return res

scen = {}
scen["primary"] = fit(df)
scen["excluding_puck_sports"] = fit(df[~df.sport_code.isin(STICK_PUCK_STRICT)])
scen["excluding_all_hockey"] = fit(df[~df.sport_code.isin(HOCKEY | FIELD_HOCKEY)])
comp = scen["primary"][["term"]].copy()
for k, v in scen.items():
    comp = comp.merge(
        v.assign(**{k: v.apply(lambda r: f"{r['or']:.2f} ({r['lo']:.2f}-{r['hi']:.2f}), p={r['p']:.3f}", axis=1)})[["term", k]],
        on="term", how="left")
comp.to_csv(P.RESULTS_DIR / "model_hockey_sensitivity.csv", index=False)
print("=== MODEL SENSITIVITY: puck/hockey exclusion ===")
print(comp.to_string(index=False))

# --- volleyball vs football / basketball dislocation percentage contrast
def disloc_pct_diff(sport_a: str, sport_b: str):
    w = df["weight"].to_numpy(float)
    a = (df.sport_group == sport_a).to_numpy()
    b = (df.sport_group == sport_b).to_numpy()
    d = (df.diagnosis_group == "dislocation").to_numpy()
    pa = w[a & d].sum() / w[a].sum()
    pb = w[b & d].sum() / w[b].sum()
    lin = (np.where(a & d, w, 0) - pa * np.where(a, w, 0)) / w[a].sum() - (
        np.where(b & d, w, 0) - pb * np.where(b, w, 0)) / w[b].sum()
    var, ok = sv._variance_from_psu(sv.psu_totals(df, lin))
    se = np.sqrt(var)
    from scipy import stats
    z = (pa - pb) / se
    return {"a": sport_a, "b": sport_b, "diff_pp": (pa - pb) * 100,
            "lo": (pa - pb - 1.96 * se) * 100, "hi": (pa - pb + 1.96 * se) * 100,
            "p": float(2 * (1 - stats.norm.cdf(abs(z))))}

out["volleyball_contrasts"] = [
    disloc_pct_diff("volleyball", "football"),
    disloc_pct_diff("volleyball", "basketball"),
]
print("\n=== VOLLEYBALL DISLOCATION %% CONTRASTS ===")
for c in out["volleyball_contrasts"]:
    print(f"{c['a']} - {c['b']}: {c['diff_pp']:+.1f} pp (95% CI {c['lo']:+.1f} to {c['hi']:+.1f}), p={c['p']:.3f}")

# --- narrative mechanism 2019-2025 with CIs
m1925 = df[df.year >= 2019].copy()
allm = np.ones(len(m1925), bool)
mech = []
for v in sorted(m1925.narrative_mechanism.dropna().unique()):
    mask = (m1925.narrative_mechanism == v).to_numpy()
    t = sv.total(m1925, mask)
    p = sv.ratio(m1925, mask, allm)
    mech.append({"mechanism": v, "n": t["n"], "est": round(t["est"]),
                 "ci": f"{t['lo']:,.0f}-{t['hi']:,.0f}", "cv_pct": round(t["cv"] * 100, 1),
                 "pct": round(p["est"] * 100, 1), "pct_ci": f"{p['lo']*100:.1f}-{p['hi']*100:.1f}"})
pd.DataFrame(mech).to_csv(P.RESULTS_DIR / "mechanism_with_ci.csv", index=False)
print("\n=== MECHANISM 2019-2025 WITH CI ===")
print(pd.DataFrame(mech).to_string(index=False))

# --- age gradient: 13-15 vs 10-12 also reported
out["note"] = "see model_main_refit.csv for the 13-15 vs 10-12 estimate"

with open(P.RESULTS_DIR / "extra_results.json", "w") as f:
    json.dump(out, f, indent=2, default=float)
print("\n=== OTHER GROUP COMPOSITION ===")
print(json.dumps(out["other_group"], indent=1))
