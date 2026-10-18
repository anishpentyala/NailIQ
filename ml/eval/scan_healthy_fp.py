"""Scan known-healthy nail photos through the real /analyze path and count false positives.

Healthy = images whose only label is 'healthy' (all sources, valid+test splits, authorized + shape sources).
Side photo is blank (top-photo conditions only; clubbing/koilonychia come from the appearance route).
Reports, per condition, the verdict the USER SEES ('shown') and the pre-policy verdict, plus the share of
healthy nails that get at least one visible "outside" flag, per source.

Run from repo root: ml/venv/Scripts/python.exe ml/eval/scan_healthy_fp.py [--splits valid test]
"""
import argparse, base64, json, sys
from collections import Counter, defaultdict
from pathlib import Path

import cv2, numpy as np

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "backend"))

from ml.eval.eval_color_sensitivity import b64, create_eval_client          # noqa: E402
from ml.eval.eval_end_to_end import gather                                    # noqa: E402
from ml.eval.eval_onycholysis_specialist_e2e import source_of                 # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", nargs="+", default=["valid", "test"])
    ap.add_argument("--out", type=Path, default=REPO / "ml" / "eval" / "healthy_fp_scan.json")
    args = ap.parse_args()
    app_module, _ = create_eval_client()
    app_module._rate_limited = lambda ip: False
    with app_module.app.app_context():
        app_module.db.create_all()
    client = app_module.app.test_client()
    _, buf = cv2.imencode(".jpg", np.full((64, 64, 3), 128, np.uint8))
    side = base64.b64encode(buf).decode()

    items = {}
    for sp in args.splits:
        for p, labels in gather(sp, include_authorized=True, include_shapes=True).items():
            if labels == {"healthy"}:
                items[p] = sp
    print(f"healthy images: {len(items)}", flush=True)

    per = defaultdict(lambda: defaultdict(Counter))      # source -> condition -> verdict counter (shown)
    pre = defaultdict(Counter)                           # condition -> pre-policy verdict counter
    any_flag = Counter(); n_src = Counter(); abstained = Counter(); flagged_files = defaultdict(list)
    for i, (p, sp) in enumerate(sorted(items.items(), key=lambda kv: str(kv[0]))):
        raw = b64(p)
        if raw is None:
            continue
        r = client.post("/analyze", json={"side_image": side, "top_image": raw})
        if r.status_code != 200:
            raise SystemExit(f"HTTP {r.status_code} on {p}")
        src = source_of(p); n_src[src] += 1
        fs = r.get_json()["findings"]
        flags = []
        for f in fs:
            if f["label"] == "clubbing":
                continue                                  # side geometry, not scored here
            per[src][f["label"]][f["verdict"]] += 1
            pre[f["label"]][f.get("unvalidated_verdict") or f["verdict"]] += 1
            if f["verdict"] == "outside":
                flags.append(f["label"])
        if flags:
            any_flag[src] += 1
            flagged_files[src].append({"path": str(p.relative_to(REPO)), "flags": flags})
        if all(f["verdict"] == "inconclusive" for f in fs if f["label"] != "clubbing"):
            abstained[src] += 1
        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(items)}", flush=True)

    conds = sorted({c for s in per.values() for c in s})
    tot = sum(n_src.values())
    print(f"\nHealthy images scanned: {tot}  by source: {dict(n_src)}")
    print("\nVisible 'outside' rate on healthy nails (what a user would see):")
    summary = {}
    for c in conds:
        n = sum(sum(per[s][c].values()) for s in per); o = sum(per[s][c]["outside"] for s in per)
        po = pre[c]["outside"]
        by = {s: f"{per[s][c]['outside']}/{sum(per[s][c].values())}" for s in per}
        summary[c] = {"shown_outside": o, "n": n, "fp": round(o / n, 3), "pre_policy_outside": po, "by_source": by}
        print(f"  {c:22s} {o:4d}/{n} = {o / n:6.1%}   (pre-policy {po / n:6.1%})  {by}")
    flagged = sum(any_flag.values())
    print(f"\nHealthy nails with at least one visible flag: {flagged}/{tot} = {flagged / tot:.1%}")
    print("  by source:", {s: f"{any_flag[s]}/{n_src[s]}" for s in n_src})
    print("Healthy nails where every condition abstained:", dict(abstained))
    json.dump({"n": tot, "by_source": dict(n_src), "per_condition": summary,
               "any_flag": dict(any_flag), "all_abstained": dict(abstained), "flagged": flagged_files},
              open(args.out, "w"), indent=1)


if __name__ == "__main__":
    main()
