"""Chain the ink film after the running Shinkai Wan batch finishes.

1. wait for 18 Shinkai Wan jobs + the assembled renders_24 manifest
2. generate 24 FLUX ink keyframes
3. prepare Wan jobs (copies keyframes into ComfyUI input)
4. generate 24 Wan clips
5. assemble and quality-check the 2-minute ink film

Everything is logged to experiments/ink_dream/run_ink_film.log. It never
touches the Shinkai job files and never runs two generation jobs at once.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = output_path("experiments/ink_dream")
SHINKAI = output_path("experiments/shinkai_scene")
LOG = BASE / "run_ink_film.log"


def log(msg: str) -> None:
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print(line, flush=True)


def successes(folder: Path) -> int:
    count = 0
    for job in folder.glob("*/job.json"):
        try:
            if json.loads(job.read_text(encoding="utf-8")).get("status") == "success":
                count += 1
        except (OSError, json.JSONDecodeError):
            pass
    return count


def wait_for_shinkai(timeout_h: float = 14.0) -> None:
    deadline = time.time() + timeout_h * 3600
    while time.time() < deadline:
        done = successes(SHINKAI / "wan24")
        log(f"shinkai wan success={done}/18")
        if done >= 18:
            break
        time.sleep(180)
    else:
        raise SystemExit("timed out waiting for the Shinkai Wan batch")

    manifest = SHINKAI / "renders_24" / "build_manifest.json"
    deadline = time.time() + 20 * 60
    while time.time() < deadline and not manifest.is_file():
        time.sleep(30)
    if not manifest.is_file():
        log("renders_24 manifest missing; assembling Shinkai cut")
        run([sys.executable, "scripts/assemble_scene_24.py",
             "--out", "experiments/shinkai_scene/renders_24"], check=False)


def run(cmd: list[str], check: bool = True) -> int:
    log("run: " + " ".join(cmd))
    proc = subprocess.run(cmd, cwd=ROOT, text=True, encoding="utf-8", errors="replace")
    if check and proc.returncode != 0:
        raise SystemExit(f"command failed ({proc.returncode}): {' '.join(cmd)}")
    return proc.returncode


def batch_with_retry(jobs: str, timeout: str) -> None:
    for attempt in range(1, 4):
        code = run([sys.executable, "scripts/r1_batch.py", "--jobs", jobs,
                    "--timeout", timeout], check=False)
        if code == 0:
            return
        log(f"batch {jobs} attempt {attempt} exit={code}; retrying in 120s")
        time.sleep(120)
    raise SystemExit(f"batch failed: {jobs}")


def main() -> int:
    BASE.mkdir(parents=True, exist_ok=True)
    log("ink chain started")
    wait_for_shinkai()
    log("GPU free; generating ink keyframes")
    batch_with_retry("experiments/ink_dream/jobs.json", "3600")
    run([sys.executable, "scripts/prepare_ink_film.py"])
    log("keyframes ready; generating Wan clips")
    batch_with_retry("experiments/ink_dream/wan24_jobs.json", "7200")
    log("Wan clips ready; assembling")
    run([sys.executable, "scripts/assemble_ink_film.py",
         "--out", "experiments/ink_dream/renders_24"])
    log("ink film done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
