# -*- coding: utf-8 -*-
"""Every number and figure input in the manuscript. Deterministic (the Sobol sequences of Section E11 are scrambled with a fixed seed). Writes ../results.json.
python reproduce.py   (about 40 minutes)"""
import json
import sys
import time

import numpy as np
import scipy
from scipy.integrate import solve_ivp
from scipy.optimize import brentq
from scipy.sparse import diags

import arclength as A
import calibration as CAL
import coupled as C
import ellipticity as E
import model as M
import momentum as MO
import stability as S
import theory as TH
import uncertainty as U

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
t0 = time.time()
RES = {"versions": {"python": sys.version.split()[0], "numpy": np.__version__, "scipy": scipy.__version__}}
LREF = 0.05          # reference smoothing length of the adaptive-field closure (m)
RES["l_ref"] = LREF
SC_STEPS = (4.0, 2.0, 1.0, 0.7, 0.5, 0.4, 0.3, 0.2, 0.15, 0.1, 0.07, 0.05, 0.04, 0.03, 0.02)


def log(msg):
    print("[%5.0f s] %s" % (time.time() - t0, msg), flush=True)
    json.dump(RES, open("../results_partial.json", "w"), default=float)       # checkpoint after every block


def steady(N, sc, P_aux=40.0, **kw):
    """Steady state on the branch connected to the baseline: pseudo-time march of the baseline, then Newton continuation in s_c."""
    m = M.Model(N, **kw)
    T, _ = M.solve(m, P_aux, None, dt=0.05, maxit=300, tol=1e-9)
    if sc is not None:
        for s_ in [x for x in SC_STEPS if x > sc] + [sc]:
            T, ok = S.steady_newton(m, s_, T, P_aux)
            if not ok:
                return m, T, False
    return m, T, True


# ------------------------------------------------------------------ E0 model checks
RES["bosch_hale"] = {"sigma_v_10keV": float(M.sigma_v(10.0)), "sigma_v_20keV": float(M.sigma_v(20.0))}
log("E0 Bosch-Hale <sigma v> at 10 and 20 keV: %.4e %.4e" % (M.sigma_v(10.0), M.sigma_v(20.0)))

# ------------------------------------------------------------------ E1 controlled comparison (regularised closure, N = 400) and operating-point benchmark
SCS = [None, 1.0, 0.5, 0.3, 0.2, 0.15, 0.1, 0.07, 0.05, 0.03, 0.02]
rows, base_Q = [], None
for sc in SCS:
    m, T, ok = steady(400, sc)
    d = M.diagnostics(m, T, 40.0, sc)
    op = CAL.operating_point(m, T, d)
    lam = S.leading_eigenvalue(m, T, sc)[0]
    if sc is None:
        base_Q = d["Q"]
    rows.append(dict(sc=sc, ok=bool(ok), Q=float(d["Q"]), Pfus=float(d["Pfus"]), tauE=float(d["tauE"]), Tavg=float(d["Tavg"]), T0=float(d["T0"]), ratio_max=float(d["ratio_max"]),
                     resid=float(d["resid"]), dQ=float(d["Q"] / base_Q - 1.0), chi_min_over_base=float(np.min(d["chi"] / d["chib"])), lam1=float(lam),
                     H98=float(op["H98"]), H89=float(op["H89"]), beta_N=float(op["beta_N"]), f_G=float(op["f_G"]), P_net=float(op["P_net"]), tau98=float(op["tau98"]),
                     tau89=float(op["tau89"])))
RES["table1"] = rows
log("E1 Table 1 done: %s" % [(r["sc"], round(r["Q"], 4)) for r in rows])
sel = [r for r in rows if r["sc"] is not None and r["sc"] >= 0.2]
Cs = [r["sc"] ** 2 * (r["Q"] - base_Q) for r in sel]
RES["linear_response"] = dict(C_mean=float(np.mean(Cs)), C_min=float(np.min(Cs)), C_max=float(np.max(Cs)), sc_min=0.2)
log("E1 linear response C = %.5f (range %.5f-%.5f)" % (np.mean(Cs), np.min(Cs), np.max(Cs)))
prof = {}
for key, sc in (("baseline", None), ("sc0.3", 0.3), ("sc0.1", 0.1)):
    m, T, ok = steady(400, sc)
    d = M.diagnostics(m, T, 40.0, sc)
    prof[key] = dict(r=m.r.tolist(), T=T.tolist(), chi=d["chi"].tolist(), chib=d["chib"].tolist(), ratio=d["ratio"].tolist(), Q=float(d["Q"]))
RES["profiles"] = prof
log("E1 profiles stored")

# ------------------------------------------------------------------ E2 auxiliary-power scan
PA = [10, 15, 20, 30, 40, 50, 60, 70, 80]
scan = {}
for key, sc in (("baseline", None), ("sc0.5", 0.5), ("sc0.3", 0.3), ("sc0.1", 0.1)):
    qs = []
    for P in PA:
        m, T, ok = steady(200, sc, float(P))
        d = M.diagnostics(m, T, float(P), sc)
        qs.append(dict(P=P, Q=float(d["Q"]), ok=bool(ok), tauE=float(d["tauE"])))
    scan[key] = qs
RES["paux_scan"] = {"P": PA, **scan}
log("E2 power scan done")

# ------------------------------------------------------------------ E3 grid convergence of the regularised closure
GR = {}
NS = (100, 200, 400, 800)
for sc in (None, 0.5, 0.2, 0.1, 0.05):
    row = []
    for N in NS:
        m, T, ok = steady(N, sc)
        d = M.diagnostics(m, T, 40.0, sc)
        row.append(dict(N=N, ok=bool(ok), Q=float(d["Q"]), T0=float(d["T0"]), ratio_max=float(d["ratio_max"]), resid=float(d["resid"]),
                        lam1=float(S.leading_eigenvalue(m, T, sc)[0]) if N <= 400 else None))
    GR["none" if sc is None else str(sc)] = row
    log("E3 s_c=%s: Q(N) = %s" % (sc, [round(r["Q"], 5) for r in row]))
orders = {}
for k, row in GR.items():
    q = [r["Q"] for r in row]
    dq = np.diff(q)
    orders[k] = [float(np.log2(abs(dq[i] / dq[i + 1]))) if dq[i] * dq[i + 1] > 0 else None for i in range(len(dq) - 1)]
RES["grid"] = {"N": list(NS), "rows": GR, "observed_order": orders}
log("E3 observed orders %s" % {k: [None if o is None else round(o, 2) for o in v] for k, v in orders.items()})


# ------------------------------------------------------------------ E3b resolution limit of the smoothed closure at very strong coupling
SM_TH = {}
SC_SM = [0.05, 0.04, 0.034, 0.028, 0.025, 0.02, 0.015]
for N in (100, 200, 400, 800):
    m = M.Model(N)
    T, _ = M.solve(m, 40.0, None, dt=0.05, maxit=300, tol=1e-9)
    for s_ in [x for x in SC_STEPS if x > SC_SM[0]]:
        T, ok = S.steady_newton(m, s_, T)
    lam = {}
    for sc in SC_SM:
        T, ok = S.steady_newton(m, sc, T)
        if not ok:
            lam[str(sc)] = None
            break
        lam[str(sc)] = float(S.leading_eigenvalue(m, T, sc)[0])
    unstable = [float(k) for k, v in lam.items() if v is not None and v > 0]
    SM_TH[str(N)] = dict(lam=lam, threshold=(max(unstable) if unstable else None))
    log("E3b smoothed closure N=%d: threshold %s" % (N, SM_TH[str(N)]["threshold"]))
RES["smoothed_threshold"] = SM_TH

# ------------------------------------------------------------------ E4 the local closure (no smoothing) is ill-posed
LOC = {}
SC_GRID = [1.0, 0.7, 0.5, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15, 0.1]
for N in (50, 100, 200, 400):
    m = M.Model(N, reg_length=0.0)
    T, _ = M.solve(m, 40.0, None, dt=0.05, maxit=300, tol=1e-9)
    row = []
    for sc in SC_GRID:
        T, ok = S.steady_newton(m, sc, T)
        if not ok:
            row.append(dict(sc=sc, ok=False))
            break
        lam, im, vec, _ = S.leading_eigenvalue(m, T, sc)
        v = vec / np.max(np.abs(vec))
        row.append(dict(sc=sc, ok=True, lam1=float(lam), Q=float(M.diagnostics(m, T, 40.0, sc)["Q"]), peak_from_edge=int(m.N - 1 - np.argmax(np.abs(v)))))
    LOC[str(N)] = row
    log("E4 local closure N=%d: %s" % (N, [(r["sc"], ("%.3g" % r["lam1"]) if r["ok"] else "FAIL") for r in row]))


def threshold(N):
    """Largest s_c (bisection on the Newton branch) at which the leading eigenvalue of the local closure is positive."""
    m = M.Model(N, reg_length=0.0)
    T, _ = M.solve(m, 40.0, None, dt=0.05, maxit=300, tol=1e-9)
    Tc, lam = {}, {}
    for sc in SC_GRID:
        T, ok = S.steady_newton(m, sc, T)
        Tc[sc] = T.copy()
        lam[sc] = S.leading_eigenvalue(m, T, sc)[0]
    unstable = [sc for sc in SC_GRID if lam[sc] >= 0]
    if not unstable:
        return None
    lo = max(unstable)
    above = [sc for sc in SC_GRID if sc > lo]
    if not above:
        return None
    hi = min(above)
    Tg = Tc[hi]
    for _ in range(14):
        mid = 0.5 * (lo + hi)
        Tm, ok = S.steady_newton(m, mid, Tg)
        if not ok:
            break
        if S.leading_eigenvalue(m, Tm, mid)[0] < 0:
            hi, Tg = mid, Tm
        else:
            lo = mid
    return 0.5 * (lo + hi)


TH_LIN = {}
for N in (50, 100, 200, 400):
    TH_LIN[str(N)] = threshold(N)
    log("E4 threshold s_c^lin(N=%d) = %s" % (N, TH_LIN[str(N)]))
ths = [(N, TH_LIN[str(N)]) for N in (100, 200, 400) if TH_LIN[str(N)]]
expo = float(np.polyfit(np.log([t[0] for t in ths]), np.log([t[1] for t in ths]), 1)[0]) if len(ths) >= 2 else None
RES["local_closure"] = dict(rows=LOC, threshold=TH_LIN, threshold_exponent=expo)
log("E4 threshold grows as N^%s" % expo)
ELL = []
m = M.Model(400, reg_length=0.0)
T, _ = M.solve(m, 40.0, None, dt=0.05, maxit=300, tol=1e-9)
for sc in (1e9, 1.0, 0.5, 0.3, 0.2, 0.15):
    T, ok = S.steady_newton(m, sc, T)
    rc, D, D1, D2 = E.d_eff(m, T, sc)
    ELL.append(dict(sc=sc, Dmin=float(D.min()), r_over_a=float(rc[int(np.argmin(D))] / 2.0), D2_min=float(D2.min())))
RES["principal_part"] = ELL
log("E4 principal part: min D_eff = %s" % [round(e["Dmin"], 4) for e in ELL])

# ------------------------------------------------------------------ E5 dependence on the edge condition and on the smoothing length
VAR = []
variants = [("local, first-order edge", dict(reg_length=0.0, stencil="first")),
            ("local, second-order edge", dict(reg_length=0.0)),
            ("local, edge value held", dict(reg_length=0.0, edge_shear="hold")),
            ("local, no suppression in the last cell", dict(reg_length=0.0, edge_shear="zero")),
            ("smoothed, l = 0.02 m", dict(reg_length=0.02)),
            ("smoothed, l = 0.05 m", dict(reg_length=0.05)),
            ("smoothed, l = 0.10 m", dict(reg_length=0.10)),
            ("smoothed, l = 0.20 m", dict(reg_length=0.20))]
for name, kw in variants:
    rec = dict(name=name)
    for sc in (0.1, 0.05):
        for N in (200, 400):
            m, T, ok = steady(N, sc, **kw)
            if ok:
                rec["Q@%g/N%d" % (sc, N)] = float(M.diagnostics(m, T, 40.0, sc)["Q"])
                rec["lam@%g/N%d" % (sc, N)] = float(S.leading_eigenvalue(m, T, sc)[0])
            else:
                rec["Q@%g/N%d" % (sc, N)] = None
                rec["lam@%g/N%d" % (sc, N)] = None
    VAR.append(rec)
    log("E5 %s: %s" % (name, {k: (None if v is None else round(v, 3)) for k, v in rec.items() if k != "name"}))
RES["edge_variants"] = VAR
m_, pts = A.branch(400, p_max=40.0, ds=0.3, max_pts=600, stop_after_fold=6, reg_length=0.0, stencil="first")
mu = np.array([q["p"] for q in pts])
k = int(np.argmax(mu))
x = np.arange(k - 1, k + 2)
c = np.polyfit(x, mu[k - 1:k + 2], 2)
xm = -c[1] / (2 * c[0])
RES["first_order_fold_N400"] = dict(sc_fold=float(1.0 / np.polyval(c, xm)), Q_fold=float(np.interp(xm, x, [pts[i]["Q"] for i in x])))
log("E5 first-order edge treatment shows a fold at %s" % RES["first_order_fold_N400"])


# ------------------------------------------------------------------ E6 independent time integration and dynamic accessibility
def integrate(m, sc, T0, tend=60.0, P_aux=40.0, stop_T0=None, rtol=1e-8, atol=1e-8):
    Sx = m.source_aux(P_aux)
    cT = 3.0 * m.n * M.KEV
    f = lambda t, T: M.residual(m, T, Sx, sc) / cT
    N = m.N
    kw = {}
    if m.p["reg_length"] == 0.0:
        kw["jac_sparsity"] = diags([np.ones(N - abs(k_)) for k_ in range(-3, 4)], list(range(-3, 4)), shape=(N, N)).tocsr()
    ev = None
    if stop_T0 is not None:
        ev = lambda t, T: T[0] - stop_T0
        ev.terminal = True
        ev.direction = 1
    sol = solve_ivp(f, (0.0, tend), T0, method="Radau", rtol=rtol, atol=atol, events=ev, **kw)
    return sol.y[:, -1], sol


TI = []
for sc in (None, 0.5, 0.1, 0.05):
    m, Tn, ok = steady(100, sc)
    Tt, sol = integrate(m, sc, 4.0 + 8.0 * (1 - (m.r / 2.0) ** 2), tend=100.0)
    TI.append(dict(sc=sc, max_abs_dT=float(np.max(np.abs(Tt - Tn))), Q_ivp=float(M.diagnostics(m, Tt, 40.0, sc)["Q"]), Q_newton=float(M.diagnostics(m, Tn, 40.0, sc)["Q"])))
RES["time_integration"] = TI
log("E6 time integration vs Newton (smoothed): %s" % [(r["sc"], "%.1e" % r["max_abs_dT"]) for r in TI])
ACC = {"smoothed": [], "local": []}
for key, kw in (("smoothed", dict(reg_length=LREF)), ("local", dict(reg_length=0.0))):
    for sc in (1.0, 0.5, 0.3, 0.2, 0.1, 0.05):
        m = M.Model(100, **kw)
        Tt, sol = integrate(m, sc, 4.0 + 8.0 * (1 - (m.r / 2.0) ** 2), tend=120.0, stop_T0=150.0, rtol=1e-7, atol=1e-7)
        d = M.diagnostics(m, Tt, 40.0, sc)
        ACC[key].append(dict(sc=sc, settled=bool(Tt[0] < 150.0 - 1e-6), t_end=float(sol.t[-1]), T0=float(Tt[0]), Q=float(d["Q"])))
    log("E6 cold-start accessibility (%s): %s" % (key, [(r["sc"], r["settled"]) for r in ACC[key]]))
RES["accessibility"] = ACC

# ------------------------------------------------------------------ E7 verification
m = M.Model(100)
Tb, _ = M.solve(m, 40.0, None, dt=0.05, maxit=300, tol=1e-9)
Tinf, _ = M.solve(m, 40.0, 1e9, dt=0.05, maxit=300, tol=1e-9)
Ta_, _ = M.solve(m, 40.0, None, T_init=4.0 + 30.0 * (1 - (m.r / 2.0) ** 2), dt=0.05, maxit=300, tol=1e-9)
Tb_, _ = M.solve(m, 40.0, None, T_init=4.0 + 4.0 * (1 - (m.r / 2.0) ** 2), dt=0.05, maxit=300, tol=1e-9)
lam_ = {}
for N_ in (100, 400):
    m_, T_, ok_ = steady(N_, 2.0)
    lam_[str(N_)] = float(S.leading_eigenvalue(m_, T_, 2.0)[0])
resid = {}
for sc in (None, 0.5, 0.1, 0.03):
    m_, T_, ok_ = steady(200, sc)
    resid["none" if sc is None else str(sc)] = float(M.diagnostics(m_, T_, 40.0, sc)["resid"])
RES["verify"] = dict(max_dT_sc_1e9=float(np.max(np.abs(Tb - Tinf))), resid=resid, ic_independence=float(np.max(np.abs(Ta_ - Tb_))), lambda1_sc2=lam_)
log("E7 verification: %s" % RES["verify"])

# ------------------------------------------------------------------ E8 closure theory (admissibility) and the rotation equation
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
log("E8a thresholds: %s" % TH_["thresholds"])

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
        SC.append(dict(m=mm, torque=Ttot, Theta_max=float(Thf.max()), exists_theory=ex_t, exists_numeric=bool(ok), Lam_sim=float(np.max(Lam)) if ok else None,
                       Lam_pred=float(np.nanmax(pred)) if ex_t else None))
RES["scalar_flux_relation"] = SC
good = [r for r in SC if r["exists_theory"] and r["exists_numeric"]]
RES["scalar_flux_relation_summary"] = dict(n_compared=len(good), max_rel_err=float(max(abs(r["Lam_sim"] / r["Lam_pred"] - 1) for r in good if r["Lam_pred"] > 0)),
                                           agree_on_existence=bool(all(r["exists_theory"] == r["exists_numeric"] for r in SC)))
log("E8b scalar flux relation: %s" % RES["scalar_flux_relation_summary"])


def last_torque(mm):
    def ok_at(Tt):
        return MO.solve_rotation(m, MO.torque_profile(m, Tt), gamma, mu0, lambda L: TH.F_alg(L, mm))[2]
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
log("E8c rotation fold: %s" % FOLDROT)

HYS = {}
th_per_torque = float(theta_faces(MO.torque_profile(m, 100.0)).max()) / 100.0
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
log("E8d rotation hysteresis computed")

# ------------------------------------------------------------------ E9 torque-driven coupled scan (smoothed heat closure)
CP = []
TQ = [0.0, 25.0, 50.0, 100.0, 150.0, 200.0, 250.0]
for sign in (1.0, -1.0):
    for clos in ("linear", "m=1", "m=2 f=0.20", "m=2"):
        for Tt in TQ:
            r = C.solve_coupled(100, Tt, 0.5, clos, sign)
            ok = bool(r["ok"])
            CP.append(dict(sign=sign, closure=clos, torque=Tt, ok=ok, Q=(float(r["Q"]) if ok else None), Theta=(r.get("Theta") if ok else None),
                           Lam_rot=(r.get("Lam_rot") if ok else None), ratio_max=(r.get("ratio_max") if ok else None), Mach=(r.get("Mach") if ok else None)))
    log("E9 sign %+d done" % sign)
RES["coupled_scan"] = CP
PR = []
for Pr in (1.0, 2.0, 4.0):
    for clos in ("linear", "m=1", "m=2"):
        r = C.solve_coupled(100, 200.0, 0.5, clos, 1.0, Pr=Pr)
        PR.append(dict(Pr=Pr, closure=clos, ok=bool(r["ok"]), Q=(float(r["Q"]) if r["ok"] else None), Theta=r.get("Theta")))
RES["coupled_Pr"] = PR
TS = []
for s_ in (1.0, 0.5, 0.3, 0.2):
    row = []
    for Tt in (0.0, 25.0, 36.0, 50.0, 100.0, 200.0):
        r = C.solve_coupled(100, Tt, s_, "linear", 1.0)
        row.append(dict(torque=Tt, Q=float(r["Q"])))
    TS.append(dict(sc=s_, rows=row))
RES["coupled_sc_torque"] = TS
log("E9 torque x s_c table done")

# ------------------------------------------------------------------ E10 physical calibration
tq_nbi = {str(Rt): float(CAL.nbi_torque(R_tan=Rt)[0]) for Rt in (4.5, 5.3, 6.0)}
RES["calibration"] = dict(nbi_torque=tq_nbi, v_beam=float(CAL.nbi_torque()[1]), rho_i_10keV=float(CAL.ion_gyroradius(10.0, 5.3)), ref=CAL.REF,
                          n_G=float(CAL.REF["I_MA"] / (np.pi * 4.0)))
log("E10 calibration: %s" % RES["calibration"])

# ------------------------------------------------------------------ E11 uncertainty and sensitivity (Sobol, fixed seed)
SCU = [0.3, 0.1, 0.05]
u = U.sobol_points(U.HEAT_BOUNDS, 7)
UR = []
for ui in u:
    par = U.scaled(ui, U.HEAT_BOUNDS)
    r = U.heat_sample(par, SCU, N=100)
    if r is None:
        UR.append(None)
        continue
    r["par"] = par
    for sc in SCU:
        r["gain@%g" % sc] = r["Q@%g" % sc] / r["Q0"] - 1.0 if np.isfinite(r["Q@%g" % sc]) else float("nan")
    UR.append(r)
okU = [r for r in UR if r is not None]
stats = {"n_samples": len(UR), "n_ok": len(okU)}
for sc in SCU:
    g = np.array([r["gain@%g" % sc] for r in okU if np.isfinite(r["gain@%g" % sc])])
    rc, n_ok = U.rank_corr(UR, U.HEAT_BOUNDS, "gain@%g" % sc)
    stats["gain@%g" % sc] = dict(n=int(len(g)), p05=float(np.percentile(g, 5)), p50=float(np.percentile(g, 50)), p95=float(np.percentile(g, 95)), rank_corr=rc)
q0 = np.array([r["Q0"] for r in okU])
stats["Q0"] = dict(p05=float(np.percentile(q0, 5)), p50=float(np.percentile(q0, 50)), p95=float(np.percentile(q0, 95)))
RES["uncertainty_heat"] = dict(stats=stats, bounds={k: v[:2] for k, v in U.HEAT_BOUNDS.items()}, seed=U.SEED)
log("E11 heat-closure uncertainty: %s" % {k: v for k, v in stats.items() if k != "n_samples"})
u2 = U.sobol_points(U.TORQUE_BOUNDS, 6)
TR = []
for ui in u2:
    par = U.scaled(ui, U.TORQUE_BOUNDS)
    r = U.torque_sample(par)
    if r is None:
        TR.append(None)
        continue
    r["par"] = par
    r["gain"] = r["Q"] / r["Q_notorque"] - 1.0
    TR.append(r)
okT = [r for r in TR if r is not None]
gt = np.array([r["gain"] for r in okT])
rct, nT = U.rank_corr(TR, U.TORQUE_BOUNDS, "gain")
RES["uncertainty_torque"] = dict(n_samples=len(TR), n_ok=len(okT), p05=float(np.percentile(gt, 5)), p50=float(np.percentile(gt, 50)), p95=float(np.percentile(gt, 95)), rank_corr=rct,
                                 bounds={k: v[:2] for k, v in U.TORQUE_BOUNDS.items()})
log("E11 torque uncertainty: %s" % {k: v for k, v in RES["uncertainty_torque"].items() if k != "bounds"})
json.dump(RES, open("../results.json", "w"), indent=1)
log("results.json written")
