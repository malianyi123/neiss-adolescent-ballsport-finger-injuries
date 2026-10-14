#!/usr/bin/env python3
"""Third revision (R3): sampling-design checks for the annual NEISS series.

Usage:  python scripts/revision_r3/r3_design_analysis.py <repo_root>

Inputs : data/raw/neiss/neiss{2015..2025}.tsv  (CPSC annual archived files)
         data/processed/cohort_main.csv         (analytic cohort, 16,066 records)
Outputs: outputs/reports/r3/*.csv, r3_results.json

What it does
 1. Reads the raw files with a reader that rejoins records whose narrative contains an
    embedded line break (8 records are split into two rows by a plain tab-delimited reader).
 2. Tabulates active sampling units (stratum x PSU) by stratum and year, entry/exit at every
    year boundary, and PSU codes that appear in more than one stratum (re-stratified hospitals).
 3. Annual cohort totals with standard errors under
      (P) the pooled 2015-2025 design (svydesign(~psu, strata=~stratum, nest=TRUE) on the pooled
          file; annual totals as domains)  -- reproduces the second-revision values, and
      (Y) year-specific designs (units reporting in that year), with the covariance between years
          estimated from the units reporting in both years (overlap estimator; Wood 2008, JOS 24:53-78).
    plus variants in which the 19 re-stratified hospitals are linked across the 2024 boundary.
 4. Trend slopes (additive and multiplicative scale) under four covariance treatments and
    ratio contrasts between years/periods for every design.
 5. Context for the 2023-2024 step (national all-injury estimate; hospitals reporting in both years).
The stratified ultimate-cluster formulas reproduce survey::svytotal / svyby(covmat=TRUE).
"""
import sys, re, math, json, csv
from pathlib import Path
from collections import defaultdict
import numpy as np, pandas as pd

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
OUT = ROOT / "outputs" / "reports" / "r3"; OUT.mkdir(parents=True, exist_ok=True)
YEARS = list(range(2015, 2026))
Z = 1.959963984540054
def p2(z): return math.erfc(abs(z) / math.sqrt(2.0))

# ---------------------------------------------------------------- 1. raw files
REC = re.compile(r'^\d+\t\d{2}/\d{2}/\d{4}\t')
agg = defaultdict(lambda: [0, 0.0, 0, 0.0, 0, 0.0, 0, 0.0]); split_rows = []
for y in YEARS:
    with open(ROOT / "data" / "raw" / "neiss" / f"neiss{y}.tsv", encoding="latin1", newline="") as f:
        lines = f.read().split("\n")
    if lines[-1] == "": lines = lines[:-1]
    hdr = [h.strip('"') for h in lines[0].rstrip("\r").split("\t")]; ix = {h: i for i, h in enumerate(hdr)}
    recs = []
    for ln in lines[1:]:
        ln = ln.rstrip("\r")
        if REC.match(ln) or not recs: recs.append(ln)
        else:
            recs[-1] += " " + ln; split_rows.append(recs[-1])
    for r in recs:
        p = r.split("\t")
        # Stratum, PSU, Weight are the last three fields; a quoted field may contain a tab
        s, u, w = p[-3], int(p[-2]), float(p[-1])
        ty = int(p[ix["Treatment_Date"]][-4:])
        try: age = int(p[ix["Age"]])
        except ValueError: age = -1
        a = agg[(ty, s, u)]; a[0] += 1; a[1] += w
        if 10 <= age <= 18:
            a[2] += 1; a[3] += w
            if p[ix["Body_Part"]] == "92":
                a[4] += 1; a[5] += w
                if p[ix["Diagnosis"]] in ("55", "57"): a[6] += 1; a[7] += w
fr = pd.DataFrame([list(k) + v for k, v in agg.items()],
                  columns=["year", "stratum", "psu", "n_all", "w_all", "n_adol", "w_adol", "n_adolf", "w_adolf", "n_adolffd", "w_adolffd"])
fr.to_csv(OUT / "r3_cluster_year_frame.csv", index=False)
with open(OUT / "r3_split_records.csv", "w", newline="") as f:
    wr = csv.writer(f); wr.writerow(["CPSC_Case_Number", "Treatment_Date", "Age", "Body_Part", "Diagnosis", "Stratum", "PSU", "Weight"])
    for r in split_rows:
        p = r.split("\t"); wr.writerow([p[0], p[1], p[2], p[7], p[8], p[-3], p[-2], p[-1]])

# ---------------------------------------------------------------- 2. sample structure
act = fr[["year", "stratum", "psu"]].drop_duplicates()
units = act[["stratum", "psu"]].drop_duplicates()
tab = act.groupby(["year", "stratum"]).size().unstack(1).fillna(0).astype(int); tab["Total"] = tab.sum(1)
tab.loc["Pooled 2015-2025"] = list(units.groupby("stratum").size()) + [len(units)]
tab.to_csv(OUT / "r3_active_units_by_stratum_year.csv")
S = {y: set(map(tuple, act[act.year == y][["stratum", "psu"]].values)) for y in YEARS}
codes_multi = set(act.groupby("psu").stratum.nunique().loc[lambda s: s > 1].index)
flows = []
for y in YEARS[1:]:
    ent = S[y] - S[y - 1]; lv = S[y - 1] - S[y]
    prev_code = {p: s for s, p in S[y - 1]}
    restrat = [1 for s, p in ent if p in prev_code and prev_code[p] != s]
    flows.append(dict(boundary=f"{y-1}-{y}", entering=len(ent), leaving=len(lv), continuing_same_stratum=len(S[y] & S[y - 1]),
                      entering_restratified=len(restrat), new_hospitals=len(ent) - len(restrat), departed_hospitals=len(lv) - len(restrat)))
pd.DataFrame(flows).to_csv(OUT / "r3_boundary_flows.csv", index=False)
rs = []
for c in sorted(codes_multi):
    sub = act[act.psu == c]
    for s in sub.stratum.unique():
        yy = sorted(sub[sub.stratum == s].year)
        rs.append(dict(psu=c, stratum=s, first_year=min(yy), last_year=max(yy), n_years=len(yy)))
pd.DataFrame(rs).to_csv(OUT / "r3_restratified_hospitals.csv", index=False)
same_year = act.groupby(["year", "psu"]).stratum.nunique().max()
eraA = set().union(*[S[y] for y in YEARS if y <= 2023]); eraB = S[2024] | S[2025]
struct = dict(stratum_nested_units=len(units), distinct_psu_codes=int(act.psu.nunique()), codes_in_more_than_one_stratum=len(codes_multi),
              max_strata_per_code_within_a_year=int(same_year), units_eraA=len(eraA), units_eraB=len(eraB), units_both_eras_same_stratum=len(eraA & eraB),
              hospitals_both_eras_linked=len({p for s, p in eraA} & {p for s, p in eraB}),
              hospitals_2023_and_2024=len({p for s, p in S[2023]} & {p for s, p in S[2024]}), hospitals_2024=len(S[2024]))

# ---------------------------------------------------------------- 3. cohort cluster totals
coh = pd.read_csv(ROOT / "data" / "processed" / "cohort_main.csv")
coh["year"] = coh.year.astype(int); coh["psu"] = coh.psu.astype(int)
eraB_str = {p: s for (y, s, p) in act[act.year >= 2024].itertuples(index=False)}
eraA_str = {p: s for (y, s, p) in act[act.year <= 2023].itertuples(index=False)}
def unit_table(link=None):
    a = act.copy()
    if link is None: a["g"] = a.stratum
    else:
        m = eraB_str if link == "B" else eraA_str
        a["g"] = [m[p] if p in codes_multi else s for s, p in zip(a.stratum, a.psu)]
    a["u"] = a.g + "_" + a.psu.astype(str); return a
def cluster_year_totals(U, mask=None):
    c = coh if mask is None else coh[mask]
    m = c.merge(U[["stratum", "psu", "u"]].drop_duplicates(), on=["stratum", "psu"], how="left"); assert m.u.notna().all()
    allu = sorted(U.u.unique())
    T = pd.crosstab(m.u, m.year, values=m.weight, aggfunc="sum").reindex(index=allu, columns=YEARS).fillna(0)
    g = U.drop_duplicates("u").set_index("u").g.reindex(allu)
    A = U.assign(v=1).pivot_table(index="u", columns="year", values="v", aggfunc="max").reindex(index=allu, columns=YEARS).fillna(0).astype(bool)
    return T.to_numpy(), g.to_numpy(), A.to_numpy()
def V_pooled(X, G):
    V = np.zeros((11, 11))
    for h in np.unique(G):
        r = G == h; n = r.sum()
        if n > 1: D = X[r] - X[r].mean(0); V += n / (n - 1) * (D.T @ D)
    return V
def V_year(X, G, A):
    """diag: year-specific ultimate-cluster variance; off-diag: overlap estimator over units reporting in both years."""
    V = np.zeros((11, 11))
    for a in range(11):
        for b in range(a, 11):
            s = 0.0
            for h in np.unique(G):
                r = (G == h) & A[:, a] & A[:, b]; n = r.sum()
                if n > 1:
                    xa = X[r, a] - X[r, a].mean(); xb = X[r, b] - X[r, b].mean(); s += n / (n - 1) * (xa @ xb)
            V[a, b] = V[b, a] = s
    return V
def V_year_linked(link):
    """year-specific variances and within-era covariances with actual strata; cross-era (2015-2023 x 2024-2025)
    covariances with the re-stratified hospitals linked by PSU code (grouped by their era-`link` stratum)."""
    V = V_year(*cluster_year_totals(unit_table(None)))
    VL = V_year(*cluster_year_totals(unit_table(link)))
    for a in range(9):
        for b in (9, 10): V[a, b] = V[b, a] = VL[a, b]
    return V

X0, G0, A0 = cluster_year_totals(unit_table(None)); est = X0.sum(0)
designs = {
    "pooled": V_pooled(X0, G0),
    "pooled_linked_eraB_stratum": V_pooled(*cluster_year_totals(unit_table("B"))[:2]),
    "pooled_linked_eraA_stratum": V_pooled(*cluster_year_totals(unit_table("A"))[:2]),
    "year_specific": V_year(X0, G0, A0),                       # PRIMARY for annual and temporal analyses
    "year_specific_linked_eraB_stratum": V_year_linked("B"),
    "year_specific_linked_eraA_stratum": V_year_linked("A"),
}
for k, V in designs.items():
    se = np.sqrt(np.diag(V)); pd.DataFrame(V / np.outer(se, se), index=YEARS, columns=YEARS).round(4).to_csv(OUT / f"r3_correlation_{k}.csv")

# annual by sport (S3a): pooled vs year-specific standard errors
rows = []
for sp in [None] + sorted(coh.sport_group.unique()):
    mask = None if sp is None else (coh.sport_group == sp)
    X, G, A = cluster_year_totals(unit_table(None), mask)
    Vp, Vy = V_pooled(X, G), V_year(X, G, A); e = X.sum(0)
    n = (coh if mask is None else coh[mask]).groupby("year").size().reindex(YEARS).fillna(0).astype(int)
    for i, y in enumerate(YEARS):
        sp_, sy = math.sqrt(Vp[i, i]), math.sqrt(Vy[i, i])
        fl = [t for t, c in (("estimate<1200", e[i] < 1200), ("n<20", n[y] < 20), ("cv>33%", sy / e[i] > 0.33)) if c]
        rows.append(dict(year=y, sport_group="All selected sports" if sp is None else sp, n=int(n[y]), estimate=e[i],
                         se_year_specific=sy, ci_lo=e[i] - Z * sy, ci_hi=e[i] + Z * sy, cv=sy / e[i], se_pooled=sp_, se_ratio=sy / sp_, flag="; ".join(fl)))
pd.DataFrame(rows).to_csv(OUT / "r3_annual_by_sport.csv", index=False)

# ---------------------------------------------------------------- 4. trends and contrasts
def fit(idx, V, log, mode):
    x = np.array([YEARS[i] for i in idx], float); y = est[idx].copy(); Vs = V[np.ix_(idx, idx)].copy()
    if log: Vs = Vs / np.outer(y, y); y = np.log(y)
    s0 = np.sqrt(np.diag(Vs)); Xd = np.column_stack([np.ones_like(x), x - x.mean()])
    if mode == "B_fixed_weights":
        W = np.diag(1 / s0 ** 2); L = (np.linalg.inv(Xd.T @ W @ Xd) @ Xd.T @ W)[1]; b = float(L @ y); s = math.sqrt(float(L @ Vs @ L))
    else:
        if mode == "A_independence": Vu = np.diag(s0 ** 2)
        elif mode == "C_unstructured_gls": Vu = Vs
        else:
            R = Vs / np.outer(s0, s0); k = len(idx); rho = (R.sum() - k) / (k * (k - 1)); Vu = np.outer(s0, s0) * ((1 - rho) * np.eye(k) + rho)
        Vi = np.linalg.inv(Vu); Ai = np.linalg.inv(Xd.T @ Vi @ Xd); b = float((Ai @ Xd.T @ Vi @ y)[1]); s = math.sqrt(Ai[1, 1])
    p = p2(b / s)
    if log: return (math.exp(b) - 1) * 100, (math.exp(b - Z * s) - 1) * 100, (math.exp(b + Z * s) - 1) * 100, p
    return b, b - Z * s, b + Z * s, p
PER = {"2015-2025": list(range(11)), "2015-2019": list(range(5)), "2022-2025": [7, 8, 9, 10], "2015-2025 excluding 2020-2021": [0, 1, 2, 3, 4, 7, 8, 9, 10]}
MODES = ["A_independence", "B_fixed_weights", "C_unstructured_gls", "D_exchangeable_gls"]
pre = {i: 0.2 for i in range(5)}
CON = {"2019 vs 2015": ({4: 1}, {0: 1}), "2020 vs 2015-2019 mean": ({5: 1}, pre), "2020 vs 2019": ({5: 1}, {4: 1}),
       "2022-2025 mean vs 2015-2019 mean": ({i: .25 for i in range(7, 11)}, pre), "2022-2023 mean vs 2015-2019 mean": ({7: .5, 8: .5}, pre),
       "2024 vs 2023": ({9: 1}, {8: 1}), "2024-2025 mean vs 2015-2019 mean": ({9: .5, 10: .5}, pre)}
def ratio(V, num, den):
    a = np.zeros(11); b = np.zeros(11)
    for i, c in num.items(): a[i] = c
    for i, c in den.items(): b[i] = c
    A_, B_ = a @ est, b @ est; R = A_ / B_; g = a / B_ - b * A_ / B_ ** 2; sl = math.sqrt(float(g @ V @ g)) / R
    return R, R * math.exp(-Z * sl), R * math.exp(Z * sl), p2(math.log(R) / sl)
tr, co, summ = [], [], {}
for dn, V in designs.items():
    se = np.sqrt(np.diag(V)); R = V / np.outer(se, se); iu = np.triu_indices(11, 1); ev = np.linalg.eigvalsh(R)
    summ[dn] = dict(mean_r=R[iu].mean(), median_r=float(np.median(R[iu])), min_r=R[iu].min(), max_r=R[iu].max(),
                    cross_era_mean_r=R[:9, 9:].mean(), cross_era_min_r=R[:9, 9:].min(), cross_era_max_r=R[:9, 9:].max(),
                    min_eigenvalue=ev.min(), condition_number=ev.max() / ev.min(), total_se=math.sqrt(np.ones(11) @ V @ np.ones(11)))
    for pn, idx in PER.items():
        for log in (False, True):
            for m in MODES:
                r = fit(idx, V, log, m)
                tr.append(dict(design=dn, period=pn, scale="pct_per_year" if log else "visits_per_year", spec=m, estimate=r[0], ci_lo=r[1], ci_hi=r[2], p=r[3]))
    for cn, (nu, de) in CON.items():
        r = ratio(V, nu, de); co.append(dict(design=dn, contrast=cn, ratio=r[0], ci_lo=r[1], ci_hi=r[2], p=r[3]))
pd.DataFrame(tr).to_csv(OUT / "r3_trend_models.csv", index=False)
pd.DataFrame(co).to_csv(OUT / "r3_contrasts.csv", index=False)

# ---------------------------------------------------------------- 5. 2023-2024 step context
nat = fr.groupby("year")[["n_all", "w_all", "n_adolffd", "w_adolffd"]].sum()
cy = coh.groupby("year").agg(n_cohort=("weight", "size"), w_cohort=("weight", "sum")); nat = nat.join(cy)
nat["cohort_share_of_adolescent_finger_fx_dx_pct"] = 100 * nat.w_cohort / nat.w_adolffd
nat["mean_cohort_weight"] = nat.w_cohort / nat.n_cohort
nat.to_csv(OUT / "r3_national_context.csv")
cont = {p for s, p in S[2023]} & {p for s, p in S[2024]}
fc = fr[fr.psu.isin(cont) & fr.year.isin([2023, 2024])].groupby("year")[["n_all", "w_all"]].sum()
cc = coh[coh.psu.isin(cont) & coh.year.isin([2023, 2024])].groupby("year").agg(n=("weight", "size"), w=("weight", "sum"))
boundary = dict(hospitals_reporting_both_years=len(cont),
                cohort_unweighted_2023=int(cc.n[2023]), cohort_unweighted_2024=int(cc.n[2024]),
                all_records_unweighted_2023=int(fc.n_all[2023]), all_records_unweighted_2024=int(fc.n_all[2024]),
                cohort_weighted_2023=cc.w[2023], cohort_weighted_2024=cc.w[2024],
                mean_cohort_weight_2023=cc.w[2023] / cc.n[2023], mean_cohort_weight_2024=cc.w[2024] / cc.n[2024],
                national_all_injury_2023=nat.w_all[2023], national_all_injury_2024=nat.w_all[2024])

# cohort-flow rows affected by the split-record fix (pooled design over all 122 units)
def tot_se(col):
    t = fr.groupby(["stratum", "psu"])[col].sum(); x = t.to_numpy(); g = t.index.get_level_values(0).to_numpy(); v = 0.0
    for h in np.unique(g):
        r = g == h; n = r.sum(); d = x[r] - x[r].mean(); v += n / (n - 1) * (d @ d)
    return float(x.sum()), math.sqrt(v)
flow = {}
for k, (nc, wc) in {"all_records": ("n_all", "w_all"), "age_10_18": ("n_adol", "w_adol"), "finger": ("n_adolf", "w_adolf"), "fracture_or_dislocation": ("n_adolffd", "w_adolffd")}.items():
    t, s = tot_se(wc); flow[k] = dict(n=int(fr[nc].sum()), estimate=t, se=s, cv=s / t, ci_lo=t - Z * s, ci_hi=t + Z * s)
pd.DataFrame(flow).T.to_csv(OUT / "r3_cohort_flow_rows.csv")

json.dump(dict(structure=struct, boundary_flows=flows, design_summary=summ, boundary_2023_2024=boundary, cohort_flow=flow,
               annual_estimates=dict(zip(map(str, YEARS), est.tolist())),
               se_year_specific=dict(zip(map(str, YEARS), np.sqrt(np.diag(designs["year_specific"])).tolist())),
               se_pooled=dict(zip(map(str, YEARS), np.sqrt(np.diag(designs["pooled"])).tolist()))),
          open(OUT / "r3_results.json", "w"), indent=1, default=float)
print(json.dumps(struct)); print("records:", int(fr.n_all.sum()), "split records rejoined:", len(split_rows)); print("done ->", OUT)
