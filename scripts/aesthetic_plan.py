"""Build a shot aesthetic plan (six dimensions, A/B variants) and freeze jobs.

This is the upstream step before FLUX: it does not generate images. It writes

* ``aesthetic_plan.json`` — shared aesthetic + per-shot A/B designs;
* ``snapshots/snapshot-<time>/A|B/`` — frozen specs, compiled prompts, jobs;
* ``jobs_<A|B>.json`` — compatible with ``scripts/r1_batch.py``.

Example::

    .venv\\Scripts\\python.exe scripts\\aesthetic_plan.py ^
        --script experiments/aesthetic/ink/work/production_script.json ^
        --style ink_wash --designs experiments/aesthetic/ink/work/designs.json ^
        --out experiments/aesthetic/ink/work/aesthetic/aesthetic_plan.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from drama_studio.domain.aesthetics import generate_plan, write_plan
from drama_studio.application.production import build_aesthetic_jobs
from drama_studio.application.script_engine import ProductionScript
from drama_studio.domain.style.presets import load_style_presets


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate an A/B shot aesthetic plan")
    parser.add_argument("--script", required=True, help="production_script.json")
    parser.add_argument("--style", default=None, help="style preset id (default: script.style_id)")
    parser.add_argument("--designs", default=None, help="authored per-shot design overrides JSON")
    parser.add_argument("--axes", default=None, help="JSON {shot_id: composition|lighting|color}")
    parser.add_argument("--out", required=True, help="aesthetic_plan.json path")
    parser.add_argument("--snapshot-root", default=None, help="default: <plan dir>/snapshots")
    parser.add_argument("--workflow", default="workflows/flux3_t2i_api.json")
    parser.add_argument("--seed-base", type=int, default=8100)
    parser.add_argument("--width", type=int, default=576)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--cfg", type=float, default=1.0)
    args = parser.parse_args(argv)

    script_path = Path(args.script)
    if not script_path.is_absolute():
        script_path = ROOT / script_path
    script = ProductionScript.model_validate(json.loads(script_path.read_text(encoding="utf-8")))
    registry = load_style_presets(ROOT)
    style_id = args.style or script.style_id
    if style_id not in registry.ids():
        raise SystemExit(
            f"cannot resolve style preset from {style_id!r}; pass --style one of {registry.ids()}"
        )
    preset = registry.get(style_id)
    designs = {}
    if args.designs:
        path = Path(args.designs)
        path = path if path.is_absolute() else ROOT / path
        designs = json.loads(path.read_text(encoding="utf-8"))
        designs = designs.get("shots", designs) if isinstance(designs, dict) else {}
    axes = {}
    if args.axes:
        path = Path(args.axes)
        path = path if path.is_absolute() else ROOT / path
        axes = json.loads(path.read_text(encoding="utf-8"))
    plan = generate_plan(
        script,
        preset,
        axes=axes,
        designs=designs,
        style_config_sha256=sha256(ROOT / "config" / "styles.yaml"),
    )
    out_path = Path(args.out)
    out_path = out_path if out_path.is_absolute() else ROOT / out_path
    write_plan(plan, out_path)

    snapshot_root = Path(args.snapshot_root) if args.snapshot_root else out_path.parent / "snapshots"
    snapshot_root = snapshot_root if snapshot_root.is_absolute() else ROOT / snapshot_root
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:19]
    run_root = snapshot_root / f"snapshot-{stamp}"
    results = []
    for variant in ("A", "B"):
        result = build_aesthetic_jobs(
            plan,
            root=ROOT,
            snapshot_dir=run_root / variant,
            variant_id=variant,
            workflow=args.workflow,
            seed_base=args.seed_base,
            width=args.width,
            height=args.height,
            steps=args.steps,
            cfg=args.cfg,
        )
        results.append(result)
    manifest = {
        "stage": "aesthetic.plan",
        "style_id": preset.id,
        "plan": out_path.relative_to(ROOT).as_posix(),
        "plan_sha256": sha256(out_path),
        "snapshot_run": run_root.relative_to(ROOT).as_posix(),
        "variants": results,
        "axes": {shot.shot_id: shot.axis for shot in plan.shots},
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    manifest_path = out_path.parent / "aesthetic_plan_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "ok": True,
        "plan": manifest["plan"],
        "shots": len(plan.shots),
        "axes": manifest["axes"],
        "jobs": [item["jobs"] for item in results],
        "snapshot_run": manifest["snapshot_run"],
        "negative_supported": results[0]["negative_supported"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
