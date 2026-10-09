# -*- coding: utf-8 -*-
"""Principal part of the linearised heat flux for the local closure,  D_eff(r) = [dPhi/dT' + d/dr (dPhi/dT'')] / (3 n),  Phi = 3 n chi(T', T'', T, r) T'.
Where D_eff < 0 the linearised steady balance is backward-diffusive (loss of ellipticity); the growth rate of grid-scale modes is then about |D_eff| (pi/dr)^2.
Units: D_eff in m^2 s^-1 (T in keV)."""
import numpy as np

import model as M

P = dict(M.PARAMS)
R0, A_, B = P["R0"], P["a"], P["B"]
C_N = P["n_shape"]


def _n(r):
    return P["n0"] * (1 - C_N * (r / A_) ** 2)


def _dlnn(r):                       # n'/n
    return -2 * C_N * r / (A_ ** 2 * (1 - C_N * (r / A_) ** 2))


def _d2lnn(r):                      # (n'/n)'
    x2 = (r / A_) ** 2
    return -2 * C_N * (1 + C_N * x2) / (A_ ** 2 * (1 - C_N * x2) ** 2)


def _q(r):
    return P["q0"] + P["q2"] * (r / A_) ** 2


def _dq(r):
    return 2 * P["q2"] * r / A_ ** 2


def omega(r, T, Tp, Tpp):
    """Signed diamagnetic shearing rate (rad/s) from the local profile data: omega = (r/q) d/dr (q E_r / (r B)), E_r = 1e3 (T' + T n'/n) V/m."""
    Er = 1e3 * (Tp + T * _dlnn(r))
    Erp = 1e3 * (Tpp + Tp * _dlnn(r) + T * _d2lnn(r))
    return (r / _q(r)) * (_dq(r) * Er / (r * B) - _q(r) * Er / (r ** 2 * B) + _q(r) * Erp / (r * B))


def flux(r, T, Tp, Tpp, s_c):
    kappa = R0 * np.abs(Tp) / T
    z = (kappa - P["kappa_c"]) / P["w"]
    chib = P["chi_n"] + P["chi_s"] * P["w"] * np.logaddexp(0.0, z)
    gamma0 = np.sqrt(T * M.KEV / M.M_ION) / R0
    chi = chib / (1.0 + (omega(r, T, Tp, Tpp) / (s_c * gamma0)) ** 2)
    return 3.0 * _n(r) * chi * Tp


def d_eff(model, T_prof, s_c):
    from scipy.interpolate import CubicSpline
    rr = np.concatenate([[0.0], model.r, [model.p["a"]]])
    TT = np.concatenate([[T_prof[0]], T_prof, [model.p["Ta"]]])
    cs = CubicSpline(rr, TT, bc_type="not-a-knot")
    rc = model.r[3:-3]
    t, t1, t2 = cs(rc), cs(rc, 1), cs(rc, 2)
    h1, h2 = 1e-5 * np.maximum(np.abs(t1), 1e-3), 1e-5 * np.maximum(np.abs(t2), 1e-3)
    d1 = (flux(rc, t, t1 + h1, t2, s_c) - flux(rc, t, t1 - h1, t2, s_c)) / (2 * h1)
    d2 = (flux(rc, t, t1, t2 + h2, s_c) - flux(rc, t, t1, t2 - h2, s_c)) / (2 * h2)
    d2r = np.gradient(d2, rc)
    return rc, (d1 + d2r) / (3.0 * _n(rc)), d1 / (3.0 * _n(rc)), d2r / (3.0 * _n(rc))
