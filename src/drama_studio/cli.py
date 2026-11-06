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

film_app = typer.Typer(no_args_is_help=True, add_completion=False, help="Script-to-Film 制作层")
app.add_typer(film_app, name="film")


@film_app.command("validate")
def film_validate(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
) -> None:
    """校验项目数据：Schema、镜头链、连续性、旁白引用。"""
    from .film import validate_project

    root = find_project_root()
    report = validate_project(root, project)
    console.print_json(json.dumps(report, ensure_ascii=False))
    raise typer.Exit(0 if report["ok"] else 1)


@film_app.command("timeline")
def film_timeline(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
    out: Annotated[Path | None, typer.Option("--out", help="输出路径（默认项目内 timeline.json）")] = None,
) -> None:
    """由分镜生成剪辑时间轴；镜头时长即剪辑目标时长。"""
    from .film import build_timeline, load_project, project_dir, write_model
    from .film.project import TIMELINE_FILE

    root = find_project_root()
    loaded = load_project(root, project)
    if loaded.storyboard is None:
        console.print("[red]缺少 storyboard.json[/red]")
        raise typer.Exit(1)
    timeline = build_timeline(loaded.storyboard)
    target = out or (project_dir(root, project) / TIMELINE_FILE)
    write_model(target, timeline)
    console.print_json(json.dumps({
        "timeline": str(target),
        "shots": len(timeline.entries),
        "total_ms": timeline.total_ms,
    }, ensure_ascii=False))


@film_app.command("plan")
def film_plan(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
    beats: Annotated[Path, typer.Option("--beats", help="导演节拍 JSON（列表）")],
    out: Annotated[Path | None, typer.Option("--out", help="输出路径（默认项目内 storyboard.json）")] = None,
) -> None:
    """把导演节拍写成受校验的 storyboard.json。"""
    from .film import load_project, plan_storyboard, project_dir, write_model
    from .film.project import STORYBOARD_FILE

    root = find_project_root()
    loaded = load_project(root, project)
    if loaded.bible is None:
        console.print("[red]缺少 visual_bible.yaml[/red]")
        raise typer.Exit(1)
    beat_list = json.loads(beats.read_text(encoding="utf-8"))
    storyboard = plan_storyboard(project, beat_list, loaded.bible)
    target = out or (project_dir(root, project) / STORYBOARD_FILE)
    write_model(target, storyboard)
    console.print_json(json.dumps({
        "storyboard": str(target),
        "shots": len(storyboard.shots),
        "total_seconds": round(sum(s.duration_seconds for s in storyboard.shots), 2),
    }, ensure_ascii=False))


@film_app.command("prompts")
def film_prompts(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
    out: Annotated[Path | None, typer.Option("--out", help="输出目录（默认项目内 prompts/）")] = None,
    style: Annotated[str | None, typer.Option("--style", help="使用风格包编译，例如 oriental.ink_wash")] = None,
) -> None:
    """由分镜与视觉圣经编译关键帧提示词和 Wan 运动提示词。"""
    from .film import compile_shot_prompts, load_project, project_dir

    root = find_project_root()
    loaded = load_project(root, project)
    if loaded.storyboard is None or loaded.bible is None:
        console.print("[red]需要 storyboard.json 与 visual_bible.yaml[/red]")
        raise typer.Exit(1)
    target = out or (project_dir(root, project) / "prompts")
    target.mkdir(parents=True, exist_ok=True)
    pack = None
    if style:
        from .style_engine import get_pack
        try:
            pack = get_pack(root, style)
        except KeyError as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(1)
    count = 0
    errors = []
    for shot in loaded.storyboard.shots:
        if pack is not None:
            from .style_engine import compile_image_prompt, compile_video_prompt
            layers = {"foreground": shot.layers.foreground, "midground": shot.layers.midground,
                      "background": shot.layers.background}
            subject = f"scene {shot.scene_id}"
            if not shot.character_in_frame:
                subject += ", no people, empty landscape"
            try:
                payload = {
                    "keyframe_prompt": compile_image_prompt(
                        pack, subject=subject, layers=layers, camera_move=shot.camera.move.value,
                        extra_note=shot.keyframe_note),
                    "video_prompt": compile_video_prompt(
                        pack, camera_move=shot.camera.move.value,
                        primary_motion=shot.motion.primary,
                        secondary_motions=shot.motion.secondary, layers=layers),
                }
            except ValueError as exc:
                errors.append(f"{shot.shot_id}: {exc}")
                continue
        else:
            payload = compile_shot_prompts(shot, loaded.bible)
        payload["style_id"] = style
        (target / f"{shot.shot_id}.json").write_text(
            json.dumps({"shot_id": shot.shot_id, **payload}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        count += 1
    console.print_json(json.dumps({"prompts": str(target), "shots": count,
                                   "style": style, "errors": errors}, ensure_ascii=False))
    if errors:
        raise typer.Exit(1)


@film_app.command("keyframes")
def film_keyframes(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
    out: Annotated[Path | None, typer.Option("--out", help="任务输出目录（默认项目内 jobs/keyframes）")] = None,
    style: Annotated[str | None, typer.Option("--style", help="使用风格包编译提示词")] = None,
) -> None:
    """由分镜生成 FLUX.3 关键帧任务文件（不执行）。"""
    from .film import load_project
    from .film.jobs import build_keyframe_jobs
    from .style_engine import get_pack

    root = find_project_root()
    pack = get_pack(root, style) if style else None
    result = build_keyframe_jobs(load_project(root, project), root, out_dir=out, pack=pack)
    console.print_json(json.dumps(result, ensure_ascii=False))


@film_app.command("wan-jobs")
def film_wan_jobs(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
    keyframes: Annotated[Path | None, typer.Option("--keyframes", help="关键帧目录")] = None,
    out: Annotated[Path | None, typer.Option("--out", help="任务输出目录（默认项目内 jobs/shots）")] = None,
    frames: Annotated[int, typer.Option("--frames", help="73 或 121；121 有颜色漂移风险")] = 121,
    allow_missing: Annotated[bool, typer.Option("--allow-missing", help="关键帧尚未生成时也写任务")] = False,
    style: Annotated[str | None, typer.Option("--style", help="使用风格包编译提示词")] = None,
) -> None:
    """由分镜与关键帧生成 Wan 镜头任务文件（不执行）。"""
    from .film import load_project
    from .film.jobs import build_wan_jobs
    from .style_engine import get_pack

    root = find_project_root()
    pack = get_pack(root, style) if style else None
    result = build_wan_jobs(load_project(root, project), root, keyframes_dir=keyframes, out_dir=out,
                            frames=frames, allow_missing_keyframes=allow_missing, pack=pack)
    console.print_json(json.dumps(result, ensure_ascii=False))


@film_app.command("voice")
def film_voice(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
    base_url: Annotated[str | None, typer.Option("--base-url", help="TTS 服务地址")] = None,
) -> None:
    """逐句合成旁白（需要 50000 上的 VoxCPM2 服务）。"""
    from .film import load_project
    from .film.voice import synthesize_narration

    from .voice.zeroshot import ZeroShotError

    root = find_project_root()
    try:
        result = synthesize_narration(load_project(root, project), root, base_url=base_url)
    except ZeroShotError as exc:
        console.print(f"[red]TTS 失败：{exc}[/red]")
        console.print("[dim]确认 50000 上的 VoxCPM2 已 ready：scripts/cosyvoice_server.ps1 -Action status[/dim]")
        raise typer.Exit(1)
    console.print_json(json.dumps(result, ensure_ascii=False))


@film_app.command("assemble")
def film_assemble(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
    out: Annotated[Path | None, typer.Option("--out", help="输出 MP4")] = None,
    bgm: Annotated[Path | None, typer.Option("--bgm", help="BGM 文件（可选）")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="只打印 FFmpeg 命令")] = False,
) -> None:
    """按 timeline.json 合成成片（镜头缺失时使用关键帧静帧）。"""
    from .film import load_project
    from .film.assemble import assemble

    root = find_project_root()
    try:
        result = assemble(load_project(root, project), root, out=out, bgm=bgm, dry_run=dry_run)
    except FileNotFoundError as exc:
        console.print(f"[red]无法合成：{exc}[/red]")
        console.print("[dim]先跑 film keyframes 生成关键帧任务，或把镜头产物放进 shots/<shot_id>/[/dim]")
        raise typer.Exit(1)
    except RuntimeError as exc:
        console.print(f"[red]FFmpeg 失败：{str(exc)[-800:]}[/red]")
        raise typer.Exit(1)
    if dry_run:
        console.print(" ".join(result["command"]))
    else:
        console.print_json(json.dumps({"out": result["out"]}, ensure_ascii=False))


@film_app.command("contact-sheet")
def film_contact_sheet(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
    out: Annotated[Path | None, typer.Option("--out", help="输出 PNG（默认 qc/keyframes_contact_sheet.png）")] = None,
) -> None:
    """把关键帧拼成联排图，供 H2 人工审片。"""
    from .film import load_project, project_dir
    from .film.review import build_contact_sheet

    root = find_project_root()
    loaded = load_project(root, project)
    if loaded.storyboard is None:
        console.print("[red]缺少 storyboard.json[/red]")
        raise typer.Exit(1)
    directory = project_dir(root, project)
    target = out or (directory / "qc" / "keyframes_contact_sheet.png")
    path = build_contact_sheet(directory, loaded.storyboard, target)
    console.print_json(json.dumps({"contact_sheet": str(path)}, ensure_ascii=False))


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
