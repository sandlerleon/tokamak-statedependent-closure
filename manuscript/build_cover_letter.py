# -*- coding: utf-8 -*-
"""Cover letter for the Journal of Plasma Physics (Research Article).   python build_cover_letter.py -> out/Cover_Letter_JPP.docx"""
import json
import os
import sys

from docx.shared import Pt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import docx_helpers as H  # noqa: E402

ROOT = os.path.join(HERE, "..")
R = json.load(open(os.path.join(ROOT, "results.json"), encoding="utf-8"))
ZEN = json.load(open(os.path.join("C:" + os.sep, "YouTube", "_tok_zenodo_state.json")))
SW, PP = ZEN["software"]["doi"], ZEN["publication"]["doi"]
RELEASE = os.environ.get("RELEASE_TAG", "v1.0.0")
REPO = "https://github.com/sandlerleon/tokamak-statedependent-closure"
TITLE = "State-dependent shear-suppression closures for reduced tokamak transport: a controlled comparison, admissibility conditions and a fold of the steady state"
T1 = {(r["sc"] if r["sc"] is not None else "base"): r for r in R["table1"]}
FOLD = R["fold"]
CP = {(r["sign"], r["closure"], r["torque"]): r for r in R["coupled_scan"]}
Q0 = T1["base"]["Q"]
FQ = (FOLD["by_N"]["200"]["Q_fold"] + FOLD["by_N"]["400"]["Q_fold"]) / 2
doc = H.new_document(size=11, line=1.15)


def para(text, bold=False, after=6):
    p = doc.add_paragraph()
    if bold:
        p.add_run(text).bold = True
    else:
        H.add_rich(p, text)
    p.paragraph_format.space_after = Pt(after)
    return p


def bullet(text):
    p = doc.add_paragraph(style="List Bullet")
    H.add_rich(p, text)
    p.paragraph_format.space_after = Pt(3)


for line in ("Leon Sandler", "Independent researcher, Northbrook, Illinois, USA", "sandler.leon@gmail.com", "ORCID: https://orcid.org/0009-0007-4584-808X"):
    para(line, after=0)
para("")
para("8 October 2026")
para("The Editors\nJournal of Plasma Physics", after=10)
para("Submission of a Research Article: “%s”" % TITLE, bold=True, after=10)
para("Dear Editors,")
para("I submit the enclosed paper for consideration as a Research Article in the Journal of Plasma Physics. It concerns a state-dependent transport closure of a kind used in tokamak transport models, in which the heat diffusivity "
     "is suppressed by the local E×B shearing rate, which is itself a function of the evolving profile. The paper asks, in a deliberately controlled reduced model, how much such a closure changes the fusion gain relative to a stiff "
     "critical-gradient baseline and whether the answer is numerically trustworthy. It is computational and theoretical: no experimental data are used and all parameters are illustrative.")
para("Main results", bold=True, after=3)
bullet("*Controlled comparison.* A one-dimensional radial energy equation with fusion heating is solved with identical geometry, density, field, heating and boundary conditions, so that only the closure differs. "
       "The solver is verified by power balance (residual below 10^{−9} of the heating), exact recovery of the baseline as the threshold s_{c} → ∞, independent time integration (agreement to %.0e keV) and grid convergence of Q "
       "(observed order from 2.0 to about 1.1). With diamagnetic shear alone Q (baseline %.2f) rises by %.2f%%, %.2f%% and %.1f%% at s_{c} = 1, 0.5 and 0.3."
       % (max(r["max_abs_dT"] for r in R["time_integration"]), Q0, 100 * T1[1.0]["dQ"], 100 * T1[0.5]["dQ"], 100 * T1[0.3]["dQ"]))
bullet("*A fold of the steady state.* The gain rises steeply as s_{c} decreases (%.0f%% at s_{c} = 0.1), and the lower branch of steady states ends in a saddle-node fold at s_{c}^{*} = %.3f (extrapolated in resolution), "
       "where Q is about %.1f. Below the fold no steady state exists and the axis temperature runs beyond the range in which the reactivity fit is valid. The gain is therefore a steep function of an uncalibrated parameter, "
       "and the paper states this as a sensitivity result, not as a prediction." % (100 * T1[0.1]["dQ"], FOLD["extrapolated"], FQ))
bullet("*Closed-form admissibility conditions.* For the rotation equation with a shear-dependent viscosity F(Λ), the steady flux relation F(Λ)Λ = Θ reduces existence, saturation, fold and hysteresis of the steady state to the "
       "monotonicity of ΛF(Λ), with closed-form thresholds (m ≤ 1 for F = 1/(1 + Λ^{m}); viscosity floors 1/9 and %.4f). Direct finite-volume solutions reproduce the relation to a relative error of %.0e, "
       "the fold and saturation values to better than 10^{−4}, and the predicted hysteresis window." % (R["theory"]["thresholds"]["floor_exp"], R["scalar_flux_relation_summary"]["max_rel_err"]))
bullet("*Torque-driven shear.* With the rotation shear added to the diamagnetic shear, Q rises by %.0f%% at 200 N m for s_{c} = 0.5 (constant viscosity), subject to the existence conditions above."
       % (100 * (CP[(1.0, "linear", 200.0)]["Q"] / Q0 - 1)))
para("Fit to the journal", bold=True, after=3)
para("The paper is about transport closures, E×B shear suppression and the existence of steady states and bifurcations in reduced models of confined plasmas, and it is written so that the claims are no stronger than the checks that support them. "
     "I also report two numerical pitfalls found during verification (a finite-difference Jacobian step that is wrong for quantities depending on second derivatives, and the resolution of the round-off floor of the residual) "
     "because they affect anyone who solves such closures. Whether the advance is sufficient for the Journal is for the Editors to judge.")
para("Code, data and declarations", bold=True, after=3)
para("All code, tests, raw results and figure scripts are public at %s (release %s) and archived at https://doi.org/%s; the manuscript is available as a preprint at https://doi.org/%s, which Cambridge University Press "
     "does not regard as prior publication. Reproducing every number takes about ten minutes. The manuscript contains the declaration of the use of artificial intelligence: Claude Sonnet 5.5 (Anthropic; model identifier "
     "claude-sonnet-5-5), accessed through the Claude Code environment of the Claude desktop application, was used between 7 and 8 October 2026 for code, derivations, numerical experiments, figures and drafting; I reviewed and edited all "
     "content, checked every reference against Crossref and take full responsibility for the paper. I am the sole author, have no competing interests and received no funding. The manuscript is not under consideration "
     "elsewhere and has not been published." % (REPO, RELEASE, SW, PP))
para("Thank you for considering the paper.")
para("Yours sincerely,", after=18)
para("Leon Sandler")
out = os.path.join(HERE, "out", "Cover_Letter_JPP.docx")
doc.save(out)
print("saved", out)
