"""Block until the overnight pipeline finishes, fails, or stops making progress; print why and exit.

Progress = newest mtime among E:/NailIQ_data/overnight/*.log|status.json and the crop-builder log. A running
pipeline that has written nothing for STALE_MIN minutes, or a driver process that is gone while status is
RUNNING, counts as a crash.
"""
import json, subprocess, sys, time
from pathlib import Path

OUT = Path("E:/NailIQ_data/overnight")
EXTRA = [Path("data/raw/onych_app_crops/abstained_new.json")]
STALE_MIN = int(sys.argv[1]) if len(sys.argv) > 1 else 45


def newest():
    fs = list(OUT.glob("*.log")) + [OUT / "status.json"] + [p for p in EXTRA if p.exists()]
    return max((f.stat().st_mtime for f in fs if f.exists()), default=0)


def driver_alive():
    out = subprocess.run(["powershell", "-Command", "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Select-Object -ExpandProperty CommandLine"],
                         capture_output=True, text=True).stdout
    return "overnight_driver.py" in out


while True:
    st = json.loads((OUT / "status.json").read_text()) if (OUT / "status.json").exists() else {}
    state = st.get("state")
    if state in ("DONE", "FAILED"):
        print(f"PIPELINE {state} at stage {st.get('stage')}"); print("\n".join(st.get("events", [])[-12:])); break
    if state == "RUNNING" and not driver_alive():
        time.sleep(20)
        if not driver_alive():
            print("DRIVER PROCESS GONE while RUNNING; last stage", st.get("stage")); print("\n".join(st.get("events", [])[-12:])); break
    if time.time() - newest() > STALE_MIN * 60:
        print(f"STALE: no log activity for {STALE_MIN} min; stage {st.get('stage')}"); print("\n".join(st.get("events", [])[-12:])); break
    time.sleep(60)
