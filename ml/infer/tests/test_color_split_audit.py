import cv2
import numpy as np

from scripts.audit_color_split_leakage import audit, main, source_family


def write(root, relative, value, compression=3):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    assert cv2.imwrite(str(path), np.full((12, 13, 3), value, np.uint8),
                       [cv2.IMWRITE_PNG_COMPRESSION, compression])
    return path


def test_rf_family_strips_crop_before_export_suffix():
    assert source_family("chaa__nail_jpg.rf.abcdef__b12.jpg") == "chaa__nail"
    assert source_family("knm__nail_png.rf.123456__b0.jpg") == "knm__nail"


def test_connected_groups_merge_pixels_and_family(tmp_path):
    write(tmp_path, "train/healthy/chaa__nail_png.rf.aaa__b0.png", 10, 0)
    write(tmp_path, "valid/pallor/ghana__different.png", 10, 9)
    write(tmp_path, "test/healthy/chaa__nail_png.rf.bbb__b1.png", 80)
    result = audit(tmp_path)
    assert result["cross_split_groups"] == 1
    group = result["groups"][0]
    assert len(group["members"]) == 3
    assert group["label_conflict"]
    assert group["evidence"] == ["pixels", "source_family"]


def test_same_split_duplicates_not_leakage_and_source_namespaced(tmp_path):
    write(tmp_path, "train/healthy/chaa__same.png", 30)
    write(tmp_path, "train/healthy/chaa__copy.png", 30)
    write(tmp_path, "test/healthy/knm__same.png", 90)
    result = audit(tmp_path)
    assert result["cross_split_groups"] == 0
    assert len(result["groups"]) == 1


def test_cli_fails_on_leakage_and_writes_report(tmp_path):
    write(tmp_path, "train/healthy/a__one.png", 15)
    write(tmp_path, "test/healthy/b__two.png", 15)
    output = tmp_path / "audit.json"
    assert main(["--root", str(tmp_path), "--out", str(output)]) == 1
    assert output.exists()


def test_unreadable_is_not_silently_ignored(tmp_path):
    broken = tmp_path / "test/healthy/a__one.png"
    broken.parent.mkdir(parents=True)
    broken.write_bytes(b"bad image")
    assert main(["--root", str(tmp_path), "--out", str(tmp_path / "report.json")]) == 2
