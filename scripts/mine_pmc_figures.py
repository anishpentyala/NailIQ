"""Method 4 (2026-10-20): caption-mined open-access case-report figures from Europe PMC (CC BY / CC0 only).

For each sign, search Europe PMC full text for the sign's name restricted to open-access articles whose licence is
CC BY / CC0, fetch the article's full-text XML, and keep figures whose caption mentions exactly one target sign
family. Records article id, licence, caption and figure URL in a manifest; --download fetches the images.
No hand labelling: the label is the caption. Panels in a figure are NOT split here (the app's own nail front end is run
later); a figure may show several patients, so figures are the grouping unit for patient-level splits.

Run: ml/venv/Scripts/python.exe scripts/mine_pmc_figures.py [--download]
"""
import argparse, json, re, sys, time
from pathlib import Path
from xml.etree import ElementTree as ET

import requests

OUT = Path("C:/NailIQ_recovery/pmc_figs"); OUT.mkdir(parents=True, exist_ok=True)
API = "https://www.ebi.ac.uk/europepmc/webservices/rest"
SIGNS = {
    "terrys_nails": [r"terry'?s? nails?", r"terry'?s? nail sign"],
    "muehrckes_lines": [r"muehrcke'?s?", r"muehrcke'?s? (?:lines|nails|bands)"],
    "lindsays_nails": [r"half[- ]and[- ]half nails?", r"lindsay'?s? nails?"],
    "beaus_lines": [r"beau'?s? lines?", r"beau'?s? line"],
}
QUERY = {
    "terrys_nails": '("Terry\'s nails" OR "Terry nails")',
    "muehrckes_lines": '(Muehrcke OR "Muehrcke\'s lines")',
    "lindsays_nails": '("half-and-half nails" OR "Lindsay\'s nails" OR "half and half nail")',
    "beaus_lines": '("Beau\'s lines" OR "Beau lines")',
}
OK_LIC = re.compile(r"\bcc[ -]?by(?!-nc|-nd)|cc0|public domain", re.I)


def search(sign, page_size=200):
    q = f'{QUERY[sign]} AND OPEN_ACCESS:y AND (LICENSE:"cc by" OR LICENSE:"cc0")'
    r = requests.get(f"{API}/search", params={"query": q, "format": "json", "pageSize": page_size, "resultType": "lite"}, timeout=60)
    r.raise_for_status()
    return r.json().get("resultList", {}).get("result", [])


def figs_for(pmcid):
    r = requests.get(f"{API}/{pmcid}/fullTextXML", timeout=60)
    if r.status_code != 200:
        return None, []
    root = ET.fromstring(r.content)
    lic = ""
    for el in root.iter():
        if el.tag.endswith("license"):
            lic = " ".join(filter(None, [el.attrib.get("{http://www.w3.org/1999/xlink}href", ""), "".join(el.itertext())]))[:300]
            break
    figs = []
    for fig in root.iter("fig"):
        cap = " ".join("".join(fig.itertext()).split())
        g = next((e for e in fig.iter() if e.tag.endswith("graphic")), None)
        href = g.attrib.get("{http://www.w3.org/1999/xlink}href") if g is not None else None
        figs.append(dict(id=fig.attrib.get("id"), caption=cap[:600], href=href))
    return lic, figs


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--download", action="store_true"); a = ap.parse_args()
    manifest = []
    for sign in SIGNS:
        res = search(sign)
        print(sign, "articles:", len(res), flush=True)
        for rec in res:
            pmcid = rec.get("pmcid")
            if not pmcid:
                continue
            lic, figs = figs_for(pmcid)
            time.sleep(0.3)
            if lic is None or not OK_LIC.search(lic or rec.get("license", "") or ""):
                continue
            for f in figs:
                cap = f["caption"].lower()
                hits = [s for s, pats in SIGNS.items() if any(re.search(p, cap) for p in pats)]
                if hits == [sign] and f["href"]:
                    manifest.append(dict(sign=sign, pmcid=pmcid, license=lic[:120], fig=f["id"], caption=f["caption"], href=f["href"],
                                         url=f"https://europepmc.org/articles/{pmcid}/bin/{f['href']}.jpg"))
    json.dump(manifest, open(OUT / "manifest.json", "w"), indent=1)
    by = {}
    for m in manifest:
        by.setdefault(m["sign"], set()).add((m["pmcid"], m["fig"]))
    print({k: len(v) for k, v in by.items()}, flush=True)
    if a.download:
        (OUT / "img").mkdir(exist_ok=True)
        n = 0
        for m in manifest:
            dest = OUT / "img" / f"{m['sign']}__{m['pmcid']}_{m['fig']}.jpg"
            if dest.exists():
                continue
            r = requests.get(m["url"], timeout=60)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
                dest.write_bytes(r.content); n += 1
            time.sleep(0.3)
        print("downloaded", n, flush=True)


if __name__ == "__main__":
    main()
