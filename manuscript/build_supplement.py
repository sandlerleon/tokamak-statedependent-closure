# -*- coding: utf-8 -*-
"""Builds the supplementary material (proofs, numerical protocol, extended results, file manifest) from results.json.   python build_supplement.py -> out/Supplementary_Material_IEEE_TPS.docx"""
import hashlib
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import docx_helpers as H  # noqa: E402

OUT = os.path.join(HERE, "out")
R = json.load(open(os.path.join(ROOT, "results.json"), encoding="utf-8"))
ZEN = json.load(open(os.path.join("C:" + os.sep, "YouTube", "_tok_zenodo_state.json")))
RELEASE = os.environ.get("RELEASE_TAG", "v1.1.1")
SW_DOI = (ZEN.get("software_" + RELEASE[1:]) or ZEN["software"])["doi"]
REPO = "https://github.com/sandlerleon/tokamak-statedependent-closure"
THR = R["theory"]["thresholds"]

doc = H.new_document(size=10.5, line=1.25)
H.page_numbers_and_line_numbers(doc, line_numbers=False)
TN = [0]


def P(text, **kw):
    kw.setdefault("align", "justify")
    return H.para(doc, text, **kw)


def HD(t, lvl=1):
    return H.heading(doc, t, lvl)


def TAB(rows, caption, widths=None, size=8):
    TN[0] += 1
    H.caption(doc, "**Table S%d.** %s" % (TN[0], caption), keep_next=True)
    H.table(doc, rows, widths=widths, size=size)


def sci(x, k=1):
    s = ("%." + str(k) + "e") % x
    mant, ex = s.split("e")
    return "%s×10^{%s}" % (mant, ("−%d" % -int(ex)) if int(ex) < 0 else ("%d" % int(ex)))


def pc(x, k=1):
    return ("%." + str(k) + "f") % (100 * x)


p = doc.add_paragraph()
H.add_rich(p, "Supplementary Material for “Numerical Admissibility and Regularization of Shear-Suppression Closures for Reduced Tokamak Transport”", size=14, bold=True)
P("L. Sandler. Contents: S1 Proofs; S2 Numerical protocol; S3 Extended results; S4 Reproduction and file manifest.", align="left")

HD("S1 Proofs")
P("*Proof of Proposition 1.* In steady state Eq. (6) of the paper gives (1/r)∂_{r}(rG) = −τ_{in} with G = μ_{eff}R_{0}²∂_{r}Ω. Integrating from the axis, where rG vanishes by regularity, gives rG(r) = −I(r) with I = ∫_{0}^{r}τ_{in}r′dr′. "
  "Hence μ_{0}R_{0}²F(Λ)|∂_{r}Ω| = I/r. With Λ = κ|∂_{r}Ω| and κ = r/(qγ_{0}), |∂_{r}Ω| = Λ/κ and F(Λ)Λ = Iκ/(rμ_{0}R_{0}²) = I/(qγ_{0}μ_{0}R_{0}²) = Θ. The total torque is ∫τ_{in}dV = 4π²R_{0}I(a). ∎")
P("*Proof of Proposition 2.* (a) Ψ′ = F + ΛF′ = F(1 + d ln F/d ln Λ) and F > 0. (b) If Ψ is strictly increasing and continuous with Ψ(0) = 0 and Ψ(Λ) → Ψ_{∞}, then Ψ(Λ) = Θ has exactly one solution for 0 ≤ Θ < Ψ_{∞} and none otherwise. "
  "(c) If Ψ increases to Ψ_{M} at Λ_{M}, decreases to Ψ_{m} at Λ_{m} and increases again, the equation has three solutions for Ψ_{m} < Θ < Ψ_{M}, one for Θ < Ψ_{m}, and one on the upper branch for Θ > Ψ_{M}. "
  "The branch from Λ = 0 is continuous in Θ until Θ = Ψ_{M}, where it ends; a state on the upper branch is continuous until Θ = Ψ_{m}. Because the steady relation is algebraic at each radius, the jump occurs at the first radius at which Θ(r) reaches the critical value, "
  "and Θ_{max} = θ′T_{tot} because Θ is linear in the torque. ∎")
P("*Proof of Proposition 3.* (i) d ln F/d ln Λ = −mΛ^{m}/(1 + Λ^{m}) decreases monotonically from 0 to −m and stays above −1 for all Λ if and only if m ≤ 1. For m > 1, Ψ′ = (1 + Λ^{m} − mΛ^{m})/(1 + Λ^{m})² = 0 at (Λ^{*})^{m} = 1/(m − 1), where F = 1/m and Ψ = Λ^{*}/m; "
  "for m = 2, Λ^{*} = 1 and Ψ = 1/2; for m = 1, Ψ = Λ/(1 + Λ) → 1. (ii) With F = f + (1 − f)/(1 + Λ²), Ψ′ = f + (1 − f)g(x), g(x) = (1 − x)/(1 + x)², x = Λ² ≥ 0. Then g′ = (x − 3)/(1 + x)³, so g has its minimum at x = 3, g = −1/8, "
  "and Ψ′ > 0 for all Λ if and only if f − (1 − f)/8 > 0, i.e. f > 1/9. (iii) With F = f + (1 − f)e^{−αΛ²}, Ψ′ = f + (1 − f)(1 − 2x)e^{−x}, x = αΛ². The function h(x) = (1 − 2x)e^{−x} has h′ = (2x − 3)e^{−x}, a minimum −2e^{−3/2} = −0.4463 at x = 3/2, "
  "so Ψ′ > 0 if and only if f > 0.4463(1 − f), i.e. f > %.4f, independent of α. For f = 0, Ψ has its maximum at Λ = (2α)^{−1/2} with Ψ = (2αe)^{−1/2}. ∎" % THR["floor_exp"])
P("*Branching of the local heat closure (Section III-B).* With T in keV, E_{r} = 10³(T′ + T n′/n) V m^{−1} and ω_{dia} = (r/q)∂_{r}(qE_{r}/rB) = ω_{0}(r, T, T′) + (10³/B)T″, where ω_{0} collects the terms without T″. "
  "The heat flux is Φ = 3nχ_{base}(T′, T)T′/[1 + ω_{dia}²/(s_{c}γ_{0})²], which depends on T″ only through ω_{dia}². Integrating the steady balance from the axis gives rΦ = −I_{h}(r). For given T′, T and a flux demand below the maximum of Φ over ω_{dia}, "
  "the equation Φ = −I_{h}/r has the two roots ω_{dia} = ±ω^{*}, i.e. two values of T″. The steady local problem is therefore a branching second-order equation; the Dirichlet edge value T(a) = T_{a} and regularity at the axis do not select a branch. "
  "In the smoothed closure the flux depends on T″ through A, the solution of A − ℓ²r^{−1}(rA′)′ = (ω_{E}/γ_{0})² with A′(0) = A′(a) = 0, so (T, A) is a closed system with four conditions for two second-order equations. This is a diagnosis consistent with the numerical evidence of Section V-A; it is not a proof of ill-posedness. "
  "The principal part of the linearization, D_{eff} = [∂Φ/∂T′ + ∂_{r}(∂Φ/∂T″)]/3n, was evaluated on the converged local profiles and is positive (Table S4), so the local problem does not lose ellipticity.")

HD("S2 Numerical protocol")
P("*Grid and discretization.* N uniform cells in r (N = 50–800); face conductivities are arithmetic means of the adjacent cell values. The cell gradient of the edge cell is (4T_{a}/3 − T_{N} − T_{N−1}/3)/Δr and the edge-face derivative of f is (8f_{a}/3 − 3f_{N} + f_{N−1}/3)/Δr (quadratics through the edge value and the last two cells); "
  "the axis cell uses T = A + Br², so ∂_{r}T = (T_{2} − T_{1})/2Δr there; u = qE_{r}/rB is extrapolated evenly to the axis, u_{0} = (4u_{1} − u_{2})/3. The edge-face diffusivity is the linear extrapolation 1.5χ_{N} − 0.5χ_{N−1}.")
P("*Steady states.* Damped Newton iteration on the steady residual; Jacobian by central differences with a relative step 10^{−8} (banded with three sub- and super-diagonals for the local closure, dense for the smoothed closure); acceptance at a residual below 10^{−8} of the volume-averaged heating. "
  "The baseline is first marched in pseudo-time (backward Euler, step 0.05 s growing by 1.5 up to 50 s) from a parabolic profile; the closure is introduced by continuation in s_{c} (4, 2, 1, 0.7, 0.5, 0.4, 0.3, 0.2, 0.15, 0.1, 0.07, 0.05, 0.04, 0.03, 0.02). "
  "Eigenvalues are those of the dense Jacobian divided by 3ne. A finite-difference step of 10^{−6} gave a wrong derivative of the shearing rate near the axis (a quadratic contribution), a spurious instability, and Newton failures, which is why the step is 10^{−8}; "
  "at N ≥ 400 the residual cannot be reduced below about 10^{−10} because of round-off, hence the tolerance.")
P("*Time integration.* Radau (rtol = atol = 10^{−8}, sparse pattern for the local closure) of dT/dt = residual/3ne from a parabolic cold profile; accessibility runs use rtol = atol = 10^{−7} and stop when the axis temperature exceeds 150 keV.")
P("*Rotation equation.* The unknown is scaled by the linear-viscosity solution; Newton iteration (hybrid method) with eight steps of torque continuation; acceptance at a scaled residual below 10^{−8}. Ramps use backward-Euler marching with the step doubled after every accepted step until the steady residual is below 10^{−10}; "
  "runs that do not converge near a fold are reported as not converged. *Coupled problem.* Fixed-point iteration between the rotation solve and the heat solve, converged when the maximum temperature change is below 10^{−7} keV.")
P("*Uncertainty study.* Scrambled Sobol sequences (scipy.stats.qmc, seed %d): %d points for the heat-closure parameters (ranges in Table S8) and %d for the torque study; failures (no steady state) are counted and excluded. Spearman rank correlations use the sampled parameter values and the relative gain." %
  (R["uncertainty_heat"]["seed"], R["uncertainty_heat"]["stats"]["n_samples"], R["uncertainty_torque"]["n_samples"]))
P("*Software.* Python %s, NumPy %s, SciPy %s; release %s of the repository contains the exact scripts and results.json." % (R["versions"]["python"], R["versions"]["numpy"], R["versions"]["scipy"], RELEASE))

HD("S3 Extended results")
H.figure(doc, os.path.join(ROOT, "figures", "fig1_profiles.png"), width_in=6.2, cap="**Figure S1.** (a) Temperature, (b) diffusivity, and (c) smoothed shearing rate against r/a at 40 MW (N = 400, ℓ = 0.05 m) for the baseline and the closure with s_{c} = 0.3 and 0.1.",
         alt="Radial profiles of temperature, diffusivity and smoothed shearing rate.")
H.figure(doc, os.path.join(ROOT, "figures", "figS1_power_scan.png"), width_in=5.4, cap="**Figure S2.** (a) Gain and (b) relative gain against auxiliary power for the baseline and three closure settings (N = 200).",
         alt="Fusion gain against heating power.")
rows = [["s_{c}", "Q", "P_{fus} (MW)", "τ_{E} (s)", "⟨T⟩ (keV)", "T_{0} (keV)", "max smoothed ω_{E}/γ_{0}", "H_{89}", "H_{98}", "β_{N}", "λ_{1} (s^{−1})"]]
for r in R["table1"]:
    rows.append(["∞" if r["sc"] is None else "%g" % r["sc"], "%.4f" % r["Q"], "%.1f" % r["Pfus"], "%.4f" % r["tauE"], "%.3f" % r["Tavg"], "%.2f" % r["T0"], "%.3f" % r["ratio_max"], "%.2f" % r["H89"], "%.2f" % r["H98"], "%.2f" % r["beta_N"], "%.2f" % r["lam1"]])
TAB(rows, "Smoothed closure (ℓ = 0.05 m, N = 200) at 40 MW; all rows are steady states with power-balance residual below 10^{−9}.", widths=[0.4, 0.6, 0.6, 0.6, 0.55, 0.55, 0.8, 0.45, 0.45, 0.45, 0.6], size=7.5)
rows = [["s_{c}", "N = 100", "N = 200", "N = 400", "N = 800", "orders (100-200-400, 200-400-800)"]]
for k, row in R["grid"]["rows"].items():
    o = R["grid"]["observed_order"][k]
    rows.append(["∞" if k == "none" else k] + ["%.5f" % r["Q"] for r in row] + [", ".join("–" if v is None else "%.2f" % v for v in o)])
TAB(rows, "Convergence of Q with N for the smoothed closure.", widths=[0.5, 0.8, 0.8, 0.8, 0.8, 1.6])
rows = [["N"] + ["s_{c} = %g" % r["sc"] for r in R["local_closure"]["rows"]["400"] if r["ok"]]]
for N in ("50", "100", "200", "400"):
    d = {r["sc"]: r for r in R["local_closure"]["rows"][N] if r["ok"]}
    rows.append([N] + ["%.3g" % d[r["sc"]]["lam1"] if r["sc"] in d else "–" for r in R["local_closure"]["rows"]["400"] if r["ok"]])
TAB(rows, "Local closure: leading eigenvalue λ_{1} (s^{−1}) of the steady state against s_{c} and N. Onset thresholds s_{c}^{lin}: " + ", ".join("N = %s: %.3f" % (k, v) for k, v in R["local_closure"]["threshold"].items() if v) + ".", widths=[0.4] + [0.55] * 10, size=7)
rows = [["Closure (edge condition)", "Q(0.1), N=200", "Q(0.1), N=400", "λ_{1}(0.1), N=400", "Q(0.05), N=200", "Q(0.05), N=400", "λ_{1}(0.05), N=400"]]
for r in R["edge_variants"]:
    f = lambda k: "–" if r.get(k) is None else ("%.3f" % r[k] if k.startswith("Q") else "%.3g" % r[k])
    rows.append([r["name"], f("Q@0.1/N200"), f("Q@0.1/N400"), f("lam@0.1/N400"), f("Q@0.05/N200"), f("Q@0.05/N400"), f("lam@0.05/N400")])
TAB(rows, "Gain Q at s_{c} = 0.1 and 0.05 for all edge treatments and smoothing lengths (– : no steady state found by Newton continuation).", widths=[1.8, 0.65, 0.65, 0.65, 0.65, 0.65, 0.65], size=7.5)
rows = [["s_{c}", "min D_{eff} (m² s^{−1})", "at r/a", "min of the T″ part (m² s^{−1})"]]
for e in R["principal_part"]:
    rows.append(["∞" if e["sc"] > 1e8 else "%g" % e["sc"], "%.4f" % e["Dmin"], "%.3f" % e["r_over_a"], "%.4f" % e["D2_min"]])
TAB(rows, "Principal part of the linearized local closure (N = 400): D_{eff} stays positive, so ellipticity is not lost.", widths=[0.6, 1.4, 0.8, 1.6])
rows = [["s_{c}", "smoothed closure (N = 100)", "t (s) / T_{0} (keV) at stop", "local closure (N = 100)", "t (s) / T_{0} (keV) at stop"]]
for a_, b_ in zip(R["accessibility"]["smoothed"], R["accessibility"]["local"]):
    rows.append(["%g" % a_["sc"], "settles" if a_["settled"] else "runs away", "%.1f / %.1f" % (a_["t_end"], a_["T0"]), "settles" if b_["settled"] else "runs away", "%.1f / %.1f" % (b_["t_end"], b_["T0"])])
TAB(rows, "Dynamic accessibility from a cold start (120 s horizon; run stopped at T_{0} = 150 keV).", widths=[0.5, 1.4, 1.4, 1.4, 1.4])
rows = [["m", "Torque (N m)", "Θ_{max}", "Λ_{max} predicted", "Λ_{max} simulated", "relative error"]]
for r in R["scalar_flux_relation"]:
    if r["exists_numeric"] and r["exists_theory"]:
        rows.append(["%g" % r["m"], "%g" % r["torque"], "%.4f" % r["Theta_max"], "%.8f" % r["Lam_pred"], "%.8f" % r["Lam_sim"], sci(abs(r["Lam_sim"] / r["Lam_pred"] - 1), 1)])
    else:
        rows.append(["%g" % r["m"], "%g" % r["torque"], "%.4f" % r["Theta_max"], "none (Θ > Ψ_{∞})", "no steady state", "–"])
TAB(rows, "Steady flux relation against the direct finite-volume solution of the rotation equation (all cases).", widths=[0.4, 0.9, 0.7, 1.4, 1.4, 1.0], size=7.5)
rows = [["σ", "Closure", "0", "25", "50", "100", "150", "200", "250 N m"]]
for sign in (1.0, -1.0):
    for clos in ("linear", "m=1", "m=2 f=0.20", "m=2"):
        row = [("+1" if sign > 0 else "−1"), clos]
        for t in (0.0, 25.0, 50.0, 100.0, 150.0, 200.0, 250.0):
            c = [x for x in R["coupled_scan"] if x["sign"] == sign and x["closure"] == clos and x["torque"] == t][0]
            row.append("%.3f" % c["Q"] if c["ok"] else "none")
        rows.append(row)
TAB(rows, "Gain with torque-driven shear (s_{c} = 0.5, N = 100, Pr = 1): all viscosity closures and both orientations.", widths=[0.35, 1.0] + [0.62] * 7, size=7.5)
rows = [["Pr", "Closure", "Θ_{max}", "Q"]]
for r in R["coupled_Pr"]:
    rows.append(["%g" % r["Pr"], r["closure"], "–" if r["Theta"] is None else "%.3f" % r["Theta"], "none" if not r["ok"] else "%.3f" % r["Q"]])
TAB(rows, "Sensitivity to the viscosity multiplier at 200 N m (s_{c} = 0.5).", widths=[0.5, 1.2, 0.8, 0.8])
rows = [["s_{c}", "Q at 0", "25", "36", "50", "100", "200 N m"]]
for r in R["coupled_sc_torque"]:
    d = {x["torque"]: x["Q"] for x in r["rows"]}
    rows.append(["%g" % r["sc"]] + ["%.3f" % d[t] for t in (0.0, 25.0, 36.0, 50.0, 100.0, 200.0)])
TAB(rows, "Gain with torque-driven shear against s_{c} (constant viscosity, shears adding, N = 100).", widths=[0.5] + [0.75] * 6)
b = R["uncertainty_heat"]["bounds"]
rows = [["Parameter", "Range", "Spearman ρ, gain at 0.3", "at 0.1", "at 0.05"]]
names = {"chi_s": "χ_{s} (m² s^{−1})", "kappa_c": "κ_{c}", "w": "w", "Ta": "T_{a} (keV)", "n0": "n_{0} (m^{−3})", "B": "B (T)", "reg_length": "ℓ (m)"}
st = R["uncertainty_heat"]["stats"]
for k in b:
    rows.append([names[k], "%g – %g" % (b[k][0], b[k][1]), "%.2f" % st["gain@0.3"]["rank_corr"][k], "%.2f" % st["gain@0.1"]["rank_corr"][k], "%.2f" % st["gain@0.05"]["rank_corr"][k]])
rows.append(["gain 5 / 50 / 95 %", "–", "%s / %s / %s %%" % tuple(pc(st["gain@0.3"][q], 2) for q in ("p05", "p50", "p95")), "%s / %s / %s %%" % tuple(pc(st["gain@0.1"][q], 1) for q in ("p05", "p50", "p95")),
             "%s / %s / %s %%" % tuple(pc(st["gain@0.05"][q], 1) for q in ("p05", "p50", "p95"))])
TAB(rows, "Heat-closure uncertainty study (%d points, %d converged): sampled ranges, rank correlations, and gain percentiles. Baseline Q: %.2f / %.2f / %.2f (5 / 50 / 95 %%)." % (st["n_samples"], st["n_ok"], st["Q0"]["p05"], st["Q0"]["p50"], st["Q0"]["p95"]),
    widths=[1.4, 1.2, 1.3, 1.1, 1.1])
bt = R["uncertainty_torque"]
rows = [["Parameter", "Range", "Spearman ρ with the gain"]]
nm2 = {"torque": "torque (N m)", "width": "torque width (a)", "Pr": "Pr", "s_c": "s_{c}", "sign": "orientation σ", "reg_length": "ℓ (m)"}
for k in bt["bounds"]:
    rows.append([nm2[k], "%g – %g" % tuple(bt["bounds"][k]), "%.2f" % bt["rank_corr"][k]])
TAB(rows, "Torque uncertainty study (%d points, %d converged): gain %s–%s %% (median %s %%)." % (bt["n_samples"], bt["n_ok"], pc(bt["p05"], 0), pc(bt["p95"], 0), pc(bt["p50"], 0)), widths=[1.6, 1.3, 1.6])
cal = R["calibration"]
rows = [["Quantity", "Value"],
        ["Reference device", "R_{0} = 6.2 m, a = 2.0 m, B = 5.3 T, I_{p} = %.0f MA, κ_{a} = %.1f, 2.5 amu" % (cal["ref"]["I_MA"], cal["ref"]["kappa_a"])],
        ["IPB98(y,2)", "τ = 0.0562 I^{0.93}B^{0.15}P^{−0.69}n_{19}^{0.41}M^{0.19}R^{1.97}ε^{0.58}κ_{a}^{0.78} (s; MA, T, MW, 10^{19} m^{−3}, amu, m)"],
        ["ITER89-P", "τ = 0.048 M^{0.5}I^{0.85}R^{1.2}a^{0.3}κ^{0.5}n_{20}^{0.1}B^{0.2}P^{−0.5}"],
        ["β_{N}; Greenwald", "β_{N} = 100 β aB/I_{p} (β from 2μ_{0}⟨p⟩/B², p = 2nT); n_{G} = I_{p}/πa² = %.2f×10^{20} m^{−3}" % cal["n_G"]],
        ["Beam torque", "T = 2PR_{t}/v; v = %.3f×10^{6} m s^{−1}; R_{t} = 4.5, 5.3, 6.0 m: %.1f, %.1f, %.1f N m" % (cal["v_beam"] / 1e6, cal["nbi_torque"]["4.5"], cal["nbi_torque"]["5.3"], cal["nbi_torque"]["6.0"])],
        ["Ion gyroradius", "ρ_{i} = (m_{i}T)^{1/2}/eB = %.2f mm at 10 keV, 5.3 T" % (cal["rho_i_10keV"] * 1e3)]]
TAB(rows, "Calibration formulas and values.", widths=[1.3, 5.2])

HD("S4 Reproduction and file manifest")
P("Running code/reproduce.py (about 40 minutes), code/tests.py (about 5 minutes), and code/figures.py regenerates results.json and the figures; the builders in manuscript/ produce the manuscript, this file, and the cover letter. No experimental data are used. "
  "The repository is %s (release %s), archived at https://doi.org/%s. The first 16 hexadecimal digits of the SHA-256 checksum of each file at release %s follow." % (REPO, RELEASE, SW_DOI, RELEASE))


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16] + "…"


files = sorted(["code/" + f for f in os.listdir(os.path.join(ROOT, "code")) if f.endswith(".py")]) + ["refs/build_refs.py", "results.json", "requirements.txt", "LICENSE"] + ["figures/" + f for f in sorted(os.listdir(os.path.join(ROOT, "figures"))) if f.endswith(".png")]
rows = [["File", "SHA-256 (first 16 hex digits)"]] + [[f, sha(os.path.join(ROOT, f))] for f in files]
TAB(rows, "File manifest.", widths=[3.2, 2.2], size=7.5)
doc.save(os.path.join(OUT, "Supplementary_Material_IEEE_TPS.docx"))
print("saved supplement; tables:", TN[0])
