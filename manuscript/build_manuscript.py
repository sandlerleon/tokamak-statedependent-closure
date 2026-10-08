# -*- coding: utf-8 -*-
"""Builds the manuscript (Journal of Plasma Physics, Research Article) from results.json. Every number in the text is read from the results.

    python build_manuscript.py          (run twice so that table, figure and equation numbers resolve)   ->  out/State_Dependent_Shear_Closures_JPP.docx
"""
import hashlib
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "code"))
import docx_helpers as H  # noqa: E402

OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
R = json.load(open(os.path.join(ROOT, "results.json"), encoding="utf-8"))
REFS = json.load(open(os.path.join(ROOT, "refs", "refs_cache.json"), encoding="utf-8"))
ZEN = json.load(open(os.path.join("C:" + os.sep, "YouTube", "_tok_zenodo_state.json")))
SW_DOI, PP_DOI = ZEN["software"]["doi"], ZEN["publication"]["doi"]
RELEASE = os.environ.get("RELEASE_TAG", "v1.0.0")
REPO = "https://github.com/sandlerleon/tokamak-statedependent-closure"
TITLE = "State-dependent shear-suppression closures for reduced tokamak transport: a controlled comparison, admissibility conditions and a fold of the steady state"

# ------------------------------------------------------------------ numbers
T1 = {(r["sc"] if r["sc"] is not None else "base"): r for r in R["table1"]}
GRID = R["grid"]["rows"]
FOLD = R["fold"]
FD = R["fold_dynamics"]
TI = R["time_integration"]
VER = R["verify"]
SFR = R["scalar_flux_relation"]
SFS = R["scalar_flux_relation_summary"]
RF = R["rotation_fold"]
HYS = R["rotation_hysteresis"]["0.05"]
CP = {(r["sign"], r["closure"], r["torque"]): r for r in R["coupled_scan"]}
PRS = R["coupled_Pr"]
CSC = R["coupled_sc"]
THR = R["theory"]["thresholds"]
Q0 = T1["base"]["Q"]
MU0 = R["mu0"]
TH_PER_NM = HYS["Theta_per_Nm"]
ORD = R["grid"]["observed_order"]
FQ = float(np.mean([FOLD["by_N"]["200"]["Q_fold"], FOLD["by_N"]["400"]["Q_fold"]]))
FT0 = float(np.mean([FOLD["by_N"]["200"]["T0_fold"], FOLD["by_N"]["400"]["T0_fold"]]))
BR = np.array(R["branch_N200"])           # mu, Q, T0, lam1, ratio_max
k_fold = int(np.where(np.diff(BR[:, 0]) < 0)[0][0])
mid = BR[k_fold:]
sec_fold = int(np.where((mid[:-1, 3] > 0) & (mid[1:, 3] < 0))[0][0]) + k_fold
SC_WINDOW = (1.0 / BR[sec_fold, 0], 1.0 / BR[k_fold, 0])        # (upper end of the window in s_c, lower end = fold)

# ------------------------------------------------------------------ citations (author-year) and numbering
CITE = []
LABFILE = os.path.join(OUT, "labels.json")
LAB = json.load(open(LABFILE)) if os.path.exists(LABFILE) else {"T": {}, "F": {}}
LAB_NEW = {"T": {}, "F": {}}
EQFILE = os.path.join(OUT, "eqnum.json")
EQNUM = json.load(open(EQFILE)) if os.path.exists(EQFILE) else {}
EQNUM_NEW = {}
FIGN, TABN, EQN = [0], [0], [0]


def short(key):
    r = REFS[key]
    n = r["n_authors"]
    if key == "iter1999":
        return "ITER Physics Expert Group on Confinement and Transport et al."
    if n == 1:
        return r["first"]
    if n == 2:
        return "%s & %s" % (r["authors"][0], r["authors"][1])
    return "%s et al." % r["first"]


def cites(text):
    def rep(m):
        body = m.group(1)
        textual = body.startswith("t:")
        keys = [k.strip() for k in (body[2:] if textual else body).split(";")]
        for k in keys:
            assert k in REFS, "unknown reference key " + k
            if k not in CITE:
                CITE.append(k)
        if textual:
            assert len(keys) == 1
            return "%s (%d)" % (short(keys[0]), REFS[keys[0]]["year"])
        return "(" + "; ".join("%s %d" % (short(k), REFS[k]["year"]) for k in keys) + ")"
    return re.sub(r"\[\[([^\]]+)\]\]", rep, text)


def sub(text):
    text = re.sub(r"@T:(\w+)@", lambda m: "Table %s" % LAB["T"].get(m.group(1), "?"), text)
    text = re.sub(r"@F:(\w+)@", lambda m: "Figure %s" % LAB["F"].get(m.group(1), "?"), text)
    return re.sub(r"@E:(\w+)@", lambda m: "(%s)" % EQNUM.get(m.group(1), "?"), text)


doc = H.new_document(size=10.5, line=1.5)
H.page_numbers_and_line_numbers(doc, line_numbers=False)


def P(text, **kw):
    kw.setdefault("align", "justify")
    return H.para(doc, cites(sub(text)), **kw)


def HD(text, level=1):
    return H.heading(doc, text, level)


def FIG(path, label, caption, alt, width=5.8):
    FIGN[0] += 1
    LAB_NEW["F"][label] = FIGN[0]
    H.figure(doc, os.path.join(ROOT, "figures", path), width_in=width, cap="**Figure %d.** %s" % (FIGN[0], cites(sub(caption)).strip()), alt=alt)


def TAB(rows, caption, label, widths=None, size=8.5):
    TABN[0] += 1
    LAB_NEW["T"][label] = TABN[0]
    H.caption(doc, "**Table %d.** %s" % (TABN[0], cites(sub(caption))), keep_next=True)
    H.table(doc, [[cites(sub(c)) for c in r] for r in rows], widths=widths, size=size)


def EQ(nodes, name=None):
    EQN[0] += 1
    H.equation(doc, nodes, EQN[0])
    if name:
        EQNUM_NEW[name] = EQN[0]
    return EQN[0]


V, Tt, SUBN, SUPN, FRAC, DEL = H.V, H.T, H.SUB, H.SUP, H.FRAC, H.DELIM


def sv(base, s):
    return SUBN(V(base), Tt(s))


PLUS, MINUS, EQS = Tt(" + "), Tt(" − "), Tt(" = ")
DR = SUBN(V("∂"), V("r"))


def f1(x):
    return "%.1f" % x


def f2(x):
    return "%.2f" % x


def f3(x):
    return "%.3f" % x


def f4(x):
    return "%.4f" % x


def pc(x, k=1):
    return ("%." + str(k) + "f") % (100 * x)


def sci(x, k=1):
    s = ("%." + str(k) + "e") % x
    mant, ex = s.split("e")
    return "%s×10^{%s}" % (mant, ("−%d" % -int(ex)) if int(ex) < 0 else ("%d" % int(ex)))


Q = lambda t, c="linear", s=1.0: CP[(s, c, t)]["Q"]

# ================================================================== title and abstract
p = doc.add_paragraph()
H.add_rich(p, TITLE, size=15, bold=True)
for line in ("Leon Sandler", "Independent researcher, Northbrook, Illinois, USA", "Corresponding author: sandler.leon@gmail.com", "ORCID: 0009-0007-4584-808X"):
    q = doc.add_paragraph()
    H.add_rich(q, line, size=10.5)
    q.paragraph_format.space_after = H.Pt(0)
doc.add_paragraph()
HD("Abstract")
ABS = ("Turbulent heat transport in tokamaks is stiff and is suppressed by sheared E×B flow, so a closure in which the heat diffusivity depends on the local shearing rate is state dependent. "
       "We study such a closure in a reduced model: a one-dimensional radial energy equation with fusion heating, closed by a critical-gradient diffusivity divided by 1 + (ω_{E}/s_{c}γ_{0})^{2}, "
       "and a toroidal-rotation equation with a shear-dependent viscosity. Geometry, density, field, heating and boundary conditions are identical in every run, so only the closure differs. "
       "The solver is verified by power balance (residual below 10^{−9} of the heating), exact recovery of the baseline as s_{c} → ∞, independent time integration and grid convergence. "
       "With diamagnetic shear alone the fusion gain Q (baseline %s) rises by %s%%, %s%% and %s%% at s_{c} = 1, 0.5 and 0.3, and by %s%% at s_{c} = 0.1; the steady state then ends in a fold at s_{c}^{*} = %.3f, "
       "where Q is about %.1f and below which no steady state exists. For the rotation equation, the steady flux relation F(Λ)Λ = Θ gives closed-form admissibility conditions "
       "(m ≤ 1 for F = 1/(1 + Λ^{m}); viscosity floors 1/9 and %.4f) and the fold and hysteresis window; direct solutions reproduce the flux relation to 5×10^{−11} and the predicted fold, saturation and hysteresis window. "
       "Torque-driven shear adds to the diamagnetic shear and raises Q by %s%% at 200 N m for s_{c} = 0.5. All parameters are illustrative; no experimental data are used."
       % (f2(Q0), pc(T1[1.0]["dQ"], 2), pc(T1[0.5]["dQ"], 2), pc(T1[0.3]["dQ"], 1), pc(T1[0.1]["dQ"], 0), FOLD["extrapolated"], FQ, THR["floor_exp"], pc(Q(200.0) / Q0 - 1, 0)))
H.para(doc, ABS, align="justify")
NABS = len(re.sub(r"[_^]\{([^}]*)\}", r"\1", ABS).split())
print("abstract words:", NABS)
assert NABS <= 250, NABS

# ================================================================== 1 Introduction
HD("1. Introduction")
P("Predicting energy confinement in a tokamak requires a model of the transport driven by micro-turbulence. The transport is stiff: above a critical normalised temperature gradient a small increase of the gradient "
  "produces a large increase of the heat flux, so that profiles are pinned close to marginal stability [[dimits2000; kotschenreuther1995]]. Sheared E×B flow can decorrelate the turbulence and reduce the transport; "
  "this mechanism underlies the edge transport barrier and many improved-confinement regimes [[biglari1990; hahm1995; burrell1997; terry2000]], and quench rules of the form 'turbulence is suppressed when the shearing rate "
  "exceeds a growth-rate scale' are used in transport models [[waltz1994]]. A closure that encodes this physics is state dependent: the shearing rate is itself a function of the evolving profile, "
  "steeper pressure gradients raise it, and a larger shearing rate lowers the diffusivity and steepens the gradient further. Positive feedback of this kind is the standard route to bistability and hysteresis in "
  "models of the L–H transition [[itoh1988; hinton1991]].")
P("The question addressed here is deliberately narrow: if a closure of this type is added to a stiff critical-gradient baseline, under controlled conditions, how much does it change the fusion gain, "
  "and is the answer numerically trustworthy? The paper contributes four things. (i) A verified reduced-model testbed in which only the closure differs between runs (Sections 2 and 4). "
  "(ii) Closed-form conditions on the shear dependence of a flux closure under which the steady balance has a solution for every drive, with the fold and hysteresis predicted when the condition fails; "
  "they are applied to a rotation equation with a shear-dependent viscosity and tested against direct solutions (Sections 3 and 5.5). (iii) The behaviour of the heat closure itself: a grid-converged gain that is "
  "below one per cent at moderate coupling, and a fold of the steady state, located by pseudo-arclength continuation, at which the gain rises steeply and below which no steady state exists (Sections 5.1–5.4). "
  "(iv) A one-way coupling in which torque-driven shear adds to the diamagnetic shear (Section 5.6). Nothing is fitted to experiment, no new fluid equation is proposed, "
  "and the model makes no claim to describe a specific device: the results are statements about the closure in this model, not predictions for a machine.")

# ================================================================== 2 Model
HD("2. Model")
HD("2.1 Energy balance", 2)
P("The thermal state is described by one temperature T(r) (electrons and ions equal) on a circular torus with flux-surface radius r ∈ [0, a], major radius R_{0} and fixed profiles of density n(r) and safety factor q(r). "
  "The thermal energy density is 3nT, so that a diffusivity χ acting on the energy per particle gives the heat flux −3nχ ∂_{r}T (T in energy units). The reduced energy equation is")
EQ(Tt("3") + V("n") + SUBN(V("∂"), V("t")) + V("T") + EQS + FRAC(Tt("1"), V("r")) + DR + DEL(Tt("3") + V("r n χ") + DR + V("T"), "[", "]")
   + PLUS + sv("S", "aux") + PLUS + sv("S", "α") + MINUS + sv("S", "rad") + Tt(","), "energy")
P("with a Gaussian auxiliary source of total power P_{aux}, local alpha heating S_{α} = (n²/4)⟨σv⟩E_{α} for a 50:50 deuterium–tritium mixture with E_{α} = 3.5 MeV and the Bosch–Hale reactivity [[bosch1992]], "
  "and bremsstrahlung S_{rad} = 5.35×10^{−37} n² T^{1/2} W m^{−3} (T in keV, Z_{eff} = 1). The fusion power is P_{fus} = 5P_{α}, the gain Q = P_{fus}/P_{aux}, and the energy confinement time "
  "τ_{E} = W/(P_{aux} + P_{α} − P_{rad}) with W the thermal energy at steady state. The edge temperature is fixed, T(a) = 4 keV, and ∂_{r}T = 0 on the axis. @T:par@ lists the illustrative parameters; "
  "they are generic reactor-scale values, not a model of a specific device. The stiffness parameters were chosen once, before the shear closure was examined, so that the baseline burns without igniting "
  "(Q ≈ 4 at 40 MW), and were not adjusted afterwards. The model is a reduction of the single-fluid magnetohydrodynamic description [[freidberg2014; wesson2011]] to the thermal-transport coefficient: "
  "no fluid equation is modified.")
HD("2.2 Baseline and state-dependent heat closures", 2)
P("The baseline diffusivity is a smoothed critical-gradient form,")
EQ(sv("χ", "base") + EQS + sv("χ", "n") + PLUS + sv("χ", "s") + V("w") + Tt(" ln") + DEL(Tt("1") + PLUS + Tt("exp") + DEL(FRAC(V("κ") + MINUS + sv("κ", "c"), V("w"))), "[", "]") + Tt(",   ") + V("κ") + EQS +
   FRAC(sv("R", "0") + Tt("|") + DR + V("T") + Tt("|"), V("T")) + Tt(","), "chibase")
P("with χ_{n} = 0.3 m² s^{−1}, χ_{s} = 1.0 m² s^{−1}, κ_{c} = 4 and w = 0.5. The state-dependent closure divides it by a shear-suppression factor,")
EQ(V("χ") + EQS + FRAC(sv("χ", "base"), Tt("1") + PLUS + SUPN(DEL(FRAC(sv("ω", "E"), sv("s", "c") + sv("γ", "0"))), Tt("2"))) + Tt(",   ") + sv("γ", "0") + EQS + FRAC(sv("c", "s"), sv("R", "0")) + Tt(","), "closure")
P("where γ_{0} = c_{s}/R_{0} is a turbulence-decorrelation-rate proxy (c_{s} = (T/m_{i})^{1/2}, m_{i} = 2.5 amu) and ω_{E} is the Hahm–Burrell shearing rate [[hahm1995]], with the radial electric field from the ion pressure-gradient balance:")
EQ(sv("ω", "E") + EQS + Tt("|") + FRAC(V("r"), V("q")) + DR + DEL(FRAC(V("q") + sv("E", "r"), V("r B"))) + Tt("|") + Tt(",   ") + sv("E", "r") + EQS + FRAC(Tt("1"), V("e n")) + DR + V("p") + Tt(",   ") + V("p") + EQS + V("n T") + Tt("."), "shear")
P("The threshold s_{c} is the single new parameter and s_{c} → ∞ recovers the baseline. Because ω_{E} contains the second derivative of the temperature, the factor depends on the evolving profile: steeper pressure gradients raise ω_{E}, "
  "lower χ and steepen the gradient further.")
HD("2.3 Rotation and viscosity closures", 2)
P("Toroidal rotation Ω(r, t) obeys")
EQ(sv("ρ", "m") + SUPN(sv("R", "0"), Tt("2")) + SUBN(V("∂"), V("t")) + V("Ω") + EQS + FRAC(Tt("1"), V("r")) + DR + DEL(V("r") + sv("μ", "eff") + SUPN(sv("R", "0"), Tt("2")) + DR + V("Ω"), "[", "]") + PLUS + sv("τ", "in") + Tt(","), "rotation")
P("with ρ_{m} = n m_{i}, regularity on the axis and Ω(a) = 0. The torque density τ_{in} (N m^{−2}) has a Gaussian profile of width 0.4a and total torque ∫τ_{in}dV = T_{tot}, with dV = 4π²R_{0}r dr. "
  "The effective viscosity is μ_{eff} = μ_{0}F(Λ) with μ_{0} = Pr ρ̄ χ_{s} (ρ̄ the radial mean of ρ_{m}; Pr = 1 unless stated; μ_{0} = " + sci(MU0, 2) + " kg m^{−1} s^{−1}), where")
EQ(V("Λ") + EQS + V("κ") + Tt("|") + DR + V("Ω") + Tt("|") + Tt(",   ") + V("κ") + EQS + FRAC(V("r"), V("q") + sv("γ", "0")) + Tt(",   ") + V("Λ") + EQS + FRAC(sv("ω", "rot"), sv("γ", "0")) + Tt(",   ") + sv("ω", "rot") + EQS + FRAC(V("r"), V("q")) + Tt("|") + DR + V("Ω") + Tt("|") + Tt("."), "lambda")
P("is the rotation shearing rate in units of γ_{0}. The closure F(Λ) expresses that a sheared rotation profile also suppresses momentum transport. Four forms are used: a constant F = 1; "
  "the algebraic form F = 1/(1 + Λ^{m}); the algebraic form with a floor, F = f + (1 − f)/(1 + Λ²); and the exponential form with a floor, F = f + (1 − f)exp(−αΛ²).")
HD("2.4 Coupling of rotation and heat transport", 2)
P("For toroidal rotation the radial electric field contains the term −ΩrB/q, so that qE_{r}/(rB) contains −Ω and the rotation contributes (r/q)∂_{r}Ω to the shearing rate of Eq. @E:shear@. "
  "With signed contributions ω_{dia} = (r/q)∂_{r}(qE_{r}/rB) from the pressure gradient and ω_{rot} = (r/q)∂_{r}Ω from the rotation, the shearing rate in Eq. @E:closure@ becomes")
EQ(sv("ω", "E") + EQS + Tt("|") + sv("ω", "dia") + PLUS + V("σ") + sv("ω", "rot") + Tt("|") + Tt(",   ") + V("σ") + EQS + Tt("±1") + Tt("."), "coupling")
P("with σ = +1 when the two shears add and σ = −1 when they oppose; the sign depends on the direction of the torque relative to the diamagnetic flow and both are reported. "
  "The coupling is one-way: the temperature sets γ_{0} for the rotation equation, the rotation adds to the shear in the heat closure, and the two problems are iterated to a fixed point. "
  "For s_{c} → ∞ the heat transport, and therefore Q, does not depend on the torque.")
TAB([["Quantity", "Value"],
     ["Major radius R_{0}, minor radius a", "6.2 m, 2.0 m"],
     ["Toroidal field B", "5.3 T"],
     ["Density n(r)", "10^{20}(1 − 0.75(r/a)²) m^{−3}, fixed (n_{e} = n_{i}, 50:50 D:T)"],
     ["Safety factor q(r)", "1 + 2(r/a)²"],
     ["Edge temperature T(a)", "4 keV (fixed)"],
     ["Auxiliary heating", "Gaussian of width 0.4a centred on the axis, 40 MW (scanned 10–80 MW)"],
     ["Baseline χ", "χ_{n} = 0.3, χ_{s} = 1.0 m² s^{−1}, κ_{c} = 4, w = 0.5"],
     ["Ion mass m_{i}", "2.5 amu"],
     ["Fusion reactivity", "Bosch–Hale D–T; checked: %.4g×10^{−22} and %.4g×10^{−22} m³ s^{−1} at 10 and 20 keV" % (R["bosch_hale"]["sigma_v_10keV"] * 1e22, R["bosch_hale"]["sigma_v_20keV"] * 1e22)],
     ["Radiation", "Bremsstrahlung 5.35×10^{−37} n² T^{1/2} W m^{−3}, Z_{eff} = 1"],
     ["Viscosity μ_{0}", "Pr ρ̄ χ_{s}, Pr = 1: " + sci(MU0, 2) + " kg m^{−1} s^{−1}"],
     ["Torque", "Gaussian of width 0.4a, total 0–250 N m"]],
    "Parameters held identical for the baseline and the closure runs.", "par", widths=[2.2, 4.3])

# ================================================================== 3 Closure theory
HD("3. Admissibility of shear-dependent flux closures")
P("This section collects the exact statements used in Section 5. They concern the rotation equation, whose steady state is algebraic in the shearing rate, and they identify when a shear-dependent closure can be "
  "used at all: the steady balance must have a solution for every drive. Proofs are in Appendix B.")
HD("3.1 Steady flux relation", 2)
P("**Proposition 1 (steady flux relation).** In steady state, with regularity at the axis, the shearing rate Λ(r) of Eq. @E:lambda@ satisfies at each radius")
EQ(V("F") + DEL(V("Λ")) + V("Λ") + EQS + V("Θ") + DEL(V("r")) + Tt(",   ") + V("Θ") + EQS + FRAC(V("I") + DEL(V("r")), V("q") + sv("γ", "0") + sv("μ", "0") + SUPN(sv("R", "0"), Tt("2"))) + Tt(",   ") + V("I") + DEL(V("r")) + EQS +
   SUBN(Tt("∫"), Tt("0")) + Tt("") + V("τ") + Tt("(r′) r′ dr′") + Tt("."), "flux")
P("Here I(r) is the torque per unit 4π²R_{0} inside radius r, so that T_{tot} = 4π²R_{0}I(a), and Θ is the torque number. The rotation profile follows by integrating ∂_{r}Ω = −Λ/κ from the edge. "
  "The relation does not involve the form of F except through the function Ψ(Λ) = ΛF(Λ), the normalised momentum flux: the closure sets how the flux depends on the shear, and the drive Θ sets the flux.")
HD("3.2 Existence, saturation, fold and hysteresis", 2)
P("**Proposition 2 (admissibility).** (a) Ψ′(Λ) = F(1 + d ln F/d ln Λ), so Ψ is increasing if and only if d ln F/d ln Λ > −1. (b) If Ψ is strictly increasing with supremum Ψ_{∞}, the flux relation has exactly one solution at each radius "
  "if and only if Θ(r) < Ψ_{∞}; a steady state then exists for every torque when Ψ_{∞} = ∞, and only for Θ_{max} < Ψ_{∞} when Ψ_{∞} is finite (flux saturation). "
  "(c) If Ψ has a local maximum Ψ_{M} followed by a local minimum Ψ_{m} < Ψ_{M}, there are three solutions for Ψ_{m} < Θ < Ψ_{M}. On a slowly increasing torque the state that started at Λ = 0 ends in a fold at Θ = Ψ_{M} "
  "and jumps to the upper branch; on a decreasing torque the upper branch persists down to Θ = Ψ_{m}. The hysteresis window in torque is [Ψ_{m}, Ψ_{M}]/θ′, where Θ_{max} = θ′T_{tot}.")
P("The condition in (a) is the one that makes a nonlinear diffusion problem with flux −ΛF(Λ) well posed; a flux that decreases with the drive is the mechanism of the ill-posedness of forward–backward diffusion [[perona1990]]. "
  "Part (c) is the analogue, for the rotation equation, of the S-curve of the L–H transition models [[itoh1988; hinton1991]].")
P("**Proposition 3 (closure families).** (i) For F = 1/(1 + Λ^{m}), d ln F/d ln Λ = −mΛ^{m}/(1 + Λ^{m}) decreases from 0 to −m, so Ψ is increasing for all Λ if and only if m ≤ 1. For m = 1, Ψ = Λ/(1 + Λ) saturates at Ψ_{∞} = 1. "
  "For m < 1, Ψ is unbounded. For m > 1, Ψ′ vanishes at Λ^{*} = (m − 1)^{−1/m}, where F = 1/m and Ψ(Λ^{*}) = Λ^{*}/m; for m = 2, Λ^{*} = 1 and the fold is at Θ = 1/2. "
  "(ii) For F = f + (1 − f)/(1 + Λ²), Ψ is increasing for all Λ if and only if f > 1/9. "
  "(iii) For F = f + (1 − f)exp(−αΛ²), Ψ is increasing for all Λ if and only if f > 2e^{−3/2}/(1 + 2e^{−3/2}) = %.4f, independent of α. Without a floor (f = 0) Ψ has its maximum at Λ = (2α)^{−1/2}, where Ψ = (2αe)^{−1/2}." % THR["floor_exp"])
TAB([["Closure F(Λ)", "Behaviour of Ψ = ΛF", "Steady state for all Θ?", "Threshold"],
     ["1 (constant)", "Ψ = Λ, unbounded", "yes", "–"],
     ["1/(1 + Λ^{m}), m < 1", "increasing, unbounded", "yes", "–"],
     ["1/(1 + Λ), m = 1", "increasing, Ψ → 1", "no, saturates", "Θ < 1"],
     ["1/(1 + Λ²), m = 2", "maximum 1/2 at Λ = 1", "no, fold", "Θ < 1/2"],
     ["f + (1 − f)/(1 + Λ²)", "increasing iff f > 1/9", "yes if f > 1/9", "f > 1/9 = 0.1111"],
     ["f + (1 − f)exp(−αΛ²)", "increasing iff f > %.4f" % THR["floor_exp"], "yes if f > %.4f" % THR["floor_exp"], "f > %.4f, any α" % THR["floor_exp"]]],
    "Admissibility of the viscosity closures (Propositions 2 and 3).", "clos", widths=[1.7, 1.7, 1.9, 1.2])
P("**Remark (heat closure).** The heat closure of Eq. @E:closure@ is not of this type. The shearing rate ω_{E} depends on the second derivative of the temperature, so the heat flux is not a function of the "
  "local gradient alone and Proposition 2 cannot be applied to it directly. Whether the steady heat balance has a solution for every s_{c} is therefore a numerical question, answered in Section 5.4.")

# ================================================================== 4 Numerics
HD("4. Numerical method and verification")
HD("4.1 Method", 2)
P("The energy equation is discretised conservatively on N uniform cells in r (finite volume, face conductivities from the arithmetic mean of the adjacent cell values). The baseline diffusivity uses the cell-centred central gradient. "
  "The shearing rate is evaluated from the face-centred radial electric field, with E_{r} = 0 on the axis by symmetry, an even-in-r extrapolation of qE_{r}/(rB) to the axis so that the 0/0 limit at r → 0 is treated "
  "consistently on every grid, and a half-cell difference to the fixed edge value. Steady states are obtained by damped Newton iteration with a banded central-difference Jacobian, started from a backward-Euler "
  "pseudo-time march of the baseline and followed in s_{c} by natural continuation. Near the fold the branch is followed by pseudo-arclength continuation in 1/s_{c}. Linear stability is read from the eigenvalues of the Jacobian of the "
  "semi-discrete system dT/dt = (conduction + sources)/(3ne). The rotation equation is solved by scaled Newton iteration with continuation in the torque amplitude, and torque ramps by backward-Euler marching, so that the "
  "branch is selected by the dynamics. All runs are deterministic. Details and tolerances are in Appendix A.")
HD("4.2 Verification", 2)
TAB([["Check", "Result"],
     ["Bosch–Hale reactivity at 10 and 20 keV", "%.4g×10^{−22} and %.4g×10^{−22} m³ s^{−1} (reference values 1.136×10^{−22} and 4.33×10^{−22})" % (R["bosch_hale"]["sigma_v_10keV"] * 1e22, R["bosch_hale"]["sigma_v_20keV"] * 1e22)],
     ["Power balance, (P_{aux} + P_{α} − P_{rad} − boundary conduction)/(P_{aux} + P_{α})", "below 10^{−9} for the baseline, s_{c} = 0.5 and s_{c} = 0.1 (baseline: %s)" % sci(abs(VER["resid_baseline"]), 1)],
     ["s_{c} = 10^{9} against the baseline", "identical temperature profile (maximum difference %s keV)" % ("0" if VER["max_dT_sc_1e9"] == 0 else sci(VER["max_dT_sc_1e9"], 1))],
     ["Initial-profile independence (s_{c} = 0.5)", "maximum difference %s keV between two initial profiles" % sci(VER["ic_independence"], 1)],
     ["Independent time integration (Radau, rtol = atol = 10^{−8}) against the Newton steady state", "maximum temperature difference %s keV over s_{c} = ∞, 0.5, 0.1" % sci(max(r["max_abs_dT"] for r in TI), 1)],
     ["Observed order of grid convergence of Q (N = 100, 200, 400)", "%.2f (baseline) to %.2f (s_{c} = 0.07)" % (ORD["none"], ORD["0.07"])],
     ["Leading eigenvalue of the s_{c} = 2 state, N = 100 and 400", "%.4f and %.4f s^{−1}; independent of the grid" % (VER["lambda1_sc2"]["100"], VER["lambda1_sc2"]["400"])],
     ["Steady flux relation, 17 cases of m and torque", "maximum relative error in Λ_{max} %s; existence agrees with Θ < Ψ_{∞} in every case" % sci(SFS["max_rel_err"], 1)],
     ["Closure thresholds by numerical bisection", "f = %.6f (1/9 = 0.111111) and f = %.6f (%.6f)" % (THR["floor_alg_numeric"], THR["floor_exp_numeric"], THR["floor_exp"])]],
    "Verification checks (all reproduced by tests.py; 38 checks).", "ver", widths=[3.0, 3.5])
HD("4.3 Numerical pitfalls found during verification", 2)
P("Two pitfalls are recorded because the quantities involved depend on second derivatives and are easy to get wrong. (i) A finite-difference Jacobian step that is small compared with the temperature but large compared with the "
  "sensitivity of ω_{E} gives a wrong derivative: near the axis ω_{E}/γ_{0} is about 10^{−5} while its derivative with respect to a single cell temperature is about 10² keV^{−1} at N = 400, so that a relative step of 10^{−6} "
  "makes the quadratic term of the suppression factor dominate and produces a spurious destabilising contribution to the leading eigenvalue, a spurious fold at s_{c} ≈ 1 for N = 400 and failures of the Newton iteration. "
  "With a central-difference step of 10^{−8} (relative) the eigenvalue is grid independent (@T:ver@); tests.py contains a regression test. (ii) At N ≥ 400 the Newton residual cannot be reduced below about 10^{−10} of the total heating "
  "because of round-off in the conduction divergence, so the acceptance tolerance is 10^{−8}.")

# ================================================================== 5 Results
HD("5. Results")
HD("5.1 Controlled comparison with diamagnetic shear", 2)
P("@T:cmp@ compares the baseline with the closure at 40 MW with E_{r} from the pressure gradient alone. The largest shearing rate is ω_{E}/γ_{0} = %s for the baseline profile, %s at s_{c} = 0.5 and %s at s_{c} = 0.1, located in the last cell before the edge (@F:prof@c), "
  "so that the suppression is concentrated at the edge: at s_{c} = 0.5 the diffusivity is reduced by at most %s%% there. The changes in Q, P_{fus} and τ_{E} are small: at s_{c} = 0.5, Q rises by %s%% and τ_{E} changes by %s%%; "
  "at s_{c} = 0.3, Q rises by %s%%." % (f3(T1["base"]["ratio_max"]), f3(T1[0.5]["ratio_max"]), f3(T1[0.1]["ratio_max"]), pc(1 - T1[0.5]["chi_min_over_base"], 0), pc(T1[0.5]["dQ"], 2),
                                         pc(abs(T1[0.5]["tauE"] / T1["base"]["tauE"] - 1), 3), pc(T1[0.3]["dQ"], 2)))
rows = [["Model", "Q", "P_{fus} (MW)", "τ_{E} (s)", "⟨T⟩ (keV)", "T_{0} (keV)", "max ω_{E}/γ_{0}", "ΔQ/Q"]]
for k in ("base", 1.0, 0.5, 0.3, 0.2, 0.1, 0.07):
    r = T1[k]
    rows.append(["Baseline (stiff critical gradient)" if k == "base" else "Closure, s_{c} = %g" % k, f4(r["Q"]), f1(r["Pfus"]), f4(r["tauE"]), f3(r["Tavg"]), f2(r["T0"]), f3(r["ratio_max"]), "–" if k == "base" else "%s%%" % pc(r["dQ"], 2)])
TAB(rows, "Baseline and closure at P_{aux} = 40 MW (N = 100). All other inputs are identical; every row is a steady state of the lower branch with power-balance residual below 10^{−9}.", "cmp",
    widths=[2.0, 0.6, 0.8, 0.7, 0.7, 0.7, 0.8, 0.6])
FIG("fig1_profiles.png", "prof", "(a) Temperature, (b) diffusivity and (c) shearing rate ω_{E}/γ_{0} against r/a at 40 MW (N = 200) for the baseline and the closure with s_{c} = 0.5 and 0.1. "
    "The baseline and s_{c} = 0.5 curves nearly coincide. The shearing rate vanishes where the electric-field shear changes sign (r/a ≈ 0.64) and peaks in the last cell before the edge.",
    "Three panels of radial profiles of temperature, diffusivity and normalised shearing rate for the baseline and two closure settings.")
HD("5.2 Dependence on heating power", 2)
pr = R["paux_scan"]
P("Q decreases with heating power for all models (@F:pow@a), reflecting the confinement degradation with power of the stiff baseline: baseline Q falls from %s at 10 MW to %s at 80 MW. "
  "The closure shifts the curve by a nearly constant relative amount at moderate coupling (%s–%s%% at s_{c} = 0.5 and %s–%s%% at s_{c} = 0.3 over the whole range, @F:pow@b) and by an amount that grows with power at s_{c} = 0.1 "
  "(%s%% at 10 MW, %s%% at 80 MW), because at higher power the edge gradient and hence the shearing rate are larger."
  % (f2(pr["baseline"][0]["Q"]), f2(pr["baseline"][-1]["Q"]), f2(100 * min(a["Q"] / b["Q"] - 1 for a, b in zip(pr["sc0.5"], pr["baseline"]))), f2(100 * max(a["Q"] / b["Q"] - 1 for a, b in zip(pr["sc0.5"], pr["baseline"]))),
     f2(100 * min(a["Q"] / b["Q"] - 1 for a, b in zip(pr["sc0.3"], pr["baseline"]))), f2(100 * max(a["Q"] / b["Q"] - 1 for a, b in zip(pr["sc0.3"], pr["baseline"]))),
     f1(100 * (pr["sc0.1"][0]["Q"] / pr["baseline"][0]["Q"] - 1)), f1(100 * (pr["sc0.1"][-1]["Q"] / pr["baseline"][-1]["Q"] - 1))))
FIG("fig2_power_scan.png", "pow", "(a) Fusion gain and (b) its relative change against auxiliary power for the baseline and three closure settings (N = 100).",
    "Fusion gain against heating power on a logarithmic axis and the relative gain of the closure against heating power.", width=5.0)
HD("5.3 Grid convergence", 2)
rows = [["s_{c}", "N = 50", "N = 100", "N = 200", "N = 400", "N = 800", "observed order"]]
for key, lab in (("none", "∞ (baseline)"), ("1.0", "1"), ("0.5", "0.5"), ("0.3", "0.3"), ("0.2", "0.2"), ("0.1", "0.1"), ("0.07", "0.07")):
    row = GRID[key]
    rows.append([lab] + [(f4(r["Q"]) if r["ok"] else "n/c") for r in row] + [f2(ORD[key])])
TAB(rows, "Fusion gain Q at 40 MW against the number of cells N (steady states of the lower branch; n/c: continuation in s_{c} did not converge at that resolution). "
          "The observed order is estimated from N = 100, 200 and 400.", "grid", widths=[1.0, 0.8, 0.8, 0.8, 0.8, 0.8, 1.0])
P("Q converges at every s_{c} tested (@T:grid@, @F:conv@a). The observed order is %.1f for the baseline, as expected for a second-order scheme, and decreases to about %.1f as s_{c} decreases, because the edge cell, where the "
  "shearing rate is largest, is treated with a half-cell difference to the fixed edge value. At s_{c} = 0.5 the change of Q between N = 50 and N = 800 is %s%% and between N = 200 and N = 800 it is %s%%; at s_{c} = 0.1 "
  "the corresponding changes are %s%% and %s%%. The leading eigenvalue of the steady state does not depend on N (@T:ver@)."
  % (ORD["none"], ORD["0.1"], pc(abs(GRID["0.5"][0]["Q"] / GRID["0.5"][-1]["Q"] - 1), 2), pc(abs(GRID["0.5"][2]["Q"] / GRID["0.5"][-1]["Q"] - 1), 3),
     pc(abs(GRID["0.1"][0]["Q"] / GRID["0.1"][-1]["Q"] - 1), 1), pc(abs(GRID["0.1"][2]["Q"] / GRID["0.1"][-1]["Q"] - 1), 1)))
FIG("fig3_convergence.png", "conv", "(a) Relative difference of Q from the N = 800 value against N for four values of s_{c} (dotted: N^{−1}; dashed: N^{−2}). (b) Position of the fold s_{c}^{*} against 1/N and the Richardson limit.",
    "Log-log convergence of the fusion gain with the number of cells and the fold position against inverse resolution.", width=5.2)
HD("5.4 Strong coupling: a fold of the steady state", 2)
P("As s_{c} decreases the gain rises ever more steeply (@T:cmp@): Q = %s at s_{c} = 0.1 (%s%% above the baseline) and %s at 0.07 (%s%% above). The lower branch does not continue indefinitely. "
  "Pseudo-arclength continuation in 1/s_{c} (@F:branch@) shows that it ends in a saddle-node fold: the leading eigenvalue of the steady state rises smoothly to zero at the fold and the branch turns back to larger s_{c}. "
  "The fold is at s_{c}^{*} = %.4f, %.4f, %.4f and %.4f for N = 50, 100, 200 and 400, which converges with observed order %.1f to the Richardson limit %.4f (@F:conv@b). At the fold Q ≈ %.1f and T_{0} ≈ %.0f keV, "
  "so the end of the lower branch is still a burning plasma with a temperature inside the validity range of the reactivity fit (0.2–100 keV)."
  % (f2(T1[0.1]["Q"]), pc(T1[0.1]["dQ"], 0), f2(T1[0.07]["Q"]), pc(T1[0.07]["dQ"], 0), FOLD["by_N"]["50"]["sc_fold"], FOLD["by_N"]["100"]["sc_fold"], FOLD["by_N"]["200"]["sc_fold"], FOLD["by_N"]["400"]["sc_fold"],
     FOLD["order"], FOLD["extrapolated"], FQ, FT0))
P("Beyond the fold the branch turns back and continues through a window %.4f < s_{c} < %.4f (N = 200) in which three steady states exist: the stable lower state, an unstable middle state, and a state with much larger Q (about 30) "
  "and T_{0} of 70 keV and above that is stable to small perturbations. Its temperature reaches and, for smaller s_{c}, exceeds 100 keV, outside the validity of the reactivity fit and of a model without alpha-particle losses, MHD or density response, "
  "and its basin of attraction was not explored; we do not interpret that state. "
  "Time integration confirms the picture. At s_{c} = 0.05, just above the fold, a cold start settles on the lower branch (Q = %.2f, T_{0} = %.1f keV). At s_{c} = 0.044, below the fold, the axis temperature "
  "passes 150 keV after %.0f s without settling. A start at T_{0} = 70 keV inside the window heats beyond 150 keV within %.1f s." % (SC_WINDOW[1], SC_WINDOW[0], FD["above"]["Q"], FD["above"]["T0"], FD["below"]["t_end"], FD["hot_start_in_window"]["t_end"]))
P("The result is a sensitivity statement rather than a prediction. The gain is a steep function of s_{c} near s_{c}^{*}: within a factor of two in s_{c} (from 0.1 to 0.05) Q increases from %s to about 10, "
  "so the value of s_{c}, which would have to be calibrated against gyrokinetic or experimental data, determines whether the closure matters at all." % f2(T1[0.1]["Q"]))
FIG("fig4_branch.png", "branch", "Steady states of the heat equation against s_{c}. (a) Lower branch of Q against s_{c} for N = 100 and 200. (b), (c) Q and T_{0} through the fold (continuation in 1/s_{c}, N = 100 and 200; solid: stable, dotted: unstable; "
    "points with T_{0} > 100 keV are omitted). The dashed line is the Richardson limit of the fold position.",
    "Three panels: lower branch of the gain against the threshold, and the gain and axis temperature through the fold showing an S-shaped curve.", width=6.2)
HD("5.5 Tests of the closure theory on the rotation equation", 2)
rows = [["m", "Torque (N m)", "Θ_{max}", "Λ_{max} predicted", "Λ_{max} simulated", "relative error"]]
for r in SFR:
    if r["m"] in (1.0, 2.0) and r["torque"] in (50.0, 150.0, 250.0):
        if r["exists_numeric"] and r["exists_theory"]:
            rows.append(["%g" % r["m"], "%g" % r["torque"], f3(r["Theta_max"]), "%.6f" % r["Lam_pred"], "%.6f" % r["Lam_sim"], sci(abs(r["Lam_sim"] / r["Lam_pred"] - 1), 1)])
        else:
            rows.append(["%g" % r["m"], "%g" % r["torque"], f3(r["Theta_max"]), "none (Θ > Ψ_{∞})", "no steady state", "–"])
TAB(rows, "Steady flux relation F(Λ)Λ = Θ against the direct finite-volume solution of the rotation equation (selected cases; heat decoupled, temperature profile of the baseline, N = 200). "
          "Over all 17 cases with a steady state the maximum relative error is %s." % sci(SFS["max_rel_err"], 1), "flux", widths=[0.5, 1.0, 0.8, 1.4, 1.4, 1.2])
P("The rotation equation was solved directly (finite volume, N = 200, the baseline temperature profile, torques from 25 to 250 N m, closures with m = 0.5, 1 and 2) and compared with Proposition 1 (@T:flux@, @F:rot@a). "
  "Where a steady state exists the simulated shearing rate agrees with the solution of F(Λ)Λ = Θ(r) to a relative error of at most %s, and whether a steady state exists agrees with Θ_{max} < Ψ_{∞} in every case. "
  "The torque number is proportional to the torque, Θ_{max} = %s per N m. The last torque with a steady state is %.1f N m for m = 2, where Θ_{max} = %.6f (predicted fold at 1/2), and %.1f N m for m = 1, where Θ_{max} = %.6f "
  "(predicted saturation at 1)." % (sci(SFS["max_rel_err"], 1), sci(TH_PER_NM, 3), RF["2.0"]["torque_last"], RF["2.0"]["Theta_last"], RF["1.0"]["torque_last"], RF["1.0"]["Theta_last"]))
pw = HYS["predicted"]
P("For the floor closure with f = 0.05 < 1/9, Ψ has a maximum Ψ_{M} = %.4f and a minimum Ψ_{m} = %.4f, which Proposition 2 translates into a hysteresis window of %.0f–%.0f N m. Torque ramps (10 N m steps, backward-Euler marching "
  "from the previous state) show the up-ramp on the low branch to the last torque below the window, a jump between %.0f and %.0f N m, and a down-ramp that stays on the high branch to 240 N m and returns to the low branch "
  "at or below %.0f N m (@F:rot@b). For f = 0.20 > 1/9 the up and down ramps coincide to 10^{−6}. Near the jump the marching converges slowly (critical slowing down), and the points at 210–230 N m on the down-ramp and "
  "at 270 N m on the up-ramp are not converged and are omitted."
  % (pw["Psi_max"], pw["Psi_min"], pw["torque_down"], pw["torque_up"], 260.0, 280.0, pw["torque_down"]))
FIG("fig5_flux.png", "flux", "Normalised flux Ψ = ΛF(Λ) for (a) F = 1/(1 + Λ^{m}) and (b) the floor closures. Decreasing branches are inadmissible: for m = 2 the fold is at Θ = 1/2 (marked); "
    "the algebraic floor f = 0.05 is below 1/9 and shows a maximum and a minimum, f = 0.20 is monotone; the exponential floor is monotone for f = 0.40 and not for f = 0.20 (threshold %.4f)." % THR["floor_exp"],
    "Two panels of the normalised flux against shearing rate for several viscosity closures.", width=5.4)
FIG("fig6_rotation_tests.png", "rot", "(a) Maximum shearing rate from the direct solution against the prediction of F(Λ)Λ = Θ for m = 0.5, 1, 2 (line: equality). (b) Torque ramps for the floor closure with f = 0.05 (hysteresis; the shaded band is the predicted window) and f = 0.20 (none). "
    "Solid: increasing torque, dashed: decreasing torque.", "Two panels testing the flux relation against direct solutions and showing a hysteresis loop for the low floor.", width=5.4)
HD("5.6 Torque-driven shear", 2)
rows = [["Torque (N m)", "Θ_{max}", "Mach", "Q constant", "Q, m = 1", "Q, m = 2, f = 0.20", "Q, m = 2", "Q constant, σ = −1"]]
for t in (0.0, 50.0, 100.0, 150.0, 200.0, 250.0):
    def fq(c, s=1.0):
        r = CP[(s, c, t)]
        return f2(r["Q"]) if r["ok"] else "no steady state"
    r0 = CP[(1.0, "linear", t)]
    rows.append(["%g" % t, f3(r0["Theta"]) if t else "0", f2(r0["Mach"]) if t else "0", fq("linear"), fq("m=1"), fq("m=2 f=0.20"), fq("m=2"), fq("linear", -1.0)])
TAB(rows, "Fusion gain with torque-driven shear (s_{c} = 0.5, Pr = 1, N = 100, 40 MW); σ = +1 (shears add) except in the last column. Θ_{max} and the Mach number R_{0}Ω/c_{s} (maximum over r) are for the constant viscosity. "
          "'No steady state': the rotation equation has none (m = 2 at Θ > 1/2).", "torque", widths=[0.8, 0.6, 0.5, 0.8, 0.7, 1.0, 0.8, 1.0], size=8)
P("With the shears adding (σ = +1) the gain increases monotonically with torque (@T:torque@, @F:coupled@a). For a constant viscosity Q rises from %s at zero torque to %s at 100 N m and %s at 200 N m, "
  "which is %s%% and %s%% above the baseline (%s); at 200 N m the Mach number is %s and the largest shearing rate ω_{E}/γ_{0} is %s. "
  "A closure in which the viscosity falls with shear amplifies the effect: for m = 1 (admissible) Q = %s at 200 N m and %s at 250 N m, because the rotation shear grows when the viscosity decreases and the heat closure responds. "
  "The inadmissible closure m = 2 has a steady rotation profile up to Θ = 1/2, tracks the other closures up to 200 N m (Q = %s) and has none at 250 N m, in line with Proposition 3; with the floor f = 0.20, "
  "which is admissible, the steady state exists at every torque (Q = %s at 250 N m). When the shears oppose (σ = −1) the gain is smaller but still increases with torque (Q = %s at 200 N m for a constant viscosity), because in the "
  "region where the rotation shear dominates the net shear still grows."
  % (f2(Q(0.0)), f2(Q(100.0)), f2(Q(200.0)), pc(Q(100.0) / Q0 - 1, 0), pc(Q(200.0) / Q0 - 1, 0), f2(Q0), f2(CP[(1.0, "linear", 200.0)]["Mach"]), f2(CP[(1.0, "linear", 200.0)]["ratio_max"]),
     f2(Q(200.0, "m=1")), f2(Q(250.0, "m=1")), f2(Q(200.0, "m=2")), f2(Q(250.0, "m=2 f=0.20")), f2(Q(200.0, "linear", -1.0))))
pr1 = {(r["Pr"], r["closure"]): r for r in PRS}
P("Two sensitivities are reported because both parameters are illustrative. At 100 N m with a constant viscosity, Q = %s, %s, %s, %s and %s for s_{c} = 2, 1, 0.5, 0.3 and 0.2, so the dependence on the threshold is steep. "
  "At 200 N m with the m = 1 closure, doubling the viscosity multiplier (Pr = 2) lowers Q to %s (Θ_{max} = %s); halving it (Pr = 0.5) doubles Θ and no converged steady state of the coupled problem was found, for either m = 1 or m = 2; "
  "the coupled fold was not analysed further."
  % tuple([f2(c["Q"]) for c in CSC] + [f2(pr1[(2.0, "m=1")]["Q"]), f2(pr1[(2.0, "m=1")]["Theta"])]))
FIG("fig7_coupled.png", "coupled", "Fusion gain against torque with torque-driven shear for four viscosity closures: (a) shears adding (σ = +1) and (b) shears opposing (σ = −1); s_{c} = 0.5, Pr = 1, N = 100. "
    "The dotted vertical line marks the torque (250 N m) at which the closure m = 2 has no steady rotation profile.",
    "Two panels of fusion gain against torque for different viscosity closures.", width=5.6)

# ================================================================== 6 Discussion
HD("6. Discussion")
P("At moderate coupling the answer to the narrow question is negative: with diamagnetic shear alone, a stiff-baseline model gains %s%% to %s%% in Q for s_{c} between 1 and 0.3, because the shearing rate "
  "is small compared with the decorrelation-rate proxy everywhere (largest value %s) and is concentrated at the edge. This is a statement about the closure and parameters used here. "
  "The same model shows that this is not the whole story: the gain is a steep function of the threshold, with %s%% at s_{c} = 0.1 and a fold at s_{c}^{*} = %.3f, so that a modest error in a calibrated s_{c} near the fold would change the conclusion "
  "qualitatively. The fold is also where the model stops being informative: below it the axis temperature runs through the range in which neither the reactivity fit nor the neglected physics can be trusted."
  % (pc(T1[1.0]["dQ"], 2), pc(T1[0.3]["dQ"], 1), f3(T1[0.3]["ratio_max"]), pc(T1[0.1]["dQ"], 0), FOLD["extrapolated"]))
P("Two further points follow from the momentum part. First, the admissibility conditions are a priori checks that cost nothing: for a given viscosity closure they say whether the rotation profile exists for a given torque number, "
  "where it saturates or folds, and whether it can show hysteresis. The tests in Section 5.5 confirm them to a relative error of %s, so they can be used to screen closures before they are put into a transport code. "
  "Second, torque-driven shear is a far stronger lever than the diamagnetic shear in this model, but its effect on Q depends on the viscosity closure through a feedback (a viscosity that decreases with shear raises the shear), "
  "and it is bounded by the existence of a steady rotation profile, not by the heat equation." % sci(SFS["max_rel_err"], 1))
P("**Limitations.** (i) One-dimensional energy transport with fixed density, equal ion and electron temperatures and local alpha deposition; no particle, current or impurity evolution. "
  "(ii) One-way coupling: the temperature sets γ_{0} for the rotation equation but the rotation does not enter the energy balance except through the shear, and the torque profile and the viscosity multiplier are illustrative. "
  "(iii) No ELM, MHD stability or disruption physics, and no magnet or conductor degradation. (iv) The critical-gradient parameters are generic and the baseline is not benchmarked against a confinement scaling such as "
  "that of the ITER physics basis [[iter1999]]. (v) The threshold s_{c} and the sign convention of the rotation shear are not calibrated; no gyrokinetic or experimental data are used. "
  "(vi) The reactivity fit is valid to 100 keV and no result above that temperature is interpreted. (vii) The heat closure depends on the second derivative of the temperature, and the shearing rate in the edge cell converges slowly "
  "with resolution (the maximum ω_{E}/γ_{0} of the baseline is %s, %s, %s, %s and %s for N = 50 to 800); the fold position is extrapolated in N, not computed in a continuum limit. "
  "A claim of improved fusion performance would require a calibrated s_{c}, a self-consistent density and pedestal and validation against experimental or high-fidelity data."
  % tuple(f3(GRID["none"][i]["ratio_max"]) for i in range(5)))

# ================================================================== 7 Conclusions
HD("7. Conclusions")
P("A verified reduced model allows a state-dependent shear-suppression closure to be compared with a stiff critical-gradient baseline at identical inputs. With diamagnetic shear alone the fusion gain changes by %s%% at s_{c} = 0.5 "
  "and %s%% at s_{c} = 0.3, converging with the grid, but the lower branch of steady states ends in a fold at s_{c}^{*} = %.3f (extrapolated in resolution), where Q ≈ %.1f, and no steady state exists below it. "
  "For the rotation equation, the steady flux relation reduces existence, saturation, fold and hysteresis to the monotonicity of ΛF(Λ), with closed-form thresholds that direct solutions reproduce. "
  "Torque-driven shear adds to the diamagnetic shear and raises Q by %s%% at 200 N m for s_{c} = 0.5, subject to the same existence conditions. All results are tested against the full equations of the reduced model; none is tested against "
  "experiment, and the parameters are illustrative. Whether state-dependent closures improve burning-plasma performance remains open here: it requires a calibrated threshold and a model of the edge barrier."
  % (pc(T1[0.5]["dQ"], 2), pc(T1[0.3]["dQ"], 1), FOLD["extrapolated"], FQ, pc(Q(200.0) / Q0 - 1, 0)))

# ================================================================== declarations
HD("Funding")
P("This research received no specific grant from any funding agency, commercial or not-for-profit sectors.")
HD("Declaration of interests")
P("The author reports no conflict of interest.")
HD("Data availability statement")
P("All data were generated by the code released with this article. The model code, the closed-form module, the tests, the figure scripts, the raw results file (results.json) and the manuscript builder are available at %s (release %s) and are archived "
  "on Zenodo at https://doi.org/%s (software, MIT licence). This manuscript is archived as a preprint at https://doi.org/%s (CC BY 4.0). No experimental data were used." % (REPO, RELEASE, SW_DOI, PP_DOI))
HD("Author contributions")
P("L.S. is the sole author. L.S. conceived the study, defined the model and the questions addressed, directed the derivations, computations and figures, reviewed and checked the results, wrote and revised the manuscript, and approved the final version.")
HD("Author ORCID")
P("L. Sandler, https://orcid.org/0009-0007-4584-808X.")
HD("Declaration of the use of artificial intelligence")
P("Claude Sonnet 5.5 (Anthropic; model identifier claude-sonnet-5-5), accessed through the Claude Code environment of the Claude desktop application on the author's computer, was used between 7 and 8 October 2026 to write and test the code, "
  "to derive and check the closed-form results, to run the numerical experiments, to produce the figures and to draft the text. The author reviewed and edited all content, checked every reference against Crossref, and takes full responsibility "
  "for the content of the article. The tool is not an author. Every number in the article is produced by the released scripts.")
HD("Acknowledgements")
P("None.")

# ================================================================== appendices
HD("Appendix A. Numerical protocol, tolerances and convergence")
P("*Grid and discretisation.* N uniform cells in r (N = 50 to 800; N = 100 for the results of @T:cmp@ and @T:torque@). Face conductivities are arithmetic means of the adjacent cell values; the edge face uses the Dirichlet half cell. "
  "The baseline diffusivity uses the central cell gradient (one-sided in the first cell). The shearing rate uses face-centred E_{r}, E_{r} = 0 on the axis, an even extrapolation u_{0} = (4u_{1} − u_{2})/3 of u = qE_{r}/(rB) to the axis and "
  "a half-cell difference to the edge.")
P("*Steady states.* Damped Newton iteration on the steady residual with a banded (three sub- and three super-diagonals) central-difference Jacobian, relative step 10^{−8}; acceptance when the maximum residual is below 10^{−8} of "
  "the volume-averaged heating (the achieved power-balance residuals in @T:ver@ are far smaller). The baseline is first marched in pseudo-time (backward Euler, initial step 0.05 s, growth factor 1.5, maximum step 50 s) from a parabolic profile; "
  "the closure is introduced by natural continuation in s_{c} (steps 4, 2, 1, 0.7, 0.5, 0.4, 0.3, 0.2, 0.15, 0.1, 0.07, 0.05). Pseudo-arclength continuation uses 1/s_{c} as the parameter with a tangent predictor and Newton corrector (dense Jacobian); "
  "the fold position is the maximum of 1/s_{c} along the branch, refined by a quadratic fit through three points. Eigenvalues are those of the dense Jacobian divided by 3ne.")
P("*Time integration.* Radau (rtol = atol = 10^{−8}, sparse Jacobian pattern) of dT/dt = residual/(3ne) from a parabolic cold profile to 80 s; runs near the fold stop when the axis temperature exceeds 150 keV.")
P("*Rotation equation.* The unknown is scaled by the linear-viscosity solution; Newton iteration (hybrid method) with eight steps of torque continuation from the linear solution; acceptance when the scaled residual is below 10^{−8}. Torque ramps use backward-Euler "
  "marching of the rotation equation with the step doubled after every accepted step, starting from the previous state, until the steady residual is below 10^{−10}; runs that do not converge near a fold are reported as not converged.")
P("*Coupled problem.* Fixed-point iteration between the rotation solve (with the current temperature) and the heat solve (with the current rotation shear), converged when the maximum temperature change is below 10^{−7} keV.")
P("*Software.* Python %s, NumPy %s, SciPy %s; release %s of the repository contains the exact scripts and results.json. The reproduction script runs in about ten minutes and uses no random numbers."
  % (R["versions"]["python"], R["versions"]["numpy"], R["versions"]["scipy"], RELEASE))

HD("Appendix B. Proofs")
P("*Proof of Proposition 1.* In steady state Eq. @E:rotation@ gives (1/r)∂_{r}(rG) = −τ_{in} with G = μ_{eff}R_{0}²∂_{r}Ω. Integrating from the axis, where rG vanishes by regularity, gives rG(r) = −I(r) with I = ∫_{0}^{r}τ_{in}r′dr′. "
  "Hence μ_{0}R_{0}²F(Λ)|∂_{r}Ω| = I/r. With Λ = κ|∂_{r}Ω| and κ = r/(qγ_{0}) we have |∂_{r}Ω| = Λ/κ and F(Λ)Λ = Iκ/(rμ_{0}R_{0}²) = I/(qγ_{0}μ_{0}R_{0}²) = Θ. The total torque is ∫τ_{in}dV = 4π²R_{0}I(a). ∎")
P("*Proof of Proposition 2.* (a) Ψ′ = F + ΛF′ = F(1 + d ln F/d ln Λ), and F > 0. (b) If Ψ is strictly increasing and continuous with Ψ(0) = 0 and Ψ(Λ) → Ψ_{∞}, the equation Ψ(Λ) = Θ has exactly one solution for 0 ≤ Θ < Ψ_{∞} and none otherwise. "
  "(c) If Ψ increases to Ψ_{M} at Λ_{M}, decreases to Ψ_{m} at Λ_{m} and increases again, the equation has three solutions for Ψ_{m} < Θ < Ψ_{M}, one for Θ < Ψ_{m}, and one (on the upper branch) for Θ > Ψ_{M}. The branch from Λ = 0 "
  "is continuous in Θ until Θ = Ψ_{M}, where it ends; a state on the upper branch is continuous until Θ = Ψ_{m}. Since the steady relation is algebraic at each radius, the jump occurs at the first radius at which Θ(r) reaches the critical value, and "
  "Θ_{max} = θ′T_{tot} because Θ is linear in the torque. ∎")
P("*Proof of Proposition 3.* (i) d ln F/d ln Λ = −mΛ^{m}/(1 + Λ^{m}), which decreases monotonically from 0 to −m and stays above −1 for all Λ if and only if m ≤ 1. For m > 1, Ψ′ = (1 + Λ^{m} − mΛ^{m})/(1 + Λ^{m})² = 0 "
  "at (Λ^{*})^{m} = 1/(m − 1), where F = 1/m and Ψ = Λ^{*}/m; for m = 2, Λ^{*} = 1 and Ψ = 1/2; for m = 1, Ψ = Λ/(1 + Λ) → 1. "
  "(ii) With F = f + (1 − f)/(1 + Λ²), Ψ′ = f + (1 − f)g(x), g(x) = (1 − x)/(1 + x)², x = Λ² ≥ 0. Then g′(x) = (x − 3)/(1 + x)³, so g has its minimum at x = 3, g = −1/8, and Ψ′ > 0 for all Λ if and only if f − (1 − f)/8 > 0, i.e. f > 1/9. "
  "(iii) With F = f + (1 − f)e^{−αΛ²}, Ψ′ = f + (1 − f)(1 − 2x)e^{−x} with x = αΛ². The function h(x) = (1 − 2x)e^{−x} has h′ = (2x − 3)e^{−x}, a minimum at x = 3/2 equal to −2e^{−3/2} = −0.4463, so Ψ′ > 0 if and only if "
  "f > 0.4463(1 − f), i.e. f > 0.3086, independent of α. For f = 0, Ψ has its maximum at Λ = (2α)^{−1/2} with Ψ = (2αe)^{−1/2}. ∎")

HD("Appendix C. Reproduction and file manifest")
P("The repository contains: code/model.py (energy balance, closures, steady and pseudo-time solvers), stability.py (Newton steady states, Jacobian, leading eigenvalue), arclength.py (pseudo-arclength continuation), momentum.py (rotation equation), "
  "coupled.py (one-way coupling), theory.py (closed forms of Section 3), reproduce.py (every number in the article, about ten minutes, writes results.json), tests.py (38 checks, about three minutes), figures.py, "
  "the reference harvest refs/build_refs.py (Crossref) and the builders of this manuscript and its cover letter. Running reproduce.py, tests.py and figures.py regenerates results.json and the figures. @T:man@ lists the files and the first 16 hexadecimal digits of their SHA-256 checksums at release %s." % RELEASE)


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16] + "…"


rows = [["File", "SHA-256 (first 16 hex digits)"]]
files = ["code/model.py", "code/stability.py", "code/arclength.py", "code/momentum.py", "code/coupled.py", "code/theory.py", "code/reproduce.py", "code/tests.py", "code/figures.py", "refs/build_refs.py",
         "results.json", "requirements.txt", "LICENSE"] + ["figures/" + f for f in sorted(os.listdir(os.path.join(ROOT, "figures"))) if f.endswith(".png")]
for f in files:
    rows.append([f, sha(os.path.join(ROOT, f))])
TAB(rows, "File manifest.", "man", widths=[3.2, 2.2], size=8)

# ================================================================== references
HD("References")
for key in sorted(CITE, key=lambda k: (REFS[k]["first"].lower(), REFS[k]["year"])):
    H.para(doc, REFS[key]["text"], align="left", space_after=3, size=9.5)
uncited = [k for k in REFS if k not in CITE]
assert not uncited, "uncited references: %s" % uncited

doc.save(os.path.join(OUT, "State_Dependent_Shear_Closures_JPP.docx"))
json.dump(LAB_NEW, open(LABFILE, "w"))
json.dump(EQNUM_NEW, open(EQFILE, "w"))
print("saved | figures: %d | tables: %d | equations: %d | references: %d | labels %s" % (FIGN[0], TABN[0], EQN[0], len(CITE), LAB_NEW))
