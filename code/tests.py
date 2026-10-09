# -*- coding: utf-8 -*-
"""Verification checks for the closed forms, the solver, and the reported results.   python tests.py   (about 3 minutes; reads ../results.json where noted)"""
import json
import os
import sys

import numpy as np

import calibration as CAL
import model as M
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


TB = {(r["sc"] if r["sc"] is not None else "base"): r for r in R["table1"]}
print("Model and solver")
check("Bosch-Hale reactivity at 10 keV (1.136e-22 m^3/s)", abs(M.sigma_v(10.0) / 1.136e-22 - 1) < 1e-3, "%.4e" % M.sigma_v(10.0))
check("Bosch-Hale reactivity at 20 keV (4.33e-22 m^3/s)", abs(M.sigma_v(20.0) / 4.33e-22 - 1) < 1e-3, "%.4e" % M.sigma_v(20.0))
check("power balance closes to < 1e-9 of the heating for s_c = inf, 0.5, 0.1, 0.03", max(abs(v) for v in R["verify"]["resid"].values()) < 1e-9, "%s" % {k: "%.1e" % v for k, v in R["verify"]["resid"].items()})
check("s_c = 1e9 reproduces the baseline temperature (< 1e-7 keV)", R["verify"]["max_dT_sc_1e9"] < 1e-7)
check("steady state independent of the initial profile (< 1e-6 keV)", R["verify"]["ic_independence"] < 1e-6, "%.1e" % R["verify"]["ic_independence"])
check("independent Radau time integration agrees with the Newton steady state (< 1e-7 keV), smoothed closure", max(r["max_abs_dT"] for r in R["time_integration"]) < 1e-7,
      "max %.1e" % max(r["max_abs_dT"] for r in R["time_integration"]))
check("baseline gain within 1 % of 3.70 at 40 MW (consistency with the reference run)", abs(TB["base"]["Q"] / 3.70 - 1) < 0.01, "Q = %.4f" % TB["base"]["Q"])

print("Smoothed closure: well posed and second-order convergent")
check("leading eigenvalue is negative for every s_c in the controlled comparison (down to 0.02)", all(r["lam1"] < 0 for r in R["table1"]), "max %.2f" % max(r["lam1"] for r in R["table1"]))
orders = [v for o in R["grid"]["observed_order"].values() for v in o if v]
check("observed order of convergence of Q is between 1.6 and 2.2 for every s_c tested", min(orders) > 1.6 and max(orders) < 2.2, "%.2f-%.2f" % (min(orders), max(orders)))
check("Q converges monotonically with N at s_c = 0.5, 0.2, 0.1, 0.05",
      all(abs(np.diff([x["Q"] for x in R["grid"]["rows"][k]])[2]) < abs(np.diff([x["Q"] for x in R["grid"]["rows"][k]])[0]) for k in ("0.5", "0.2", "0.1", "0.05")))
check("leading eigenvalue of the s_c = 2 state is grid independent (N = 100, 400; < 0.01 /s)", abs(R["verify"]["lambda1_sc2"]["100"] - R["verify"]["lambda1_sc2"]["400"]) < 0.01,
      "%.4f, %.4f" % (R["verify"]["lambda1_sc2"]["100"], R["verify"]["lambda1_sc2"]["400"]))
lr = R["linear_response"]
check("gain follows C/s_c^2 within 15 % over 0.02 <= s_c <= 1", all(abs((r["Q"] - TB["base"]["Q"]) / (lr["C_mean"] / r["sc"] ** 2) - 1) < 0.15 for r in R["table1"] if r["sc"] is not None), "C = %.5f" % lr["C_mean"])
check("a cold start settles on the steady state for every s_c tested (smoothed closure)", all(r["settled"] for r in R["accessibility"]["smoothed"]))
check("closure gain at s_c = 0.3 is positive and below 1 %", 0 < TB[0.3]["dQ"] < 0.01, "%.2f %%" % (100 * TB[0.3]["dQ"]))

smt = R["smoothed_threshold"]
check("smoothed closure: the resolution-limited instability threshold falls with N (0.034 > 0.025 > 0.015 > none at N = 800)",
      smt["100"]["threshold"] > smt["200"]["threshold"] > smt["400"]["threshold"] > 0 and smt["800"]["threshold"] is None, "%s" % {k: v["threshold"] for k, v in smt.items()})

print("Local closure: ill posed")
lc = R["local_closure"]
th = [lc["threshold"][k] for k in ("50", "100", "200", "400")]
check("instability threshold increases with N", all(b > a for a, b in zip(th, th[1:])), "%s" % np.round(th, 3))
check("threshold grows roughly as N^(1/2) (exponent 0.4-0.7)", 0.4 < lc["threshold_exponent"] < 0.7, "%.2f" % lc["threshold_exponent"])
r2 = {x["sc"]: x for x in lc["rows"]["200"] if x["ok"]}
r4 = {x["sc"]: x for x in lc["rows"]["400"] if x["ok"]}
check("growth rate at s_c = 0.2 rises by more than a factor 5 from N = 200 to 400", r4[0.2]["lam1"] > 5 * r2[0.2]["lam1"] > 0, "%.2g -> %.2g /s" % (r2[0.2]["lam1"], r4[0.2]["lam1"]))
check("the unstable mode is localized within 10 cells of the edge", all(x["peak_from_edge"] < 10 for N in ("100", "200", "400") for x in lc["rows"][N] if x["ok"] and x["lam1"] > 0))
check("the principal part stays elliptic (min D_eff > 0.2 m^2/s)", min(p["Dmin"] for p in R["principal_part"]) > 0.2, "min %.4f" % min(p["Dmin"] for p in R["principal_part"]))
ev = {r["name"]: r for r in R["edge_variants"]}
q_hold, q_zero = ev["local, edge value held"]["Q@0.05/N400"], ev["local, no suppression in the last cell"]["Q@0.05/N400"]
check("the converged local-closure answer depends on the edge condition (> 5 % at s_c = 0.05)", abs(q_hold / q_zero - 1) > 0.05, "%.3f vs %.3f" % (q_hold, q_zero))
sm = [ev["smoothed, l = %s m" % x]["Q@0.1/N400"] for x in ("0.02", "0.05", "0.10", "0.20")]
check("the smoothed closure is insensitive to l (< 3 % over 0.02-0.20 m at s_c = 0.1)", max(sm) / min(sm) - 1 < 0.03, "%.2f %%" % (100 * (max(sm) / min(sm) - 1)))
check("the first-order edge treatment shows a spurious fold (s_c about 0.05)", 0.03 < R["first_order_fold_N400"]["sc_fold"] < 0.07, "%.4f" % R["first_order_fold_N400"]["sc_fold"])
mm = M.Model(200, reg_length=0.0)
T, _ = M.solve(mm, 40.0, None, dt=0.05, maxit=300, tol=1e-9)
for s_ in (1.0, 0.5, 0.3):
    T, ok = S.steady_newton(mm, s_, T)
lam = S.leading_eigenvalue(mm, T, 0.3)[0]
check("regression: the local closure at N = 200, s_c = 0.3 is stable (lambda_1 < 0)", lam < 0, "%.3f" % lam)

print("Closure theory")
check("algebraic closure is admissible iff m <= 1 (numerical slope test agrees with theory for all m tested)", all(r["admissible_numeric"] == r["admissible_theory"] for r in R["theory"]["alg"]))
thr = R["theory"]["thresholds"]
check("floor threshold for F = f + (1-f)/(1+L^2) is 1/9 (numerical bisection)", abs(thr["floor_alg_numeric"] - 1.0 / 9.0) < 2e-4, "%.5f" % thr["floor_alg_numeric"])
check("floor threshold for the exponential form is 0.3086 (numerical bisection)", abs(thr["floor_exp_numeric"] - TH.floor_exp_threshold()) < 2e-4, "%.5f" % thr["floor_exp_numeric"])
check("peak of L exp(-L^2): L = 1/sqrt(2), Psi = 0.4289", abs(thr["exp_peak_L"] - 2 ** -0.5) < 1e-12 and abs(thr["exp_peak_Psi"] - 0.42888) < 1e-4)
check("m = 2: stationary point L* = 1 with Psi = 1/2", abs(TH.alg_stationary_point(2.0)[0] - 1) < 1e-12 and abs(TH.alg_stationary_point(2.0)[1] - 0.5) < 1e-12)
s = R["scalar_flux_relation_summary"]
check("steady flux relation matches the direct solution (max relative error < 1e-9)", s["max_rel_err"] < 1e-9, "%d cases, max %.1e" % (s["n_compared"], s["max_rel_err"]))
check("existence of a steady rotation profile agrees with Theta < Psi_max in every case", s["agree_on_existence"])
check("rotation fold for m = 2 at Theta = 1/2 (within 0.1 %)", abs(R["rotation_fold"]["2.0"]["Theta_last"] / 0.5 - 1) < 1e-3, "%.5f" % R["rotation_fold"]["2.0"]["Theta_last"])
check("flux saturation for m = 1 at Theta = 1 (within 0.1 %)", abs(R["rotation_fold"]["1.0"]["Theta_last"] - 1.0) < 1e-3, "%.5f" % R["rotation_fold"]["1.0"]["Theta_last"])
h = R["rotation_hysteresis"]
pw = h["0.05"]["predicted"]
tq, up5, dn5 = h["0.05"]["torque"], h["0.05"]["up"], h["0.05"]["down"]
inside = [i for i, t_ in enumerate(tq) if pw["torque_down"] + 5 < t_ < pw["torque_up"] - 5]
check("floor 0.05 (< 1/9): inside the predicted window the up-ramp is on the low branch and the down-ramp on the high branch",
      len(inside) > 0 and all(up5[i] is not None and up5[i] < 2.0 for i in inside) and all(dn5[i] is not None and dn5[i] > 3.0 for i in inside if tq[i] >= 240), "window %.0f-%.0f N m" % (pw["torque_down"], pw["torque_up"]))
check("floor 0.20 (> 1/9) shows no hysteresis", all(u is not None and d_ is not None and abs(u - d_) < 1e-6 for u, d_ in zip(h["0.2"]["up"], h["0.2"]["down"])))

print("Torque-driven coupling")
cp = {(r["sign"], r["closure"], r["torque"]): r for r in R["coupled_scan"]}
check("zero torque reproduces the torque-free closure for every viscosity closure", all(abs(cp[(1.0, c, 0.0)]["Q"] - cp[(1.0, "linear", 0.0)]["Q"]) < 1e-9 for c in ("linear", "m=1", "m=2", "m=2 f=0.20")))
q = [cp[(1.0, "linear", t)]["Q"] for t in (0.0, 25.0, 50.0, 100.0, 150.0, 200.0, 250.0)]
check("Q increases monotonically with torque when the shears add (constant viscosity)", all(b > a for a, b in zip(q, q[1:])), "%s" % np.round(q, 3))
check("m = 2 viscosity has no steady state at 250 N m (Theta > 1/2)", not cp[(1.0, "m=2", 250.0)]["ok"])
check("admissible closures (m = 1, floor 0.20) keep a steady state up to 250 N m", cp[(1.0, "m=1", 250.0)]["ok"] and cp[(1.0, "m=2 f=0.20", 250.0)]["ok"])

print("Calibration and uncertainty")
check("baseline H89 within 5 % of 1 (L-mode scaling reproduced)", abs(TB["base"]["H89"] - 1.0) < 0.05, "H89 = %.3f" % TB["base"]["H89"])
check("baseline H98 below 0.6 (L-mode-like)", TB["base"]["H98"] < 0.6, "H98 = %.3f" % TB["base"]["H98"])
check("Greenwald fraction between 0.5 and 0.8", 0.5 < TB["base"]["f_G"] < 0.8, "%.2f" % TB["base"]["f_G"])
check("beta_N stays below 2.8 for every s_c in the study", max(r["beta_N"] for r in R["table1"]) < 2.8, "max %.2f" % max(r["beta_N"] for r in R["table1"]))
cal = R["calibration"]["nbi_torque"]
check("full-energy beam torque for 33 MW, 1 MeV is 30-41 N m for R_t = 4.5-6 m (T = 2 P R_t / v)", 29.0 < cal["4.5"] < 31.0 and 39.0 < cal["6.0"] < 41.0, "%.1f-%.1f" % (cal["4.5"], cal["6.0"]))
t_, v_ = CAL.nbi_torque(R_tan=5.3)
m_d = 2.0141 * 1.66053907e-27
rate = 33e6 / (0.5 * m_d * v_ ** 2)                              # particles per second, P / E
check("beam torque equals (particle rate) x m v R_t", abs(t_ / (rate * m_d * v_ * 5.3) - 1) < 1e-3, "%.2f N m" % t_)
g36 = {r["sc"]: dict((x["torque"], x["Q"]) for x in r["rows"]) for r in R["coupled_sc_torque"]}
check("gain at the beam torque (36 N m) is below 3 % for s_c = 0.5", g36[0.5][36.0] / g36[0.5][0.0] - 1 < 0.03, "%.2f %%" % (100 * (g36[0.5][36.0] / g36[0.5][0.0] - 1)))
uh = R["uncertainty_heat"]["stats"]
check("heat-closure uncertainty study: at least 100 of 128 samples converge", uh["n_ok"] >= 100, "%d of %d" % (uh["n_ok"], uh["n_samples"]))
check("relative gain at s_c = 0.3 stays below 2 % over the sampled parameters (95th percentile)", uh["gain@0.3"]["p95"] < 0.02, "%.2f %%" % (100 * uh["gain@0.3"]["p95"]))
check("relative gain at s_c = 0.1 has a 5-95 % interval within 3-12 %", uh["gain@0.1"]["p05"] > 0.03 and uh["gain@0.1"]["p95"] < 0.12, "%.1f-%.1f %%" % (100 * uh["gain@0.1"]["p05"], 100 * uh["gain@0.1"]["p95"]))

print("Plant power balance (screening level)")
import plant as PL
a0 = dict(eta_th=0.5, M=1.0, eta_aux=0.5, P_other=0.0, kappa=0.0)
b_ = PL.balance(100.0, 20.0, a0)
check("plant balance: hand calculation (P_fus 100, P_aux 20, M = 1, eta 0.5: P_th = 120, P_gross = 60, P_recirc = 40, P_net = 20)", abs(b_["Pth"] - 120) < 1e-9 and abs(b_["Pgross"] - 60) < 1e-9 and abs(b_["Precirc"] - 40) < 1e-9 and abs(b_["Pnet"] - 20) < 1e-9)
qb = PL.q_breakeven(40.0)
check("plant balance: P_net vanishes at the breakeven gain Q_b", abs(PL.balance(qb * 40.0, 40.0)["Pnet"]) < 1e-9, "Q_b = %.3f" % qb)
check("plant balance: neutron energy fraction 14.06/17.59", abs(PL.F_N - 0.7993) < 1e-3)
pl = R["plant"]
check("plant block in results.json reproduces plant.block(results) exactly", abs(pl["cases"][0]["Pnet"] - PL.block(R)["cases"][0]["Pnet"]) < 1e-9)
check("closure gain raises the net electric power at every threshold tested", all(c["dPnet"] > 0 for c in pl["cases"][1:]), "%s" % ["%.1f" % c["dPnet"] for c in pl["cases"][1:]])
check("assumption study: the closure adds 3-5 MW at s_c = 0.1 for 90 % of the sampled assumptions", pl["uncertainty"]["dPnet"]["0.1"]["p05"] > 3.0 and pl["uncertainty"]["dPnet"]["0.1"]["p95"] < 5.0)

print("\n%d checks, %d failed" % (n, len(fails)))
if fails:
    print("FAILED:", fails)
    sys.exit(1)
print("ALL CHECKS PASSED")
