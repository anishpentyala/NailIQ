from pathlib import Path
import pytest

from scripts.prepare_color_exclusions import build_exclusions, excludes_source


def test_quarantine_expands_to_patient_repeats_without_moving_files(tmp_path):
    names = ["train/pallor/ghana__Anemic_FN_232_1_.jpg",
             "valid/pallor/ghana__Anemic_FN_156_1_.jpg",
             "train/pallor/ghana__Anemic_FN_232_2_.jpg",
             "valid/pallor/ghana__Anemic_FN_156_2_.jpg",
             "test/pallor/ghana__Anemic_FN_999_1_.jpg"]
    for name in names:
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(name.encode())
    report = {"groups": [{"cross_split": True, "members": [{"path": p} for p in names[:2]]}],
              "limitations": "test"}
    manifest = build_exclusions(tmp_path, report)
    assert manifest["excluded_crops"] == sorted(names[:4])
    assert manifest["counts_by_split"] == {"train": 2, "valid": 2}
    assert all((tmp_path / name).exists() for name in names)
    raw = Path("data/raw/fingernails-ghana-anemia/Fingernails/Anemic_FN_232 (2).png")
    assert excludes_source(raw, manifest)


def test_roboflow_exports_share_quarantine_family():
    manifest = {"excluded_families": ["chaa__nail7"]}
    assert excludes_source(Path("data/raw/yolov8-nails-segmentation-ckvkd/test/images/nail7_jpg.rf.abc123.jpg"), manifest)
    assert not excludes_source(Path("data/raw/yolov8-nails-segmentation-ckvkd/test/images/nail8_jpg.rf.abc123.jpg"), manifest)


def test_only_confirmed_reviewed_pairs_are_quarantined(tmp_path):
    names = ["train/healthy/chaa__one.jpg", "valid/healthy/chaa__two.jpg"]
    for name in names:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"sample")
    pair = {"a": names[0], "b": names[1], "decision": "candidate"}
    report = {"groups": [], "limitations": "test"}
    assert build_exclusions(tmp_path, report, [pair])["excluded_crops"] == []
    pair["decision"] = "confirmed_duplicate"
    assert build_exclusions(tmp_path, report, [pair])["excluded_crops"] == names
    pair["b"] = "valid/healthy/missing.jpg"
    with pytest.raises(ValueError, match="does not exist"):
        build_exclusions(tmp_path, report, [pair])
