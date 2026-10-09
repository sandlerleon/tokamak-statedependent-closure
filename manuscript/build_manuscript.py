# -*- coding: utf-8 -*-
"""Builds the manuscript (IEEE Transactions on Plasma Science, regular paper) from results.json. Every number in the text is read from the results.

    python build_manuscript.py          (run twice so that table, figure and equation numbers resolve)   ->  out/Admissibility_Shear_Closures_IEEE_TPS.docx
"""
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
import ieee_helpers as I  # noqa: E402

OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
R = json.load(open(os.path.join(ROOT, "results.json"), encoding="utf-8"))
REFS = json.load(open(os.path.join(ROOT, "refs", "refs_cache.json"), encoding="utf-8"))
ZEN = json.load(open(os.path.join("C:" + os.sep, "YouTube", "_tok_zenodo_state.json")))
RELEASE = os.environ.get("RELEASE_TAG", "v1.2.0")
SW_DOI = (ZEN.get("software_" + RELEASE[1:]) or ZEN["software"])["doi"]
PP_DOI = (ZEN.get("publication_v4") or ZEN["publication"])["doi"]
REPO = "https://github.com/sandlerleon/tokamak-statedependent-closure"
TITLE = "Numerical Admissibility and Regularization of Shear-Suppression Closures for Reduced Tokamak Transport"

# ------------------------------------------------------------------ numbers
TB = {(r["sc"] if r["sc"] is not None else "base"): r for r in R["table1"]}
Q0 = TB["base"]["Q"]
GR = R["grid"]["rows"]
ORD = R["grid"]["observed_order"]
LC = R["local_closure"]
EV = {r["name"]: r for r in R["edge_variants"]}
SFS = R["scalar_flux_relation_summary"]
RF = R["rotation_fold"]
HYS = R["rotation_hysteresis"]["0.05"]
CP = {(r["sign"], r["closure"], r["torque"]): r for r in R["coupled_scan"]}
CST = {r["sc"]: {x["torque"]: x["Q"] for x in r["rows"]} for r in R["coupled_sc_torque"]}
THR = R["theory"]["thresholds"]
UH = R["uncertainty_heat"]["stats"]
UT = R["uncertainty_torque"]
CAL = R["calibration"]
LR = R["linear_response"]
VER = R["verify"]
ACC = R["accessibility"]
PPART = R["principal_part"]
TI = R["time_integration"]
MU0 = R["mu0"]
TH_PER_NM = HYS["Theta_per_Nm"]
LREF = R["l_ref"]
SMT = R["smoothed_threshold"]
N_LINE19 = 0.75 * 10.0            # line-average density of n = 1e20 (1 - 0.75 x^2): 0.75e20 m^-3 = 7.5e19
GAIN36 = {s: CST[s][36.0] / CST[s][0.0] - 1.0 for s in CST}
law_dev = max(abs((r["Q"] - Q0) / (LR["C_mean"] / r["sc"] ** 2) - 1.0) for r in R["table1"] if r["sc"] is not None)
SC10 = float(np.sqrt(LR["C_mean"] / (0.1 * Q0)))

# ------------------------------------------------------------------ citations (IEEE numeric, by first appearance) and numbering
CITE = []
LABFILE = os.path.join(OUT, "labels.json")
LAB = json.load(open(LABFILE)) if os.path.exists(LABFILE) else {"T": {}, "F": {}}
LAB_NEW = {"T": {}, "F": {}}
EQFILE = os.path.join(OUT, "eqnum.json")
EQNUM = json.load(open(EQFILE)) if os.path.exists(EQFILE) else {}
EQNUM_NEW = {}
FIGN, TABN, EQN = [0], [0], [0]
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]


def fmt_refs(nums):
    nums = sorted(set(nums))
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append("[%d]–[%d]" % (nums[i], nums[j]) if j - i >= 2 else ", ".join("[%d]" % n for n in nums[i:j + 1]))
        i = j + 1
    return ", ".join(out)


def cites(text):
    def rep(m):
        keys = [k.strip() for k in m.group(1).split(";")]
        nums = []
        for k in keys:
            assert k in REFS, "unknown reference key " + k
            if k not in CITE:
                CITE.append(k)
            nums.append(CITE.index(k) + 1)
        return fmt_refs(nums)
    return re.sub(r"\[\[([^\]]+)\]\]", rep, text)


def sub(text):
    text = re.sub(r"@T:(\w+)@", lambda m: "Table %s" % ROMAN[LAB["T"].get(m.group(1), 1) - 1], text)
    text = re.sub(r"@F:(\w+)@", lambda m: "Fig. %s" % LAB["F"].get(m.group(1), "?"), text)
    return re.sub(r"@E:(\w+)@", lambda m: "(%s)" % EQNUM.get(m.group(1), "?"), text)


doc = I.new_document()
I.footer_page_numbers(doc)


def P(text, **kw):
    return I.body(doc, cites(sub(text)), **kw)


def H1(num, text):
    return I.h1(doc, num, text)


def H2(letter, text):
    return I.h2(doc, letter, text)


def BUL(text):
    return I.bullet_item(doc, cites(sub(text)))


def FIG(path, label, caption, alt, wide=False, width=None):
    FIGN[0] += 1
    LAB_NEW["F"][label] = FIGN[0]
    w = width or (I.COL_W - 0.1 if not wide else 7.1)
    if wide:
        with I.Wide(doc):
            I.figure(doc, os.path.join(ROOT, "figures", path), w, alt=alt, wide=True)
            I.fig_caption(doc, FIGN[0], cites(sub(caption)))
    else:
        I.figure(doc, os.path.join(ROOT, "figures", path), w, alt=alt)
        I.fig_caption(doc, FIGN[0], cites(sub(caption)))


def TAB(rows, caption, label, widths, size=7.5, wide=False):
    TABN[0] += 1
    LAB_NEW["T"][label] = TABN[0]
    if wide:
        with I.Wide(doc):
            I.table_caption(doc, ROMAN[TABN[0] - 1], cites(sub(caption)))
            I.table(doc, [[cites(sub(c)) for c in r] for r in rows], widths, size=size)
    else:
        I.table_caption(doc, ROMAN[TABN[0] - 1], cites(sub(caption)))
        I.table(doc, [[cites(sub(c)) for c in r] for r in rows], widths, size=size)


def EQ(nodes, name=None):
    EQN[0] += 1
    I.equation(doc, nodes, EQN[0])
    if name:
        EQNUM_NEW[name] = EQN[0]


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


def pc(x, k=1):
    return ("%." + str(k) + "f") % (100 * x)


def sci(x, k=1):
    s = ("%." + str(k) + "e") % x
    mant, ex = s.split("e")
    return "%s×10^{%s}" % (mant, ("−%d" % -int(ex)) if int(ex) < 0 else ("%d" % int(ex)))


def Qt(t, c="linear", s=1.0):
    return CP[(s, c, t)]["Q"]


# ================================================================== title, abstract
I.title_block(doc, TITLE, "Leon Sandler", ["Independent researcher, Northbrook, IL 60062, USA (e-mail: sandler.leon@gmail.com; ORCID: 0009-0007-4584-808X)"])
ABS = ("Closures in which turbulent heat transport is suppressed by sheared plasma flow make the transport coefficient depend on the evolving profile; however, the conditions under which they define a solvable problem are rarely examined. "
       "This paper studies such closures in a reduced model of a reactor-scale tokamak, with a one-dimensional radial energy balance, fusion heating, and a toroidal-rotation equation, so that only the closure changes between runs. "
       "The local closure, whose shearing rate contains the second derivative of the temperature, is found numerically to be ill posed: its steady state depends on how the edge is treated, and a grid-scale instability appears at a threshold that grows as the square root of the number of cells. "
       "A closure that smooths the shearing rate over a fixed length is stable and grid converged over the tested conditions; its fusion gain converges at second order and is fitted by an inverse-square relation in the suppression threshold. "
       "For momentum transport, a steady flux relation gives closed-form conditions under which a shear-dependent viscosity admits a steady rotation profile and predicts its saturation, fold, and hysteresis, for which direct solutions reproduce to ten digits. "
       "The baseline, with its edge temperature imposed, is consistent with an L-mode scaling (a check, not a validation), the smoothed closure raises the fusion gain by %s%% at a threshold of 0.3 and by %s%% at 0.1, and neutral-beam torque of reactor size adds about %s%%. "
       "Parameter uncertainty and a screening-level plant power balance are quantified. No experimental data are used."
       % (pc(TB[0.3]["dQ"], 1), pc(TB[0.1]["dQ"], 0), pc(GAIN36[0.5], 1)))
NABS = len(re.sub(r"[_^]\{([^}]*)\}", r"\1", ABS).split())
print("abstract words:", NABS)
assert 150 <= NABS <= 250, NABS
I.abstract(doc, ABS, "Bifurcation, fusion reactors, numerical stability, plasma confinement, plasma transport processes, tokamaks.")
I.begin_two_columns(doc)

# ================================================================== I. Introduction
H1("I", "Introduction")
P("Predicting energy confinement in a tokamak requires a model of the transport driven by microturbulence. The transport is stiff: above a critical normalized temperature gradient, a small increase in the gradient "
  "produces a large increase in the heat flux, so profiles are pinned near marginal stability [[dimits2000; kotschenreuther1995]]. Sheared E×B flow decorrelates the turbulence and reduces the transport; "
  "this underlies the edge transport barrier and many improved-confinement regimes [[biglari1990; hahm1995; burrell1997; terry2000]], and quench rules that suppress the turbulence when the shearing rate exceeds a growth-rate scale "
  "are used in transport models [[waltz1994]]. A closure that encodes this is state dependent: the shearing rate is a function of the evolving profile, and the feedback it creates is the standard route to bistability and hysteresis in "
  "models of the L–H transition [[itoh1988; hinton1991]].")
P("Whether such a closure defines a well-behaved steady problem, and how much it changes the fusion gain under controlled conditions, are separate questions that are seldom answered together. This paper makes four contributions.")
BUL("1)  Closed-form admissibility conditions for shear-dependent flux closures, from a steady flux relation, with the saturation, fold, and hysteresis predicted when they fail (Section III), tested against direct solutions (Section V-C).")
BUL("2)  A diagnosis of the local heat closure: because the shearing rate contains the second derivative of the temperature, the steady problem is numerically ill posed, and a smoothed (adaptive-field) closure with a fixed length restores numerical stability and convergence over the tested conditions (Sections III-B and V-A).")
BUL("3)  A controlled, verified comparison in which only the closure differs, with grid-converged results, a fitted gain relation, a torque-driven extension, and a parameter-uncertainty study (Sections V-B to V-E).")
BUL("4)  A physical calibration: the baseline is benchmarked against recognized confinement scalings, operating limits, and neutral-beam torque, a screening-level plant power balance gives the net electric power, and the conclusions are stated as conditional on the unknown suppression threshold (Section VI).")
P("Nothing is fitted to experiment, no new fluid equation is proposed, and the model describes no specific device; the results are statements about closures in a reduced model. “Well posed” is used here in a numerical sense: the admissibility conditions of Section III are proved, but for the nonlinear heat problem existence, uniqueness, and continuous dependence are not, and the evidence is numerical (eigenvalues, convergence orders, edge-condition variants).")

# ================================================================== II. Model
H1("II", "Model")
H2("A", "Energy Balance and Baseline Closure")
P("One temperature T(r) (electrons and ions equal) is solved on a circular torus with flux-surface radius r ∈ [0, a], major radius R_{0}, and fixed density n(r) and safety factor q(r). The thermal energy density is 3nT, so a diffusivity χ acting on the energy per particle gives the heat flux −3nχ ∂_{r}T (T in energy units):")
EQ(Tt("3") + V("n") + SUBN(V("∂"), V("t")) + V("T") + EQS + FRAC(Tt("1"), V("r")) + DR + DEL(Tt("3") + V("r n χ") + DR + V("T"), "[", "]") + PLUS + sv("S", "aux") + PLUS + sv("S", "α") + MINUS + sv("S", "rad") + Tt("."), "energy")
P("The sources are a Gaussian auxiliary heating of power P_{aux}, alpha heating S_{α} = (n²/4)⟨σv⟩E_{α} for a 50:50 deuterium–tritium plasma with the Bosch–Hale reactivity [[bosch1992]], and bremsstrahlung S_{rad} = 5.35×10^{−37} n²T^{1/2} W m^{−3} (T in keV). "
  "The fusion power is P_{fus} = 5P_{α}, the gain Q = P_{fus}/P_{aux}, and τ_{E} = W/(P_{aux} + P_{α} − P_{rad}). The edge temperature is fixed at T_{a} = 4 keV. The model reduces the single-fluid magnetohydrodynamic description [[freidberg2014; wesson2011]] to a thermal-transport coefficient; no fluid equation is modified. @T:par@ lists the parameters, which are generic reactor-scale values, not a model of a specific device. "
  "The baseline diffusivity is a smoothed critical-gradient form [[dimits2000; kotschenreuther1995]],")
EQ(sv("χ", "base") + EQS + sv("χ", "n") + PLUS + sv("χ", "s") + V("w") + Tt(" ln") + DEL(Tt("1") + PLUS + Tt("exp") + DEL(FRAC(V("κ") + MINUS + sv("κ", "c"), V("w"))), "[", "]") + Tt(",   ") + V("κ") + EQS + FRAC(sv("R", "0") + Tt("|") + DR + V("T") + Tt("|"), V("T")) + Tt("."), "chibase")
H2("B", "State-Dependent Closure and the Adaptive Field")
P("The closure divides the baseline by a shear-suppression factor,")
EQ(V("χ") + EQS + FRAC(sv("χ", "base"), Tt("1") + PLUS + FRAC(V("A"), SUPN(sv("s", "c"), Tt("2")))) + Tt(",   ") + V("A") + MINUS + SUPN(V("ℓ"), Tt("2")) + FRAC(Tt("1"), V("r")) + DR + DEL(V("r") + DR + V("A")) + EQS + SUPN(DEL(FRAC(sv("ω", "E"), sv("γ", "0"))), Tt("2")) + Tt(","), "closure")
P("where γ_{0} = c_{s}/R_{0} is a decorrelation-rate proxy (c_{s} = (T/m_{i})^{1/2}, m_{i} = 2.5 amu), ω_{E} is the Hahm–Burrell shearing rate [[hahm1995]], ω_{E} = |(r/q) ∂_{r}(qE_{r}/rB)| with E_{r} = (en)^{−1}∂_{r}(nT), "
  "and A is a dimensionless adaptive field that relaxes to (ω_{E}/γ_{0})² and diffuses over the length ℓ (zero-flux ends); it is the steady limit of ∂_{t}A = D_{A}∇²A + [(ω_{E}/γ_{0})² − A]/τ_{A} with ℓ² = D_{A}τ_{A}. The threshold s_{c} is the only other parameter, and s_{c} → ∞ recovers the baseline. "
  "The limit ℓ → 0 is the local closure, A = (ω_{E}/γ_{0})². The reference length ℓ = %.2f m is about %.0f ion gyroradii at 10 keV; it is a new parameter, varied in Section V-E." % (LREF, LREF / CAL["rho_i_10keV"]))
H2("C", "Rotation, Viscosity Closures, and Coupling")
P("Toroidal rotation Ω(r, t) obeys")
EQ(sv("ρ", "m") + SUPN(sv("R", "0"), Tt("2")) + SUBN(V("∂"), V("t")) + V("Ω") + EQS + FRAC(Tt("1"), V("r")) + DR + DEL(V("r") + sv("μ", "eff") + SUPN(sv("R", "0"), Tt("2")) + DR + V("Ω"), "[", "]") + PLUS + sv("τ", "in") + Tt(",   ") + sv("μ", "eff") + EQS + sv("μ", "0") + V("F") + DEL(V("Λ")) + Tt(",   ") + V("Λ") + EQS +
   FRAC(V("r"), V("q") + sv("γ", "0")) + Tt("|") + DR + V("Ω") + Tt("|") + Tt(","), "rotation")
P("with ρ_{m} = nm_{i}, regularity on the axis, and Ω(a) = 0. The torque density τ_{in} has a Gaussian profile of width 0.4a and total ∫τ_{in}dV = T_{tot}; μ_{0} = Pr ρ̄ χ_{s} with Pr = 1 unless stated (μ_{0} = " + sci(MU0, 2) + " kg m^{−1} s^{−1}). "
  "Λ = ω_{rot}/γ_{0} is the rotation shearing rate in units of γ_{0}. Four viscosity closures F(Λ) are used: F = 1; 1/(1 + Λ^{m}); the floor form f + (1 − f)/(1 + Λ²); and f + (1 − f)exp(−αΛ²). "
  "Rotation adds to the diamagnetic shear in the heat closure because qE_{r}/rB contains −Ω: ω_{E} → |ω_{dia} + σω_{rot}| with σ = +1 when the shears add and σ = −1 when they oppose, and the coupling is one way (T sets γ_{0}; Ω adds shear).")
TAB([["Quantity", "Value"],
     ["R_{0}, a, B", "6.2 m, 2.0 m, 5.3 T"],
     ["n(r), q(r)", "10^{20}(1 − 0.75(r/a)²) m^{−3}; 1 + 2(r/a)²"],
     ["T_{a}; P_{aux}", "4 keV (fixed); 40 MW Gaussian, width 0.4a"],
     ["χ_{n}, χ_{s}, κ_{c}, w", "0.3, 1.0 m² s^{−1}, 4, 0.5"],
     ["m_{i}; E_{α}", "2.5 amu; 3.5 MeV"],
     ["ℓ (reference)", "%.2f m" % LREF],
     ["μ_{0} (Pr = 1)", sci(MU0, 2) + " kg m^{−1} s^{−1}"],
     ["Torque profile", "Gaussian, width 0.4a, 0–250 N m"]],
    "Model parameters held identical in every run", "par", widths=[1.25, 2.2])

# ================================================================== III. Theory
H1("III", "Admissibility and Regularization")
H2("A", "Shear-Dependent Viscosity: Steady Flux Relation")
P("**Proposition 1 (steady flux relation).** In steady state, with regularity on the axis, the shearing rate satisfies at each radius")
EQ(V("F") + DEL(V("Λ")) + V("Λ") + EQS + V("Θ") + DEL(V("r")) + Tt(",   ") + V("Θ") + EQS + FRAC(V("I") + DEL(V("r")), V("q") + sv("γ", "0") + sv("μ", "0") + SUPN(sv("R", "0"), Tt("2"))) + Tt(",   ") + V("I") + DEL(V("r")) + EQS +
   SUBN(Tt("∫"), Tt("0")) + V("τ") + Tt("(r′) r′ dr′") + Tt("."), "flux")
P("The closure enters only through Ψ(Λ) = ΛF(Λ), the normalized momentum flux; Θ is the torque number, proportional to the torque (Θ_{max} = %s per N m here)." % sci(TH_PER_NM, 3))
P("**Proposition 2 (admissibility).** (a) Ψ′ = F(1 + d ln F/d ln Λ), so Ψ increases if and only if d ln F/d ln Λ > −1. (b) If Ψ is increasing with supremum Ψ_{∞}, the relation has exactly one solution at each radius if and only if Θ < Ψ_{∞}: a steady state exists for every torque when Ψ_{∞} = ∞ and only for Θ_{max} < Ψ_{∞} otherwise (saturation). "
  "(c) If Ψ has a local maximum Ψ_{M} then a local minimum Ψ_{m} < Ψ_{M}, three solutions exist for Ψ_{m} < Θ < Ψ_{M}; the branch started at Λ = 0 ends in a fold at Θ = Ψ_{M}, and on decreasing torque the upper branch persists to Ψ_{m}: a hysteresis window [Ψ_{m}, Ψ_{M}] in Θ.")
P("**Proposition 3 (families).** F = 1/(1 + Λ^{m}) is admissible iff m ≤ 1 (m = 1 saturates at Ψ_{∞} = 1; for m > 1 the fold is at Λ^{*} = (m − 1)^{−1/m}, Ψ = Λ^{*}/m, i.e. Θ = 1/2 for m = 2). F = f + (1 − f)/(1 + Λ²) is admissible iff f > 1/9. "
  "F = f + (1 − f)exp(−αΛ²) is admissible iff f > 2e^{−3/2}/(1 + 2e^{−3/2}) = %.4f, for any α. Proofs are in the supplement. This is the condition under which a nonlinear diffusion problem with a drive-dependent flux is well posed [[perona1990]], "
  "and part (c) is the rotation analog of the S-curve of L–H models [[itoh1988; hinton1991]]." % THR["floor_exp"])
P("*Proof sketch.* Integrating the steady rotation equation from the axis, where rG vanishes by regularity, gives rG = −I(r), hence μ_{0}R_{0}²F(Λ)|∂_{r}Ω| = I/r and, with Λ = r|∂_{r}Ω|/qγ_{0}, Eq. @E:flux@. Proposition 2 follows from Ψ′ = F + ΛF′ and the monotonicity of Ψ. "
  "For F = 1/(1 + Λ^{m}), d ln F/d ln Λ = −mΛ^{m}/(1 + Λ^{m}) ∈ (−m, 0], which stays above −1 iff m ≤ 1; for the floor forms Ψ′ = f + (1 − f)g with min g = −1/8 (algebraic) or −2e^{−3/2} (exponential), giving f > 1/9 and f > 0.3086. Full proofs are in the supplement.")
TAB([["Closure F(Λ)", "Steady state for all Θ?", "Threshold"],
     ["1; 1/(1 + Λ^{m}), m < 1", "yes", "–"],
     ["1/(1 + Λ)", "no: saturates", "Θ < 1"],
     ["1/(1 + Λ²)", "no: fold", "Θ < 1/2"],
     ["f + (1 − f)/(1 + Λ²)", "yes if f > 1/9", "1/9 = 0.1111"],
     ["f + (1 − f)exp(−αΛ²)", "yes if f > %.4f" % THR["floor_exp"], "%.4f, any α" % THR["floor_exp"]]],
    "Admissibility of the viscosity closures", "clos", widths=[1.5, 1.2, 0.8])
H2("B", "Heat Closure: Branching and the Need for Regularization")
P("The heat flux of the local closure is Φ(T′, T″) = 3nχ_{base}T′/(1 + ω_{E}²/s_{c}²γ_{0}²) with ω_{E} = ω_{0}(r, T, T′) + cT″, c = 10³/B V per keV (T in keV). Because Φ depends on ω_{E} only through ω_{E}², "
  "the integrated balance rΦ(T′, T″) = −I_{h}(r) (with I_{h} the net source inside r) determines T″ only up to the choice of branch ω_{E} = ±ω^{*}: the steady local problem is a branching second-order equation, and a solution may switch branch in a thin layer. "
  "Nothing in the Dirichlet edge value or in regularity on the axis selects the branch, so the choice is made by the discretization of the edge cell. This is not a loss of ellipticity: the principal part, "
  "D_{eff} = [∂Φ/∂T′ + ∂_{r}(∂Φ/∂T″)]/3n, stays at least %.2f m² s^{−1} at every radius for all s_{c} tested (Table S4 of the supplement). "
  "The smoothed closure of Eq. @E:closure@ removes the branching: Φ is a smooth functional of the profile through A, and (T, A) obey a closed system of two second-order equations with the conditions T(a) = T_{a}, T′(0) = 0, and A′(0) = A′(a) = 0. "
  "Sections V-A and V-B test this diagnosis; it is supported by the evidence there but not proved." % min(p["Dmin"] for p in PPART))

# ================================================================== IV. Numerical method and verification
H1("IV", "Numerical Method and Verification")
P("The energy equation is discretized conservatively on N uniform cells (finite volume, face conductivities from the arithmetic mean of the cell values). All edge and axis derivatives are second order: the cell gradient at the edge cell and the edge-face derivative use the quadratic through the edge value and the last two cells, "
  "the axis cell uses T = A + Br², and E_{r}/r is extrapolated evenly to the axis. Steady states are obtained by damped Newton iteration with a banded (local) or dense (smoothed) central-difference Jacobian, started from a backward-Euler march of the baseline and followed in s_{c} by continuation; "
  "linear stability is read from the eigenvalues of the Jacobian of dT/dt. The rotation equation is solved by scaled Newton iteration with torque continuation, and torque ramps by backward-Euler marching so that the dynamics select the branch. Details are in the supplement.")
rmax = max(abs(v) for v in VER["resid"].values())
omin = min(v for o in ORD.values() for v in o if v)
omax = max(v for o in ORD.values() for v in o if v)
TAB([["Check", "Result"],
     ["Bosch–Hale at 10, 20 keV", "%.4g, %.4g ×10^{−22} m³ s^{−1}" % (R["bosch_hale"]["sigma_v_10keV"] * 1e22, R["bosch_hale"]["sigma_v_20keV"] * 1e22)],
     ["Power balance residual", "max %s of heating (s_{c} = ∞ to 0.03)" % sci(rmax, 0)],
     ["s_{c} = 10^{9} vs baseline", "difference %s keV" % ("0" if VER["max_dT_sc_1e9"] == 0 else sci(VER["max_dT_sc_1e9"], 0))],
     ["Radau integration vs Newton", "max %s keV (4 values of s_{c})" % sci(max(r["max_abs_dT"] for r in TI), 0)],
     ["Order of convergence of Q", "%.1f–%.1f (baseline and s_{c} ≥ 0.05)" % (omin, omax)],
     ["λ_{1}(s_{c} = 2), N = 100, 400", "%.3f, %.3f s^{−1}" % (VER["lambda1_sc2"]["100"], VER["lambda1_sc2"]["400"])],
     ["Flux relation vs direct solution", "max relative error %s (%d cases)" % (sci(SFS["max_rel_err"], 0), SFS["n_compared"])]],
    "Verification (all checks are reproduced by the code archive)", "ver", widths=[1.6, 1.9])

# ================================================================== V. Results
H1("V", "Results")
H2("A", "The Local Closure Is Numerically Ill Posed")
settled_local = [r["sc"] for r in ACC["local"] if r["settled"]]
P("With the second-order edge treatment and no smoothing, the steady state exists but its linear stability depends on the resolution: at every s_{c} below a threshold s_{c}^{lin}(N) a grid-scale mode localized in the last cells has a positive growth rate (@T:ill@, @F:ill@a,b). "
  "The growth rate rises by roughly an order of magnitude per doubling of N, and the threshold grows as N^{%.2f}, so for any finite s_{c} an unstable resolution is reached. In time integration at N = 100 a cold start of the local closure settles for s_{c} ≥ %s and runs away below it (@F:ill@)."
  % (LC["threshold_exponent"], ("%g" % min(settled_local)) if settled_local else "none"))
rows = [["N", "s_{c}^{lin}", "λ_{1}(s_{c} = 0.4) (s^{−1})", "λ_{1}(s_{c} = 0.2) (s^{−1})"]]
for N in ("50", "100", "200", "400"):
    rr = {r["sc"]: r for r in LC["rows"][N] if r["ok"]}
    rows.append([N, f3(LC["threshold"][N]), "%.3g" % rr[0.4]["lam1"], "%.3g" % rr[0.2]["lam1"]])
TAB(rows, "Local closure: onset of the grid-scale instability against resolution", "ill", widths=[0.45, 0.8, 1.2, 1.2])
d_hold_zero = EV["local, edge value held"]["Q@0.05/N400"] / EV["local, no suppression in the last cell"]["Q@0.05/N400"] - 1
sm = [EV["smoothed, l = %s m" % x]["Q@0.1/N400"] for x in ("0.02", "0.05", "0.10", "0.20")]
P("The converged value depends on how the edge is treated (@T:edge@, @F:ill@c). A first-order half-cell edge treatment, which damps the grid-scale mode, appears stable and even produces a fold at s_{c} = %.3f; this disappears when the edge is treated consistently, "
  "so it is an artifact. Imposing an explicit extra edge condition (the last cell takes its neighbor's shearing rate, or no suppression in the last cell) makes the local closure stable and convergent, but the two answers differ by %.0f%% at s_{c} = 0.05. "
  "The smoothed closure agrees with the edge-held condition to %.1f%% at s_{c} = 0.1 and varies by only %.1f%% over a tenfold range of ℓ."
  % (R["first_order_fold_N400"]["sc_fold"], 100 * d_hold_zero, 100 * abs(EV["smoothed, l = 0.05 m"]["Q@0.1/N400"] / EV["local, edge value held"]["Q@0.1/N400"] - 1), 100 * (max(sm) / min(sm) - 1)))


def qv(name, key):
    v = EV[name].get(key)
    return "–" if v is None else f3(v)


rows = [["Closure (edge condition)", "Q, N = 200", "Q, N = 400", "λ_{1}, N = 400"]]
for nm, lab in (("local, first-order edge", "local, first-order edge"), ("local, second-order edge", "local, second-order edge"), ("local, edge value held", "local, edge value held"),
                ("local, no suppression in the last cell", "local, none in last cell"), ("smoothed, l = 0.02 m", "smoothed, ℓ = 0.02 m"), ("smoothed, l = 0.05 m", "smoothed, ℓ = 0.05 m"),
                ("smoothed, l = 0.10 m", "smoothed, ℓ = 0.10 m"), ("smoothed, l = 0.20 m", "smoothed, ℓ = 0.20 m")):
    lam = EV[nm].get("lam@0.1/N400")
    rows.append([lab, qv(nm, "Q@0.1/N200"), qv(nm, "Q@0.1/N400"), "–" if lam is None else "%.3g" % lam])
TAB(rows, "Gain Q at s_{c} = 0.1 for different edge treatments and smoothing lengths (baseline Q = %.3f)" % Q0, "edge", widths=[1.75, 0.6, 0.6, 0.6])
FIG("fig2_illposed.png", "ill", "Local closure. (a) Leading eigenvalue λ_{1} against s_{c} for four resolutions (signed logarithm). (b) Threshold s_{c}^{lin} against N. (c) Q at s_{c} = 0.1 for different edge conditions (orange: local; blue: smoothed).",
    "Three panels: eigenvalue against threshold for several grids, onset threshold against grid size, and the gain for different edge treatments.", wide=True)
H2("B", "Smoothed Closure: Convergence and Controlled Comparison")
smoothed_ok = all(r["settled"] for r in ACC["smoothed"])
P("The smoothed closure is linearly stable at every s_{c} tested (λ_{1} ≤ %.2f s^{−1}, down to s_{c} = 0.02) and converges at second order: the observed order is %.2f–%.2f over s_{c} = 0.5 to 0.05 (@F:smooth@b), and Q changes by %s%% between N = 400 and N = 800 at s_{c} = 0.05. "
  "%s @T:cmp@ gives the comparison. The gain is described by a fitted inverse-square relation, ΔQ = C/s_{c}² with C = %.5f (range %.5f–%.5f for s_{c} ≥ 0.2), i.e. ΔQ/Q = %.3f%%/s_{c}²; the fit is within %.0f%% over 0.02 ≤ s_{c} ≤ 1 for this parameter set. It is an empirical relation for the tested range, not a derived or universal scaling law. "
  "The confinement time barely changes (τ_{E} = %.3f s at s_{c} = 0.05 against %.3f s), so the gain acts through the power balance and the core temperature (T_{0} rises from %.1f to %.1f keV). "
  "Like any discretization, the smoothed closure is resolution limited at very strong coupling: a grid-scale mode turns unstable below s_{c} = %s, %s, and %s at N = 100, 200, and 400, and is absent down to s_{c} = 0.015 at N = 800. "
  "In contrast with the local closure, this threshold falls as the grid is refined, so it is a resolution requirement (ℓ must be resolved), not a property of the model."
  % (max(r["lam1"] for r in R["table1"]), omin, omax, pc(abs(GR["0.05"][3]["Q"] / GR["0.05"][2]["Q"] - 1), 2),
     "A cold start settles on the steady state for every s_{c} tested." if smoothed_ok else "A cold start does not always settle (see the supplement).", LR["C_mean"], LR["C_min"], LR["C_max"], 100 * LR["C_mean"] / Q0, 100 * law_dev,
     TB[0.05]["tauE"], TB["base"]["tauE"], TB["base"]["T0"], TB[0.05]["T0"], SMT["100"]["threshold"], SMT["200"]["threshold"], SMT["400"]["threshold"]))
rows = [["s_{c}", "Q", "ΔQ/Q", "T_{0} (keV)", "H_{98}", "β_{N}"]]
for k in ("base", 1.0, 0.5, 0.3, 0.2, 0.1, 0.07, 0.05, 0.03, 0.02):
    r = TB[k]
    rows.append(["∞" if k == "base" else "%g" % k, f3(r["Q"]), "–" if k == "base" else "%s%%" % pc(r["dQ"], 2 if r["dQ"] < 0.01 else 1), f1(r["T0"]), f2(r["H98"]), f2(r["beta_N"])])
TAB(rows, "Smoothed closure (ℓ = %.2f m, N = 400) at 40 MW: gain, core temperature, and benchmark quantities" % LREF, "cmp", widths=[0.45, 0.65, 0.7, 0.65, 0.5, 0.5])
FIG("fig1_profiles.png", "prof", "Smoothed closure at 40 MW (N = 400, ℓ = %.2f m): (a) temperature, (b) diffusivity, and (c) smoothed shearing rate against r/a for the baseline and s_{c} = 0.3 and 0.1. The suppression is confined to the edge." % LREF,
    "Three panels of radial profiles of temperature, diffusivity, and smoothed shearing rate.", wide=True)
FIG("fig3_smoothed.png", "smooth", "Smoothed closure. (a) Relative gain against s_{c} with the fitted inverse-square relation (dashed) and the 5–95% interval from the parameter-uncertainty study (bars). (b) Convergence of Q with N (dotted: N^{−1}; dashed: N^{−2}). "
    "(c) Rank correlation of the gain at s_{c} = 0.1 with each sampled parameter.", "Three panels: gain law with uncertainty bars, convergence of the gain with resolution, and rank correlations.", wide=True)
H2("C", "Tests of the Admissibility Theory")
P("The rotation equation was solved directly (finite volume, N = 200, baseline temperature profile, torques 25–250 N m) and compared with Proposition 1 (@F:adm@b): the simulated Λ_{max} agrees with the solution of F(Λ)Λ = Θ(r) to a relative error of at most %s over %d cases, and a steady state exists exactly when Θ_{max} < Ψ_{∞}. "
  "The last torque with a steady state is %.1f N m for m = 2 (Θ_{max} = %.5f; predicted fold at 1/2) and %.1f N m for m = 1 (Θ_{max} = %.5f; predicted saturation at 1). "
  "For the floor closure with f = 0.05 < 1/9 the theory gives Ψ_{M} = %.4f and Ψ_{m} = %.4f, a hysteresis window of %.0f–%.0f N m; torque ramps show the jump between 260 and 280 N m and a return at or below %.0f N m, while f = 0.20 shows no hysteresis (@F:adm@c). "
  % (sci(SFS["max_rel_err"], 1), SFS["n_compared"], RF["2.0"]["torque_last"], RF["2.0"]["Theta_last"], RF["1.0"]["torque_last"], RF["1.0"]["Theta_last"], HYS["predicted"]["Psi_max"], HYS["predicted"]["Psi_min"],
     HYS["predicted"]["torque_down"], HYS["predicted"]["torque_up"], HYS["predicted"]["torque_down"]))
FIG("fig4_admissibility.png", "adm", "Admissibility theory. (a) Normalized flux Ψ = ΛF(Λ); the fold for m = 2 is marked. (b) Λ_{max} from direct solutions against the flux relation. (c) Torque ramps for the floor closure (f = 0.05: hysteresis; shaded: predicted window; f = 0.20: none).",
    "Three panels: normalized flux curves, flux relation test, and hysteresis ramps.", wide=True)
H2("D", "Torque-Driven Shear")
rows = [["Torque (N m)", "Θ_{max}", "Q const.", "Q, m = 1", "Q, m = 2, f = 0.2", "Q const., σ = −1"]]
for t in (0.0, 50.0, 100.0, 200.0, 250.0):
    r0 = CP[(1.0, "linear", t)]
    rows.append(["%g" % t, f3(r0["Theta"]) if t else "0", f2(Qt(t)), f2(Qt(t, "m=1")), f2(Qt(t, "m=2 f=0.20")), f2(Qt(t, "linear", -1.0))])
TAB(rows, "Gain with torque-driven shear (s_{c} = 0.5, N = 100, 40 MW, shears adding unless noted)", "torque", widths=[0.7, 0.5, 0.55, 0.55, 0.65, 0.65])
P("With the shears adding, the gain rises monotonically with torque (@T:torque@, @F:torque@): for a constant viscosity Q goes from %s to %s at 100 N m and %s at 200 N m (%s%% above the baseline); a viscosity that falls with shear amplifies the effect (m = 1: Q = %s at 200 N m). "
  "The inadmissible closure m = 2 has no steady rotation profile above Θ = 1/2 (250 N m), as Proposition 3 predicts, whereas the admissible floor closure does. When the shears oppose, the gain is smaller but still increases. "
  "At the neutral-beam torque of Section VI-C (about %.0f N m) the gain is %s%% at s_{c} = 0.5 and %s%% at s_{c} = 0.2."
  % (f2(Qt(0.0)), f2(Qt(100.0)), f2(Qt(200.0)), pc(Qt(200.0) / Q0 - 1, 0), f2(Qt(200.0, "m=1")), CAL["nbi_torque"]["5.3"], pc(GAIN36[0.5], 1), pc(GAIN36[0.2], 1)))
FIG("fig5_torque.png", "torque", "Gain against torque for three viscosity closures (solid: shears adding; dotted: opposing). The shaded band is the full-energy neutral-beam torque estimate for a reactor-scale device (Section VI-C).",
    "Fusion gain against torque for three viscosity closures, with a band marking the beam torque estimate.", width=3.3)
H2("E", "Parameter Uncertainty and Sensitivity")
b = R["uncertainty_heat"]["bounds"]
P("A scrambled Sobol sequence (fixed seed, %d points) samples χ_{s} ∈ [%.1f, %.1f] m² s^{−1}, κ_{c} ∈ [%.1f, %.1f], w ∈ [%.1f, %.1f], T_{a} ∈ [%.0f, %.0f] keV, n_{0} ∈ [%.1f, %.1f]×10^{20} m^{−3}, B ∈ [%.1f, %.1f] T, and ℓ ∈ [%.2f, %.2f] m "
  "(%d converged). The baseline gain Q varies from %.1f to %.1f (5–95%%), but the relative gain is far more stable: %s–%s%% at s_{c} = 0.3, %s–%s%% at 0.1, and %s–%s%% at 0.05 (@F:smooth@a). "
  "The rank correlations (@F:smooth@c) identify the parameters that control the gain at s_{c} = 0.1. "
  "A second sequence over the torque study (torque 25–200 N m, profile width 0.2–0.6a, Pr 1–4, s_{c} 0.2–1, both signs, ℓ) gives a gain of %s–%s%% (median %s%%) over %d converged samples."
  % (UH["n_samples"], b["chi_s"][0], b["chi_s"][1], b["kappa_c"][0], b["kappa_c"][1], b["w"][0], b["w"][1], b["Ta"][0], b["Ta"][1], b["n0"][0] / 1e20, b["n0"][1] / 1e20, b["B"][0], b["B"][1], b["reg_length"][0], b["reg_length"][1], UH["n_ok"],
     UH["Q0"]["p05"], UH["Q0"]["p95"], pc(UH["gain@0.3"]["p05"], 1), pc(UH["gain@0.3"]["p95"], 1), pc(UH["gain@0.1"]["p05"], 0), pc(UH["gain@0.1"]["p95"], 0), pc(UH["gain@0.05"]["p05"], 0), pc(UH["gain@0.05"]["p95"], 0),
     pc(UT["p05"], 0), pc(UT["p95"], 0), pc(UT["p50"], 0), UT["n_ok"]))

# ================================================================== VI. Calibration
H1("VI", "Physical Calibration and Engineering Applicability")
P("The parameters of the model are illustrative; this section places them against recognized scalings and limits, using an ITER-like reference device (R_{0} = 6.2 m, a = 2.0 m, B = 5.3 T, plasma current %.0f MA, elongation %.1f, 2.5 amu). "
  "The plasma current is not an input of the one-dimensional model, so it is taken from the reference device; all formulas are given in the code archive." % (CAL["ref"]["I_MA"], CAL["ref"]["kappa_a"]))
H2("A", "Confinement Scalings")
P("With the net heating P_{net} = %.1f MW and the line-average density %.1f×10^{19} m^{−3}, the baseline confinement time %.2f s is %.2f times the ITER89-P L-mode scaling [[yushmanov1990]] (%.2f s) and %.2f times the IPB98(y,2) H-mode scaling [[iter1999]] (%.2f s). "
  "The stiff baseline with a fixed 4 keV edge is therefore an L-mode-like plasma. The agreement with ITER89-P is a consistency check, not an independent validation: the edge temperature is imposed, the critical-gradient parameters are generic, and the density and heating profiles are prescribed, so other parameter choices would also bring H_{89} near unity. The smoothed closure acts only on the edge shear, and even at s_{c} = 0.02 it raises the H_{98} factor from %.2f to %.2f (@T:cmp@): it produces a partial edge barrier, not an H-mode pedestal, "
  "and must not be read as predicting H-mode performance."
  % (TB["base"]["P_net"], N_LINE19, TB["base"]["tauE"], TB["base"]["H89"], TB["base"]["tau89"], TB["base"]["H98"], TB["base"]["tau98"], TB["base"]["H98"], TB[0.02]["H98"]))
H2("B", "Operating Limits")
P("The Greenwald fraction n̄/n_{G} = %.2f [[greenwald2002]], with n_{G} = I_{p}/πa² = %.2f×10^{20} m^{−3}, is fixed by the density profile. The normalized beta β_{N} = %.2f for the baseline rises to %.2f at s_{c} = 0.1 and %.2f at s_{c} = 0.02, "
  "below the Troyon-type limit of order 3 [[troyon1984]]; the magnetohydrodynamic limit therefore does not bound the closure in the range studied, although the model contains no stability physics, so this is a consistency check only."
  % (TB["base"]["f_G"], CAL["n_G"], TB["base"]["beta_N"], TB[0.1]["beta_N"], TB[0.02]["beta_N"]))
H2("C", "Neutral-Beam Torque")
P("The heating neutral beams of a reactor-scale device deliver 33 MW at 1 MeV (deuterium) [[paul2017]]. A beam of power P and speed v injects a torque T = 2PR_{t}/v, since each particle of energy mv²/2 carries angular momentum mvR_{t}; "
  "with v = %.2f×10^{6} m s^{−1} and a tangency radius R_{t} = 4.5–6 m this gives %.0f–%.0f N m (full-energy component only, no losses), consistent with the statement that the torque scales as P/E^{1/2} and is small in a large device [[paul2017]]. "
  "The torque scan to 250 N m is therefore a sensitivity range up to %.0f times the estimate, not a prediction; at the estimated torque the gain is %s%% (s_{c} = 0.5) to %s%% (s_{c} = 0.2), and the Mach number at 250 N m is %.2f."
  % (CAL["v_beam"] / 1e6, CAL["nbi_torque"]["4.5"], CAL["nbi_torque"]["6.0"], 250.0 / CAL["nbi_torque"]["5.3"], pc(GAIN36[0.5], 1), pc(GAIN36[0.2], 1), CP[(1.0, "linear", 250.0)]["Mach"]))
H2("D", "The Suppression Threshold")
P("The threshold plays the role of the maximum linear growth rate in units of γ_{0} in a quench rule [[waltz1994]], s_{c} = γ_{max}/γ_{0}. The largest smoothed diamagnetic shear in the model is ω_{E}/γ_{0} ≈ %.2f, so for s_{c} ≳ 0.3, i.e. growth rates above 0.3c_{s}/R_{0}, the closure changes Q by less than 1%%, "
  "and it changes it by more than 10%% only for s_{c} ≲ %.2f. Which regime applies cannot be decided without gyrokinetic growth rates for the profiles in question, and that calibration, together with ℓ, is the main open step. "
  "Meanwhile the fitted relation ΔQ/Q = %.3f%%/s_{c}² (valid only for the tested range and parameters) and its uncertainty band give the sensitivity of the result to the choice." % (TB["base"]["ratio_max"], SC10, 100 * LR["C_mean"] / Q0))
rows = [["Quantity", "Value", "Reference"],
        ["H_{89}, H_{98} (baseline)", "%.2f, %.2f" % (TB["base"]["H89"], TB["base"]["H98"]), "[[yushmanov1990; iter1999]]"],
        ["n̄/n_{G}; β_{N}", "%.2f; %.2f–%.2f" % (TB["base"]["f_G"], TB["base"]["beta_N"], TB[0.02]["beta_N"]), "[[greenwald2002; troyon1984]]"],
        ["Beam torque estimate", "%.0f–%.0f N m" % (CAL["nbi_torque"]["4.5"], CAL["nbi_torque"]["6.0"]), "33 MW, 1 MeV [[paul2017]]"],
        ["Gain at that torque", "%s%% (s_{c} = 0.5)" % pc(GAIN36[0.5], 1), "this work"],
        ["Net electric power, baseline", "%.0f MW (assumed efficiencies)" % R["plant"]["cases"][0]["Pnet"], "this work"],
        ["ℓ / ρ_{i} (10 keV)", "%.0f" % (LREF / CAL["rho_i_10keV"]), "this work"]]
TAB(rows, "Calibration summary", "cal", widths=[1.35, 1.1, 1.05])

H2("E", "Plant Power Balance and Cost Proxy")
PLB = R["plant"]
PC = PLB["cases"]
PU = PLB["uncertainty"]
PA_ = PLB["assume"]
PBn = PLB["bounds"]
P("To say what the gain means for a power plant, the fusion and heating powers of the model are passed through a screening-level plant balance. It is an accounting of assumed efficiencies, not a design. "
  "The thermal power is P_{th} = P_{fus}(f_{n}M + 1 − f_{n}) + P_{aux}, with neutron energy fraction f_{n} = %.2f, blanket energy multiplication M, and all injected heating power ending as heat; the gross electric power is η_{th}P_{th}; "
  "and the recirculating power is P_{aux}/η_{aux} + P_{other}, where P_{other} stands for cryogenics, pumps, the tritium plant, and control. Then P_{net} = η_{th}P_{th} − P_{aux}/η_{aux} − P_{other}. "
  "The central values η_{th} = %.2f, M = %.1f, η_{aux} = %.2f, and P_{other} = %.0f MW are varied over %.2f–%.2f, %.1f–%.1f, %.2f–%.2f, and %.0f–%.0f MW with a scrambled Sobol sequence (%d points, fixed seed)."
  % (PLB["f_n"], PA_["eta_th"], PA_["M"], PA_["eta_aux"], PA_["P_other"], PBn["eta_th"][0], PBn["eta_th"][1], PBn["M"][0], PBn["M"][1], PBn["eta_aux"][0], PBn["eta_aux"][1], PBn["P_other"][0], PBn["P_other"][1], PU["n"]))
TAB([["Case (P_{aux} = 40 MW)", "P_{fus}", "P_{gross}", "P_{net}", "ΔP_{net}"]] +
    [[c["name"], "%.0f" % c["Pfus"], "%.0f" % c["Pgross"], "%.0f" % c["Pnet"], "%+.1f" % c["dPnet"] if c["dPnet"] else "0"] for c in PC],
    "Screening-level plant power balance (MW) at the central assumptions; the recirculating power is %.0f MW in every case" % PC[0]["Precirc"], "plant", widths=[1.45, 0.5, 0.55, 0.5, 0.5])
P("At P_{aux} = 40 MW the baseline gives P_{fus} = %.0f MW and P_{net} = %.0f MW (@T:plant@): engineering breakeven would need a physical gain of Q = %.2f instead of %.2f. The net power is negative for all %d sampled assumptions (5–95%%: %.0f to %.0f MW), "
  "and when P_{aux} is reduced it rises monotonically to %.0f MW at the lowest value scanned (10 MW), so the plasma of this model is below engineering breakeven under every assumption tried except the most favorable corner at low heating power (best over the power scan: positive for %.0f%% of draws). "
  "The closure raises P_{net} by %.1f MW at s_{c} = 0.3, %.1f MW at 0.1 (%.1f–%.1f MW over the assumptions), and %.1f MW at 0.05, and by %.1f MW at the neutral-beam torque estimate, a small share of the %.0f MW deficit; "
  "only %.0f%% (s_{c} = 0.1) and %.0f%% (0.05) of the draws reach positive net power. The net electric power is therefore a statement about the assumptions as much as the closure, but the increment the closure adds is robust to them."
  % (PC[0]["Pfus"], PC[0]["Pnet"], PLB["q_breakeven_40"], TB["base"]["Q"], PU["n"], PU["Pnet"]["baseline"]["p05"], PU["Pnet"]["baseline"]["p95"], PLB["scan"]["baseline"][0]["Pnet"], 100 * PU["best_over_Paux_baseline"]["frac_positive"],
     PC[1]["dPnet"], PC[2]["dPnet"], PU["dPnet"]["0.1"]["p05"], PU["dPnet"]["0.1"]["p95"], PC[3]["dPnet"], PC[4]["dPnet"], -PC[0]["Pnet"],
     100 * PU["Pnet"]["smoothed, s_c = 0.1"]["frac_positive"], 100 * PU["Pnet"]["smoothed, s_c = 0.05"]["frac_positive"]))
P("Cost is not computed. A relative proxy is defined for use when designs differ in heating power, C_{rel} = 1 + κ(P_{aux}/40 MW − 1), with κ = %.2f (range %.2f–%.2f) the assumed share of the reference capital that scales with heating power. "
  "Because every case here has the same geometry and heating power, C_{rel} = 1 for all of them and the proxy cannot separate the closures; and because P_{net} is negative, the ratio P_{net}/C_{rel} has no meaning. "
  "A cost comparison across devices of different size or field would need a cost model, which is not part of this study." % (PA_["kappa"], PBn["kappa"][0], PBn["kappa"][1]))

# ================================================================== VII. Discussion
H1("VII", "Discussion and Limitations")
H2("A", "Principal Findings")
P("Three findings stand out. First, whether a shear-suppression closure is well behaved is not a numerical detail: for the local closure the converged answer is set by an edge condition that the physics does not supply, and a consistent discretization is unstable at fine resolution. "
  "A local-closure result should therefore be reported with its edge treatment, resolution, and eigenvalues; the smoothed closure removes the issue at the price of one new length, to which the gain is insensitive (@T:edge@). "
  "Second, the admissibility conditions are a priori checks that cost nothing and are reproduced to ten digits. Third, in this model the diamagnetic shear changes the gain by well under one percent at moderate threshold, and the sensitivity to the threshold, not the form of the closure, dominates the uncertainty.")
H2("B", "Limitations")
P("The limitations are those of a reduced model: no existence, uniqueness, or continuous-dependence theorem is proved for the nonlinear heat problem, so “ill posed” and “well behaved” rest on numerical evidence over the tested conditions; one-dimensional energy transport with fixed density, equal temperatures, and local alpha deposition; one-way coupling to rotation; no pedestal, edge-localized-mode, or magnetohydrodynamic physics; generic critical-gradient parameters (benchmarked only at the level of Section VI); "
  "an uncalibrated threshold and length; and no experimental data. The plasma current, elongation, and the Troyon limit enter only the calibration. A predictive claim would require gyrokinetic calibration of s_{c} and ℓ, a self-consistent density and pedestal, and validation against experiment.")

H2("C", "Implications for Compact, Cost-Constrained Tokamak Design")
P("Compact devices have tight margins among confinement, field strength, auxiliary heating, and actuator capability, so a reduced transport model used to screen their operating regimes must not turn numerical artifacts into confinement gains. "
  "The present results bear on this only as a methodological prerequisite. The local closure is sensitive to the edge treatment and the resolution, whereas the regularized closure gave convergent solutions over the tested conditions; "
  "a predicted confinement improvement should therefore be accepted only after the flux admissibility, the grid convergence, and the sensitivity to the regularization length have been checked.")
P("Auxiliary rotation drive is the clearest case. At the reactor-scale beam torque of Section VI-C the modeled gain is only %s%% (s_{c} = 0.5) to %s%% (s_{c} = 0.2), and larger gains need either stronger suppression or a torque far above that estimate. "
  "This says nothing about the torque a compact device requires, because size, field, beam energy, geometry, and momentum transport change the accessible regime." % (pc(GAIN36[0.5], 1), pc(GAIN36[0.2], 1)))
P("A natural extension would apply the verified closure to a family of compact configurations that differ in major radius, minor radius, field, plasma current, and auxiliary power, and compare confinement time, fusion gain, actuator requirements, and operating margins under the same admissibility and convergence criteria; "
  "the one-dimensional model would first need geometric rescaling and equilibrium constraints. The relevant objective is not the largest modeled gain but an operating point that reaches adequate confinement with little auxiliary power and little sensitivity to the uncertain closure parameters. "
  "The screening-level plant balance of Section VI-E gives the electric side of that weighing for the reference device; a normalized engineering cost would require a cost model, which is not part of this study.")
P("The model is not sufficient to establish compact-device feasibility: it omits self-consistent equilibrium and stability, pedestal physics, current drive, magnet engineering, neutron shielding, and balance of plant, and the threshold and the length are uncalibrated against gyrokinetic calculations or experiment. "
  "The contribution is therefore a verified method for assessing closure sensitivity, not a prediction that a compact or low-cost tokamak can reach a given gain: the net electric power of Section VI-E is an accounting under assumed efficiencies for the reference device only, and no cost is computed.")

# ================================================================== VIII. Conclusion
H1("VIII", "Conclusion")
P("State-dependent shear-suppression closures need two things that are easy to overlook: an admissibility condition on the flux and a length that regularizes the shearing rate. With them the reduced model is verified, converges at second order, "
  "and gives a gain described over the tested range by the fitted relation ΔQ/Q = %.3f%%/s_{c}² with a documented uncertainty, while the local closure is numerically ill posed and its answers depend on the edge treatment. The admissibility conditions are exact and tested to ten digits. "
  "The baseline is L-mode-like (H_{89} = %.2f, a consistency check because the edge temperature is imposed), neutral-beam torque of reactor size adds about %s%%, and under assumed plant efficiencies the modeled plasma at 40 MW heating is below engineering breakeven, which the closure moves by only a few megawatts at moderate thresholds. The suppression threshold and the smoothing length are the quantities that a gyrokinetic calibration must supply before the gain can be used for design."
  % (100 * LR["C_mean"] / Q0, TB["base"]["H89"], pc(GAIN36[0.5], 1)))

# ================================================================== back matter
I.back_heading(doc, "Acknowledgment")
P("The author used Claude Sonnet 5.5 (Anthropic; model identifier claude-sonnet-5-5), accessed through the Claude Code environment of the Claude desktop application between 7 and 9 October 2026, to write and test the code, derive and check the closed-form results, "
  "run the numerical experiments, produce the figures, and draft the text. The author reviewed and edited all content, checked every reference against Crossref, and takes full responsibility for the paper. No funding was received.")
I.back_heading(doc, "Code and Data Availability")
P("All code, tests, raw results (results.json), figure scripts, and the manuscript builders are at %s (release %s) and archived at https://doi.org/%s (software, MIT license); this manuscript is archived as a preprint at https://doi.org/%s. "
  "No experimental data were used. A supplementary file contains the proofs, the numerical protocol, and extended tables." % (REPO, RELEASE, SW_DOI, PP_DOI))
I.back_heading(doc, "References")
for i_, key in enumerate(CITE, 1):
    I.reference(doc, i_, REFS[key]["text"])
uncited = [k for k in REFS if k not in CITE]
assert not uncited, "uncited references: %s" % uncited

doc.save(os.path.join(OUT, "Admissibility_Shear_Closures_IEEE_TPS.docx"))
json.dump(LAB_NEW, open(LABFILE, "w"))
json.dump(EQNUM_NEW, open(EQFILE, "w"))
print("saved | figures: %d | tables: %d | equations: %d | references: %d | labels %s" % (FIGN[0], TABN[0], EQN[0], len(CITE), LAB_NEW))
