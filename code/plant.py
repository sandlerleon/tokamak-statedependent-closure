# -*- coding: utf-8 -*-
"""Screening-level plant power balance and relative cost proxy, as post-processing of fusion powers computed by the transport model.

Nothing here is a plant design. The efficiencies and overheads are assumptions (ASSUME), varied over ranges in `block`; the cost proxy is relative to the reference
device and has an assumed heating share. Inputs are fusion power and auxiliary power from results already in RES (no new transport solves).

    P_th    = P_fus (f_n M + f_a) + P_aux            neutron fraction f_n = 14.06/17.59, alpha fraction f_a = 1 - f_n, blanket multiplication M,
                                                     all injected heating power ends as heat
    P_gross = eta_th P_th
    P_recirc= P_aux / eta_aux + P_other              heating wall-plug efficiency, cryogenics/pumps/tritium/control
    P_net   = P_gross - P_recirc ;  Q_eng = P_gross / P_recirc
    C_rel   = 1 + kappa (P_aux / P_ref - 1) ;  J = P_net / C_rel     (kappa: share of the reference capital cost that scales with heating power)
"""
import numpy as np
from scipy.stats import qmc

F_N = 14.06 / 17.59
F_A = 1.0 - F_N
P_REF = 40.0
SEED = 20261009
ASSUME = {"eta_th": 0.40, "M": 1.2, "eta_aux": 0.40, "P_other": 30.0, "kappa": 0.10}
BOUNDS = {"eta_th": (0.33, 0.45), "M": (1.1, 1.3), "eta_aux": (0.30, 0.50), "P_other": (10.0, 60.0), "kappa": (0.05, 0.20)}


def balance(Pfus, Paux, a=None):
    a = a or ASSUME
    Pth = Pfus * (F_N * a["M"] + F_A) + Paux
    Pg = a["eta_th"] * Pth
    Pr = Paux / a["eta_aux"] + a["P_other"]
    Pn = Pg - Pr
    C = 1.0 + a["kappa"] * (Paux / P_REF - 1.0)
    return dict(Pfus=Pfus, Pth=Pth, Pgross=Pg, Precirc=Pr, Pnet=Pn, Qeng=Pg / Pr, C=C, J=Pn / C)


def q_breakeven(Paux, a=None):
    """Physical gain Q = P_fus/P_aux at which P_net = 0 for the given P_aux."""
    a = a or ASSUME
    return ((Paux / a["eta_aux"] + a["P_other"]) / a["eta_th"] - Paux) / ((F_N * a["M"] + F_A) * Paux)


def block(RES):
    t1 = {(r["sc"] if r["sc"] is not None else "base"): r for r in RES["table1"]}
    cst = {r["sc"]: {x["torque"]: x["Q"] for x in r["rows"]} for r in RES["coupled_sc_torque"]}
    cases = [("baseline", t1["base"]["Pfus"]), ("smoothed, s_c = 0.3", t1[0.3]["Pfus"]), ("smoothed, s_c = 0.1", t1[0.1]["Pfus"]), ("smoothed, s_c = 0.05", t1[0.05]["Pfus"]),
             ("s_c = 0.5, 36 N m", cst[0.5][36.0] * P_REF), ("s_c = 0.5, 200 N m", cst[0.5][200.0] * P_REF)]
    out = {"assume": ASSUME, "bounds": BOUNDS, "f_n": F_N, "cases": [], "q_breakeven_40": q_breakeven(P_REF)}
    base = balance(cases[0][1], P_REF)
    for name, pf in cases:
        r = balance(pf, P_REF)
        r["name"] = name
        r["dPnet"] = r["Pnet"] - base["Pnet"]
        out["cases"].append(r)
    # power scan: net electric power against auxiliary power
    ps = RES["paux_scan"]
    scan = {}
    for key in ("baseline", "sc0.5", "sc0.3", "sc0.1"):
        rows = []
        for P, d in zip(ps["P"], ps[key]):
            r = balance(d["Q"] * P, float(P))
            rows.append(dict(P=P, Q=d["Q"], Pnet=r["Pnet"], Qeng=r["Qeng"], J=r["J"]))
        scan[key] = rows
    out["scan"] = scan
    # assumption uncertainty (scrambled Sobol, fixed seed): 2^8 points over the 5 assumptions
    u = qmc.Sobol(d=len(BOUNDS), scramble=True, seed=SEED).random_base2(8)
    names = list(BOUNDS)
    keys = [("baseline", "base"), ("smoothed, s_c = 0.1", 0.1), ("smoothed, s_c = 0.05", 0.05)]
    res = {k: [] for k, _ in keys}
    best = []
    dP = {0.1: [], 0.05: []}
    for ui in u:
        a = {n: BOUNDS[n][0] + x * (BOUNDS[n][1] - BOUNDS[n][0]) for n, x in zip(names, ui)}
        pn = {}
        for k, sc in keys:
            pn[sc] = balance(t1[sc]["Pfus"], P_REF, a)["Pnet"]
            res[k].append(pn[sc])
        for sc in (0.1, 0.05):
            dP[sc].append(pn[sc] - pn["base"])
        best.append(max(balance(d["Q"] * P, float(P), a)["Pnet"] for P, d in zip(ps["P"], ps["baseline"])))
    pct = lambda v: dict(p05=float(np.percentile(v, 5)), p50=float(np.percentile(v, 50)), p95=float(np.percentile(v, 95)))
    out["uncertainty"] = {"n": len(u), "seed": SEED,
                          "Pnet": {k: dict(pct(v), frac_positive=float(np.mean(np.array(v) > 0))) for k, v in res.items()},
                          "dPnet": {str(k): pct(v) for k, v in dP.items()},
                          "best_over_Paux_baseline": dict(pct(best), frac_positive=float(np.mean(np.array(best) > 0)))}
    return out
