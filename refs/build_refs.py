# -*- coding: utf-8 -*-
"""Harvest every journal reference from Crossref by DOI and format it in Journal of Plasma Physics style (author-year, all authors listed).   python build_refs.py"""
import json
import re
import time
import urllib.request

DOIS = {
    "bosch1992": "10.1088/0029-5515/32/4/i07",
    "dimits2000": "10.1063/1.873896",
    "kotschenreuther1995": "10.1063/1.871261",
    "biglari1990": "10.1063/1.859529",
    "burrell1997": "10.1063/1.872367",
    "hahm1995": "10.1063/1.871313",
    "terry2000": "10.1103/revmodphys.72.109",
    "perona1990": "10.1109/34.56205",
    "waltz1994": "10.1063/1.870934",
    "itoh1988": "10.1103/physrevlett.60.2276",
    "hinton1991": "10.1063/1.859866",
    "iter1999": "10.1088/0029-5515/39/12/302",
}
BOOKS = {
    "freidberg2014": dict(authors=["Freidberg, J. P."], year=2014, text="Freidberg, J. P. 2014 Ideal MHD. Cambridge University Press."),
    "wesson2011": dict(authors=["Wesson, J."], year=2011, text="Wesson, J. 2011 Tokamaks, 4th edn. Oxford University Press."),
}
JOURNAL = {"Physics of Plasmas": "Phys. Plasmas", "Nuclear Fusion": "Nucl. Fusion", "Physics of Fluids B: Plasma Physics": "Phys. Fluids B", "Reviews of Modern Physics": "Rev. Mod. Phys.",
           "Physical Review Letters": "Phys. Rev. Lett.", "IEEE Transactions on Pattern Analysis and Machine Intelligence": "IEEE Trans. Pattern Anal. Mach. Intell."}


def initials(given):
    parts = re.split(r"[\s\-]+", given.replace(".", " ").strip())
    return " ".join(p[0] + "." for p in parts if p)


def clean(t):
    t = re.sub(r"<[^>]+>", "", t)
    return re.sub(r"\s+", " ", t).strip()


out = {}
for key, doi in DOIS.items():
    r = json.load(urllib.request.urlopen(urllib.request.Request("https://api.crossref.org/works/" + doi, headers={"User-Agent": "refbuild/1.0 (mailto:sandler.leon@gmail.com)"}), timeout=60))["message"]
    authors = [(a.get("family", ""), a.get("given", "")) for a in r.get("author", []) if a.get("family")]
    if key == "iter1999":
        authors = []
    title = clean((r.get("title") or [""])[0]).replace("E×B", "E×B")
    jr = (r.get("container-title") or [""])[0]
    jr = JOURNAL.get(jr, jr)
    vol, page = r.get("volume"), r.get("page") or r.get("article-number")
    year = r["issued"]["date-parts"][0][0]
    names = ["%s, %s" % (f, initials(g)) for f, g in authors]
    names = [n.replace("Bosch, H. S.", "Bosch, H.-S.").replace("Itoh, S. I.", "Itoh, S.-I.") for n in names]
    if key == "itoh1988":
        title = "Model of L to H-mode transition in tokamak"
    if key == "iter1999":
        title = "ITER Physics Basis, chapter 2: plasma confinement and transport"
    if key == "iter1999":
        names = ["ITER Physics Expert Group on Confinement and Transport", "ITER Physics Expert Group on Confinement Modelling and Database", "ITER Physics Basis Editors"]
    if len(names) > 1:
        who = ", ".join(names[:-1]) + " & " + names[-1]
    else:
        who = names[0]
    if page and "-" in page:
        page = page.replace("-", "–")
    txt = "%s %d %s. %s %s, %s. https://doi.org/%s" % (who, year, title.rstrip("."), jr, vol, page, r["DOI"]) if jr else ""
    out[key] = dict(doi=r["DOI"], year=year, first=(authors[0][0] if authors else "ITER Physics Expert Group"), n_authors=len(authors) if key != "iter1999" else 3, authors=[f for f, g in authors] if key != "iter1999" else ["ITER Physics Expert Group"], text=txt)
    print(key, "|", txt[:200])
    time.sleep(0.3)
for key, b in BOOKS.items():
    out[key] = dict(doi=None, year=b["year"], first=b["authors"][0].split(",")[0], n_authors=1, authors=[b["authors"][0].split(",")[0]], text=b["text"])
json.dump(out, open("refs_cache.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(len(out), "references written")
