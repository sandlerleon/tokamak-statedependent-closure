# -*- coding: utf-8 -*-
"""Harvest every journal reference from Crossref by DOI and format it in IEEE style (initials first, abbreviated journal, vol./no./pp., more than six authors -> et al.).
python build_refs.py   ->  refs_cache.json"""
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
    "waltz1994": "10.1063/1.870934",
    "itoh1988": "10.1103/physrevlett.60.2276",
    "hinton1991": "10.1063/1.859866",
    "iter1999": "10.1088/0029-5515/39/12/302",
    "yushmanov1990": "10.1088/0029-5515/30/10/001",
    "troyon1984": "10.1088/0741-3335/26/1a/319",
    "greenwald2002": "10.1088/0741-3335/44/8/201",
    "paul2017": "10.1088/1741-4326/aa7fa4",
    "perona1990": "10.1109/34.56205",
}
BOOKS = {
    "freidberg2014": "J. P. Freidberg, Ideal MHD. Cambridge, U.K.: Cambridge Univ. Press, 2014.",
    "wesson2011": "J. Wesson, Tokamaks, 4th ed. Oxford, U.K.: Oxford Univ. Press, 2011.",
}
JOURNAL = {"Physics of Plasmas": "Phys. Plasmas", "Nuclear Fusion": "Nucl. Fusion", "Physics of Fluids B: Plasma Physics": "Phys. Fluids B", "Reviews of Modern Physics": "Rev. Mod. Phys.",
           "Physical Review Letters": "Phys. Rev. Lett.", "IEEE Transactions on Pattern Analysis and Machine Intelligence": "IEEE Trans. Pattern Anal. Mach. Intell.",
           "Plasma Physics and Controlled Fusion": "Plasma Phys. Control. Fusion"}
TITLE_FIX = {"itoh1988": "Model of L to H-mode transition in tokamak", "iter1999": "Chapter 2: Plasma confinement and transport"}


def initials(given):
    parts = re.split(r"[\s]+", given.replace(".", ". ").strip())
    out = []
    for p in parts:
        if not p:
            continue
        out.append("-".join(q[0] + "." for q in p.split("-") if q) if "-" in p else p[0] + ".")
    return " ".join(out)


def clean(t):
    t = re.sub(r"<[^>]+>", "", t)
    return re.sub(r"\s+", " ", t).strip()


out = {}
for key, doi in DOIS.items():
    r = json.load(urllib.request.urlopen(urllib.request.Request("https://api.crossref.org/works/" + doi, headers={"User-Agent": "refbuild/1.0 (mailto:sandler.leon@gmail.com)"}), timeout=60))["message"]
    authors = [(a.get("family", ""), a.get("given", "")) for a in r.get("author", []) if a.get("family")]
    title = TITLE_FIX.get(key, clean((r.get("title") or [""])[0]))
    jr = JOURNAL.get((r.get("container-title") or [""])[0], (r.get("container-title") or [""])[0])
    vol, issue, page = r.get("volume"), r.get("issue"), r.get("page") or r.get("article-number")
    year = r["issued"]["date-parts"][0][0]
    if key == "iter1999":
        who = "ITER Physics Expert Group on Confinement and Transport et al."
        first, nA = "ITER Physics Expert Group", 3
    else:
        names = ["%s %s" % (initials(g), f) for f, g in authors]
        names = [n.replace("H. S. Bosch", "H.-S. Bosch") for n in names]
        names = [n.replace("S. I. Itoh", "S.-I. Itoh") for n in names]
        if len(names) > 6:
            who = names[0] + " et al."
        elif len(names) > 2:
            who = ", ".join(names[:-1]) + ", and " + names[-1]
        elif len(names) == 2:
            who = names[0] + " and " + names[1]
        else:
            who = names[0]
        first, nA = authors[0][0], len(authors)
    loc = ""
    if page:
        page = page.replace("-", "–")
        loc = ("pp. %s" % page) if ("–" in page) else ("Art. no. %s" % page)
    parts = ['%s, "%s," %s' % (who, title.rstrip("."), jr)]
    if vol:
        parts.append("vol. %s" % vol)
    if issue:
        parts.append("no. %s" % issue)
    if loc:
        parts.append(loc)
    parts.append(str(year))
    txt = ", ".join(parts) + ", doi: %s." % r["DOI"]
    out[key] = dict(doi=r["DOI"], year=year, first=first, n_authors=nA, authors=[f for f, g in authors] if key != "iter1999" else ["ITER Physics Expert Group"], text=txt)
    print(key, "|", txt[:230])
    time.sleep(0.3)
for key, txt in BOOKS.items():
    out[key] = dict(doi=None, year=int(re.findall(r"(\d{4})\.$", txt)[0]), first=txt.split(",")[0], n_authors=1, authors=[txt.split(",")[0]], text=txt)
json.dump(out, open("refs_cache.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(len(out), "references written")
