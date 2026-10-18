"""Audit public label metadata; never download images or authorize dataset access."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import io
import json
import re
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


SCIN_BASE = "https://storage.googleapis.com/dx-scin-public-data/dataset/"
MAX_REMOTE_BYTES = 4 * 1024 * 1024
MAX_LOCAL_BYTES = 32 * 1024 * 1024
SIGN_NAMES = {
    "clubbing": ("clubbing", "digital clubbing"),
    "koilonychia": ("koilonychia", "spoon nails"),
    "leukonychia": ("leukonychia",),
    "melanonychia": ("melanonychia",),
    "pallor": ("pallor", "nail pallor", "nailbed pallor", "nail bed pallor"),
    "cyanosis": ("cyanosis", "nail cyanosis", "nailbed cyanosis"),
    "terrys_nails": ("terry's nails", "terry nails"),
    "lindsays_nails": ("lindsay's nails", "lindsay nails", "half and half nails"),
    "onycholysis": ("onycholysis",),
    "beaus_lines": ("beau's lines", "beau lines"),
    "muehrckes_lines": ("muehrcke's lines", "muehrcke lines"),
    "splinter_hemorrhages": ("splinter hemorrhages", "splinter haemorrhages"),
    "pitting": ("nail pitting", "pitting"),
    "onychogryphosis": ("onychogryphosis",),
}


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def literal(value: str, expected: type):
    if not value or not value.strip():
        return expected()
    result = ast.literal_eval(value)
    if not isinstance(result, expected):
        raise ValueError(f"Expected {expected.__name__} in SCIN metadata")
    return result


def fetch_csv(filename: str) -> tuple[list[dict], dict]:
    url = SCIN_BASE + filename
    request = urllib.request.Request(url, headers={"User-Agent": "NailIQ-metadata-audit/1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        declared_size = response.headers.get("Content-Length")
        if declared_size and int(declared_size) > MAX_REMOTE_BYTES:
            raise ValueError(f"Metadata exceeds size limit: {filename}")
        raw = response.read(MAX_REMOTE_BYTES + 1)
    if len(raw) > MAX_REMOTE_BYTES:
        raise ValueError(f"Metadata exceeds size limit: {filename}")
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    if not rows or "case_id" not in rows[0]:
        raise ValueError(f"Missing case_id or empty metadata: {filename}")
    if len({row["case_id"] for row in rows}) != len(rows):
        raise ValueError(f"Duplicate case IDs in metadata: {filename}")
    return rows, {"url": url, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def audit_scin() -> dict:
    cases, cases_source = fetch_csv("scin_cases.csv")
    labels, labels_source = fetch_csv("scin_labels.csv")
    by_case = {row["case_id"]: row for row in cases}
    required = {"dermatologist_skin_condition_on_label_name", "dermatologist_skin_condition_confidence", "weighted_skin_condition_label"}
    if not required.issubset(labels[0]):
        raise ValueError("SCIN label schema changed; inspect before using")
    aliases = {normalized(alias): slug for slug, names in SIGN_NAMES.items() for alias in names}
    sign_counts = Counter({slug: 0 for slug in SIGN_NAMES})
    original_label_counts = Counter()
    matches = []
    for row in labels:
        case_id = row["case_id"]
        if case_id not in by_case:
            raise ValueError("SCIN label has no corresponding case")
        names = literal(row["dermatologist_skin_condition_on_label_name"], list)
        confidence = literal(row["dermatologist_skin_condition_confidence"], list)
        weights = literal(row["weighted_skin_condition_label"], dict)
        if len(names) != len(confidence) or not all(isinstance(name, str) for name in names):
            raise ValueError("SCIN names/confidence schema mismatch")
        for name in set(names):
            original_label_counts[name] += 1
        signs = sorted({aliases[normalized(name)] for name in names if normalized(name) in aliases})
        sign_counts.update(signs)
        if not signs:
            continue
        case = by_case[case_id]
        fields = [key for key in case if key.startswith("body_parts_") or key.startswith("image_")]
        matches.append({
            "case_id": case_id,
            "sign_mentions": signs,
            "original_labels": names,
            "original_confidence": confidence,
            "original_weighted_differential": weights,
            "public_site_metadata": {key: case.get(key, "") for key in ["related_category", *fields]},
            "clinical_eligible": False,
            "reason": "Differential possibilities are not exhaustive binary sign assessments; photos not reviewed.",
        })
    return {
        "sources": {"cases": cases_source, "labels": labels_source},
        "schema_url": "https://github.com/google-research-datasets/scin/blob/main/dataset_schema.md",
        "license_url": "https://github.com/google-research-datasets/scin/blob/main/LICENSE",
        "case_count": len(cases),
        "label_row_count": len(labels),
        "self_reported_nail_problem_count": sum(row.get("related_category") == "NAIL_PROBLEM" for row in cases),
        "exact_sign_aliases": SIGN_NAMES,
        "exact_sign_case_counts": dict(sign_counts),
        "matched_case_count": len(matches),
        "matched_cases": matches,
        "nail_word_label_counts": {name: count for name, count in sorted(original_label_counts.items()) if "nail" in name.lower() or "onycho" in name.lower()},
        "clinical_eligible": False,
        "missing_or_pending": [
            "No exhaustive per-sign negative labels; omitted differential terms do not mean absent.",
            "No image inspection, nail adequacy review, paired side-profile confirmation, or independent patient verification.",
            "Tiny differential-positive counts cannot establish condition accuracy or clear withholding.",
        ],
    }


def audit_sewa_local(paths: list[Path]) -> dict:
    result = {
        "card_url": "https://huggingface.co/datasets/sewa-rural-care/anemia-survey-data",
        "remote_access_attempted": False,
        "agreements_accepted": False,
        "clinical_eligible": False,
        "missing_or_pending": [
            "Access requires contact sharing and explicit acceptance of the source agreement.",
            "Nail examination vocabulary, assessor qualifications, sign-label completeness and agreement are unverified.",
            "Haemoglobin/anemia labels are not visible-pallor ground truth.",
            "Noncommercial research and no raw redistribution terms apply; public/commercial use needs separate review.",
        ],
        "local_metadata": [],
    }
    for path in paths:
        if not path.is_file() or path.stat().st_size > MAX_LOCAL_BYTES:
            raise ValueError("Local metadata must be a file no larger than 32 MiB")
        raw = path.read_bytes()
        suffix = path.suffix.lower()
        if suffix == ".csv":
            rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
        elif suffix == ".json":
            rows = json.loads(raw)
            if isinstance(rows, dict):
                rows = [rows]
        elif suffix == ".parquet":
            try:
                import pandas as pd
                rows = pd.read_parquet(path).to_dict("records")
            except ImportError as error:
                raise ValueError("Optional pandas/parquet reader unavailable; no packages installed") from error
        else:
            raise ValueError("Local metadata must be CSV, JSON, or Parquet")
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise ValueError("Local metadata must contain records")
        fields = sorted({key for row in rows for key in row})
        exam_fields = [field for field in fields if normalized(field) == "nail examination"]
        vocab = {}
        for field in exam_fields:
            counts = Counter()
            missing = 0
            for row in rows:
                value = row.get(field)
                if value is None or (isinstance(value, float) and value != value) or value == "":
                    missing += 1
                    continue
                counts[json.dumps(value, default=str, sort_keys=True)] += 1
            vocab[field] = {"missing": missing, "observed_values": dict(counts)}
        result["local_metadata"].append({
            "filename": path.name,
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "record_count": len(rows),
            "fields": fields,
            "nail_examination_vocabulary": vocab,
            "clinical_eligible": False,
            "reason": "Local vocabulary does not establish qualified sign labels or their validity.",
        })
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sewa-metadata", type=Path, action="append", default=[], help="Already-authorized LOCAL metadata only; never remote gated content")
    args = parser.parse_args()
    report = {
        "audit_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "images_downloaded": 0,
        "clinical_eligible": False,
        "scin": audit_scin(),
        "sewa": audit_sewa_local(args.sewa_metadata),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "scin_cases": report["scin"]["case_count"], "sign_mentions": report["scin"]["exact_sign_case_counts"], "images_downloaded": 0, "clinical_eligible": False}))


if __name__ == "__main__":
    main()
