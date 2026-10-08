# -*- coding: utf-8 -*-
"""Create the two Zenodo drafts (software and preprint) and pre-reserve their DOIs, so that the DOIs can be written into
the manuscript before anything is published. State (ids, DOIs, upload buckets; no token) goes to
C:\YouTube\_tok_zenodo_state.json. The token is read from ZENODO_TOKEN and never written to disk."""
import json
import os
import urllib.request

TOKEN = os.environ["ZENODO_TOKEN"]
STATE = os.path.join("C:" + os.sep, "YouTube", "_tok_zenodo_state.json")
if os.path.exists(STATE):
    raise SystemExit("already reserved: " + open(STATE).read())
out = {}
for kind in ("software", "publication"):
    req = urllib.request.Request("https://zenodo.org/api/deposit/depositions", method="POST",
                                 data=json.dumps({"metadata": {"upload_type": kind, "prereserve_doi": True}}).encode(),
                                 headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"})
    dep = json.load(urllib.request.urlopen(req, timeout=60))
    out[kind] = {"id": dep["id"], "doi": dep["metadata"]["prereserve_doi"]["doi"], "bucket": dep["links"]["bucket"],
                 "concept_doi": "10.5281/zenodo.%s" % dep.get("conceptrecid")}
json.dump(out, open(STATE, "w"), indent=1)
print(json.dumps({k: {kk: v[kk] for kk in ("id", "doi", "concept_doi")} for k, v in out.items()}, indent=1))
