# -*- coding: utf-8 -*-
"""Steady states (stable or not) by damped Newton, linear stability of the semi-discrete system dT/dt = R(T)/(3 n e), and continuation in s_c."""
import numpy as np
from scipy.linalg import solve_banded
import model as M


def jacobian_dense(m, T, S, sc):
    N = m.N
    R = M.residual(m, T, S, sc)
    J = np.zeros((N, N)); h = 1e-8 * np.maximum(T, 1.0)
    for j in range(N):
        Tp = T.copy(); Tp[j] += h[j]; Tm = T.copy(); Tm[j] -= h[j]
        J[:, j] = (M.residual(m, Tp, S, sc) - M.residual(m, Tm, S, sc)) / (2 * h[j])
    return R, J


def jacobian_banded(m, T, S, sc, reg=None):
    N = m.N
    R = M.residual(m, T, S, sc)
    ab = np.zeros((7, N)); h = 1e-8 * np.maximum(T, 1.0)
    for g in range(7):
        idx = np.arange(g, N, 7)
        Tp = T.copy(); Tp[idx] += h[idx]; Tm = T.copy(); Tm[idx] -= h[idx]
        col = M.residual(m, Tp, S, sc) - M.residual(m, Tm, S, sc)
        for j in idx:
            lo, hi = max(0, j - 3), min(N, j + 4)
            ab[3 + np.arange(lo, hi) - j, j] = col[lo:hi] / (2 * h[j])
    return R, ab


def steady_newton(m, sc, T0, P_aux=40.0, tol=1e-8, maxit=60):
    """Damped Newton on R(T) = 0 (no pseudo-time). Returns (T, converged)."""
    S = m.source_aux(P_aux)
    scale = P_aux * 1e6 / np.sum(m.vol)
    T = T0.copy()
    for it in range(maxit):
        if (m.p["reg_length"] > 0.0 or m.p["filt_length"] > 0.0):
            R, Jd = jacobian_dense(m, T, S, sc)
        else:
            R, ab = jacobian_banded(m, T, S, sc)
        r0 = np.max(np.abs(R)) / scale
        if r0 < tol:
            return T, True
        try:
            dT = np.linalg.solve(Jd, -R) if (m.p["reg_length"] > 0.0 or m.p["filt_length"] > 0.0) else solve_banded((3, 3), ab, -R)
        except Exception:
            return T, False
        lam = 1.0
        for _ in range(25):
            Tn = T + lam * dT
            if Tn.min() > m.p["Ta"] - 1e-9 and Tn.max() < m.p["T_cap"] and np.max(np.abs(M.residual(m, Tn, S, sc))) / scale < r0 * (1 - 1e-4 * lam):
                break
            lam *= 0.5
        else:
            return T, False
        T = Tn
    return T, np.max(np.abs(M.residual(m, T, S, sc))) / scale < 1e-7


def leading_eigenvalue(m, T, sc, P_aux=40.0):
    """Largest real part of the eigenvalues of d(RHS)/dT with RHS = R/(3 n e), in 1/s, and the corresponding eigenvector."""
    S = m.source_aux(P_aux)
    R, J = jacobian_dense(m, T, S, sc)
    N = m.N
    A = J / (3.0 * m.n * M.KEV)[:, None]
    w, v = np.linalg.eig(A)
    k = int(np.argmax(w.real))
    return float(w[k].real), float(w[k].imag), v[:, k].real, w


def continuation_in_sc(N, sc_list, P_aux=40.0, **kw):
    """Follow the steady branch from s_c = infinity down the list; returns a list of dicts (Q, leading eigenvalue, ratio_max, converged)."""
    m = M.Model(N, **kw)
    T, st = M.solve(m, P_aux, None, dt=0.05, maxit=300, tol=1e-9)
    out = []
    for sc in sc_list:
        Tn, ok = steady_newton(m, sc, T, P_aux)
        if not ok:
            out.append(dict(sc=sc, ok=False)); break
        T = Tn
        d = M.diagnostics(m, T, P_aux, sc)
        lam, im, vec, _ = leading_eigenvalue(m, T, sc, P_aux)
        out.append(dict(sc=sc, ok=True, Q=float(d["Q"]), T0=float(d["T0"]), lam=lam, im=im, ratio_max=float(d["ratio_max"]), resid=float(d["resid"]),
                        vec_peak_r=float(m.r[int(np.argmax(np.abs(vec)))])))
    return out
