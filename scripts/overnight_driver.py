"""Unattended pipeline for the 2026-10-18 scope change (onychomycosis / psoriasis / nail dystrophy specialists).

Runs stages one after another; each stage is skipped if its done-marker exists, retried (RETRIES) on a nonzero
exit or timeout, and logged to E:/NailIQ_data/overnight/<stage>.log. status.json is rewritten on every event, and
the final state (DONE or FAILED) is written to status.json too. Safe to re-run: finished stages are skipped and
the crop builders skip files that already exist.

Run from repo root: ml/venv/Scripts/python.exe scripts/overnight_driver.py
"""
import json, subprocess, sys, time
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = Path("E:/NailIQ_data/overnight")
PY = str(REPO / "ml" / "venv" / "Scripts" / "python.exe")
RETRIES = 2
HAN = Path("E:/NailIQ_data/raw/han-onychomycosis-figshare")
CROPS = REPO / "data" / "raw" / "onych_app_crops"

STAGES = [
    ("v2_han_normal", [PY, "scripts/build_new_sign_crops.py", "han", "--cap", "1500", "--han-normal", "1500"], 3 * 3600),
    ("v2_train_onychomycosis", [PY, "scripts/train_sign_specialist.py", "--target", "onychomycosis", "--folds", "han,nihati", "--tag", "app2_", "--final"], 4 * 3600),
    ("v2_train_psoriasis", [PY, "scripts/train_sign_specialist.py", "--target", "psoriasis", "--tag", "app2_", "--final"], 3 * 3600),
    ("v2_train_naildystrophy", [PY, "scripts/train_sign_specialist.py", "--target", "naildystrophy", "--folds", "han", "--tag", "app2_", "--final"], 3 * 3600),
]


def status(**kw):
    s = json.loads((OUT / "status.json").read_text()) if (OUT / "status.json").exists() else {"events": []}
    s.update(kw); s["updated"] = datetime.now().isoformat(timespec="seconds")
    (OUT / "status.json").write_text(json.dumps(s, indent=1))


def event(msg):
    s = json.loads((OUT / "status.json").read_text()) if (OUT / "status.json").exists() else {"events": []}
    s["events"].append(f"{datetime.now().isoformat(timespec='seconds')} {msg}")
    (OUT / "status.json").write_text(json.dumps(s, indent=1))


def wait_for(pred, what, timeout):
    t0 = time.time()
    while not pred():
        if time.time() - t0 > timeout:
            event(f"gave up waiting for {what}")
            return False
        time.sleep(30)
    return True


def visible_ready():
    f = HAN / "visible_signs.csv"
    if not f.exists():
        return False
    txt = f.read_text()
    return ",onychomycosis," in txt and ",naildystrophy," in txt


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    status(events=[], state="RUNNING", stage="waiting_inputs", started=datetime.now().isoformat(timespec="seconds"))
    ok = wait_for(visible_ready, "Han visibility scores", 2 * 3600) and wait_for(lambda: (CROPS / "abstained_new.json").exists(), "NIHATI crops", 3 * 3600)
    if not ok:
        status(state="FAILED", stage="waiting_inputs"); sys.exit(1)
    for name, cmd, timeout in STAGES:
        marker = OUT / f"{name}.done"
        if marker.exists():
            event(f"{name}: already done"); continue
        for attempt in range(1, RETRIES + 2):
            status(stage=name, attempt=attempt)
            event(f"{name}: start attempt {attempt}")
            with open(OUT / f"{name}.log", "a", encoding="utf-8") as log:
                log.write(f"\n=== attempt {attempt} {datetime.now().isoformat(timespec='seconds')}\n"); log.flush()
                try:
                    rc = subprocess.run(cmd, cwd=REPO, stdout=log, stderr=subprocess.STDOUT, timeout=timeout).returncode
                except subprocess.TimeoutExpired:
                    rc = -9
            if rc == 0:
                marker.write_text(datetime.now().isoformat()); event(f"{name}: done"); break
            event(f"{name}: failed rc={rc}")
            time.sleep(20)
        else:
            status(state="FAILED", stage=name); sys.exit(2)
    status(state="DONE", stage="all")


if __name__ == "__main__":
    main()
