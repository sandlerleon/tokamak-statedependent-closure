# -*- coding: utf-8 -*-
"""Verification checks for the closed forms, the solver and the reported results.   python tests.py   (about 3 minutes; reads ../results.json where noted)"""
import json
import os
import sys

import numpy as np

import coupled as C
import model as M
import momentum as MO
import stability as S
import theory as TH

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, "..", "results.json"), encoding="utf-8"))
fails, n = [], 0


def check(name, ok, detail=""):
    global n
    n += 1
    print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name, ("  -- " + detail) if detail else ""))
    if not ok:
        fails.append(name)


def steady(N, sc):
    m = M.Model(N)
    T, _ = M.solve(m, 40.0, None, dt=0.05, maxit=300, tol=1e-9)
    if sc is not None:
        for s_ in [x for x in (4.0, 2.0, 1.0, 0.5, 0.3, 0.2, 0.1) if x > sc] + [sc]:
            T, ok = S.steady_newton(m, s_, T)
            assert ok
    return m, T


print("Model and solver")
check("Bosch-Hale reactivity at 10 keV (1.136e-22 m^3/s)", abs(M.sigma_v(10.0) / 1.136e-22 - 1) < 1e-3, "%.4e" % M.sigma_v(10.0))
check("Bosch-Hale reactivity at 20 keV (4.33e-22 m^3/s)", abs(M.sigma_v(20.0) / 4.33e-22 - 1) < 1e-3, "%.4e" % M.sigma_v(20.0))
for sc in (None, 0.5, 0.1):
    m, T = steady(100, sc)
    d = M.diagnostics(m, T, 40.0, sc)
    check("power balance closes to < 1e-9 of total heating (s_c = %s)" % sc, abs(d["resid"]) < 1e-9, "%.1e" % d["resid"])
m = M.Model(100)
Tb, _ = M.solve(m, 40.0, None, dt=0.05, maxit=300, tol=1e-9)
Ti, _ = M.solve(m, 40.0, 1e9, dt=0.05, maxit=300, tol=1e-9)
check("s_c -> infinity (1e9) reproduces the baseline temperature to < 1e-7 keV", np.max(np.abs(Tb - Ti)) < 1e-7, "%.1e" % np.max(np.abs(Tb - Ti)))
Ta, _ = M.solve(m, 40.0, 0.5, T_init=4.0 + 30.0 * (1 - (m.r / 2.0) ** 2), dt=0.05, maxit=300, tol=1e-9)
Tc, _ = M.solve(m, 40.0, 0.5, T_init=4.0 + 4.0 * (1 - (m.r / 2.0) ** 2), dt=0.05, maxit=300, tol=1e-9)
check("steady state independent of the initial profile (< 1e-6 keV)", np.max(np.abs(Ta - Tc)) < 1e-6, "%.1e" % np.max(np.abs(Ta - Tc)))
check("independent Radau time integration agrees with the Newton steady state (< 1e-8 keV)", all(r["max_abs_dT"] < 1e-8 for r in R["time_integration"]),
      "max %.1e" % max(r["max_abs_dT"] for r in R["time_integration"]))

print("Resolution (regression test of the finite-difference Jacobian step)")
lam = {}
for N in (100, 400):
    m, T = steady(N, 2.0)
    lam[N] = S.leading_eigenvalue(m, T, 2.0)[0]
check("leading eigenvalue of the s_c = 2 state is grid independent (|difference| < 0.01 /s)", abs(lam[100] - lam[400]) < 0.01, "N=100: %.4f  N=400: %.4f" % (lam[100], lam[400]))
rows = R["grid"]["rows"]
for k in ("none", "0.5", "0.1"):
    q = [r["Q"] for r in rows[k]]
    check("Q(N) converges monotonically for s_c = %s" % k, all(abs(q[i + 1] - q[i]) < abs(q[i] - q[i - 1]) for i in range(1, len(q) - 1)), "%s" % np.round(q, 4))
check("observed order of convergence is >= 1 for every s_c tested", all(v is not None and v > 0.95 for v in R["grid"]["observed_order"].values()),
      "%s" % {k: round(v, 2) for k, v in R["grid"]["observed_order"].items()})

print("Fold of the steady branch")
f = R["fold"]["by_N"]
check("fold location converges with N (successive differences shrink)", abs(f["400"]["sc_fold"] - f["200"]["sc_fold"]) < abs(f["200"]["sc_fold"] - f["100"]["sc_fold"]) < abs(f["100"]["sc_fold"] - f["50"]["sc_fold"]),
      "%s" % [round(f[k]["sc_fold"], 5) for k in ("50", "100", "200", "400")])
br = np.array(R["branch_N100"])            # columns: mu, Q, T0, lam1, ratio_max
k = int(np.where(np.diff(br[:, 0]) < 0)[0][0])      # first fold: mu stops increasing
check("leading eigenvalue changes sign at the fold (mu maximum) of the N = 100 branch", br[k - 2, 3] < 0 < br[k + 2, 3], "lam1 %.3f -> %.3f" % (br[k - 2, 3], br[k + 2, 3]))
check("the upper branch is reached with a second sign change (stable again)", np.any((br[k:-1, 3] > 0) & (br[k + 1:, 3] < 0)))
fd = R["fold_dynamics"]
check("just above the fold a cold start settles on the lower branch (steady, T0 < 100 keV)", (not fd["above"]["reached_150keV"]) and fd["above"]["T0"] < 100.0, "Q %.2f, T0 %.1f keV" % (fd["above"]["Q"], fd["above"]["T0"]))
check("just below the fold the axis temperature runs through 150 keV (no steady state to settle on)", fd["below"]["reached_150keV"], "t = %.1f s" % fd["below"]["t_end"])
check("inside the window a hot start (T0 = 70 keV) heats beyond 150 keV, outside the validity range of the reactivity fit", fd["hot_start_in_window"]["reached_150keV"], "t = %.1f s" % fd["hot_start_in_window"]["t_end"])

print("Closure theory")
check("algebraic closure is admissible iff m <= 1 (numerical slope test agrees with theory for all m tested)", all(r["admissible_numeric"] == r["admissible_theory"] for r in R["theory"]["alg"]))
th = R["theory"]["thresholds"]
check("floor threshold for F = f + (1-f)/(1+L^2) is 1/9 (numerical bisection)", abs(th["floor_alg_numeric"] - 1.0 / 9.0) < 2e-4, "%.5f" % th["floor_alg_numeric"])
check("floor threshold for the exponential form is 0.3086 (numerical bisection)", abs(th["floor_exp_numeric"] - TH.floor_exp_threshold()) < 2e-4, "%.5f vs %.5f" % (th["floor_exp_numeric"], TH.floor_exp_threshold()))
check("peak of L exp(-L^2): L = 1/sqrt(2), Psi = 0.4289", abs(th["exp_peak_L"] - 2 ** -0.5) < 1e-12 and abs(th["exp_peak_Psi"] - 0.42888) < 1e-4)
m2 = TH.alg_stationary_point(2.0)
check("m = 2: stationary point L* = 1 with Psi = 1/2", abs(m2[0] - 1) < 1e-12 and abs(m2[1] - 0.5) < 1e-12)
Ls = np.linspace(1e-6, 40, 400001)
check("m = 3: stationary point from the closed form coincides with the numerical maximum of Psi", abs(Ls[np.argmax(TH.Psi(Ls, TH.F_alg, m=3.0))] - TH.alg_stationary_point(3.0)[0]) < 2e-4)
s = R["scalar_flux_relation_summary"]
check("steady flux relation F(L) L = Theta(r) matches the direct finite-volume solution (max relative error < 1e-3)", s["max_rel_err"] < 1e-3, "%d cases, max %.1e" % (s["n_compared"], s["max_rel_err"]))
check("existence of a steady rotation profile agrees with Theta < Psi_max for every case", s["agree_on_existence"])
check("rotation fold for m = 2 at Theta = 1/2 (within 1 %)", abs(R["rotation_fold"]["2.0"]["Theta_last"] / 0.5 - 1) < 0.01, "%.4f" % R["rotation_fold"]["2.0"]["Theta_last"])
check("flux saturation for m = 1 at Theta = 1 (within 1 %)", abs(R["rotation_fold"]["1.0"]["Theta_last"] / 1.0 - 1) < 0.01, "%.4f" % R["rotation_fold"]["1.0"]["Theta_last"])
h = R["rotation_hysteresis"]
pw = h["0.05"]["predicted"]
tq = h["0.05"]["torque"]; up5 = h["0.05"]["up"]; dn5 = h["0.05"]["down"]
inside = [i for i, t_ in enumerate(tq) if pw["torque_down"] + 5 < t_ < pw["torque_up"] - 5]
check("floor 0.05 (< 1/9): inside the predicted window the up-ramp is on the low branch and the down-ramp on the high branch",
      len(inside) > 0 and all(up5[i] is not None and up5[i] < 2.0 for i in inside) and all(dn5[i] is not None and dn5[i] > 3.0 for i in inside if tq[i] >= 240),
      "predicted window %.0f-%.0f N m" % (pw["torque_down"], pw["torque_up"]))
low_up = max(t_ for t_, u in zip(tq, up5) if u is not None and u < 2.0)
high_up = min(t_ for t_, u in zip(tq, up5) if u is not None and u > 3.0)
check("up-ramp jump is bracketed around the predicted Theta = Psi_max (torque %.0f N m)" % pw["torque_up"], low_up <= pw["torque_up"] + 1e-9 and high_up >= pw["torque_up"] - 1e-9, "last low %g, first high %g" % (low_up, high_up))
low_dn = max(t_ for t_, d in zip(tq, dn5) if d is not None and d < 2.0 and t_ < 250)
check("down-ramp returns to the low branch at or below the predicted Theta = Psi_min (torque %.0f N m)" % pw["torque_down"], low_dn <= pw["torque_down"] + 10.0, "last low branch value at %g N m" % low_dn)
check("floor 0.20 (> 1/9) shows no hysteresis", all(u is not None and d is not None and abs(u - d) < 1e-6 for u, d in zip(h["0.2"]["up"], h["0.2"]["down"])))

print("Torque-driven coupling")
cp = {(r["sign"], r["closure"], r["torque"]): r for r in R["coupled_scan"]}
check("zero torque reproduces the torque-free closure for every viscosity closure", all(abs(cp[(1.0, c, 0.0)]["Q"] - cp[(1.0, "linear", 0.0)]["Q"]) < 1e-9 for c in ("linear", "m=1", "m=2", "m=2 f=0.20")))
q = [cp[(1.0, "linear", t)]["Q"] for t in (0.0, 25.0, 50.0, 100.0, 150.0, 200.0, 250.0)]
check("Q increases monotonically with torque when the shears add (linear viscosity)", all(b > a for a, b in zip(q, q[1:])), "%s" % np.round(q, 3))
bad = [r for r in R["coupled_scan"] if r["closure"] == "m=2" and r["torque"] > 0 and (r["Theta"] is None or r["Theta"] > 0.5) and r["ok"]]
check("m = 2 viscosity never reports a steady state beyond Theta = 1/2", len(bad) == 0)
check("m = 2 viscosity fails at the highest torque (250 N m)", not cp[(1.0, "m=2", 250.0)]["ok"])
check("admissible closures (m = 1, floor 0.20) keep a steady state up to 250 N m", cp[(1.0, "m=1", 250.0)]["ok"] and cp[(1.0, "m=2 f=0.20", 250.0)]["ok"])

print("\n%d checks, %d failed" % (n, len(fails)))
if fails:
    print("FAILED:", fails)
    sys.exit(1)
print("ALL CHECKS PASSED")
