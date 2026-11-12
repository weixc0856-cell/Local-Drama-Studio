"""CLI entry point.

R0 exposes diagnostics only. Pipeline commands (create / script / assets /
images / videos / audio / render / run / resume) are specified in
docs/ARCHITECTURE.md and are added stage by stage, only after the previous
stage is verified on this machine.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .config import find_project_root, load_settings
from .doctor import (
    FAIL,
    NOT_RUN,
    PASS_LIMITED,
    PASS_VERIFIED,
    collect_checks,
    summarize,
    write_report,
)

app = typer.Typer(no_args_is_help=True, add_completion=False, help="Local AI drama production lab")
console = Console()

# When stdout is a pipe (CI, captured logs, MSYS shell) Python defaults to the
# ANSI code page on Windows and Chinese text becomes mojibake. Console output
# is unaffected because it is written through the console API.
if not sys.stdout.isatty():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

_STATUS_STYLE = {
    PASS_VERIFIED: "green",
    PASS_LIMITED: "yellow",
    FAIL: "red",
    NOT_RUN: "dim",
}


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"local-drama-studio {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool, typer.Option("--version", callback=_version_callback, is_eager=True, help="显示版本")
    ] = False,
) -> None:
    """Local-Drama-Studio: script -> storyboard -> image/video -> voice -> subtitles -> MP4."""


@app.command()
def doctor(
    as_json: Annotated[bool, typer.Option("--json", help="以 JSON 输出完整报告")] = False,
    report: Annotated[
        Path | None, typer.Option("--report", help="报告输出路径（默认 logs/doctor-<时间>.json）")
    ] = None,
    no_report: Annotated[bool, typer.Option("--no-report", help="不写报告文件")] = False,
) -> None:
    """检查硬件、依赖、服务与模型的真实状态（R0-A）。"""
    root = find_project_root()
    settings = load_settings(root)
    checks = collect_checks(settings)
    summary = summarize(checks)

    report_path: Path | None = None
    if not no_report:
        report_path = write_report(settings, checks, report)

    if as_json:
        payload = {
            "root": str(settings.root),
            "summary": summary,
            "checks": [
                {
                    "id": c.id,
                    "title": c.title,
                    "status": c.status,
                    "required": c.required,
                    "detail": c.detail,
                }
                for c in checks
            ],
            "report": str(report_path) if report_path else None,
        }
        console.print_json(json.dumps(payload, ensure_ascii=False))
    else:
        table = Table(title="Local-Drama-Studio / doctor", show_lines=False)
        table.add_column("检查", style="bold")
        table.add_column("状态", no_wrap=True)
        table.add_column("说明", overflow="fold")
        for check in checks:
            style = _STATUS_STYLE.get(check.status, "white")
            required = " *" if check.required else ""
            table.add_row(
                check.title + required,
                f"[{style}]{check.status}[/{style}]",
                check.detail,
            )
        console.print(table)
        counts = summary["counts"]
        console.print(
            "  ".join(
                f"[{_STATUS_STYLE[s]}]{s}={counts.get(s, 0)}[/{_STATUS_STYLE[s]}]"
                for s in (PASS_VERIFIED, PASS_LIMITED, FAIL, NOT_RUN)
            )
        )
        console.print("[dim]* = 必需项；只有必需项 FAIL 才返回非零退出码[/dim]")
        if report_path:
            console.print(f"报告: [bold]{report_path}[/bold]")

    raise typer.Exit(0 if summary["ok"] else 1)


@app.command()
def serve(
    host: Annotated[str, typer.Option(help="监听地址（默认仅本机）")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="工作台端口（默认 8765，避开 8080/8188/50000）")] = 8765,
    reload: Annotated[bool, typer.Option(help="开发模式自动重载")] = False,
) -> None:
    """启动本地生产工作台（FastAPI + 静态前端）。"""
    import uvicorn

    console.print(f"[bold]Local Drama Studio — Production Workspace[/bold]  http://{host}:{port}")
    console.print("[dim]只读派生真实产物状态；任务仅限注册表。Ctrl+C 停止。[/dim]")
    uvicorn.run("drama_studio.workspace.api:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()


# --------------------------------------------------------------------------
# Script-to-Film production layer (docs/FILM_PRODUCTION_GUIDE.md)
# --------------------------------------------------------------------------

# Script-to-Film commands live in film/cli.py; the root app only registers them.
from .film.cli import film_app  # noqa: E402

app.add_typer(film_app, name="film")


# --------------------------------------------------------------------------
# Visual Style Engine (docs/VISUAL_STYLE_ENGINE.md)
# --------------------------------------------------------------------------

style_app = typer.Typer(no_args_is_help=True, add_completion=False, help="视觉风格引擎")
app.add_typer(style_app, name="style")


@style_app.command("list")
def style_list(
    group: Annotated[str | None, typer.Option("--group", help="retro / oriental / artistic")] = None,
) -> None:
    """列出已注册的风格包。"""
    from .style_engine import list_packs

    root = find_project_root()
    packs = list_packs(root, group)
    table = Table(title="Visual Style Packs", show_lines=False)
    table.add_column("id", style="bold")
    table.add_column("name")
    table.add_column("version")
    table.add_column("status")
    for pack in packs:
        table.add_row(pack.identity.id, pack.identity.name, pack.identity.version, pack.identity.status)
    console.print(table)
    console.print(f"[dim]{len(packs)} styles[/dim]")


@style_app.command("show")
def style_show(style_id: Annotated[str, typer.Argument(help="例如 oriental.ink_wash")]) -> None:
    """显示一个风格包的完整配置。"""
    from .style_engine import get_pack

    root = find_project_root()
    pack = get_pack(root, style_id)
    console.print_json(json.dumps(pack.model_dump(mode="json"), ensure_ascii=False))


@style_app.command("validate")
def style_validate(
    style_id: Annotated[str | None, typer.Option("--style", help="只校验一个；默认全部")] = None,
) -> None:
    """校验风格包 Schema、id/路径、版本与数值范围。"""
    from .style_engine import load_all, packs_root, validate_pack
    from .style_engine.registry import load_pack

    root = find_project_root()
    base = packs_root(root)
    problems = []
    directories = sorted(base.glob("*/*"))
    for directory in directories:
        if not directory.is_dir():
            continue
        pack = load_pack(directory)
        if style_id and pack.identity.id != style_id:
            continue
        for message in validate_pack(pack, directory):
            problems.append({"style": pack.identity.id, "issue": message})
    if problems:
        console.print_json(json.dumps({"ok": False, "problems": problems}, ensure_ascii=False))
        raise typer.Exit(1)
    console.print_json(json.dumps({"ok": True, "packs": len(load_all(root))}, ensure_ascii=False))


@style_app.command("check-image")
def style_check_image(
    style_id: Annotated[str, typer.Option("--style", help="例如 oriental.ink_wash")],
    image: Annotated[Path, typer.Option("--image", help="待检查的图片")],
) -> None:
    """按风格包检查色板、饱和度、边缘密度与黑边。"""
    from .style_engine import check_image, get_pack

    root = find_project_root()
    pack = get_pack(root, style_id)
    issues = check_image(image, pack)
    console.print_json(json.dumps({
        "ok": not any(item.level == "error" for item in issues),
        "style": style_id,
        "image": str(image),
        "issues": [{"level": i.level, "code": i.code, "message": i.message} for i in issues],
    }, ensure_ascii=False))
    raise typer.Exit(0 if not any(item.level == "error" for item in issues) else 1)
