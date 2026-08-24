"""Design-based estimation for NEISS, matching the project's original estimator.

Variance for a weighted total uses the stratified with-replacement (ultimate
cluster) estimator:
    V(t) = sum_h  m_h/(m_h - 1) * sum_k (t_hk - tbar_h)^2
where t_hk is the sum of domain weights in PSU k of stratum h. Strata that
contribute only one observed PSU are dropped from the variance sum (they add
zero), which is the standard "single-PSU stratum = certainty/no contribution"
convention used in the original pipeline.

Ratios and contrasts use Taylor linearization on the same PSU totals.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

Z = 1.959963984540054


def psu_totals(df: pd.DataFrame, values: np.ndarray) -> pd.DataFrame:
    """Aggregate a per-record linear variable to stratum x PSU totals."""
    tmp = pd.DataFrame(
        {
            "stratum": df["stratum"].to_numpy(),
            "psu": df["psu"].to_numpy(),
            "v": np.asarray(values, dtype=float),
        }
    )
    return tmp.groupby(["stratum", "psu"], dropna=False)["v"].sum().reset_index()


def _variance_from_psu(grouped: pd.DataFrame) -> tuple[float, bool]:
    var = 0.0
    usable = False
    for _, g in grouped.groupby("stratum", dropna=False):
        m = len(g)
        if m <= 1:
            continue
        usable = True
        vals = g["v"].to_numpy(dtype=float)
        var += m / (m - 1) * float(((vals - vals.mean()) ** 2).sum())
    return var, usable


def total(df: pd.DataFrame, mask=None) -> dict:
    """Weighted total with SE, CV and 95% CI."""
    w = df["weight"].to_numpy(dtype=float)
    if mask is None:
        dom = w.copy()
        n = len(df)
    else:
        m = np.asarray(mask, dtype=bool)
        dom = np.where(m, w, 0.0)
        n = int(m.sum())
    est = float(dom.sum())
    var, usable = _variance_from_psu(psu_totals(df, dom))
    if not usable or est <= 0:
        return {"n": n, "est": est, "se": np.nan, "cv": np.nan, "lo": np.nan, "hi": np.nan}
    se = math.sqrt(max(var, 0.0))
    return {
        "n": n,
        "est": est,
        "se": se,
        "cv": se / est,
        "lo": est - Z * se,
        "hi": est + Z * se,
    }


def ratio(df: pd.DataFrame, num_mask, den_mask, log_ci: bool = True) -> dict:
    """Design-based ratio of two weighted totals (Taylor linearization).

    Used for proportions (den = domain), and for year-to-year ratios.
    CI on the log scale by default, which keeps proportions/ratios positive.
    """
    w = df["weight"].to_numpy(dtype=float)
    nm = np.where(np.asarray(num_mask, dtype=bool), w, 0.0)
    dm = np.where(np.asarray(den_mask, dtype=bool), w, 0.0)
    num = float(nm.sum())
    den = float(dm.sum())
    n_num = int(np.asarray(num_mask, dtype=bool).sum())
    if den <= 0:
        return {"n": n_num, "est": np.nan, "se": np.nan, "cv": np.nan, "lo": np.nan, "hi": np.nan}
    r = num / den
    lin = (nm - r * dm) / den
    var, usable = _variance_from_psu(psu_totals(df, lin))
    if not usable or r <= 0:
        return {"n": n_num, "est": r, "se": np.nan, "cv": np.nan, "lo": np.nan, "hi": np.nan}
    se = math.sqrt(max(var, 0.0))
    if log_ci:
        se_log = se / r
        lo, hi = r * math.exp(-Z * se_log), r * math.exp(Z * se_log)
    else:
        lo, hi = r - Z * se, r + Z * se
    return {"n": n_num, "est": r, "se": se, "cv": se / r, "lo": lo, "hi": hi}


def difference(df: pd.DataFrame, a_mask, b_mask) -> dict:
    """Design-based difference of two weighted totals (A - B)."""
    w = df["weight"].to_numpy(dtype=float)
    am = np.where(np.asarray(a_mask, dtype=bool), w, 0.0)
    bm = np.where(np.asarray(b_mask, dtype=bool), w, 0.0)
    d = float(am.sum() - bm.sum())
    var, usable = _variance_from_psu(psu_totals(df, am - bm))
    if not usable:
        return {"est": d, "se": np.nan, "lo": np.nan, "hi": np.nan, "p": np.nan}
    se = math.sqrt(max(var, 0.0))
    from scipy import stats

    z = d / se if se > 0 else np.nan
    p = 2 * (1 - stats.norm.cdf(abs(z))) if se > 0 else np.nan
    return {"est": d, "se": se, "lo": d - Z * se, "hi": d + Z * se, "z": z, "p": p}


def linear_combination(df: pd.DataFrame, coefs: dict) -> dict:
    """Weighted total of sum_j c_j * t_j where coefs maps mask -> coefficient.

    coefs: list of (mask, coefficient) pairs passed as a dict is awkward, so
    accept a list of tuples instead via `coefs` = [(mask, c), ...].
    """
    raise NotImplementedError


def lincom(df: pd.DataFrame, terms: list) -> dict:
    """terms = [(mask, coefficient), ...]; returns estimate/SE/CI of the sum."""
    w = df["weight"].to_numpy(dtype=float)
    v = np.zeros(len(df), dtype=float)
    for mask, c in terms:
        v = v + c * np.where(np.asarray(mask, dtype=bool), w, 0.0)
    est = float(v.sum())
    var, usable = _variance_from_psu(psu_totals(df, v))
    if not usable:
        return {"est": est, "se": np.nan, "lo": np.nan, "hi": np.nan}
    se = math.sqrt(max(var, 0.0))
    return {"est": est, "se": se, "lo": est - Z * se, "hi": est + Z * se}


def ratio_of_lincom(df: pd.DataFrame, num_terms: list, den_terms: list) -> dict:
    """Ratio where numerator and denominator are each linear combinations."""
    w = df["weight"].to_numpy(dtype=float)

    def build(terms):
        v = np.zeros(len(df), dtype=float)
        for mask, c in terms:
            v = v + c * np.where(np.asarray(mask, dtype=bool), w, 0.0)
        return v

    nv, dv = build(num_terms), build(den_terms)
    num, den = float(nv.sum()), float(dv.sum())
    if den == 0:
        return {"est": np.nan, "se": np.nan, "lo": np.nan, "hi": np.nan}
    r = num / den
    lin = (nv - r * dv) / den
    var, usable = _variance_from_psu(psu_totals(df, lin))
    if not usable or r <= 0:
        return {"est": r, "se": np.nan, "lo": np.nan, "hi": np.nan}
    se = math.sqrt(max(var, 0.0))
    se_log = se / r
    return {
        "est": r,
        "se": se,
        "lo": r * math.exp(-Z * se_log),
        "hi": r * math.exp(Z * se_log),
    }


def fmt_est(d: dict, decimals: int = 0) -> str:
    if pd.isna(d.get("est")):
        return ""
    if pd.isna(d.get("lo")):
        return f"{d['est']:,.{decimals}f}"
    return f"{d['est']:,.{decimals}f} ({d['lo']:,.{decimals}f}-{d['hi']:,.{decimals}f})"


def fmt_pct(d: dict, decimals: int = 1) -> str:
    if pd.isna(d.get("est")):
        return ""
    if pd.isna(d.get("lo")):
        return f"{d['est']*100:.{decimals}f}%"
    return f"{d['est']*100:.{decimals}f}% ({d['lo']*100:.{decimals}f}-{d['hi']*100:.{decimals}f})"
