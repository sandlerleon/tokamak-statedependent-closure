# -*- coding: utf-8 -*-
"""Physical calibration of the reduced model against recognised confinement scalings, operational limits and neutral-beam torque.

The reduced model is circular and one-dimensional; the plasma current is not an input. The comparison therefore uses an ITER-like reference device (R0 = 6.2 m, a = 2.0 m, B = 5.3 T,
I_p = 15 MA, elongation kappa_a = 1.7, M = 2.5 amu) for which the model profile q(r) = 1 + 2 (r/a)^2 has q_a = 3. All formulas are written out here; none is fitted.
"""
import numpy as np

import model as M

MU0 = 4e-7 * np.pi
REF = dict(I_MA=15.0, kappa_a=1.7, M_amu=2.5)


def ipb98y2(I_MA, B, P_MW, n19, M_amu, R, eps, kappa_a):
    """ITER Physics Basis H-mode thermal energy confinement scaling IPB98(y,2), seconds (I in MA, B in T, P in MW, n in 1e19 m^-3, R in m)."""
    return 0.0562 * I_MA ** 0.93 * B ** 0.15 * P_MW ** -0.69 * n19 ** 0.41 * M_amu ** 0.19 * R ** 1.97 * eps ** 0.58 * kappa_a ** 0.78


def iter89p(I_MA, B, P_MW, n20, M_amu, R, a, kappa):
    """ITER89-P L-mode scaling (Yushmanov et al. 1990), seconds (n in 1e20 m^-3)."""
    return 0.048 * M_amu ** 0.5 * I_MA ** 0.85 * R ** 1.2 * a ** 0.3 * kappa ** 0.5 * n20 ** 0.1 * B ** 0.2 * P_MW ** -0.5


def operating_point(model, T, d):
    """Benchmark quantities of a converged state; d is the dictionary returned by model.diagnostics."""
    p = model.p
    R0, a, B = p["R0"], p["a"], p["B"]
    n_line = float(np.sum(model.n * model.dr) / a)                                  # line-average density (m^-3)
    P_net = d["W"] / d["tauE"]                                                      # P_aux + P_alpha - P_rad (MW)
    tau98 = ipb98y2(REF["I_MA"], B, P_net, n_line / 1e19, REF["M_amu"], R0, a / R0, REF["kappa_a"])
    tau89 = iter89p(REF["I_MA"], B, P_net, n_line / 1e20, REF["M_amu"], R0, a, REF["kappa_a"])
    nT = float(np.sum(model.n * T * 1e3 * M.E_CH * model.vol) / np.sum(model.vol))     # volume-average n T (J m^-3)
    p_avg = 2.0 * nT                                                                # total pressure, electrons + ions
    beta = 2.0 * MU0 * p_avg / B ** 2
    beta_N = 100.0 * beta * a * B / REF["I_MA"]
    n_G = REF["I_MA"] / (np.pi * a ** 2)                                            # Greenwald density, 1e20 m^-3
    return dict(P_net=P_net, tau_E=d["tauE"], tau98=tau98, H98=d["tauE"] / tau98, tau89=tau89, H89=d["tauE"] / tau89, beta=beta, beta_N=beta_N, f_G=(n_line / 1e20) / n_G, n_line=n_line)


def nbi_torque(P_MW=33.0, E_MeV=1.0, R_tan=5.3, m_amu=2.0141):
    """Torque of a neutral beam injected tangentially at radius R_tan. The particle rate is P/E with E = m v^2/2 and each particle carries angular momentum m v R_tan, so
    T = (P/E) m v R_tan = 2 P R_tan / v, v = (2 E/m)^{1/2} (full-energy component only; no shine-through, orbit or charge-exchange losses)."""
    v = np.sqrt(2.0 * E_MeV * 1e6 * M.E_CH / (m_amu * M.AMU))
    return 2.0 * P_MW * 1e6 * R_tan / v, v


def ion_gyroradius(T_keV, B, m_amu=2.5):
    """Thermal ion gyroradius rho_i = (m T)^{1/2}/(e B) with T in keV."""
    return np.sqrt(m_amu * M.AMU * T_keV * 1e3 * M.E_CH) / (M.E_CH * B)
