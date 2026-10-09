# -*- coding: utf-8 -*-
"""Cover letter for IEEE Transactions on Plasma Science (regular paper).   python build_cover_letter.py -> out/Cover_Letter_IEEE_TPS.docx"""
import json
import os
import sys

import numpy as np
from docx.shared import Pt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import docx_helpers as H  # noqa: E402

ROOT = os.path.join(HERE, "..")
R = json.load(open(os.path.join(ROOT, "results.json"), encoding="utf-8"))
ZEN = json.load(open(os.path.join("C:" + os.sep, "YouTube", "_tok_zenodo_state.json")))
SW = (ZEN.get("software_1.1.0") or ZEN["software"])["doi"]
PP = (ZEN.get("publication_v2") or ZEN["publication"])["doi"]
RELEASE = os.environ.get("RELEASE_TAG", "v1.1.0")
REPO = "https://github.com/sandlerleon/tokamak-statedependent-closure"
TITLE = "Well-Posed Shear-Suppression Closures for Reduced Tokamak Transport: Admissibility, Regularization, and Physical Calibration"
TB = {(r["sc"] if r["sc"] is not None else "base"): r for r in R["table1"]}
LC = R["local_closure"]
LR = R["linear_response"]
CST = {r["sc"]: {x["torque"]: x["Q"] for x in r["rows"]} for r in R["coupled_sc_torque"]}
EV = {r["name"]: r for r in R["edge_variants"]}
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
para("9 October 2026")
para("The Editor-in-Chief\nIEEE Transactions on Plasma Science", after=10)
para("Submission of a regular paper: “%s”" % TITLE, bold=True, after=10)
para("Dear Editor,")
para("I submit the enclosed paper for consideration as a regular paper in the IEEE Transactions on Plasma Science. It addresses a modelling question that matters for fusion transport codes: when a turbulent-transport closure is suppressed by sheared E×B flow, "
     "does it define a well-posed steady problem, and how much does it change the fusion gain once it does? The study is computational and theoretical, uses a reduced one-dimensional model of a reactor-scale tokamak, and uses no experimental data.")
para("Main results", bold=True, after=3)
bullet("*Well-posedness.* The local closure, whose shearing rate contains the second derivative of the temperature, is ill posed: its converged answer depends on how the edge is treated (%.0f%% apart at a threshold of 0.05 for two natural edge conditions), "
       "and a grid-scale instability appears at a threshold that grows as N^{%.2f} with the number of cells N, so that every finite threshold becomes unstable at fine resolution. A first-order edge treatment hides this and produces a spurious fold. "
       "An adaptive-field closure that smooths the shearing rate over a fixed length is well posed, converges at second order, and is insensitive to the length (%.1f%% over a tenfold range)."
       % (100 * abs(EV["local, edge value held"]["Q@0.05/N400"] / EV["local, no suppression in the last cell"]["Q@0.05/N400"] - 1), LC["threshold_exponent"],
          100 * (max(EV["smoothed, l = %s m" % x]["Q@0.1/N400"] for x in ("0.02", "0.05", "0.10", "0.20")) / min(EV["smoothed, l = %s m" % x]["Q@0.1/N400"] for x in ("0.02", "0.05", "0.10", "0.20")) - 1)))
bullet("*Closed-form admissibility conditions* for a shear-dependent viscosity in the rotation equation (m ≤ 1 for 1/(1 + Λ^{m}); floors 1/9 and %.4f), with the predicted saturation, fold, and hysteresis window, "
       "reproduced by direct solutions to a relative error of %.0e." % (R["theory"]["thresholds"]["floor_exp"], R["scalar_flux_relation_summary"]["max_rel_err"]))
bullet("*A gain law and its uncertainty.* The smoothed closure raises the fusion gain by %.2f%% at a suppression threshold of 0.3 and %.1f%% at 0.1, following ΔQ/Q = %.3f%%/s_{c}²; a Sobol study over seven parameters gives the spread, and the baseline reproduces the "
       "ITER89-P L-mode scaling (H_{89} = %.2f)." % (100 * TB[0.3]["dQ"], 100 * TB[0.1]["dQ"], 100 * LR["C_mean"] / TB["base"]["Q"], TB["base"]["H89"]))
bullet("*Physical calibration* (Section VI) against confinement scalings, the Greenwald and Troyon limits, and neutral-beam torque: at the estimated torque of a reactor-scale device (%.0f N m) the torque-driven gain is about %.1f%% (threshold 0.5)."
       % (R["calibration"]["nbi_torque"]["5.3"], 100 * (CST[0.5][36.0] / CST[0.5][0.0] - 1)))
para("Fit to the journal", bold=True, after=3)
para("The paper concerns transport modelling for fusion devices and the numerical reliability of the closures used in it; it states what has and has not been established and keeps the claims no stronger than the checks. "
     "A supplementary file contains the proofs, the numerical protocol, and extended tables.")
para("Code, data, and declarations", bold=True, after=3)
para("All code, tests, raw results, and figure scripts are public at %s (release %s) and archived at https://doi.org/%s; the manuscript is available as a preprint at https://doi.org/%s. Reproducing every number takes under an hour. "
     "In line with IEEE policy, the use of artificial intelligence is disclosed in the Acknowledgment: Claude Sonnet 5.5 (Anthropic; model identifier claude-sonnet-5-5), accessed through the Claude Code environment of the Claude desktop application, was used between 7 and 9 October 2026 "
     "for code, derivations, numerical experiments, figures, and drafting; I reviewed and edited all content, checked every reference against Crossref, and take full responsibility for the paper. I am the sole author, have no conflicts of interest, and received no funding. "
     "The manuscript has not been published in a journal and is not under consideration elsewhere. An earlier version of the preprint (https://doi.org/%s) reported a steady-state fold that I have since shown to be an artifact of a first-order edge treatment; it is superseded by the version cited above." % (REPO, RELEASE, SW, PP, ZEN["publication"]["doi"]))
para("Thank you for considering the paper.")
para("Yours sincerely,", after=18)
para("Leon Sandler")
out = os.path.join(HERE, "out", "Cover_Letter_IEEE_TPS.docx")
doc.save(out)
print("saved", out)
