# -*- coding: utf-8 -*-
"""Publish the two Zenodo records reserved by zenodo_reserve.py / zenodo_newversion.py:

  software     the tagged GitHub release as a zip (MIT)
  preprint     the manuscript and the supplementary material (docx only; no PDFs are deposited) (CC BY 4.0)

The DOIs were reserved first so that they could be written into the manuscript and the cover letter. The token is read from ZENODO_TOKEN and never written to disk.

    python zenodo_publish.py software|preprint [--version=1.1.0] [--ms=2] [--dry]
"""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

TOKEN = os.environ.get("ZENODO_TOKEN")
if not TOKEN:
    raise SystemExit("ZENODO_TOKEN is not set in the environment")
API = "https://zenodo.org/api"
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
STATE = os.path.join("C:" + os.sep, "YouTube", "_tok_zenodo_state.json")
VERSION = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--version=")), "1.1.0")
MS = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--ms=")), "2")
TAG = "v" + VERSION
DRY = "--dry" in sys.argv
GITHUB = "https://github.com/sandlerleon/tokamak-statedependent-closure"
CREATORS = [{"name": "Sandler, Leon", "affiliation": "Independent Researcher", "orcid": "0009-0007-4584-808X"}]
TITLE_PAPER = "Numerical Admissibility and Regularization of Shear-Suppression Closures for Reduced Tokamak Transport"
TITLE_CODE = "Numerical admissibility and regularization of shear-suppression closures for reduced tokamak transport: model, solvers, tests, figures and manuscript"
KEYWORDS = ["tokamak transport", "ExB shear suppression", "numerical admissibility", "regularization", "critical-gradient model", "stiff transport", "reduced model", "fusion gain",
            "toroidal rotation", "flux closure admissibility", "verification", "uncertainty quantification"]
ABOUT = """<p><strong>A computational and theoretical paper. No experimental data are used and all parameters are illustrative.</strong> Prepared for submission to <em>IEEE Transactions on Plasma Science</em>.
A one-dimensional radial energy-transport model with fusion heating and a toroidal-rotation equation is used to study closures in which the heat diffusivity is suppressed by the local ExB shearing rate.
The local closure, whose shearing rate contains the second derivative of the temperature, is numerically ill posed: the steady state depends on the edge treatment and a grid-scale instability appears at a threshold that grows as N^0.5 with the number
of cells. An adaptive-field closure that smooths the shearing rate over a fixed length is stable and grid converged over the tested conditions, converges at second order, and gives a fusion gain that is fitted by an inverse-square relation in the suppression threshold (an empirical fit over the tested range, not a universal scaling).
For the rotation equation, a steady flux relation F(L) L = Theta gives closed-form admissibility conditions (m &le; 1; viscosity floors 1/9 and 0.3086) and the saturation, fold and hysteresis, reproduced by direct solutions to a relative error of 5e-11.
The baseline is compared with the ITER89-P and IPB98(y,2) scalings, operating limits and neutral-beam torque (a consistency check, not a validation, because the edge temperature is imposed), and a Sobol study quantifies parameter uncertainty.</p>"""
NEWVER_111 = ("<p><strong>Version %s.</strong> Wording revision of 1.1.0 after review: the title is changed, the well-posedness claims are qualified as numerical (no existence-uniqueness theorem is claimed for the nonlinear heat problem), "
              "the inverse-square gain relation is described as an empirical fit over the tested range, the ITER89-P agreement is stated to be a consistency check, and a discussion subsection on compact, cost-constrained tokamak design is added. "
              "Computed results are unchanged. Supersedes 1.1.0 and 1.0.0 (the latter reported a fold at s_c = 0.047 that is an artifact of a first-order edge treatment).</p>" % VERSION)
NEWVER = ("<p><strong>Version %s.</strong> Retargeted to IEEE Transactions on Plasma Science and extended after review. The earlier version (1.0.0) reported a steady-state fold at s_c = 0.047 that is an artifact of a first-order edge treatment of the shearing rate; "
          "this version treats the edge consistently at second order, shows that the local closure is ill posed, introduces the smoothed (adaptive-field) closure, adds a physical calibration, a parameter-uncertainty study and a supplementary file, and supersedes version 1.0.0.</p>" % VERSION)
if VERSION == "1.1.1":
    NEWVER = NEWVER_111
DESC_CODE = NEWVER + ABOUT + """<p>Contents: model and solvers (<code>code/model.py</code>, <code>stability.py</code>, <code>arclength.py</code>), rotation equation and coupling (<code>momentum.py</code>, <code>coupled.py</code>),
closed forms (<code>theory.py</code>), calibration (<code>calibration.py</code>), uncertainty study (<code>uncertainty.py</code>), the script that produces every result (<code>reproduce.py</code>), tests (<code>tests.py</code>), figure scripts,
the Crossref reference harvest and the manuscript builders. Manuscript preprint: <a href="https://doi.org/{PP}">{PP}</a>.</p>"""
DESC_PAPER = NEWVER.replace("Version %s" % VERSION, "Version %s" % MS) + ABOUT + """<p>Code and results: <a href="%s">%s</a>, archived at <a href="https://doi.org/{SW}">{SW}</a>.</p>""" % (GITHUB, GITHUB)


def req(method, url, data=None, headers=None, raw=None):
    h = {"Authorization": "Bearer " + TOKEN}
    if headers:
        h.update(headers)
    body = raw if raw is not None else (json.dumps(data).encode() if data is not None else None)
    if data is not None and raw is None:
        h["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=600) as resp:
            t = resp.read()
            return json.loads(t) if t else {}
    except urllib.error.HTTPError as e:
        raise SystemExit("%s %s -> %s\n%s" % (method, url, e.code, e.read().decode()[:800]))


def clear_inherited(d):
    for f in req("GET", "%s/deposit/depositions/%s/files" % (API, d["id"])):
        req("DELETE", "%s/deposit/depositions/%s/files/%s" % (API, d["id"], f["id"]))


def upload(bucket, path, name):
    with open(path, "rb") as fh:
        req("PUT", "%s/%s" % (bucket, urllib.parse.quote(name)), raw=fh.read(), headers={"Content-Type": "application/octet-stream"})
    print("   uploaded %-62s %9.1f kB" % (name, os.path.getsize(path) / 1024.0))


def finish(did, meta):
    req("PUT", "%s/deposit/depositions/%s" % (API, did), data={"metadata": meta})
    print("   metadata written")
    if DRY:
        print("   DRY RUN - draft %s left unpublished" % did)
        return
    pub = req("POST", "%s/deposit/depositions/%s/actions/publish" % (API, did))
    rec = req("GET", "%s/records/%s" % (API, pub["id"]))
    print("   PUBLISHED  DOI %s  concept %s" % (rec.get("doi"), rec.get("conceptdoi")))


def software():
    st = json.load(open(STATE))
    d = st.get("software_" + VERSION) or st["software"]
    tmp = os.path.join(os.environ.get("TEMP", "."), "tokamak-statedependent-closure-%s.zip" % VERSION)
    subprocess.check_call(["git", "-C", REPO, "archive", "--format=zip", "--prefix=tokamak-statedependent-closure-%s/" % VERSION, "-o", tmp, TAG])
    pdoi = (st.get("publication_v" + MS) or st["publication"])["doi"]
    print("=== software draft %s (reserved DOI %s)" % (d["id"], d["doi"]))
    clear_inherited(d)
    upload(d["bucket"], tmp, os.path.basename(tmp))
    meta = {"title": TITLE_CODE, "upload_type": "software", "description": DESC_CODE.replace("{PP}", pdoi), "creators": CREATORS, "keywords": KEYWORDS, "access_right": "open", "license": "mit-license",
            "version": VERSION, "language": "eng", "prereserve_doi": {"doi": d["doi"]},
            "related_identifiers": [{"identifier": GITHUB + "/tree/" + TAG, "relation": "isSupplementTo", "scheme": "url"}, {"identifier": pdoi, "relation": "isSupplementTo", "scheme": "doi"}]}
    finish(d["id"], meta)


def preprint():
    st = json.load(open(STATE))
    d = st.get("publication_v" + MS) or st["publication"]
    sdoi = (st.get("software_" + VERSION) or st["software"])["doi"]
    print("=== preprint draft %s (reserved DOI %s)" % (d["id"], d["doi"]))
    clear_inherited(d)
    for name in ("Admissibility_Shear_Closures_IEEE_TPS.docx", "Supplementary_Material_IEEE_TPS.docx"):
        upload(d["bucket"], os.path.join(REPO, "manuscript", name), name)
    meta = {"title": TITLE_PAPER, "upload_type": "publication", "publication_type": "preprint", "description": DESC_PAPER.replace("{SW}", sdoi), "creators": CREATORS, "keywords": KEYWORDS,
            "access_right": "open", "license": "cc-by-4.0", "version": MS, "language": "eng", "prereserve_doi": {"doi": d["doi"]},
            "related_identifiers": [{"identifier": sdoi, "relation": "isSupplementedBy", "scheme": "doi"}, {"identifier": GITHUB, "relation": "isSupplementedBy", "scheme": "url"}]}
    finish(d["id"], meta)


if __name__ == "__main__":
    what = [a for a in sys.argv[1:] if not a.startswith("--")]
    if what == ["software"]:
        software()
    elif what == ["preprint"]:
        preprint()
    else:
        raise SystemExit("usage: zenodo_publish.py software|preprint [--version=] [--ms=] [--dry]")
