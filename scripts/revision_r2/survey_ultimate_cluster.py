"""Stratified ultimate-cluster (Taylor) totals & covariances, replicating survey::svytotal
and svyby(..., covmat=TRUE) for a domain of a stratified single-stage design."""
import numpy as np, pandas as pd, math

def norm_ppf(p):  # inverse std normal, Acklam-free: use erfinv via bisection-free formula
    from math import sqrt
    # Beasley-Springer-Moro is fine, but use scipy-free rational approx (Wichura AS241)
    q = p - 0.5
    if abs(q) <= 0.425:
        r = 0.180625 - q*q
        num = (((((((2509.0809287301226727*r+33430.575583588128105)*r+67265.770927008700853)*r+45921.953931549871457)*r+13731.693765509461125)*r+1971.5909503065514427)*r+133.14166789178437745)*r+3.387132872796366608)
        den = (((((((5226.495278852545925*r+28729.085735721942674)*r+39307.89580009271061)*r+21213.794301586595867)*r+5394.1960214247511077)*r+687.1870074920579083)*r+42.313330701600911252)*r+1.0)
        return q*num/den
    r = p if q < 0 else 1-p
    r = math.sqrt(-math.log(r))
    if r <= 5:
        r -= 1.6
        num=(((((((7.7454501427834140764e-4*r+0.0227238449892691845833)*r+0.24178072517745061177)*r+1.27045825245236838258)*r+3.64784832476320460504)*r+5.7694972214606914055)*r+4.6303378461565452959)*r+1.42343711074968357734)
        den=(((((((1.05075007164441684324e-9*r+5.475938084995344946e-4)*r+0.0151986665636164571966)*r+0.14810397642748007459)*r+0.68976733498510000455)*r+1.6763848301838038494)*r+2.05319162663775882187)*r+1.0)
    else:
        r -= 5
        num=(((((((2.01033439929228813265e-7*r+2.71155556874348757815e-5)*r+0.0012426609473880784386)*r+0.026532189526576123093)*r+0.29656057182850489123)*r+1.7848265399172913358)*r+5.4637849111641143699)*r+6.6579046435011037772)
        den=(((((((2.04426310338993978564e-15*r+1.4215117583164458887e-7)*r+1.8463183175100546818e-5)*r+7.868691311456132591e-4)*r+0.0148753612908506148525)*r+0.13692988092273580531)*r+0.59983220655588793769)*r+1.0)
    v = num/den
    return -v if q < 0 else v

def norm_sf2(z):  # two-sided p
    return math.erfc(abs(z)/math.sqrt(2.0))

Z = norm_ppf(0.975)   # 1.959963984540054

class Design:
    """frame: DataFrame with columns stratum, psu  = ALL clusters in the design (full file)."""
    def __init__(self, frame):
        f = frame[["stratum","psu"]].drop_duplicates().sort_values(["stratum","psu"]).reset_index(drop=True)
        self.clusters = f
        self.key = list(map(tuple, f.values))
        self.index = {k:i for i,k in enumerate(self.key)}
        self.strata = f["stratum"].values
        self.nh = f.groupby("stratum").size().to_dict()
        self.m = len(f)

    def cluster_totals(self, data, ycols):
        """data: cohort rows with stratum, psu, weight and 0/1 (or numeric) columns in ycols.
        returns matrix (m clusters x len(ycols)) of weighted cluster totals."""
        T = np.zeros((self.m, len(ycols)))
        w = data["weight"].to_numpy(float)
        idx = np.array([self.index[(s,p)] for s,p in zip(data["stratum"], data["psu"])])
        for j,c in enumerate(ycols):
            np.add.at(T[:,j], idx, w*data[c].to_numpy(float))
        return T

    def vcov(self, T):
        """Stratified ultimate-cluster covariance of the column totals of T."""
        k = T.shape[1]; V = np.zeros((k,k))
        for h, nh in self.nh.items():
            if nh < 2: continue
            rows = (self.strata == h)
            A = T[rows,:]
            D = A - A.mean(axis=0, keepdims=True)
            V += (nh/(nh-1.0)) * (D.T @ D)
        return V

    def totals(self, data, ycols):
        T = self.cluster_totals(data, ycols)
        est = T.sum(axis=0)
        V = self.vcov(T)
        return est, V
