# -*- coding: utf-8 -*-
"""Pseudo-arclength continuation of the steady states of the heat equation in the coupling parameter p = 1/s_c^2 (p = 0 is the baseline)."""
import numpy as np
import model as M
import stability as S


def residual_p(m, T, mu, Sx):
    """mu = 1/s_c (mu = 0: baseline)."""
    sc = None if mu <= 1e-12 else 1.0 / mu
    return M.residual(m, T, Sx, sc)


def jac_p(m, T, p, Sx, dp=None):
    N = m.N
    R = residual_p(m, T, p, Sx)
    J = np.zeros((N, N)); h = 1e-8 * np.maximum(T, 1.0)
    for j in range(N):
        Tp = T.copy(); Tp[j] += h[j]; Tm = T.copy(); Tm[j] -= h[j]
        J[:, j] = (residual_p(m, Tp, p, Sx) - residual_p(m, Tm, p, Sx)) / (2 * h[j])
    dp = 1e-6 * max(abs(p), 1e-2) if dp is None else dp
    Fp = (residual_p(m, T, p + dp, Sx) - residual_p(m, T, p - dp, Sx)) / (2 * dp)
    return R, J, Fp


def branch(N, p_max=25.0, ds=0.05, max_pts=400, P_aux=40.0, T_start=None, verbose=False, mu0=0.3, stop_after_fold=0, **model_kw):
    """Follow the branch starting at the baseline (p = 0) toward increasing p with pseudo-arclength steps; returns dict of arrays."""
    m = M.Model(N, **model_kw)
    Sx = m.source_aux(P_aux)
    scale = P_aux * 1e6 / np.sum(m.vol)
    cT = 3 * m.n * M.KEV
    T, _ = M.solve(m, P_aux, None, dt=0.05, maxit=300, tol=1e-9)
    T, ok = S.steady_newton(m, 1.0 / mu0, T, P_aux)
    p = mu0
    W = lambda T_: np.sqrt(np.mean(T_ ** 2))
    pts = []

    def record(T_, p_):
        d = M.diagnostics(m, T_, P_aux, None if p_ <= 1e-12 else 1.0 / p_)
        R, J, Fp = jac_p(m, T_, p_, Sx)
        lam = np.max(np.linalg.eigvals(J / cT[:, None]).real)
        pts.append(dict(p=p_, sc=(np.inf if p_ <= 0 else 1.0 / p_), Q=float(d["Q"]), T0=float(T_[0]), lam=float(lam), ratio_max=float(d["ratio_max"]), Tavg=float(d["Tavg"]), tauE=float(d["tauE"])))

    # initial tangent: dT/dp from J dT = -Fp, direction of increasing p
    R, J, Fp = jac_p(m, T, p, Sx)
    v = np.linalg.solve(J, -Fp)
    t = np.concatenate([v, [1.0]]); t /= np.linalg.norm(t * np.concatenate([np.ones(N) / 10.0, [1.0]]))   # scaled norm: T in units of 10 keV
    record(T, p)
    sc_vec = np.concatenate([np.ones(N) / 10.0, [1.0]])
    ds_cur = ds
    for k in range(max_pts):
        step = ds_cur
        ok = False
        iters_used = 0
        for attempt in range(12):
            Tp_ = T + step * t[:N]; pp = p + step * t[N]
            pp = max(pp, 1e-3)
            x = np.concatenate([Tp_, [pp]])
            conv = False
            for it in range(25):
                R = residual_p(m, x[:N], x[N], Sx)
                g = np.dot((x - np.concatenate([T, [p]])) * sc_vec ** 2, t) - step
                if np.max(np.abs(R)) / scale < 1e-8 and abs(g) < 1e-10:
                    conv = True; iters_used = it; break
                R_, J, Fp = jac_p(m, x[:N], x[N], Sx)
                A = np.zeros((N + 1, N + 1))
                A[:N, :N] = J; A[:N, N] = Fp
                A[N, :N] = t[:N] * (1 / 10.0) ** 2; A[N, N] = t[N]
                rhs = -np.concatenate([R_, [g]])
                try:
                    dx = np.linalg.solve(A, rhs)
                except np.linalg.LinAlgError:
                    break
                x = x + dx
                if x[:N].min() < 4.0 - 1e-9 or x[:N].max() > 600.0 or not np.all(np.isfinite(x)):
                    break
            if conv:
                ok = True; break
            step *= 0.5
        if not ok:
            if verbose: print("continuation stopped at", p)
            break
        # new tangent
        Tn, pn = x[:N], x[N]
        R, J, Fp = jac_p(m, Tn, pn, Sx)
        A = np.zeros((N + 1, N + 1)); A[:N, :N] = J; A[:N, N] = Fp; A[N, :N] = t[:N] * (1 / 10.0) ** 2; A[N, N] = t[N]
        tn = np.linalg.solve(A, np.concatenate([np.zeros(N), [1.0]]))
        tn /= np.linalg.norm(tn * sc_vec)
        if np.dot(tn * sc_vec ** 2, t) < 0:
            tn = -tn
        T, p, t = Tn, pn, tn
        ds_cur = min(step * (1.8 if iters_used <= 3 else (1.0 if iters_used <= 6 else 0.6)), 3.0)
        record(T, p)
        if verbose and k % 10 == 0:
            print(k, "p %.3f s_c %.4f Q %.4f lam %.3f" % (pts[-1]["p"], pts[-1]["sc"], pts[-1]["Q"], pts[-1]["lam"]), flush=True)
        if p > p_max:
            break
        if stop_after_fold and len(pts) > 3 and pts[-1]["p"] < max(q["p"] for q in pts):
            stop_after_fold -= 1
            if stop_after_fold == 0:
                break
    return m, pts
