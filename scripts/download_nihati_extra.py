"""Download the NIHATI classes the app has not used so far (onychomycosis, psoriasis) for the 2026-10-18 scope change.

Same Roboflow project family and CC BY 4.0 source already audited as `nail-disease-classification-nihati`
(project mohit-fc0fl/nail-disease-classification-f7gwn has identical class counts). No exportable version is used;
images come from Project.search()/Project.image() like the earlier NIHATI pull. 8 parallel workers, resumable
(.part -> rename). Output: E:/NailIQ_data/raw/nihati_extra/<class>/<id>.<ext> + manifest.csv (id, class, split, name).

Run from repo root: backend/venv/Scripts/python.exe scripts/download_nihati_extra.py
"""
import csv, os, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv

REPO = Path(__file__).resolve().parent.parent
load_dotenv(REPO / "backend" / ".env")
from roboflow import Roboflow  # noqa: E402

OUT = Path("E:/NailIQ_data/raw/nihati_extra")
CLASSES = ("onychomycosis", "psoriasis")


def listing(proj, cls):
    rows, offset = [], 0
    while True:
        page = proj.search(class_name=cls, limit=100, offset=offset, fields=["id", "name", "labels", "split"])
        if not page:
            return rows
        rows += [r for r in page if cls in (r.get("labels") or [])]
        offset += len(page)
        if len(page) < 100:
            return rows


def fetch(args):
    proj, cls, r = args
    info = proj.image(r["id"])
    url = (info.get("urls") or {}).get("original") or info.get("image", {}).get("urls", {}).get("original") or info.get("urls", {}).get("thumb")
    if not url:
        return r["id"], "no_url"
    ext = Path(r["name"]).suffix.lower() or ".png"
    dest = OUT / cls / f"{r['id']}{ext}"
    if dest.exists():
        return r["id"], "exists"
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    urllib.request.urlretrieve(url, part)
    part.rename(dest)
    return r["id"], "ok"


def main():
    rf = Roboflow(api_key=os.environ["ROBOFLOW_API_KEY"])
    proj = rf.workspace("mohit-fc0fl").project("nail-disease-classification-f7gwn")
    todo, manifest = [], []
    for cls in CLASSES:
        rows = listing(proj, cls)
        print(cls, len(rows), flush=True)
        manifest += [[r["id"], cls, r.get("split"), r["name"]] for r in rows]
        todo += [(proj, cls, r) for r in rows]
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "manifest.csv", "w", newline="") as f:
        csv.writer(f).writerows([["id", "class", "split", "name"]] + manifest)
    stats = {}
    with ThreadPoolExecutor(8) as ex:
        for i, (_, status) in enumerate(ex.map(fetch, todo)):
            stats[status] = stats.get(status, 0) + 1
            if (i + 1) % 100 == 0:
                print(" ", i + 1, "/", len(todo), flush=True)
    print(stats)


if __name__ == "__main__":
    main()
