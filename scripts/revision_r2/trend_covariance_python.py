"""Second-revision Python cross-check of the pooled-design covariance and trend analysis.
Usage: python scripts/revision_r2/trend_covariance_python.py <repo_root>  (after r3_design_analysis.py)"""
import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd, numpy as np, glob, math, json
from pathlib import Path
from survey_ultimate_cluster import Design, Z, norm_sf2
ROOT=Path(sys.argv[1]) if len(sys.argv)>1 else Path(".")
coh=pd.read_csv(ROOT/"data"/"processed"/"cohort_main.csv")
coh["year"]=coh["year"].astype(int); coh["psu"]=coh["psu"].astype(int)
# cluster-year frame written by scripts/revision_r3/r3_design_analysis.py (run that first)
fr=pd.read_csv(ROOT/"outputs"/"reports"/"r3"/"r3_cluster_year_frame.csv")
fr=fr.rename(columns={"Stratum":"stratum","PSU":"psu"})
fr["psu"]=pd.to_numeric(fr["psu"],errors="coerce"); fr=fr.dropna(subset=["psu"]); fr["psu"]=fr["psu"].astype(int)
years=list(range(2015,2026))
for y in years: coh[f"y{y}"]=(coh.year==y).astype(float)
cols=[f"y{y}" for y in years]

def build(splitname):
    if splitname=="pooled":
        d=Design(fr[["stratum","psu"]]); c=coh.copy()
    else:  # cluster = (redesign era, psu): era A = 2015-2023, era B = 2024-2025
        f2=fr.copy(); f2["era"]=np.where(f2.year>=2024,"B","A")
        f2["psu"]=f2["era"]+"_"+f2["psu"].astype(str)
        d=Design(f2[["stratum","psu"]])
        c=coh.copy(); c["psu"]=np.where(c.year>=2024,"B_","A_")+c["psu"].astype(str)
    return d,c

def slope_fixed_w(idx, V, est, w, log):
    """WLS slope with FIXED weights w -> linear combination of estimates; design-based variance a'Va."""
    x=np.array([years[i] for i in idx],float)
    if log:
        Vs=V[np.ix_(idx,idx)]/np.outer(est[idx],est[idx]); y=np.log(est[idx])
    else:
        Vs=V[np.ix_(idx,idx)]; y=est[idx]
    X=np.column_stack([np.ones_like(x),x-x.mean()]); W=np.diag(w)
    A=np.linalg.inv(X.T@W@X); L=(A@X.T@W)[1]          # slope = L . y
    b=float(L@y); var=float(L@Vs@L); s=math.sqrt(var); z=b/s; p=norm_sf2(z)
    if log: return ((math.exp(b)-1)*100,(math.exp(b-Z*s)-1)*100,(math.exp(b+Z*s)-1)*100,p)
    return (b,b-Z*s,b+Z*s,p)

def gls(idx,V,est,log,corr=None):
    x=np.array([years[i] for i in idx],float)
    if log: Vs=V[np.ix_(idx,idx)]/np.outer(est[idx],est[idx]); y=np.log(est[idx])
    else:   Vs=V[np.ix_(idx,idx)].copy(); y=est[idx]
    s0=np.sqrt(np.diag(Vs))
    if corr=="exch":
        R=Vs/np.outer(s0,s0); k=len(idx); rho=(R.sum()-k)/(k*(k-1)); R=(1-rho)*np.eye(k)+rho*np.ones((k,k)); Vs=np.outer(s0,s0)*R
    if corr=="indep": Vs=np.diag(s0**2)
    X=np.column_stack([np.ones_like(x),x-x.mean()]); Vi=np.linalg.inv(Vs)
    A=np.linalg.inv(X.T@Vi@X); b=A@(X.T@Vi@y); s=math.sqrt(A[1,1]); p=norm_sf2(b[1]/s)
    if log: return ((math.exp(b[1])-1)*100,(math.exp(b[1]-Z*s)-1)*100,(math.exp(b[1]+Z*s)-1)*100,p)
    return (b[1],b[1]-Z*s,b[1]+Z*s,p)

periods={"Full 2015-2025":[i for i,y in enumerate(years)],
         "Pre 2015-2019":[i for i,y in enumerate(years) if y<=2019],
         "Post 2022-2025":[i for i,y in enumerate(years) if y>=2022],
         "Excl pandemic":[i for i,y in enumerate(years) if y not in (2020,2021)]}

for dn in ["pooled","era"]:
    d,c=build(dn); est,V=d.totals(c,cols); se=np.sqrt(np.diag(V)); R=V/np.outer(se,se)
    off=R[np.triu_indices(11,1)]
    print("#"*100); print(f"DESIGN = {dn}   clusters={d.m}   mean off-diag r = {off.mean():.3f} (median {np.median(off):.3f})")
    print(f"{'Period':<16}{'scale':<7}{'A: IVW indep (current)':<36}{'B: IVW wts, cov-corrected SE':<36}{'C: full GLS':<34}{'D: exchangeable GLS':<34}")
    for nm,idx in periods.items():
        for log,lab,fmt in [(False,"visits","{:,.0f}"),(True,"%/yr","{:.2f}")]:
            if log: w=1.0/ (np.diag(V)[idx]/est[idx]**2)
            else:   w=1.0/ np.diag(V)[idx]
            A=gls(idx,V,est,log,"indep"); B=slope_fixed_w(idx,V,est,w,log)
            C=gls(idx,V,est,log,None);    D=gls(idx,V,est,log,"exch")
            f=lambda r: f"{fmt.format(r[0])} [{fmt.format(r[1])},{fmt.format(r[2])}] p={r[3]:.3f}"
            print(f"{nm:<16}{lab:<7}{f(A):<36}{f(B):<36}{f(C):<34}{f(D):<34}")
    print()
