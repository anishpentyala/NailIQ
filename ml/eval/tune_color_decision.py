"""Choose the color track's per-condition decision rule on VALID, score it once on TEST.

Input: per-image caches from eval_end_to_end.py (--cache) holding the CNN's full
probability vector and the classical heuristic's verdict for every image. Candidates
are replayed through the PRODUCTION functions -- color_classifier.opinion_from_probs and
color_fusion._fuse_one -- with only their module-level tables patched, so a chosen
rule is exactly what /analyze will do once those tables are set.

Step 0 (parity): replaying the shipped tables must reproduce every cached verdict
(/analyze rounds probs to 3 decimals, so top probs within 0.001 of a cutoff are counted
separately) -- otherwise the simulation isn't the pipeline.

Per condition C the search covers (C's verdict depends only on these, so conditions are
optimized independently):
  floor   CLASS_CONFIDENCE_THRESHOLD[C]      top-class vote cutoff
  ovr     color_fusion.OVR_THRESHOLD[C]      p(C) vote even when C isn't the top class
  support color_fusion.HEURISTIC_MIN_CNN_SUPPORT[C]  min p(C) for heuristic-only "outside"

Metrics are STRICT so abstaining can't game them: recall = outside / all positives
(an inconclusive positive counts as a miss); FP = outside / all healthy images.
Selection, in order:
  1. new abstentions on healthy images may only replace false alarms: extra healthy
     abstention <= FP reduction + ABSTAIN_SLACK (an abstention is better than a false
     alarm, but a rule may not abstain on healthy nails it used to get right)
  2. if any reach FP <= MAX_FP_RATE: highest recall among them
  3. else: highest Youden J (recall - FP) among candidates with FP <= shipped FP
Ties -> fewer outside calls on healthy, then fewer changed tables, then higher cutoffs.

Then the VALIDATION POLICY (ml/infer/validation_policy.py): a condition may only give
verdicts if its chosen rule reaches recall >= MIN_RECALL and FP <= MAX_POLICY_FP on
VALID (a 95%-specificity screening bar); otherwise it is marked unvalidated.

Selecting among many candidates on small valid counts is optimistic by construction;
the TEST columns (never used for selection) are the honest numbers.

    backend/venv/Scripts/python.exe ml/eval/tune_color_decision.py \
        --valid ml/eval/e2e_valid_baseline.json --test ml/eval/e2e_test_baseline.json
"""
import argparse
import itertools
import json
import sys
from contextlib import contextmanager
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

from ml.infer import color_classifier, color_fusion  # noqa: E402

MAX_FP_RATE = 0.03
ABSTAIN_SLACK = 0.02
MIN_RECALL = 0.50
MAX_POLICY_FP = 0.05
FLOORS = [None] + [round(0.25 + 0.05 * i, 2) for i in range(14)]  # None = shipped value
OVRS = [None, 0.15, 0.2, 0.25, 0.3, 0.4]
SUPPORTS = [None, 0.02, 0.05, 0.1, 0.2]


@contextmanager
def patched(condition, floor, ovr, support):
    saved = (dict(color_classifier.CLASS_CONFIDENCE_THRESHOLD), dict(color_fusion.OVR_THRESHOLD),
             dict(color_fusion.HEURISTIC_MIN_CNN_SUPPORT))
    try:
        for table, value in ((color_classifier.CLASS_CONFIDENCE_THRESHOLD, floor),
                             (color_fusion.OVR_THRESHOLD, ovr),
                             (color_fusion.HEURISTIC_MIN_CNN_SUPPORT, support)):
            if value is not None:
                table[condition] = value
        yield
    finally:
        color_classifier.CLASS_CONFIDENCE_THRESHOLD.clear(); color_classifier.CLASS_CONFIDENCE_THRESHOLD.update(saved[0])
        color_fusion.OVR_THRESHOLD.clear(); color_fusion.OVR_THRESHOLD.update(saved[1])
        color_fusion.HEURISTIC_MIN_CNN_SUPPORT.clear(); color_fusion.HEURISTIC_MIN_CNN_SUPPORT.update(saved[2])


def replay(r, c):
    f = r["findings"][c]
    if c not in color_classifier.app_conditions() or not r["probs"]:
        return f["verdict"]
    failure = f["failure_reason"] if f["heuristic"] == "inconclusive" else None
    heur = {"label": c, "display_name": "", "value": None, "unit": None,
            "verdict": f["heuristic"], "confidence": 0.5, "failure_reason": failure}
    return color_fusion._fuse_one(heur, color_classifier.opinion_from_probs(r["probs"]))["verdict"]


def strict(records, c):
    pos = [replay(r, c) for r in records if c in r["labels"] and c in r["findings"]]
    hea = [replay(r, c) for r in records if r["labels"] == ["healthy"] and c in r["findings"]]
    frac = lambda v, k: v.count(k) / len(v) if v else None  # noqa: E731
    return {"recall": frac(pos, "outside"), "fp": frac(hea, "outside"),
            "abstain_pos": frac(pos, "inconclusive"), "abstain_healthy": frac(hea, "inconclusive"),
            "n_pos": len(pos), "n_healthy": len(hea)}


def parity(records):
    bad, rounding = [], 0
    for r in records:
        for c, f in r["findings"].items():
            if replay(r, c) == f["verdict"]:
                continue
            p = r["probs"] or {}
            top = max(p, key=p.get) if p else None
            cut = color_classifier.CLASS_CONFIDENCE_THRESHOLD.get(top, color_classifier.CONFIDENCE_THRESHOLD)
            if top and abs(p[top] - cut) <= 0.001:
                rounding += 1
            else:
                bad.append((r["path"], c))
    return bad, rounding


def tune_condition(valid, c):
    base = strict(valid, c)
    cands = []
    for floor, ovr, support in itertools.product(FLOORS, OVRS, SUPPORTS):
        with patched(c, floor, ovr, support):
            m = strict(valid, c)
        if m["recall"] is None or m["fp"] is None:
            continue
        extra_abstain = m["abstain_healthy"] - base["abstain_healthy"]
        if extra_abstain > (base["fp"] - m["fp"]) + ABSTAIN_SLACK + 1e-9:
            continue
        cands.append(((floor, ovr, support), m))

    def tiebreak(cfg):
        return (-sum(v is not None for v in cfg), tuple(-1 if v is None else v for v in cfg))
    under_cap = [x for x in cands if x[1]["fp"] <= MAX_FP_RATE + 1e-9]
    if under_cap:
        pick = max(under_cap, key=lambda x: (x[1]["recall"], -x[1]["fp"], tiebreak(x[0])))
    else:
        ok = [x for x in cands if x[1]["fp"] <= base["fp"] + 1e-9]
        pick = max(ok, key=lambda x: (x[1]["recall"] - x[1]["fp"], -x[1]["fp"], tiebreak(x[0])))
    return pick[0], pick[1]


def pct(x):
    return "  n/a" if x is None else f"{x:5.1%}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--valid", type=Path, required=True)
    ap.add_argument("--test", type=Path)
    ap.add_argument("--out", type=Path, help="write chosen tables as JSON")
    args = ap.parse_args()
    valid = json.loads(args.valid.read_text())
    test = json.loads(args.test.read_text()) if args.test else None

    bad, rounding = parity(valid)
    print(f"parity: {len(bad)} mismatches, {rounding} at-cutoff rounding cases" + (f" e.g. {bad[:3]}" if bad else ""))
    if bad:
        raise SystemExit("simulation does not match the pipeline -- fix before tuning")

    chosen, unvalidated = {}, []
    print(f"\n{'condition':21s} {'(floor, ovr, support)':>22s} | split  recall  FP   abstain(pos/healthy) | shipped recall  FP   abstain")
    for c in color_classifier.app_conditions():
        cfg, vm = tune_condition(valid, c)
        chosen[c] = cfg
        if vm["recall"] < MIN_RECALL or vm["fp"] > MAX_POLICY_FP:
            unvalidated.append(c)
        for name, recs in (("valid", valid), ("test", test)):
            if recs is None:
                continue
            b = strict(recs, c)
            with patched(c, *cfg):
                t = strict(recs, c)
            print(f"{c:21s} {str(cfg):>22s} | {name:5s} {pct(t['recall'])} {pct(t['fp'])} "
                  f"{pct(t['abstain_pos'])}/{pct(t['abstain_healthy'])} | "
                  f"      {pct(b['recall'])} {pct(b['fp'])} {pct(b['abstain_pos'])}/{pct(b['abstain_healthy'])}"
                  f"  (n_pos={t['n_pos']}, n_healthy={t['n_healthy']})")
    if args.out:
        args.out.write_text(json.dumps({"rules": chosen, "unvalidated": unvalidated}, indent=1))
    print("\nchosen (floor, ovr, support):", json.dumps(chosen))
    print(f"fails validation policy on VALID (recall < {MIN_RECALL:.0%} or FP > {MAX_POLICY_FP:.0%}):", unvalidated)


if __name__ == "__main__":
    main()
