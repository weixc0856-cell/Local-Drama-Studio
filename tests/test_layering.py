"""Dependency-direction guard for the DDD layout.

Domain must not depend on application, infrastructure or interfaces. This test
reads the source instead of importing it, so it also covers modules that only
load on Windows.
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "drama_studio"
LAYERS = ("domain", "application", "infrastructure", "interfaces", "web")


def module_name(path: Path) -> str:
    parts = list(path.relative_to(SRC).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def resolve(owner: str, level: int, module: str | None) -> str:
    if level == 0:
        return module or ""
    package = owner.split(".")
    if not (SRC / Path(*owner.split(".")) / "__init__.py").is_file():
        package = package[:-1]
    keep = len(package) - (level - 1)
    prefix = ".".join(package[: max(keep, 0)])
    return f"{prefix}.{module}" if module else prefix


def imports_of(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    owner = module_name(path)
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            target = resolve(owner, node.level, node.module)
        elif isinstance(node, ast.Import):
            target = None
            for alias in node.names:
                if alias.name.startswith("drama_studio"):
                    found.add(alias.name[len("drama_studio."):])
            continue
        else:
            continue
        if target.startswith("drama_studio"):
            found.add(target[len("drama_studio."):])
        elif target and target.split(".")[0] in LAYERS:
            found.add(target)
    return found


def test_domain_does_not_import_outer_layers() -> None:
    violations: list[str] = []
    for path in (SRC / "domain").rglob("*.py"):
        for target in imports_of(path):
            if target.split(".")[0] in ("application", "infrastructure", "interfaces", "web"):
                violations.append(f"{path.relative_to(SRC)} -> {target}")
    assert not violations, "domain must stay independent of outer layers:\n" + "\n".join(violations)


def test_application_does_not_import_interfaces() -> None:
    violations: list[str] = []
    for path in (SRC / "application").rglob("*.py"):
        for target in imports_of(path):
            if target.split(".")[0] in ("interfaces", "web"):
                violations.append(f"{path.relative_to(SRC)} -> {target}")
    assert not violations, "application must not depend on interfaces:\n" + "\n".join(violations)
