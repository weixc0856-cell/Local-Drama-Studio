r"""Move modules into DDD layers, rewriting imports and leaving shims behind.

Stages are idempotent: files already at their destination are skipped, and
shims are only written for paths that no longer hold the implementation.

    .venv\Scripts\python.exe scripts\restructure_ddd.py --stage domain [--apply]
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src" / "drama_studio"

STAGES: dict[str, dict[str, str]] = {
    "domain": {
        "models": "domain.contracts",
        "style_engine": "domain.style",
        "style_engine.schemas": "domain.style.schemas",
        "style_engine.registry": "domain.style.registry",
        "style_engine.compiler": "domain.style.compiler",
        "style_engine.consistency": "domain.style.consistency",
        "style_presets": "domain.style.presets",
        "style_lock": "domain.style.lock",
        "aesthetics": "domain.aesthetics",
        "bible": "domain.bible",
        "voice.profiles": "domain.voice.profiles",
        "voice.pronunciation": "domain.voice.pronunciation",
        "voice.recitation": "domain.voice.recitation",
        "motion.spec": "domain.motion.spec",
        "motion.camera": "domain.motion.camera",
        "motion.noise": "domain.motion.noise",
        "film.schemas": "domain.film.schemas",
        "film.continuity": "domain.film.continuity",
        "film.text": "domain.film.text",
    },
    "application": {
        "production": "application.production",
        "script_engine": "application.script_engine",
        "quality": "application.quality",
        "style_consistency": "application.style_consistency",
        "content_package": "application.content_package",
        "doctor": "application.doctor",
        "film": "application.film",
        "film.project": "application.film.project",
        "film.script": "application.film.script",
        "film.storyboard": "application.film.storyboard",
        "film.prompts": "application.film.prompts",
        "film.jobs": "application.film.jobs",
        "film.clips": "application.film.clips",
        "film.wan_chain": "application.film.wan_chain",
        "film.wan_qc": "application.film.wan_qc",
        "film.voice": "application.film.voice",
        "film.audio": "application.film.audio",
        "film.segments": "application.film.segments",
        "film.assemble": "application.film.assemble",
        "film.motion_plan": "application.film.motion_plan",
        "film.status": "application.film.status",
        "film.review": "application.film.review",
        "film.upscale": "application.film.upscale",
        "film.assets": "application.film.assets",
        "film.config": "application.film.config",
        "film.static_gate": "application.film.static_gate",
        "film.timeline": "application.film.timeline",
        "voice.tts": "application.voice.tts",
        "voice.zeroshot": "application.voice.zeroshot",
        "voice.mix": "application.voice.mix",
        "voice.timeline": "application.voice.timeline",
        "voice.audio_assets": "application.voice.audio_assets",
        "voice.audio_timeline": "application.voice.audio_timeline",
        "voice.soundscape": "application.voice.soundscape",
        "motion.render": "application.motion.render",
        "motion.local": "application.motion.local",
        "motion.plates": "application.motion.plates",
        "motion.transition": "application.motion.transition",
        "motion.texture": "application.motion.texture",
        "workspace.tasks": "application.operations.tasks",
    },
    "infrastructure": {
        "workspace.store": "infrastructure.storage.store",
        "workspace.discovery": "infrastructure.storage.discovery",
        "workspace.media": "infrastructure.media",
        "workspace.envprobe": "infrastructure.envprobe",
        "fonts": "infrastructure.fonts",
        "locks": "infrastructure.locks",
    },
    "interfaces": {
        "cli": "interfaces.cli",
        "film.cli": "interfaces.film_cli",
        "workspace.api": "interfaces.http.api",
        "workspace.film_api": "interfaces.http.film_api",
    },
}

ACK = "Compatibility shim. The implementation lives in {target}."


def module_file(mod: str) -> Path:
    """The file that holds a module: ``x/y.py`` or ``x/y/__init__.py``."""
    base = SRC / Path(*mod.split("."))
    if base.with_suffix(".py").exists():
        return base.with_suffix(".py")
    if (base / "__init__.py").exists():
        return base / "__init__.py"
    return base.with_suffix(".py")


def destination_for(mod: str, *, package: bool) -> Path:
    base = SRC / Path(*mod.split("."))
    return base / "__init__.py" if package else base.with_suffix(".py")


def is_pkg(mod: str) -> bool:
    return (SRC / Path(*mod.split(".")) / "__init__.py").exists()


def old_module_of(path: Path) -> str:
    rel = path.relative_to(SRC).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def resolve_relative(owner: str, level: int, module: str | None, packages: set[str]) -> str:
    base = owner.split(".")
    if owner not in packages:
        base = base[:-1]
    keep = len(base) - (level - 1)
    prefix = ".".join(base[:max(keep, 0)])
    if not prefix:
        return module or ""
    return f"{prefix}.{module}" if module else prefix


def rewrite_relative_imports(path: Path, old_mod: str, mapping: dict[str, str], packages: set[str]) -> None:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    lines = text.splitlines()
    edits: list[tuple[int, int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.level == 0:
            continue
        target = resolve_relative(old_mod, node.level, node.module, packages)
        new_target = mapping.get(target, target)
        names = ", ".join(
            alias.name + (f" as {alias.asname}" if alias.asname else "")
            for alias in node.names
        )
        package = f"drama_studio.{new_target}" if new_target else "drama_studio"
        statement = f"from {package} import {names}"
        indent = re.match(r"[ 	]*", lines[node.lineno - 1]).group(0)
        edits.append((node.lineno, node.end_lineno or node.lineno, indent + statement))
    for start, end, statement in sorted(edits, reverse=True):
        lines[start - 1:end] = [statement]
    if edits:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def rewrite_absolute(text: str, mapping: dict[str, str]) -> str:
    for old in sorted(mapping, key=len, reverse=True):
        text = text.replace(f"drama_studio.{old}", f"drama_studio.{mapping[old]}")
    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=sorted(STAGES), required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    mapping = STAGES[args.stage]

    packages = {old for old in mapping if module_file(old).name == "__init__.py"}
    moves: list[tuple[str, str, Path, Path]] = []
    for old, new in mapping.items():
        src = module_file(old)
        dst = destination_for(new, package=src.name == "__init__.py")
        if not src.exists():
            print(f"skip (already moved): {old}")
            continue
        moves.append((old, new, src, dst))

    if not args.apply:
        for old, new, src, dst in moves:
            print(f"move {src.relative_to(REPO)} -> {dst.relative_to(REPO)}")
        return

    for old, new, src, dst in moves:
        dst.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "mv", str(src), str(dst)], cwd=REPO, check=True)
        print(f"moved {old} -> {new}")

    # Rewrite imports in every python file that references a moved module.
    touched = 0
    for path in list(SRC.rglob("*.py")) + list((REPO / "scripts").glob("*.py")) + list((REPO / "tests").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        new_text = rewrite_absolute(text, mapping)
        if new_text != text:
            path.write_text(new_text, encoding="utf-8")
            touched += 1
    print(f"rewrote absolute imports in {touched} files")

    # Relative imports inside moved files now resolve from their new depth.
    for old, new, src, dst in moves:
        if dst.is_file():
            rewrite_relative_imports(dst, old, mapping, packages)

    # Leave shims at every old path.
    for old, new, src, dst in moves:
        shim = src
        if shim.exists():
            continue
        shim.parent.mkdir(parents=True, exist_ok=True)
        if shim.name == "__init__.py":
            body = (
                f'"""{ACK.format(target=f"drama_studio.{new}")}"""\n\n'
                f"from drama_studio.{new} import *  # noqa: F401,F403\n"
            )
        else:
            body = (
                f'"""Compatibility shim: re-points to ``drama_studio.{new}``."""\n\n'
                "import importlib\nimport sys\n\n"
                f'_impl = importlib.import_module("drama_studio.{new}")\n'
                '_parent_name, _, _leaf = __name__.rpartition(".")\n'
                '_parent = sys.modules.get(_parent_name)\n'
                "if _parent is not None:\n"
                "    setattr(_parent, _leaf, _impl)\n"
                "sys.modules[__name__] = _impl\n"
            )
        shim.write_text(body, encoding="utf-8")
        print(f"shim {shim.relative_to(REPO)}")


if __name__ == "__main__":
    main()
