# -*- coding: utf-8 -*-
"""One-dimensional radial energy-transport model of a tokamak with a baseline critical-gradient closure and a state-dependent
E x B shear-suppression closure. Only the closure differs between runs. Units: r in m, T in keV, n in m^-3, chi in m^2/s, power density in W/m^3.

    chi = chi_base / [1 + (omega_E / (s_c gamma_0))^2],   s_c -> infinity recovers chi_base.
"""
import numpy as np
from scipy.linalg import solve_banded

KEV = 1.602176634e-16          # J per keV
E_CH = 1.602176634e-19         # C
AMU = 1.66053907e-27           # kg
M_ION = 2.5 * AMU              # mean D-T ion mass

# ---- fusion reactivity: Bosch-Hale (1992), D-T, Nucl. Fusion 32, 611, coefficients for T in keV (0.2-100 keV)
_BG, _MRC2 = 34.3827, 1124656.0
_C = [1.17302e-9, 1.51361e-2, 7.51886e-2, 4.60643e-3, 1.35000e-2, -1.06750e-4, 1.36600e-5]


def sigma_v(T):
    """<sigma v> in m^3/s for T in keV."""
    T = np.maximum(np.asarray(T, float), 0.2)
    th = T / (1.0 - (T * (_C[1] + T * (_C[3] + T * _C[5]))) / (1.0 + T * (_C[2] + T * (_C[4] + T * _C[6]))))
    xi = (_BG ** 2 / (4.0 * th)) ** (1.0 / 3.0)
    return 1e-6 * _C[0] * th * np.sqrt(xi / (_MRC2 * T ** 3)) * np.exp(-3.0 * xi)


PARAMS = dict(R0=6.2, a=2.0, B=5.3, n0=1e20, n_shape=0.75, q0=1.0, q2=2.0, Ta=4.0, chi_n=0.3, chi_s=1.0, kappa_c=4.0, w=0.5,
              E_alpha=3.5e6 * E_CH, brems=5.35e-37, width=0.4, T_cap=300.0, flux_factor=3.0, shear_scheme="face", reg_length=0.0, filt_length=0.0)


class Model:
    def __init__(self, N=100, **kw):
        p = dict(PARAMS); p.update(kw); self.p = p
        self.N = N
        a = p["a"]
        self.dr = a / N
        self.r = (np.arange(N) + 0.5) * self.dr                 # cell centres
        self.rf = np.arange(N + 1) * self.dr                    # faces
        x = self.r / a; xf = self.rf / a
        self.n = p["n0"] * (1 - p["n_shape"] * x ** 2)
        self.nf = p["n0"] * (1 - p["n_shape"] * xf ** 2)
        self.q = p["q0"] + p["q2"] * x ** 2
        self.qf = p["q0"] + p["q2"] * xf ** 2
        self.vol = 4 * np.pi ** 2 * p["R0"] * (self.rf[1:] ** 2 - self.rf[:-1] ** 2) / 2.0 * 2.0 / 2.0 * 1.0   # placeholder, set below
        self.vol = 2 * np.pi * self.r * self.dr * 2 * np.pi * p["R0"]       # dV = 4 pi^2 R0 r dr
        self.area = 4 * np.pi ** 2 * p["R0"] * self.rf                   # surface area x (1/ r) handled via face radii

    # --- heating source (Gaussian, normalised to P_aux)
    def source_aux(self, P_aux):
        g = np.exp(-(self.r / (self.p["width"] * self.p["a"])) ** 2)
        return P_aux * 1e6 * g / np.sum(g * self.vol)

    def diag(self, T):
        p = self.p
        S_a = 0.25 * self.n ** 2 * sigma_v(T) * p["E_alpha"]
        S_r = p["brems"] * self.n ** 2 * np.sqrt(np.maximum(T, 0.0))
        return S_a, S_r

    def gradient_cell(self, T):
        """dT/dr at cell centres (central, one-sided at the axis, Dirichlet half-cell at the edge)."""
        Te = np.concatenate([[T[0]], T, [self.p["Ta"]]])
        rr = np.concatenate([[0.0], self.r, [self.p["a"]]])
        g = np.empty_like(T)
        g[1:-1] = (T[2:] - T[:-2]) / (2 * self.dr)
        g[0] = (T[1] - T[0]) / self.dr * 0.5 + 0.0
        g[0] = (T[1] - T[0]) / self.dr          # first cell, forward
        g[-1] = (self.p["Ta"] - T[-2]) / (1.5 * self.dr)
        return g

    def _helmholtz(self, rhs, l=None):
        """Solve A - l^2 (1/r) d/dr (r dA/dr) = rhs on the cell grid with zero-flux ends (steady limit of the adaptive field dA/dt = D_A lap(A) + (Lambda^2 - A)/tau_A, l^2 = D_A tau_A)."""
        l = self.p["reg_length"] if l is None else l
        cache = getattr(self, "_helm_cache", None)
        if cache is None:
            cache = self._helm_cache = {}
        if l not in cache:
            N, dr, rf, r = self.N, self.dr, self.rf, self.r
            l2 = l ** 2
            ab = np.zeros((3, N))
            cu = l2 * rf[1:-1] / (r[:-1] * dr * dr)                       # coupling of cell i to i+1  (i = 0..N-2), uses face i+1
            cl = l2 * rf[1:-1] / (r[1:] * dr * dr)                        # coupling of cell i+1 to i
            ab[1] = 1.0
            ab[1, :-1] += cu; ab[1, 1:] += cl
            ab[0, 1:] = -cu                                               # upper diagonal: A[i, i+1]
            ab[2, :-1] = -cl                                              # lower diagonal: A[i+1, i]
            cache[l] = ab
        return solve_banded((1, 1), cache[l], rhs)

    def _ratio_face(self, T):
        """omega_E / gamma_0 at cell centres, from face-centred E_r (E_r = 0 on the axis by symmetry) and an even-in-r extrapolation of
        u = q E_r/(r B) to the axis, so that the 0/0 limit at r -> 0 is treated consistently on every grid."""
        p, N, dr = self.p, self.N, self.dr
        pr = self.n * T * 1e3
        if p["filt_length"] > 0.0:
            pr = self._helmholtz(pr, l=p["filt_length"])
        prb = np.concatenate([pr, [self.nf[-1] * p["Ta"] * 1e3]])              # pressure at cell centres plus the edge value at r = a
        # faces 1..N-1: centred difference between neighbouring cells; face N: half-cell difference to the Dirichlet edge
        dp = np.empty(N)                                                       # dp/dr at faces 1..N
        dp[:-1] = (pr[1:] - pr[:-1]) / dr
        dp[-1] = (prb[-1] - pr[-1]) / (0.5 * dr)
        nface = self.nf[1:]
        Er = dp / nface                                                        # V/m at faces 1..N
        rface, qface = self.rf[1:], self.qf[1:]
        u = qface * Er / (rface * p["B"])                                      # faces 1..N
        u0 = (4.0 * u[0] - u[1]) / 3.0                                         # even extrapolation to r = 0
        uf = np.concatenate([[u0], u])                                         # faces 0..N
        du = np.diff(uf) / dr                                                  # at cell centres
        omega_dia = self.r / self.q * du                                       # signed
        rot = getattr(self, "omega_rot", None)                                 # signed rotation shear (r/q) dOmega/dr at cell centres, rad/s
        omega = np.abs(omega_dia + (0.0 if rot is None else p.get("rot_sign", 1.0) * rot))
        gamma0 = np.sqrt(T * KEV / M_ION) / p["R0"]
        return omega / gamma0

    def chi_faces(self, T, s_c):
        """chi at the N-1 interior faces and the edge face from face gradients (central), shear rate from cell values."""
        p = self.p
        Tf = np.empty(self.N + 1)
        Tf[1:-1] = 0.5 * (T[:-1] + T[1:]); Tf[0] = T[0]; Tf[-1] = p["Ta"]
        gf = np.empty(self.N + 1)
        gf[1:-1] = (T[1:] - T[:-1]) / self.dr
        gf[0] = 0.0
        gf[-1] = (p["Ta"] - T[-1]) / (0.5 * self.dr)
        kap = p["R0"] * np.abs(gf) / np.maximum(Tf, 1e-3)
        z = (kap - p["kappa_c"]) / p["w"]
        chib = p["chi_n"] + p["chi_s"] * p["w"] * np.logaddexp(0.0, z)
        _, _, ratio = self.chi_parts(T, s_c)
        rf = np.concatenate([[ratio[0]], 0.5 * (ratio[:-1] + ratio[1:]), [ratio[-1]]])
        if s_c is None or not np.isfinite(s_c):
            return chib, chib, rf
        return chib / (1.0 + (rf / s_c) ** 2), chib, rf

    def chi_parts(self, T, s_c):
        p = self.p
        g = self.gradient_cell(T)
        kap = p["R0"] * np.abs(g) / np.maximum(T, 1e-3)
        z = (kap - p["kappa_c"]) / p["w"]
        sp = p["w"] * (np.logaddexp(0.0, z))
        chi_base = p["chi_n"] + p["chi_s"] * sp
        # E x B shearing rate from the ion pressure-gradient balance
        if p["shear_scheme"] == "face":
            ratio_face = self._ratio_face(T)
            if p["reg_length"] > 0.0:
                ratio_face = np.sqrt(np.maximum(self._helmholtz(ratio_face ** 2), 0.0))
            chi_base_ = chi_base
            gamma0_ = np.sqrt(T * KEV / M_ION) / p["R0"]
            if s_c is None or not np.isfinite(s_c):
                supp_ = np.ones_like(T)
            else:
                supp_ = 1.0 / (1.0 + (ratio_face / s_c) ** 2)
            return chi_base_ * supp_, chi_base_, ratio_face
        pr = self.n * T * 1e3                                  # n * T[eV] (so E_r in V/m = (1/n) dp/dr with p in n*eV)
        pe = np.concatenate([[pr[0]], pr, [self.nf[-1] * p["Ta"] * 1e3]])
        dpdr = np.empty_like(T)
        dpdr[1:-1] = (pr[2:] - pr[:-2]) / (2 * self.dr)
        dpdr[0] = (pr[1] - pr[0]) / self.dr
        dpdr[-1] = (self.nf[-1] * p["Ta"] * 1e3 - pr[-2]) / (1.5 * self.dr)
        Er = dpdr / self.n                                     # V/m
        u = self.q * Er / (self.r * p["B"])                    # q E_r / (r B)
        ue = np.concatenate([[u[0] * 0 + u[0]], u, [u[-1]]])
        du = np.empty_like(u)
        du[1:-1] = (u[2:] - u[:-2]) / (2 * self.dr)
        du[0] = (u[1] - u[0]) / self.dr
        du[-1] = (u[-1] - u[-2]) / self.dr
        omega_E = np.abs(self.r / self.q * du)
        gamma0 = np.sqrt(T * KEV / M_ION) / p["R0"]
        ratio = omega_E / gamma0
        if s_c is None or not np.isfinite(s_c):
            supp = np.ones_like(T)
        else:
            supp = 1.0 / (1.0 + (ratio / s_c) ** 2)
        return chi_base * supp, chi_base, ratio


def residual(model, T, S_aux, s_c):
    """Steady energy balance per cell, W/m^3: conduction divergence + auxiliary + alpha - radiation."""
    p, N = model.p, model.N
    k = p["flux_factor"]
    chi, _, _ = model.chi_parts(T, s_c)
    D = k * model.nf[1:-1] * 0.5 * (chi[:-1] + chi[1:])
    Dend = k * model.nf[-1] * chi[-1]
    rf, dr = model.rf, model.dr
    F = np.empty(N + 1)
    F[0] = 0.0
    F[1:-1] = D * rf[1:-1] * (T[1:] - T[:-1]) / dr
    F[-1] = Dend * rf[-1] * (p["Ta"] - T[-1]) / (0.5 * dr)
    cond = KEV * (F[1:] - F[:-1]) / (model.r * dr)
    Sa, Sr = model.diag(T)
    return cond + S_aux + Sa - Sr


def solve(model, P_aux=40.0, s_c=None, dt=0.05, tol=1e-9, maxit=4000, T_init=None, relax=1.0, verbose=False, return_hist=False, dt_max=50.0):
    """Backward Euler pseudo-time march to steady state. Each implicit step is solved by damped Newton with a finite-difference Jacobian
    (coloured, bandwidth 3). A step is rejected and repeated with half the time step if Newton does not converge or the temperature leaves
    (T_a, T_cap): the time step grows by 1.5 after every accepted step."""
    p, N = model.p, model.N
    S_aux = model.source_aux(P_aux)
    T = (4.0 + 8.0 * (1 - (model.r / p["a"]) ** 2)) if T_init is None else np.array(T_init, float)
    cT = 3.0 * model.n * KEV                                   # energy density 3 n T
    scale = (P_aux * 1e6) / np.sum(model.vol)
    hist, step, rejects = [], 0, 0
    BW = 7
    while step < maxit:
        Told = T.copy()
        ok, Tk = False, Told.copy()
        for it in range(30):
            R = cT / dt * (Tk - Told) - residual(model, Tk, S_aux, s_c)
            ab = np.zeros((7, N))                                    # banded Jacobian (central differences), 3 sub- and 3 super-diagonals
            h = 1e-8 * np.maximum(Tk, 1.0)
            for g in range(BW):
                idx = np.arange(g, N, BW)
                Tp = Tk.copy(); Tp[idx] += h[idx]; Tm = Tk.copy(); Tm[idx] -= h[idx]
                col = (cT / dt * (Tp - Tm) - (residual(model, Tp, S_aux, s_c) - residual(model, Tm, S_aux, s_c)))
                for jj in idx:
                    lo_, hi_ = max(0, jj - 3), min(N, jj + 4)
                    ab[3 + np.arange(lo_, hi_) - jj, jj] = col[lo_:hi_] / (2 * h[jj])
            try:
                dT = solve_banded((3, 3), ab, -R)
            except Exception:
                break
            lam, r0 = 1.0, np.max(np.abs(R))
            for _ in range(15):
                Tn = Tk + lam * dT
                if Tn.min() > p["Ta"] - 1e-9 and Tn.max() < p["T_cap"]:
                    Rn = cT / dt * (Tn - Told) - residual(model, Tn, S_aux, s_c)
                    if np.max(np.abs(Rn)) < r0:
                        break
                lam *= 0.5
            else:
                break
            Tk = Tn
            if np.max(np.abs(Rn)) < 1e-9 * scale:
                ok = True
                break
        if not ok or not np.all(np.isfinite(Tk)):
            dt *= 0.5; rejects += 1
            if dt < 1e-5:
                T = Tk; break
            continue
        T = np.maximum(Tk, p["Ta"])
        step += 1
        res = np.max(np.abs(residual(model, T, S_aux, s_c))) / scale
        hist.append(res)
        if res < tol:
            break
        dt = min(dt * 1.5, dt_max)
    model.rejects = rejects
    out = (T, step)
    return out + (np.array(hist),) if return_hist else out


def diagnostics(model, T, P_aux, s_c):
    p = model.p
    Sa, Sr = model.diag(T)
    chi, chib, ratio = model.chi_parts(T, s_c)
    chi_edge = chi[-1]
    Pa = np.sum(Sa * model.vol) / 1e6
    Pr = np.sum(Sr * model.vol) / 1e6
    W = np.sum(3.0 * model.n * T * KEV * model.vol) / 1e6          # MJ  (3 n T)
    Pf = 5 * Pa
    # boundary conduction
    g_edge = (p["Ta"] - T[-1]) / (0.5 * model.dr)
    Pcond = -p["flux_factor"] * model.nf[-1] * chi_edge * g_edge * KEV * model.area[-1] / 1e6
    bal = (P_aux + Pa - Pr - Pcond) / (P_aux + Pa)
    return dict(Q=Pf / P_aux, Pfus=Pf, tauE=W / (P_aux + Pa - Pr), Tavg=np.sum(T * model.vol) / np.sum(model.vol), T0=T[0], Pa=Pa, Prad=Pr, W=W,
                resid=bal, ratio_max=ratio.max(), chi=chi, chib=chib, ratio=ratio)


if __name__ == "__main__":
    print("sigma_v(10), sigma_v(20):", sigma_v(10.0), sigma_v(20.0))
    for k in (1.0, 2.0):
        m = Model(100, flux_factor=k)
        T, st = solve(m, 40.0, None)
        d = diagnostics(m, T, 40.0, None)
        print("flux_factor", k, "steps", st, {x: round(float(v), 4) for x, v in d.items() if np.ndim(v) == 0})


def solve_refined(N, P_aux=40.0, s_c=None, N0=50, tol=1e-9, **kw):
    """Solve on N0 cells by pseudo-time marching, then refine by interpolation (N0 -> 2 N0 -> ...) with a steady Newton solve on each grid.
    Returns (model, T, info). Extra keyword arguments are passed to Model."""
    Ns = [N0]
    while Ns[-1] * 2 <= N:
        Ns.append(Ns[-1] * 2)
    if Ns[-1] != N:
        Ns.append(N)
    m = Model(Ns[0], **kw)
    T, st, h = solve(m, P_aux, s_c, dt=0.05, maxit=500, tol=tol, return_hist=True)
    info = dict(res=h[-1], steps=st)
    for Nn in Ns[1:]:
        mn = Model(Nn, **kw)
        Tn = np.interp(mn.r, m.r, T)
        Tn, st, h = solve(mn, P_aux, s_c, dt=0.5, maxit=300, tol=tol, T_init=Tn, return_hist=True)
        m, T = mn, Tn
        info = dict(res=h[-1], steps=st)
    return m, T, info
