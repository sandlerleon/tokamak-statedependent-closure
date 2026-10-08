# -*- coding: utf-8 -*-
"""Reduced toroidal-rotation equation with a shear-dependent viscosity, solved independently of the closed forms in theory.py.

    rho_m R0^2 dOmega/dt = r^-1 d/dr ( r mu_eff R0^2 dOmega/dr ) + tau_in(r),   mu_eff = mu0 F(Lambda),   Lambda = kappa |dOmega/dr|,   kappa = r/(q gamma),

Omega(a) = 0 (no slip at the edge), regularity at r = 0. The heat equation is decoupled here (profiles of T, gamma are taken from a baseline run), so that the steady
flux relation  F(Lambda) Lambda = Theta(r) = I(r)/(q gamma mu0 R0^2),  I(r) = int_0^r tau_in r' dr'  can be tested against a direct numerical solution.
"""
import numpy as np
from scipy.optimize import root

import model as M

AMU = M.AMU


def torque_profile(model, T_total, width=0.4):
    """Gaussian torque density (N m / m^3) normalised so that int tau dV = T_total (N m)."""
    g = np.exp(-(model.r / (width * model.p["a"])) ** 2)
    return T_total * g / np.sum(g * model.vol)


def theta_profile(model, tau, gamma, mu0):
    """Theta(r) = I(r)/(q gamma mu0 R0^2) at cell centres; I = int_0^r tau r' dr' (midpoint rule on the cell grid)."""
    rf, dr = model.rf, model.dr
    I_face = np.concatenate([[0.0], np.cumsum(tau * model.r * dr)])
    Ic = 0.5 * (I_face[1:] + I_face[:-1])
    return Ic / (model.q * gamma * mu0 * model.p["R0"] ** 2), I_face


def solve_rotation(model, tau, gamma, mu0, F, tol=1e-12, Omega0=None, cold=True, nsteps=8):
    """Direct steady solution of the rotation equation (finite volume, scaled Newton-type root finding with continuation in the torque amplitude).
    F is a callable F(Lambda). Returns (Omega, Lambda at cells, converged, Lambda at faces). With cold=False the solve starts from Omega0 (branch following)."""
    N, dr, r, rf = model.N, model.dr, model.r, model.rf
    R02 = model.p["R0"] ** 2
    qf = model.qf
    gam_f = np.concatenate([[gamma[0]], 0.5 * (gamma[:-1] + gamma[1:]), [gamma[-1]]])
    kap_f = rf / (qf * gam_f)
    tmax = float(np.max(np.abs(tau))) if np.max(np.abs(tau)) > 0 else 1.0

    def flux_faces(Om):
        dO = np.empty(N + 1)
        dO[0] = 0.0
        dO[1:-1] = (Om[1:] - Om[:-1]) / dr
        dO[-1] = (0.0 - Om[-1]) / (0.5 * dr)
        Lam = kap_f * np.abs(dO)
        return mu0 * R02 * F(Lam) * dO, Lam, dO

    def res_fn(frac):
        def f(x):
            Om = x * scale
            G, _, _ = flux_faces(Om)
            return ((rf[1:] * G[1:] - rf[:-1] * G[:-1]) / (r * dr) + frac * tau) / tmax
        return f

    def lin_res(Om):
        Gl = np.concatenate([[0.0], mu0 * R02 * (Om[1:] - Om[:-1]) / dr, [mu0 * R02 * (0.0 - Om[-1]) / (0.5 * dr)]])
        return (rf[1:] * Gl[1:] - rf[:-1] * Gl[:-1]) / (r * dr) + tau

    # linear-viscosity solution (tridiagonal, exact) sets the scale and the starting point
    sol0 = root(lin_res, np.maximum(0.0, 1.0 - (r / model.p["a"]) ** 2) * 1.0e3, method="hybr", tol=1e-13)
    scale = float(np.max(np.abs(sol0.x))) or 1.0
    if cold:
        x = sol0.x / scale
        fracs = np.linspace(0.0, 1.0, nsteps + 1)[1:]
    else:
        x = np.array(Omega0, float) / scale
        fracs = [1.0]
    ok = True
    for frac in fracs:
        sol = root(res_fn(frac), x, method="hybr", tol=1e-10)
        if np.max(np.abs(res_fn(frac)(sol.x))) > 1e-8 or not np.all(np.isfinite(sol.x)):
            ok = False
            break
        x = sol.x
    if not ok:
        return x * scale, np.full(N, np.nan), False, np.full(N + 1, np.nan)
    Om = x * scale
    G, Lam, dO = flux_faces(Om)
    return Om, 0.5 * (Lam[1:] + Lam[:-1]), True, Lam


def march_rotation(model, tau, gamma, mu0, F, Om0, rho_m=None, tol=1e-10, maxit=200, dt0=1e-6):
    """Backward-Euler pseudo-time evolution of the rotation equation from Om0 to a steady state (branch selection by the dynamics).
    Returns (Omega, Lambda at faces, converged)."""
    from scipy.linalg import solve_banded
    N, dr, r, rf = model.N, model.dr, model.r, model.rf
    R02 = model.p["R0"] ** 2
    qf = model.qf
    gam_f = np.concatenate([[gamma[0]], 0.5 * (gamma[:-1] + gamma[1:]), [gamma[-1]]])
    kap_f = rf / (qf * gam_f)
    rho = model.n * M.M_ION if rho_m is None else rho_m
    tmax = float(np.max(np.abs(tau))) or 1.0

    def div(Om):
        dO = np.empty(N + 1)
        dO[0] = 0.0
        dO[1:-1] = (Om[1:] - Om[:-1]) / dr
        dO[-1] = (0.0 - Om[-1]) / (0.5 * dr)
        Lam = kap_f * np.abs(dO)
        G = mu0 * R02 * F(Lam) * dO
        return (rf[1:] * G[1:] - rf[:-1] * G[:-1]) / (r * dr), Lam

    scale = max(float(np.max(np.abs(Om0))), 1.0)
    Om = np.array(Om0, float)
    dt = dt0
    cap = rho * R02
    for step in range(maxit):
        Old = Om.copy()
        x = Om.copy()
        for it in range(40):
            d, _ = div(x)
            Rv = (cap * (x - Old) / dt - d - tau) / tmax
            ab = np.zeros((3, N))
            h = 1e-7 * scale
            for g in range(3):
                idx = np.arange(g, N, 3)
                xp = x.copy(); xp[idx] += h; xm = x.copy(); xm[idx] -= h
                col = ((cap * (xp - Old) / dt - div(xp)[0] - tau) - (cap * (xm - Old) / dt - div(xm)[0] - tau)) / (2 * h * tmax)
                for j in idx:
                    for i in (j - 1, j, j + 1):
                        if 0 <= i < N:
                            ab[1 + i - j, j] = col[i]
            dx = solve_banded((1, 1), ab, -Rv)
            lam = 1.0
            for _ in range(20):
                xn = x + lam * dx
                dn, _ = div(xn)
                if np.max(np.abs((cap * (xn - Old) / dt - dn - tau) / tmax)) < np.max(np.abs(Rv)) or lam < 1e-4:
                    break
                lam *= 0.5
            x = xn
            if np.max(np.abs(dx)) < 1e-12 * scale:
                break
        Om = x
        d, Lam = div(Om)
        if np.max(np.abs(d + tau)) / tmax < tol:
            return Om, Lam, True
        dt = min(dt * 2.0, 1e12)
    d, Lam = div(Om)
    return Om, Lam, bool(np.max(np.abs(d + tau)) / tmax < 1e-6)
