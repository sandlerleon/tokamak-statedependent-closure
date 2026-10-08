# -*- coding: utf-8 -*-
"""Publish the two Zenodo records reserved by zenodo_reserve.py:

  software     the tagged GitHub release as a zip (MIT)
  preprint     the manuscript (docx only; no PDFs are deposited) (CC BY 4.0)

The DOIs were reserved first so that they could be written into the manuscript and the cover letter. The token is read from ZENODO_TOKEN and never written to disk.

    python zenodo_publish.py software|preprint [--version=1.0.0] [--dry]
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
VERSION = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--version=")), "1.0.0")
TAG = "v" + VERSION
DRY = "--dry" in sys.argv
GITHUB = "https://github.com/sandlerleon/tokamak-statedependent-closure"
CREATORS = [{"name": "Sandler, Leon", "affiliation": "Independent Researcher", "orcid": "0009-0007-4584-808X"}]
TITLE_PAPER = "State-dependent shear-suppression closures for reduced tokamak transport: a controlled comparison, admissibility conditions and a fold of the steady state"
TITLE_CODE = "State-dependent shear-suppression closures for reduced tokamak transport: model, solvers, tests, figures and manuscript"
KEYWORDS = ["tokamak transport", "E×B shear suppression", "critical-gradient model", "stiff transport", "reduced model", "saddle-node bifurcation", "fusion gain",
            "toroidal rotation", "flux closure admissibility", "verification"]
ABOUT = """<p><strong>A computational and theoretical paper. No experimental data are used and all parameters are illustrative.</strong> Prepared for submission to the <em>Journal of Plasma Physics</em>.
A one-dimensional radial energy-transport model with fusion heating and a toroidal-rotation equation is used to compare a state-dependent shear-suppression closure (heat diffusivity divided by
1 + (omega_E / s_c gamma_0)^2) with a stiff critical-gradient baseline at identical inputs. The solver is verified by power balance, recovery of the baseline as s_c tends to infinity, independent time integration
and grid convergence. With diamagnetic shear alone the fusion gain changes by well under one per cent at moderate coupling; the lower branch of steady states ends in a saddle-node fold at s_c* = 0.047
(extrapolated in resolution), below which no steady state exists. For the rotation equation with a shear-dependent viscosity, the steady flux relation F(L) L = Theta reduces existence, saturation, fold and hysteresis
to the monotonicity of L F(L), with closed-form thresholds (m &le; 1; floors 1/9 and 0.3086) that direct solutions reproduce. Torque-driven shear adds to the diamagnetic shear in a one-way coupling.</p>"""
DESC_CODE = ABOUT + """<p>Contents: model and solvers (<code>code/model.py</code>, <code>stability.py</code>, <code>arclength.py</code>), rotation equation and coupling (<code>momentum.py</code>, <code>coupled.py</code>),
closed forms (<code>theory.py</code>), the script that produces every result (<code>reproduce.py</code>), 38 tests (<code>tests.py</code>), figure scripts, the Crossref reference harvest and the manuscript builders.
Manuscript preprint: <a href="https://doi.org/{PP}">{PP}</a>.</p>"""
DESC_PAPER = ABOUT + """<p>Code and results: <a href="%s">%s</a>, archived at <a href="https://doi.org/{SW}">{SW}</a>.</p>""" % (GITHUB, GITHUB)


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
    d = st["software"]
    tmp = os.path.join(os.environ.get("TEMP", "."), "tokamak-statedependent-closure-%s.zip" % VERSION)
    subprocess.check_call(["git", "-C", REPO, "archive", "--format=zip", "--prefix=tokamak-statedependent-closure-%s/" % VERSION, "-o", tmp, TAG])
    print("=== software draft %s (reserved DOI %s)" % (d["id"], d["doi"]))
    upload(d["bucket"], tmp, os.path.basename(tmp))
    meta = {"title": TITLE_CODE, "upload_type": "software", "description": DESC_CODE.replace("{PP}", st["publication"]["doi"]),
            "creators": CREATORS, "keywords": KEYWORDS, "access_right": "open", "license": "mit-license", "version": VERSION, "language": "eng",
            "prereserve_doi": {"doi": d["doi"]},
            "related_identifiers": [{"identifier": GITHUB + "/tree/" + TAG, "relation": "isSupplementTo", "scheme": "url"},
                                    {"identifier": st["publication"]["doi"], "relation": "isSupplementTo", "scheme": "doi"}]}
    finish(d["id"], meta)


def preprint():
    st = json.load(open(STATE))
    d = st["publication"]
    print("=== preprint draft %s (reserved DOI %s)" % (d["id"], d["doi"]))
    name = "State_Dependent_Shear_Closures_JPP.docx"
    upload(d["bucket"], os.path.join(REPO, "manuscript", name), name)
    meta = {"title": TITLE_PAPER, "upload_type": "publication", "publication_type": "preprint", "description": DESC_PAPER.replace("{SW}", st["software"]["doi"]),
            "creators": CREATORS, "keywords": KEYWORDS, "access_right": "open", "license": "cc-by-4.0", "version": "1", "language": "eng", "prereserve_doi": {"doi": d["doi"]},
            "related_identifiers": [{"identifier": st["software"]["doi"], "relation": "isSupplementedBy", "scheme": "doi"},
                                    {"identifier": GITHUB, "relation": "isSupplementedBy", "scheme": "url"}]}
    finish(d["id"], meta)


if __name__ == "__main__":
    what = [a for a in sys.argv[1:] if not a.startswith("--")]
    if what == ["software"]:
        software()
    elif what == ["preprint"]:
        preprint()
    else:
        raise SystemExit("usage: zenodo_publish.py software|preprint [--version=] [--dry]")
