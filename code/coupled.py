# -*- coding: utf-8 -*-
"""One-way coupled heat + rotation problem. The rotation equation (momentum.py) is driven by a torque and closed by a shear-dependent viscosity; its
signed shearing rate (r/q) dOmega/dr is added (rot_sign = +1: shears add, -1: shears oppose) to the diamagnetic shearing rate that suppresses the heat
diffusivity (model.py). The two problems are iterated to a fixed point; T sets gamma_0 and the rotation sets the extra shear."""
import numpy as np
import model as M
import stability as S
import momentum as MO
import theory as TH

CLOSURES = {
    "linear":      lambda L: np.ones_like(np.asarray(L, float)),
    "m=1":         lambda L: TH.F_alg(L, 1.0),
    "m=2":         lambda L: TH.F_alg(L, 2.0),
    "m=2 f=0.20":  lambda L: TH.F_floor_alg(L, 0.20),
    "m=2 f=0.05":  lambda L: TH.F_floor_alg(L, 0.05),
}


def rot_shear(model, Om):
    """Signed (r/q) dOmega/dr at cell centres; Omega(a) = 0 and dOmega/dr = 0 on the axis."""
    Omg = np.concatenate([[Om[0]], Om, [0.0]])
    rr = np.concatenate([[-model.r[0]], model.r, [model.p["a"]]])
    d = np.empty(model.N)
    d[1:-1] = (Om[2:] - Om[:-2]) / (2 * model.dr)
    d[0] = (Om[1] - Om[0]) / (2 * model.dr)
    d[-1] = (0.0 - Om[-2]) / (1.5 * model.dr)
    return model.r / model.q * d


def solve_coupled(N=100, torque=0.0, s_c=0.5, closure="linear", sign=1.0, Pr=1.0, P_aux=40.0, iters=40, tol=1e-9, verbose=False, T_start=None, scale_chi=1.0, width=0.4, **model_kw):
    m = M.Model(N, rot_sign=sign, **model_kw)
    F = CLOSURES[closure]
    m.omega_rot = None
    T, _ = M.solve(m, P_aux, None, dt=0.05, maxit=400, tol=1e-9, T_init=T_start)
    for s_ in [x for x in (4.0, 2.0, 1.0, 0.7, 0.5, 0.4, 0.3, 0.2, 0.15, 0.1) if x > s_c] + [s_c]:
        T, ok0 = S.steady_newton(m, s_, T, P_aux)
        if not ok0:
            return dict(ok=False, why="no steady heat state without rotation", Q=np.nan, T=T, model=m)
    tau = MO.torque_profile(m, torque, width=width) if torque > 0 else np.zeros(N)
    rho_m = m.n * M.M_ION
    mu0 = Pr * np.mean(rho_m) * scale_chi * m.p["chi_s"]
    last_Q, hist, Om, ok = None, [], np.zeros(N), True
    if torque == 0:
        d = M.diagnostics(m, T, P_aux, s_c)
        return dict(ok=True, Q=d["Q"], T=T, Om=Om, Theta=0.0, Lam_rot=0.0, ratio_max=d["ratio_max"], iters=0, model=m, diag=d, Lam_f=np.zeros(N + 1))
    for it in range(iters):
        gamma = np.sqrt(T * M.KEV / M.M_ION) / m.p["R0"]
        Om, Lc, ok, Lam_f = MO.solve_rotation(m, tau, gamma, mu0, F)
        gam_f = np.concatenate([[gamma[0]], 0.5 * (gamma[:-1] + gamma[1:]), [gamma[-1]]])
        if not ok:
            return dict(ok=False, why="no steady rotation profile", Q=np.nan, T=T, Om=Om, model=m, it=it)
        m.omega_rot = rot_shear(m, Om)
        om_full = m.omega_rot.copy()
        Tn, okh = T.copy(), True
        for frac in (0.25, 0.5, 0.75, 1.0):
            m.omega_rot = frac * om_full
            Tn, okh = S.steady_newton(m, s_c, Tn, P_aux)
            if not okh:
                break
        m.omega_rot = om_full
        if not okh:
            return dict(ok=False, why="no steady heat state with rotation shear", Q=np.nan, T=T, Om=Om, model=m, it=it)
        d = M.diagnostics(m, Tn, P_aux, s_c)
        hist.append(d["Q"])
        dT = np.max(np.abs(Tn - T)); T = Tn
        if verbose:
            print("  it", it, "Q", round(d["Q"], 5), "dT", dT)
        if dT < tol * 100:
            break
    _, Iface = MO.theta_profile(m, tau, gamma, mu0)
    Theta = Iface / (m.qf * gam_f * mu0 * m.p["R0"] ** 2)
    return dict(ok=True, Q=d["Q"], T=T, Om=Om, Theta=float(Theta.max()), Lam_rot=float(Lam_f.max()), ratio_max=float(d["ratio_max"]), iters=it + 1, model=m, diag=d,
                Lam_f=Lam_f, Mach=float(np.max(np.abs(Om) * m.p["R0"] / np.sqrt(T * M.KEV / M.M_ION))), Theta_max=float(Theta.max()))
