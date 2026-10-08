# -*- coding: utf-8 -*-
"""Every number and figure input in the manuscript. Deterministic (no random numbers). Writes ../results.json.   python reproduce.py   (about 10-15 minutes)"""
import json
import sys
import time

import numpy as np
import scipy
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

import arclength as A
import coupled as C
import model as M
import momentum as MO
import stability as S
import theory as TH

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
t0 = time.time()
RES = {"versions": {"python": sys.version.split()[0], "numpy": np.__version__, "scipy": scipy.__version__}}


def log(msg):
    print("[%5.0f s] %s" % (time.time() - t0, msg), flush=True)


def steady(N, sc, P_aux=40.0, **kw):
    """Steady state of the lower (physical) branch: pseudo-time march of the baseline, then Newton continuation in s_c."""
    m = M.Model(N, **kw)
    T, _ = M.solve(m, P_aux, None, dt=0.05, maxit=300, tol=1e-9)
    if sc is not None:
        for s_ in [x for x in (4.0, 2.0, 1.0, 0.7, 0.5, 0.4, 0.3, 0.2, 0.15, 0.1, 0.07, 0.05) if x > sc] + [sc]:
            T, ok = S.steady_newton(m, s_, T, P_aux)
            if not ok:
                return m, T, False
    return m, T, True


# ------------------------------------------------------------------ E0 model checks
RES["bosch_hale"] = {"sigma_v_10keV": float(M.sigma_v(10.0)), "sigma_v_20keV": float(M.sigma_v(20.0))}
log("E0 Bosch-Hale <sigma v> at 10 and 20 keV: %.4e %.4e (reference 1.136e-22, 4.33e-22)" % (M.sigma_v(10.0), M.sigma_v(20.0)))

# ------------------------------------------------------------------ E1 controlled comparison (Table 1), N = 100
rows = []
SCS = [None, 1.0, 0.5, 0.3, 0.2, 0.15, 0.1, 0.07]
base_Q = None
for sc in SCS:
    m, T, ok = steady(100, sc)
    d = M.diagnostics(m, T, 40.0, sc)
    if sc is None:
        base_Q = d["Q"]
    rows.append(dict(sc=sc, ok=bool(ok), Q=float(d["Q"]), Pfus=float(d["Pfus"]), tauE=float(d["tauE"]), Tavg=float(d["Tavg"]), T0=float(d["T0"]),
                     ratio_max=float(d["ratio_max"]), resid=float(d["resid"]), dQ=float(d["Q"] / base_Q - 1.0),
                     chi_min_over_base=float(np.min(d["chi"] / d["chib"]))))
RES["table1"] = rows
log("E1 Table 1 done: %s" % [(r["sc"], round(r["Q"], 4)) for r in rows])
prof = {}
for key, sc in (("baseline", None), ("sc0.5", 0.5), ("sc0.1", 0.1)):
    m, T, ok = steady(200, sc)
    d = M.diagnostics(m, T, 40.0, sc)
    prof[key] = dict(r=m.r.tolist(), T=T.tolist(), chi=d["chi"].tolist(), chib=d["chib"].tolist(), ratio=d["ratio"].tolist(), Q=float(d["Q"]))
RES["profiles"] = prof

# ------------------------------------------------------------------ E2 auxiliary-power scan
PA = [10, 15, 20, 30, 40, 50, 60, 70, 80]
scan = {}
for key, sc in (("baseline", None), ("sc0.5", 0.5), ("sc0.3", 0.3), ("sc0.1", 0.1)):
    qs = []
    for P in PA:
        m, T, ok = steady(100, sc, float(P))
        d = M.diagnostics(m, T, float(P), sc)
        qs.append(dict(P=P, Q=float(d["Q"]), ok=bool(ok), tauE=float(d["tauE"])))
    scan[key] = qs
RES["paux_scan"] = {"P": PA, **scan}
log("E2 power scan done: baseline Q %s" % [round(q["Q"], 3) for q in scan["baseline"]])

# ------------------------------------------------------------------ E3 grid convergence (Table 3)
GR = {}
Ns = (50, 100, 200, 400, 800)
for sc in (None, 1.0, 0.5, 0.3, 0.2, 0.1, 0.07):
    row = []
    for N in Ns:
        m, T, ok = steady(N, sc)
        d = M.diagnostics(m, T, 40.0, sc)
        row.append(dict(N=N, ok=bool(ok), Q=float(d["Q"]), T0=float(d["T0"]), ratio_max=float(d["ratio_max"]), resid=float(d["resid"])))
    GR["none" if sc is None else str(sc)] = row
    log("E3 s_c=%s: Q(N) = %s" % (sc, [round(r["Q"], 4) for r in row]))
orders = {}
for k, row in GR.items():
    q = {r["N"]: r["Q"] for r in row if r["ok"]}
    if all(n in q for n in (100, 200, 400)):
        a, b = q[100] - q[200], q[200] - q[400]
        orders[k] = float(np.log2(abs(a / b))) if b != 0 and a * b > 0 else None
RES["grid"] = {"N": list(Ns), "rows": GR, "observed_order": orders}
log("E3 observed orders %s" % orders)

# ------------------------------------------------------------------ E4 bifurcation: fold location and the S-curve
FOLD = {}
for N in (50, 100, 200, 400):
    m, pts = A.branch(N, p_max=40.0, ds=0.3, max_pts=500, stop_after_fold=6)
    mu = np.array([q["p"] for q in pts])
    k = int(np.argmax(mu))
    x = np.arange(k - 1, k + 2)
    c = np.polyfit(x, mu[k - 1:k + 2], 2)
    xm = -c[1] / (2 * c[0])
    mumax = float(np.polyval(c, xm))
    FOLD[str(N)] = dict(sc_fold=1.0 / mumax, mu_fold=mumax, Q_fold=float(np.interp(xm, x, [pts[i]["Q"] for i in x])),
                        T0_fold=float(np.interp(xm, x, [pts[i]["T0"] for i in x])))
    log("E4 fold N=%d: s_c* = %.5f  Q = %.2f  T0 = %.1f keV" % (N, 1.0 / mumax, FOLD[str(N)]["Q_fold"], FOLD[str(N)]["T0_fold"]))
sc_f = [FOLD[str(N)]["sc_fold"] for N in (100, 200, 400)]
d1, d2 = sc_f[0] - sc_f[1], sc_f[1] - sc_f[2]
p_ord = float(np.log2(d1 / d2))
sc_inf = float(sc_f[2] - d2 / (2 ** p_ord - 1))
RES["fold"] = dict(by_N=FOLD, order=p_ord, extrapolated=sc_inf)
log("E4 fold: observed order %.2f, Richardson limit s_c* = %.5f" % (p_ord, sc_inf))
for N, key in ((100, "branch_N100"), (200, "branch_N200")):
    m, pts = A.branch(N, p_max=26.0, ds=0.2, max_pts=900)
    RES[key] = [(q["p"], q["Q"], q["T0"], q["lam"], q["ratio_max"]) for q in pts]
log("E4 S-curve branches stored")

# ------------------------------------------------------------------ E5 independent time integration (Radau) of the semi-discrete system
from scipy.sparse import diags


def integrate(m, sc, T0, tend=60.0, P_aux=40.0, stop_T0=None, rtol=1e-8, atol=1e-8):
    """Radau integration of dT/dt = residual/(3 n e). With stop_T0 the run stops (event) when the axis temperature exceeds that value (keV)."""
    Sx = m.source_aux(P_aux)
    cT = 3.0 * m.n * M.KEV
    f = lambda t, T: M.residual(m, T, Sx, sc) / cT
    N = m.N
    sp = diags([np.ones(N - abs(k)) for k in range(-3, 4)], list(range(-3, 4)), shape=(N, N)).tocsr()
    ev = None
    if stop_T0 is not None:
        ev = lambda t, T: T[0] - stop_T0
        ev.terminal = True
        ev.direction = 1
    sol = solve_ivp(f, (0.0, tend), T0, method="Radau", rtol=rtol, atol=atol, jac_sparsity=sp, events=ev)
    return sol.y[:, -1], sol


TI = []
for sc in (None, 0.5, 0.1):
    m, Tn, ok = steady(100, sc)
    Tt, sol = integrate(m, sc, 4.0 + 8.0 * (1 - (m.r / 2.0) ** 2), tend=80.0)
    TI.append(dict(sc=sc, max_abs_dT=float(np.max(np.abs(Tt - Tn))), Q_ivp=float(M.diagnostics(m, Tt, 40.0, sc)["Q"]), Q_newton=float(M.diagnostics(m, Tn, 40.0, sc)["Q"]),
                   nfev=int(sol.nfev)))
RES["time_integration"] = TI
log("E5 time integration vs Newton: %s" % [(r["sc"], "%.1e" % r["max_abs_dT"]) for r in TI])
# behaviour around the fold: (i) just above s_c*, cold start; (ii) just below s_c*, start from the lower-branch state at s_c = 0.06; (iii) hot start inside the window
FD = {}
m = M.Model(100)
cold = 4.0 + 8.0 * (1 - (m.r / 2.0) ** 2)
for key, sc_ in (("above", 0.0500), ("below", 0.0440)):
    Tt, sol = integrate(m, sc_, cold, tend=200.0, stop_T0=150.0)
    d = M.diagnostics(m, Tt, 40.0, sc_)
    FD[key] = dict(sc=sc_, t_end=float(sol.t[-1]), reached_150keV=bool(Tt[0] >= 150.0 - 1e-6), Q=float(d["Q"]), T0=float(Tt[0]))
Th, solh = integrate(m, 0.0500, 4.0 + 66.0 * (1 - (m.r / 2.0) ** 2), tend=200.0, stop_T0=150.0)
FD["hot_start_in_window"] = dict(sc=0.0500, t_end=float(solh.t[-1]), reached_150keV=bool(Th[0] >= 150.0 - 1e-6), T0=float(Th[0]))
RES["fold_dynamics"] = FD
log("E5 dynamics around the fold: %s" % FD)

# ------------------------------------------------------------------ E6 verification
m = M.Model(100)
Tb, _ = M.solve(m, 40.0, None, dt=0.05, maxit=300, tol=1e-9)
Tinf, _ = M.solve(m, 40.0, 1e9, dt=0.05, maxit=300, tol=1e-9)
Ta_, _ = M.solve(m, 40.0, 0.5, T_init=4.0 + 30.0 * (1 - (m.r / 2.0) ** 2), dt=0.05, maxit=300, tol=1e-9)
Tb_, _ = M.solve(m, 40.0, 0.5, T_init=4.0 + 4.0 * (1 - (m.r / 2.0) ** 2), dt=0.05, maxit=300, tol=1e-9)
RES["verify"] = dict(max_dT_sc_1e9=float(np.max(np.abs(Tb - Tinf))), resid_baseline=float(M.diagnostics(m, Tb, 40.0, None)["resid"]),
                     ic_independence=float(np.max(np.abs(Ta_ - Tb_))))
lam_ = {}
for N_ in (100, 400):
    m_, T_, ok_ = steady(N_, 2.0)
    lam_[str(N_)] = float(S.leading_eigenvalue(m_, T_, 2.0)[0])
RES["verify"]["lambda1_sc2"] = lam_
log("E6 verification: %s" % RES["verify"])

# ------------------------------------------------------------------ E7 closure theory (admissibility) and the rotation equation
TH_ = {"alg": []}
Ls = np.linspace(1e-6, 60, 600001)
for mm in (0.5, 1.0, 1.5, 2.0, 3.0):
    Pp = np.gradient(TH.Psi(Ls, TH.F_alg, m=mm), Ls)
    TH_["alg"].append(dict(m=mm, min_slope=float(Pp.min()), admissible_numeric=bool(Pp.min() > -1e-9), admissible_theory=bool(TH.alg_admissible(mm))))
Lc_ = Ls[:120001]
TH_["floor_alg"] = []
for f in (0.05, 0.10, 0.111, 0.112, 0.15, 0.20):
    Pp = np.gradient(TH.Psi(Lc_, TH.F_floor_alg, f=f), Lc_)
    TH_["floor_alg"].append(dict(f=f, min_slope=float(Pp.min()), admissible=bool(Pp.min() > 0)))
TH_["floor_exp"] = []
for f in (0.10, 0.30, 0.31, 0.40):
    Pp = np.gradient(TH.Psi(Lc_, TH.F_floor_exp, f=f), Lc_)
    TH_["floor_exp"].append(dict(f=f, min_slope=float(Pp.min()), admissible=bool(Pp.min() > 0)))
TH_["thresholds"] = dict(floor_alg=TH.floor_alg_threshold(), floor_exp=TH.floor_exp_threshold(), exp_peak_L=float(TH.exp_nofloor_peak(1.0)[0]),
                         exp_peak_Psi=float(TH.exp_nofloor_peak(1.0)[1]))
Lfine = np.linspace(1e-6, 12, 240001)
TH_["thresholds"]["floor_alg_numeric"] = float(brentq(lambda f: float(np.gradient(TH.Psi(Lfine, TH.F_floor_alg, f=f), Lfine).min()), 0.05, 0.3, xtol=1e-6))
TH_["thresholds"]["floor_exp_numeric"] = float(brentq(lambda f: float(np.gradient(TH.Psi(Lfine, TH.F_floor_exp, f=f), Lfine).min()), 0.1, 0.5, xtol=1e-6))
RES["theory"] = TH_
log("E7a thresholds: %s" % TH_["thresholds"])

m = M.Model(200)
Tprof, _ = M.solve(m, 40.0, None, dt=0.05, maxit=300, tol=1e-9)
gamma = np.sqrt(Tprof * M.KEV / M.M_ION) / m.p["R0"]
gam_f = np.concatenate([[gamma[0]], 0.5 * (gamma[:-1] + gamma[1:]), [gamma[-1]]])
mu0 = 1.0 * np.mean(m.n * M.M_ION) * m.p["chi_s"]
RES["mu0"] = float(mu0)


def theta_faces(tau):
    _, Iface = MO.theta_profile(m, tau, gamma, mu0)
    return Iface / (m.qf * gam_f * mu0 * m.p["R0"] ** 2)


SC = []
for mm in (0.5, 1.0, 2.0):
    for Ttot in (25.0, 50.0, 100.0, 150.0, 200.0, 250.0):
        tau = MO.torque_profile(m, Ttot)
        Om, Lc, ok, Lam = MO.solve_rotation(m, tau, gamma, mu0, lambda L, mm_=mm: TH.F_alg(L, mm_))
        Thf = theta_faces(tau)
        pred = np.array([TH.theta_to_lambda_alg(t, mm) if t > 0 else 0.0 for t in Thf])
        ex_t = bool(np.all(np.isfinite(pred)))
        SC.append(dict(m=mm, torque=Ttot, Theta_max=float(Thf.max()), exists_theory=ex_t, exists_numeric=bool(ok),
                       Lam_sim=float(np.max(Lam)) if ok else None, Lam_pred=float(np.nanmax(pred)) if ex_t else None))
RES["scalar_flux_relation"] = SC
good = [r for r in SC if r["exists_theory"] and r["exists_numeric"]]
RES["scalar_flux_relation_summary"] = dict(n_compared=len(good), max_rel_err=float(max(abs(r["Lam_sim"] / r["Lam_pred"] - 1) for r in good if r["Lam_pred"] > 0)),
                                           agree_on_existence=bool(all(r["exists_theory"] == r["exists_numeric"] for r in SC)))
log("E7b scalar flux relation: %s" % RES["scalar_flux_relation_summary"])


def last_torque(mm):
    def ok_at(Tt):
        tau = MO.torque_profile(m, Tt)
        return MO.solve_rotation(m, tau, gamma, mu0, lambda L: TH.F_alg(L, mm))[2]
    lo, hi = 10.0, 2000.0
    assert ok_at(lo)
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if ok_at(mid):
            lo = mid
        else:
            hi = mid
    return float(lo), float(theta_faces(MO.torque_profile(m, lo)).max())


FOLDROT = {}
for mm, thc in ((2.0, 0.5), (1.0, 1.0)):
    tq, th = last_torque(mm)
    FOLDROT[str(mm)] = dict(torque_last=tq, Theta_last=th, Theta_predicted=thc)
RES["rotation_fold"] = FOLDROT
log("E7c rotation fold: %s" % FOLDROT)

HYS = {}
th_per_torque = float(theta_faces(MO.torque_profile(m, 100.0)).max()) / 100.0     # Theta_max is proportional to the torque
for f in (0.05, 0.20):
    Fn = lambda L, f_=f: TH.F_floor_alg(L, f_)
    torques = [float(x) for x in np.arange(10.0, 301.0, 10.0)]
    up, down = [], []
    Om = np.zeros(m.N) + 1.0
    for Tt in torques:
        Om, Lam, ok = MO.march_rotation(m, MO.torque_profile(m, Tt), gamma, mu0, Fn, Om)
        up.append(float(np.max(Lam)) if ok else None)
    for Tt in torques[::-1]:
        Om, Lam, ok = MO.march_rotation(m, MO.torque_profile(m, Tt), gamma, mu0, Fn, Om)
        down.append(float(np.max(Lam)) if ok else None)
    Lg = np.linspace(1e-4, 10, 200001)
    Pg = TH.Psi(Lg, TH.F_floor_alg, f=f)
    sgn = np.where(np.diff(np.sign(np.gradient(Pg, Lg))) != 0)[0]
    window = None
    if len(sgn) >= 2:
        window = dict(Psi_max=float(Pg[sgn[0]]), Psi_min=float(Pg[sgn[1]]), torque_up=float(Pg[sgn[0]] / th_per_torque), torque_down=float(Pg[sgn[1]] / th_per_torque))
    HYS[str(f)] = dict(torque=torques, up=up, down=down[::-1], predicted=window, Theta_per_Nm=th_per_torque)
RES["rotation_hysteresis"] = HYS
log("E7d rotation hysteresis computed")

# ------------------------------------------------------------------ E8 torque-driven coupled scan
CP = []
TQ = [0.0, 25.0, 50.0, 100.0, 150.0, 200.0, 250.0]
for sign in (1.0, -1.0):
    for clos in ("linear", "m=1", "m=2 f=0.20", "m=2"):
        for Tt in TQ:
            r = C.solve_coupled(100, Tt, 0.5, clos, sign)
            ok = bool(r["ok"])
            CP.append(dict(sign=sign, closure=clos, torque=Tt, ok=ok, Q=(float(r["Q"]) if ok else None), Theta=(r.get("Theta") if ok else None),
                           Lam_rot=(r.get("Lam_rot") if ok else None), ratio_max=(r.get("ratio_max") if ok else None), Mach=(r.get("Mach") if ok else None)))
    log("E8 sign %+d done" % sign)
RES["coupled_scan"] = CP
PR = []
for Pr in (0.5, 1.0, 2.0):
    for clos in ("m=1", "m=2"):
        r = C.solve_coupled(100, 200.0, 0.5, clos, 1.0, Pr=Pr)
        PR.append(dict(Pr=Pr, closure=clos, ok=bool(r["ok"]), Q=(float(r["Q"]) if r["ok"] else None), Theta=r.get("Theta")))
RES["coupled_Pr"] = PR
RES["coupled_sc"] = [dict(sc=s_, Q=float(C.solve_coupled(100, 100.0, s_, "linear", 1.0)["Q"])) for s_ in (2.0, 1.0, 0.5, 0.3, 0.2)]
log("E8 done")
json.dump(RES, open("../results.json", "w"), indent=1)
log("results.json written")
