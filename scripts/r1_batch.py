"""R1 batch runner for FLUX asset jobs.

Reuses the verified R0 HTTP probe (submit -> poll -> download) and adds only
what R1-E needs: a job manifest, resume/skip, bounded retries, reference-image
staging, and per-asset provenance.

No new dependencies. Run with the project venv:

    .venv\\Scripts\\python.exe scripts\\r1_batch.py --jobs experiments/r1/jobs.json

A job is considered done only when job.json says success AND every recorded
output still exists with the same sha256.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from drama_studio.locks import FileLock, LockHeld

ROOT = Path(__file__).resolve().parents[1]

PROBE = ROOT / "scripts" / "r0_comfy_probe.py"
COMFY_INPUT = ROOT / "runtime" / "ComfyUI" / "input"
MAX_ATTEMPTS = 3  # initial try + 2 retries


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def job_is_done(job: dict) -> bool:
    out_dir = (ROOT / job["out"]).resolve()
    meta_path = out_dir / "job.json"
    if not meta_path.is_file():
        return False
    meta = read_json(meta_path)
    if meta.get("status") != "success":
        return False
    for item in meta.get("outputs", []):
        path = Path(item["path"])
        if not path.is_file() or sha256(path) != item["sha256"]:
            return False
    return bool(meta.get("outputs"))


def stage_reference(job: dict) -> dict | None:
    ref = job.get("reference")
    if not ref:
        return None
    source = (ROOT / ref["source"]).resolve()
    if not source.is_file():
        raise FileNotFoundError(f"reference image not found: {source}")
    COMFY_INPUT.mkdir(parents=True, exist_ok=True)
    target = COMFY_INPUT / ref["input_name"]
    shutil.copy2(source, target)
    return {
        "source": str(source),
        "input_name": ref["input_name"],
        "sha256": sha256(source),
    }


def run_job(job: dict, force: bool = False, timeout: int = 1800) -> dict:
    job_id = job["id"]
    out_dir = (ROOT / job["out"]).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    workflow = (ROOT / job["workflow"]).resolve()
    params_path = (ROOT / job["params"]).resolve()

    if not force and job_is_done(job):
        meta = read_json(out_dir / "job.json")
        return {"id": job_id, "status": "skipped", "attempts": meta.get("attempts", 0)}

    workflow_sha = sha256(workflow)
    params = read_json(params_path)
    reference = stage_reference(job)
    last_error = ""

    for attempt in range(1, MAX_ATTEMPTS + 1):
        cmd = [
            sys.executable,
            str(PROBE),
            "--workflow",
            str(workflow),
            "--params",
            str(params_path),
            "--out",
            str(out_dir),
            "--timeout",
            str(timeout),
        ]
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        (out_dir / f"probe_attempt{attempt}.log").write_text(
            (proc.stdout or "") + (proc.stderr or ""), encoding="utf-8"
        )

        run_json = out_dir / "run.json"
        if proc.returncode == 0 and run_json.is_file():
            run = read_json(run_json)
            outputs = []
            for raw in run.get("outputs", []):
                path = Path(raw)
                if not path.is_absolute():
                    path = (ROOT / path).resolve()
                if path.is_file():
                    outputs.append(
                        {"path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size}
                    )
            if not outputs:
                last_error = "probe succeeded but no output files were downloaded"
                continue
            meta = {
                "job_id": job_id,
                "status": "success",
                "attempts": attempt,
                "workflow": str(workflow),
                "workflow_sha256": workflow_sha,
                "params": params,
                "reference": reference,
                "prompt_id": run.get("prompt_id"),
                "submitted_at": run.get("submitted_at"),
                "elapsed_seconds": run.get("elapsed_seconds"),
                "peak_vram_used_bytes": run.get("peak_vram_used_bytes"),
                "outputs": outputs,
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
            write_json(out_dir / "job.json", meta)
            return {
                "id": job_id,
                "status": "success",
                "attempts": attempt,
                "elapsed_seconds": meta["elapsed_seconds"],
                "outputs": [o["path"] for o in outputs],
            }

        last_error = (proc.stderr or proc.stdout or f"exit code {proc.returncode}").strip()[-2000:]
        write_json(
            out_dir / "job.json",
            {
                "job_id": job_id,
                "status": "failed",
                "attempts": attempt,
                "workflow": str(workflow),
                "params": params,
                "reference": reference,
                "error": last_error,
                "created_at": datetime.now().isoformat(timespec="seconds"),
            },
        )

    return {"id": job_id, "status": "failed", "attempts": MAX_ATTEMPTS, "error": last_error}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs", required=True, type=Path)
    parser.add_argument("--only", default="", help="comma-separated job ids")
    parser.add_argument("--force", action="store_true", help="ignore existing success metadata")
    parser.add_argument("--timeout", type=int, default=1800, help="per-job timeout in seconds")
    args = parser.parse_args()
    lock_path = ROOT / "logs" / "locks" / "gpu-comfy.lock"
    try:
        with FileLock(lock_path, name="r1_batch"):
            return _run(args)
    except LockHeld as exc:
        print(f"[locked] {exc}", file=sys.stderr)
        print("[locked] another generation job is running; refusing to start", file=sys.stderr)
        return 3


def _run(args: argparse.Namespace) -> int:
    jobs = read_json(ROOT / args.jobs)
    only = {x.strip() for x in args.only.split(",") if x.strip()}
    if only:
        jobs = [j for j in jobs if j["id"] in only]

    results = []
    for job in jobs:
        print(f"[job] {job['id']} -> {job['out']}")
        result = run_job(job, force=args.force, timeout=args.timeout)
        print(f"[job] {job['id']} {result['status']} attempts={result.get('attempts')}")
        results.append(result)

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "counts": {
            "success": sum(r["status"] == "success" for r in results),
            "skipped": sum(r["status"] == "skipped" for r in results),
            "failed": sum(r["status"] == "failed" for r in results),
        },
        "results": results,
    }
    manifest_path = ROOT / args.jobs.parent / f"{args.jobs.stem}_manifest.json"
    write_json(manifest_path, summary)
    print(json.dumps(summary["counts"], ensure_ascii=False))
    return 0 if summary["counts"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
