# -*- coding: utf-8 -*-
"""Closed-form results for flux closures F(Lambda): admissibility (monotone normalised flux Psi = Lambda F(Lambda)), thresholds, flux saturation,
and the steady flux relation of the reduced rotation equation. Pure functions; every statement is checked against numerics in tests.py."""
import numpy as np


def F_alg(L, m):                       # F = 1/(1 + L^m)
    return 1.0 / (1.0 + np.asarray(L, float) ** m)


def F_floor_alg(L, f):                 # F = f + (1-f)/(1+L^2)
    L = np.asarray(L, float)
    return f + (1 - f) / (1 + L ** 2)


def F_floor_exp(L, f, alpha=1.0):      # F = f + (1-f) exp(-alpha L^2)
    L = np.asarray(L, float)
    return f + (1 - f) * np.exp(-alpha * L ** 2)


def Psi(L, F, **kw):
    L = np.asarray(L, float)
    return L * F(L, **kw)


def dlnF_dlnL_alg(L, m):
    L = np.asarray(L, float)
    return -m * L ** m / (1 + L ** m)


def alg_admissible(m):
    """Psi = L/(1+L^m) is nondecreasing for all L iff m <= 1."""
    return m <= 1.0


def alg_stationary_point(m):
    """For m > 1, Psi' = 0 at L*^m = 1/(m-1); returns (L*, Psi(L*)), Psi(L*) = L*/m."""
    assert m > 1
    Ls = (m - 1.0) ** (-1.0 / m)
    return Ls, Ls / m


def floor_alg_threshold():
    """F = f + (1-f)/(1+L^2): admissible iff f > 1/9."""
    return 1.0 / 9.0


def floor_exp_threshold():
    """F = f + (1-f) exp(-alpha L^2): admissible iff f > 2 e^{-3/2} / (1 + 2 e^{-3/2}) = 0.3086, independent of alpha."""
    c = 2.0 * np.exp(-1.5)
    return c / (1.0 + c)


def exp_nofloor_peak(alpha=1.0):
    """Psi = L exp(-alpha L^2) has its maximum at L = (2 alpha)^(-1/2), Psi = (2 alpha e)^(-1/2)."""
    return (2.0 * alpha) ** -0.5, (2.0 * alpha * np.e) ** -0.5


def theta_to_lambda_alg(theta, m):
    """Solve Psi(L) = theta for L on the increasing branch, F = 1/(1+L^m); returns nan beyond the maximum (no steady state)."""
    from scipy.optimize import brentq
    if m <= 1.0:
        if m == 1.0:
            return theta / (1.0 - theta) if theta < 1.0 else np.nan
        # m < 1: Psi increases without bound? Psi = L/(1+L^m) ~ L^(1-m) -> inf
    else:
        _, pmax = alg_stationary_point(m)
        if theta >= pmax:
            return np.nan
    hi = 1.0
    while Psi(hi, F_alg, m=m) < theta:
        hi *= 2.0
        if hi > 1e12:
            return np.nan
    lo = 0.0
    if m > 1:
        hi = alg_stationary_point(m)[0]
    return brentq(lambda L: Psi(L, F_alg, m=m) - theta, lo, hi, xtol=1e-14)
