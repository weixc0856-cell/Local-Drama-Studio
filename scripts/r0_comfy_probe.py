"""R0-only ComfyUI probe.

Not product code. R3 replaces this with the real orchestration client
(WebSocket progress, state machine, cache keys). This script exists solely to
prove model compatibility in R0-C/R0-D with the smallest possible surface:

    submit API workflow -> poll /history -> download outputs -> record evidence

Usage:
    python scripts/r0_comfy_probe.py --workflow workflows/flux3_t2i_api.json \
        --out logs/r0/flux_t2i --timeout 1800
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

BASE = "http://127.0.0.1:8188"
PLACEHOLDER = re.compile(r"^\{\{(\w+)\}\}$")

# Never route localhost through the system/environment proxy.
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _render(value, params: dict):
    """Replace whole-string {{name}} placeholders, keeping JSON types."""
    if isinstance(value, dict):
        return {k: _render(v, params) for k, v in value.items()}
    if isinstance(value, list):
        return [_render(v, params) for v in value]
    if isinstance(value, str):
        match = PLACEHOLDER.match(value)
        if match:
            key = match.group(1)
            if key not in params:
                raise KeyError(f"missing workflow parameter: {key}")
            return params[key]
    return value


def _get(path: str) -> dict:
    with OPENER.open(BASE + path, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post(path: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE + path, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with OPENER.open(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _download(filename: str, subfolder: str, kind: str, out_dir: Path) -> Path:
    query = urllib.parse.urlencode({"filename": filename, "subfolder": subfolder, "type": kind})
    target = out_dir / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    with OPENER.open(f"{BASE}/view?{query}", timeout=120) as resp, target.open("wb") as fh:
        shutil.copyfileobj(resp, fh)
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workflow", required=True, type=Path)
    parser.add_argument("--params", type=Path, help="JSON file with {{placeholder}} values")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=1800)
    parser.add_argument("--poll", type=float, default=2.0)
    args = parser.parse_args()

    workflow = json.loads(args.workflow.read_text(encoding="utf-8"))
    if args.params:
        params = json.loads(args.params.read_text(encoding="utf-8"))
        workflow = _render(workflow, params)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "workflow.submitted.json").write_text(
        json.dumps(workflow, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    stats_before = _get("/system_stats")
    started = time.time()
    submitted_at = datetime.now().isoformat(timespec="seconds")
    response = _post("/prompt", {"prompt": workflow, "client_id": str(uuid.uuid4())})
    prompt_id = response["prompt_id"]
    print(f"[submit] prompt_id={prompt_id} at {submitted_at}")

    history = None
    peak_vram_used = 0
    while time.time() - started < args.timeout:
        try:
            ds = _get("/system_stats").get("devices", [])
            if ds:
                used = int(ds[0].get("vram_total", 0)) - int(ds[0].get("vram_free", 0))
                peak_vram_used = max(peak_vram_used, used)
        except Exception:
            pass
        data = _get(f"/history/{prompt_id}")
        if prompt_id in data:
            history = data[prompt_id]
            status = history.get("status", {})
            if status.get("status_str") == "error":
                print(f"[error] {json.dumps(status, ensure_ascii=False)[:2000]}")
                (args.out / "history.json").write_text(
                    json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                return 1
            if status.get("completed", False):
                break
        time.sleep(args.poll)
    else:
        print(f"[timeout] no completion within {args.timeout}s")
        return 1

    elapsed = time.time() - started
    stats_after = _get("/system_stats")
    (args.out / "history.json").write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    downloaded: list[str] = []
    for node_id, node_output in (history.get("outputs") or {}).items():
        for item in node_output.get("images", []):
            path = _download(item["filename"], item.get("subfolder", ""), item.get("type", "output"), args.out)
            downloaded.append(str(path))
            print(f"[output] {path}")
        for key in ("videos", "gifs"):
            for item in node_output.get(key, []):
                path = _download(item["filename"], item.get("subfolder", ""), item.get("type", "output"), args.out)
                downloaded.append(str(path))
                print(f"[output] {path}")

    record = {
        "prompt_id": prompt_id,
        "workflow": str(args.workflow),
        "submitted_at": submitted_at,
        "elapsed_seconds": round(elapsed, 2),
        "peak_vram_used_bytes": peak_vram_used,
        "outputs": downloaded,
        "system_stats_before": stats_before,
        "system_stats_after": stats_after,
    }
    (args.out / "run.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] {elapsed:.1f}s, {len(downloaded)} output(s) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
