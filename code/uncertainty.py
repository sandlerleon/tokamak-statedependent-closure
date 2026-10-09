# -*- coding: utf-8 -*-
"""Parameter-uncertainty and sensitivity study with a scrambled Sobol sequence (fixed seed; the sequence is deterministic). Outputs: gain of the regularised closure
relative to its own baseline, and Spearman rank correlations with the sampled parameters."""
import numpy as np
from scipy.stats import qmc, spearmanr

import coupled as C
import model as M
import stability as S

SEED = 20261008
HEAT_BOUNDS = {                # name: (low, high, log?)
    "chi_s": (0.7, 1.4, False),
    "kappa_c": (3.6, 4.4, False),
    "w": (0.3, 0.7, False),
    "Ta": (3.0, 5.0, False),
    "n0": (0.8e20, 1.2e20, False),
    "B": (4.8, 5.8, False),
    "reg_length": (0.02, 0.10, False),
}
TORQUE_BOUNDS = {
    "torque": (25.0, 200.0, False),
    "width": (0.2, 0.6, False),
    "Pr": (1.0, 4.0, True),
    "s_c": (0.2, 1.0, True),
    "sign": (-1.0, 1.0, False),                 # thresholded at 0
    "reg_length": (0.02, 0.10, False),
}


def scaled(u, bounds):
    out = {}
    for i, (k, (lo, hi, lg)) in enumerate(bounds.items()):
        out[k] = float(np.exp(np.log(lo) + u[i] * (np.log(hi) - np.log(lo)))) if lg else float(lo + u[i] * (hi - lo))
    return out


def sobol_points(bounds, n_log2):
    return qmc.Sobol(d=len(bounds), scramble=True, seed=SEED).random_base2(m=n_log2)


def heat_sample(par, sc_list, N=100):
    """Baseline Q and closure Q at each s_c for one sampled parameter set; NaN where no steady state was found."""
    kw = {k: v for k, v in par.items()}
    m = M.Model(N, **kw)
    try:
        T, _ = M.solve(m, 40.0, None, dt=0.05, maxit=300, tol=1e-9)
        d0 = M.diagnostics(m, T, 40.0, None)
        if abs(d0["resid"]) > 1e-6:
            raise RuntimeError("baseline not converged")
    except Exception:
        return None
    out = dict(Q0=float(d0["Q"]), tauE0=float(d0["tauE"]))
    Tc = T
    for sc in sorted(sc_list, reverse=True):
        ok = True
        for s_ in [x for x in (1.0, 0.5, 0.3, 0.2, 0.15, 0.1, 0.07) if x > sc] + [sc]:
            Tc, ok = S.steady_newton(m, s_, Tc)
            if not ok:
                break
        out["Q@%g" % sc] = float(M.diagnostics(m, Tc, 40.0, sc)["Q"]) if ok else float("nan")
    return out


def torque_sample(par, N=100):
    sign = 1.0 if par["sign"] >= 0 else -1.0
    r = C.solve_coupled(N, par["torque"], par["s_c"], "linear", sign, Pr=par["Pr"], width=par["width"], reg_length=par["reg_length"])
    if not r["ok"]:
        return None
    base = C.solve_coupled(N, 0.0, par["s_c"], "linear", sign, reg_length=par["reg_length"])
    return dict(Q=float(r["Q"]), Q_notorque=float(base["Q"]), Theta=float(r.get("Theta", 0.0)), Mach=float(r.get("Mach", 0.0)))


def rank_corr(rows, bounds, key):
    """Spearman rank correlation of each sampled parameter with the output `key`."""
    ok = [r for r in rows if r is not None and np.isfinite(r.get(key, np.nan))]
    res = {}
    for k in bounds:
        x = [r["par"][k] for r in ok]
        y = [r[key] for r in ok]
        c = spearmanr(x, y)
        res[k] = float(c.statistic if hasattr(c, "statistic") else c[0])
    return res, len(ok)
