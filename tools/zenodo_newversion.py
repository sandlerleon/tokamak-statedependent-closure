# -*- coding: utf-8 -*-
"""Open new-version drafts of the software and preprint records and pre-reserve their DOIs, so the DOIs can be written into the
manuscript before anything is published. Adds keys `software_<version>` and `publication_v<ms>` to C:\YouTube\_tok_zenodo_state.json.
The token is read from ZENODO_TOKEN and never written to disk.

    python zenodo_newversion.py 1.1.0 2
"""
import json
import os
import sys
import urllib.request

TOKEN = os.environ["ZENODO_TOKEN"]
STATE = os.path.join("C:" + os.sep, "YouTube", "_tok_zenodo_state.json")
API = "https://zenodo.org/api"
version, ms = sys.argv[1], sys.argv[2]
st = json.load(open(STATE))


def req(method, url):
    r = urllib.request.Request(url, method=method, headers={"Authorization": "Bearer " + TOKEN})
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.load(resp)


for kind, key in (("software", "software_" + version), ("publication", "publication_v" + ms)):
    if key in st:
        print("already reserved:", key)
        continue
    concept_rec = st[kind]["concept_doi"].split(".")[-1]
    latest = req("GET", "%s/records/%s/versions/latest" % (API, concept_rec))
    dep = req("POST", "%s/deposit/depositions/%s/actions/newversion" % (API, latest["id"]))
    draft = req("GET", dep["links"]["latest_draft"])
    st[key] = {"id": draft["id"], "doi": draft["metadata"]["prereserve_doi"]["doi"], "bucket": draft["links"]["bucket"],
               "inherited_files": [f["id"] for f in draft.get("files", [])], "parent": latest["id"], "concept_doi": st[kind]["concept_doi"]}
    json.dump(st, open(STATE, "w"), indent=1)
    print(key, st[key]["id"], st[key]["doi"], "inherited files:", len(st[key]["inherited_files"]))
