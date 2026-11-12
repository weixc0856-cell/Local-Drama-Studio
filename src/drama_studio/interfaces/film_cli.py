"""CLI for the Script-to-Film production layer.

The film layer owns project data and orchestration, not FFmpeg. Every command
here either writes a validated contract or calls the shared build engine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from drama_studio.paths import output_root, repo_root
from drama_studio.application.film.assemble import AssembleError, assemble as run_assemble
from drama_studio.application.film.audio import AudioError, load_audio_manifest
from drama_studio.application.film.clips import ClipError, build_clips
from drama_studio.application.film.config import load_production
from drama_studio.application.film.motion_plan import build_motion_plan, render_motion
from drama_studio.application.film.project import load_project, project_dir, validate_project
from drama_studio.application.film.status import film_status, record_review, write_state
from drama_studio.application.film.timeline import build_edit_timeline, build_timeline
from drama_studio.application.film.upscale import UpscaleError
from drama_studio.application.film.assets import resolve_all

film_app = typer.Typer(no_args_is_help=True, add_completion=False,
                       help="Script-to-Film 制作层")


def _meta(directory: Path) -> dict:
    return json.loads((directory / "project.json").read_text(encoding="utf-8"))


def _timeline_for(project, root: Path, *, planned: bool = False):
    if project.storyboard is None:
        raise typer.BadParameter("storyboard.json is required")
    directory = project_dir(root, project.project_id)
    settings = load_production(_meta(directory))
    audio_path = directory / "assets" / "audio" / "audio_manifest.json"
    if planned or not audio_path.is_file():
        return build_timeline(project.storyboard, fps=settings.fps), settings
    manifest = load_audio_manifest(audio_path)
    assets = resolve_all(directory, [shot.shot_id for shot in project.storyboard.shots])
    return build_edit_timeline(project.storyboard, manifest, settings=settings, assets=assets), settings


@film_app.command("init")
def film_init(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
    text: Annotated[Path, typer.Option("--text", help="原始文本文件（UTF-8/GBK）")],
    title: Annotated[str | None, typer.Option("--title", help="作品标题")] = None,
    author: Annotated[str, typer.Option("--author", help="作者")] = "",
    dynasty: Annotated[str | None, typer.Option("--dynasty", help="朝代")] = None,
    style: Annotated[str, typer.Option("--style", help="风格包 id")] = "oriental.ink_wash",
    duration: Annotated[float | None, typer.Option("--duration", help="目标时长秒数（规划用）")] = None,
    speed: Annotated[float, typer.Option("--speed", help="旁白语速 0.5-2.0")] = 1.0,
    force: Annotated[bool, typer.Option("--force", help="覆盖已有项目数据")] = False,
) -> None:
    """从一段文本创建影视项目：分句、旁白、视觉圣经、导演节拍与分镜。"""
    from drama_studio.application.film.script import ScriptError, init_project

    root = output_root()
    raw = text.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            body = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        typer.echo(f"无法解码文本：{text}")
        raise typer.Exit(1)
    try:
        result = init_project(
            root, project,
            title=title or text.stem,
            text=body,
            author=author,
            dynasty=dynasty,
            style_id=style,
            target_duration_seconds=duration,
            speed=speed,
            force=force,
        )
    except ScriptError as exc:
        typer.echo(f"初始化失败：{exc}")
        raise typer.Exit(1)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@film_app.command("script")
def film_script(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
    text: Annotated[Path | None, typer.Option("--text", help="原始文本文件；留空读 source.json")] = None,
    duration: Annotated[float | None, typer.Option("--duration", help="目标时长秒数（规划用）")] = None,
    speed: Annotated[float, typer.Option("--speed", help="旁白语速 0.5-2.0")] = 1.0,
    write_storyboard: Annotated[bool, typer.Option("--write-storyboard", help="同时写 storyboard.json")] = False,
) -> None:
    """为已有项目重做分句、旁白与导演节拍；不覆盖视觉圣经。"""
    from drama_studio.domain.style import get_pack
    from drama_studio.application.film.project import SOURCE_FILE
    from drama_studio.application.film.script import ScriptError, build_beats, build_narration, build_screenplay, split_text

    root = output_root()
    loaded = load_project(root, project)
    directory = project_dir(root, project)
    if text is not None:
        raw = text.read_bytes()
        for encoding in ("utf-8-sig", "utf-8", "gb18030"):
            try:
                body = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            typer.echo(f"无法解码文本：{text}")
            raise typer.Exit(1)
    else:
        source_path = directory / SOURCE_FILE
        if not source_path.is_file():
            typer.echo("缺少 source.json；用 --text 指定文本")
            raise typer.Exit(1)
        body = json.loads(source_path.read_text(encoding="utf-8"))["text"]
    if loaded.bible is None:
        typer.echo("缺少 visual_bible.yaml；先运行 film init")
        raise typer.Exit(1)
    settings = load_production(_meta(directory))
    pack = get_pack(repo_root(), loaded.style_id) if loaded.style_id else None
    try:
        lines = split_text(body)
        narration = build_narration(project, lines, speed=speed)
        screenplay = build_screenplay(project, _meta(directory).get("title", project), body)
        beats = build_beats(
            body, narration, loaded.bible, settings=settings,
            allowed_cameras=list(pack.camera.allowed_moves) if pack else None,
            target_duration_seconds=duration,
        )
    except ScriptError as exc:
        typer.echo(f"失败：{exc}")
        raise typer.Exit(1)
    (directory / "narration.json").write_text(
        json.dumps(narration.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    (directory / "screenplay.json").write_text(
        json.dumps(screenplay.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    (directory / "beats.json").write_text(
        json.dumps(beats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = {"lines": len(lines), "beats": len(beats)}
    if write_storyboard:
        from drama_studio.application.film.storyboard import plan_storyboard
        board = plan_storyboard(project, beats, loaded.bible)
        (directory / "storyboard.json").write_text(
            json.dumps(board.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        result["shots"] = len(board.shots)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@film_app.command("validate")
def film_validate(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
) -> None:
    """校验项目数据：Schema、镜头链、连续性、旁白引用。"""
    root = output_root()
    report = validate_project(root, project)
    typer.echo(json.dumps(report, ensure_ascii=False, indent=2))
    raise typer.Exit(0 if report["ok"] else 1)


@film_app.command("timeline")
def film_timeline(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
    out: Annotated[Path | None, typer.Option("--out", help="输出路径（默认项目内 timeline.json）")] = None,
    planned: Annotated[bool, typer.Option("--planned", help="忽略真实音频，只用分镜时长")] = False,
) -> None:
    """生成剪辑时间轴；有 audio_manifest 时以旁白真实时长为准。"""
    root = output_root()
    loaded = load_project(root, project)
    try:
        timeline, settings = _timeline_for(loaded, root, planned=planned)
    except AudioError as exc:
        typer.echo(f"音频清单错误：{exc}")
        raise typer.Exit(1)
    target = out or (project_dir(root, project) / "timeline.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(timeline.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    typer.echo(json.dumps({
        "timeline": str(target),
        "mode": "planned" if planned else "audio_first",
        "shots": len(timeline.entries),
        "total_ms": timeline.total_ms,
        "lines": len(timeline.narration_events),
        "fps": settings.fps,
    }, ensure_ascii=False, indent=2))


@film_app.command("plan")
def film_plan(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
    beats: Annotated[Path, typer.Option("--beats", help="导演节拍 JSON（列表）")],
    out: Annotated[Path | None, typer.Option("--out", help="输出路径（默认项目内 storyboard.json）")] = None,
) -> None:
    """把导演节拍写成受校验的 storyboard.json。"""
    from drama_studio.application.film.project import STORYBOARD_FILE
    from drama_studio.application.film.storyboard import plan_storyboard

    root = output_root()
    loaded = load_project(root, project)
    if loaded.bible is None:
        typer.echo("缺少 visual_bible.yaml")
        raise typer.Exit(1)
    beat_list = json.loads(beats.read_text(encoding="utf-8"))
    storyboard = plan_storyboard(project, beat_list, loaded.bible)
    target = out or (project_dir(root, project) / STORYBOARD_FILE)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(storyboard.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    typer.echo(json.dumps({
        "storyboard": str(target),
        "shots": len(storyboard.shots),
        "total_seconds": round(sum(s.duration_seconds for s in storyboard.shots), 2),
    }, ensure_ascii=False, indent=2))


@film_app.command("prompts")
def film_prompts(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
    out: Annotated[Path | None, typer.Option("--out", help="输出目录（默认项目内 prompts/）")] = None,
    style: Annotated[str | None, typer.Option("--style", help="使用风格包编译，默认取 project.json")] = None,
) -> None:
    """由分镜与视觉圣经编译关键帧提示词和 Wan 运动提示词。"""
    from drama_studio.domain.style import compile_image_prompt, compile_video_prompt, get_pack
    from drama_studio.application.film.prompts import compile_shot_prompts

    root = output_root()
    loaded = load_project(root, project)
    if loaded.storyboard is None or loaded.bible is None:
        typer.echo("需要 storyboard.json 与 visual_bible.yaml")
        raise typer.Exit(1)
    target = out or (project_dir(root, project) / "prompts")
    target.mkdir(parents=True, exist_ok=True)
    pack = None
    style_id = style or loaded.style_id
    if style_id:
        try:
            pack = get_pack(repo_root(), style_id)
        except KeyError as exc:
            typer.echo(str(exc))
            raise typer.Exit(1)
    count = 0
    errors = []
    for shot in loaded.storyboard.shots:
        if pack is not None:
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
        payload["style_id"] = style_id
        (target / f"{shot.shot_id}.json").write_text(
            json.dumps({"shot_id": shot.shot_id, **payload}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        count += 1
    typer.echo(json.dumps({"prompts": str(target), "shots": count, "style": style_id,
                           "errors": errors}, ensure_ascii=False, indent=2))
    if errors:
        raise typer.Exit(1)


@film_app.command("keyframes")
def film_keyframes(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
    out: Annotated[Path | None, typer.Option("--out", help="任务输出目录（默认项目内 jobs/keyframes）")] = None,
    style: Annotated[str | None, typer.Option("--style", help="覆盖项目风格包")] = None,
) -> None:
    """由分镜生成 FLUX.3 关键帧任务文件（不执行）。"""
    from drama_studio.domain.style import get_pack
    from drama_studio.application.film.jobs import build_keyframe_jobs

    root = output_root()
    loaded = load_project(root, project)
    style_id = style or loaded.style_id
    pack = get_pack(repo_root(), style_id) if style_id else None
    result = build_keyframe_jobs(loaded, root, out_dir=out, pack=pack)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@film_app.command("wan-jobs")
def film_wan_jobs(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
    keyframes: Annotated[Path | None, typer.Option("--keyframes", help="关键帧目录")] = None,
    out: Annotated[Path | None, typer.Option("--out", help="任务输出目录（默认项目内 jobs/shots）")] = None,
    frames: Annotated[int | None, typer.Option("--frames", help="49/65/73/81/121；默认按镜头时长选择")] = None,
    width: Annotated[int, typer.Option("--width", help="Wan 宽度，必须能被 32 整除")] = 576,
    height: Annotated[int, typer.Option("--height", help="Wan 高度，必须能被 32 整除")] = 1024,
    profile: Annotated[str | None, typer.Option("--profile", help="safe8g = 448x768 + 65 帧")] = None,
    allow_missing: Annotated[bool, typer.Option("--allow-missing", help="关键帧尚未生成时也写任务")] = False,
    style: Annotated[str | None, typer.Option("--style", help="覆盖项目风格包")] = None,
) -> None:
    """由分镜与关键帧生成 Wan 镜头任务文件（不执行）。"""
    from drama_studio.domain.style import get_pack
    from drama_studio.application.film.jobs import build_wan_jobs

    root = output_root()
    loaded = load_project(root, project)
    style_id = style or loaded.style_id
    pack = get_pack(repo_root(), style_id) if style_id else None
    if profile == "safe8g":
        width, height = 448, 768
        frames = frames or 49
    elif profile not in (None, ""):
        typer.echo(f"unknown profile: {profile}")
        raise typer.Exit(1)
    result = build_wan_jobs(loaded, root, keyframes_dir=keyframes, out_dir=out,
                            width=width, height=height, frames=frames,
                            allow_missing_keyframes=allow_missing, pack=pack)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@film_app.command("wan-chain")
def film_wan_chain(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
    shot: Annotated[str, typer.Option("--shot", help="镜头 id，例如 S01")],
    segments: Annotated[int, typer.Option("--segments", help="续接段数")] = 3,
    frames: Annotated[int, typer.Option("--frames", help="每段帧数（4n+1）")] = 49,
    width: Annotated[int, typer.Option("--width", help="Wan 宽度（32 的倍数）")] = 448,
    height: Annotated[int, typer.Option("--height", help="Wan 高度（32 的倍数）")] = 768,
    timeout: Annotated[int, typer.Option("--timeout", help="每段超时秒数")] = 7200,
    seed_base: Annotated[int, typer.Option("--seed-base", help="种子基数；重跑某段时换一个")] = 7100,
    camera: Annotated[str | None, typer.Option("--camera", help="覆盖运镜，例如 static")] = None,
    style: Annotated[str | None, typer.Option("--style", help="覆盖项目风格包")] = None,
) -> None:
    """同一镜头多段 Wan 续接：前段末帧作为后段首帧，最后编码为一个镜头。"""
    from drama_studio.domain.style import get_pack
    from drama_studio.application.film.wan_chain import ChainError, chain_shot

    root = output_root()
    loaded = load_project(root, project)
    style_id = style or loaded.style_id
    pack = get_pack(repo_root(), style_id) if style_id else None
    try:
        result = chain_shot(loaded, root, shot, segments=segments, frames=frames,
                            width=width, height=height, timeout=timeout,
                            seed_base=seed_base, camera_override=camera, pack=pack)
    except ChainError as exc:
        typer.echo(f"续接失败：{exc}")
        raise typer.Exit(1)
    typer.echo(json.dumps({k: v for k, v in result.items() if k != "prompt"},
                          ensure_ascii=False, indent=2))


@film_app.command("voice")
def film_voice(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
    base_url: Annotated[str | None, typer.Option("--base-url", help="TTS 服务地址")] = None,
    force: Annotated[bool, typer.Option("--force", help="忽略已有 WAV，全部重合成")] = False,
    allow_noncommercial: Annotated[bool | None, typer.Option("--allow-noncommercial/--no-allow-noncommercial", help="允许 BLOCKED/非商用音色（仅本地研究）")] = None,
) -> None:
    """逐句合成旁白，写标准 audio_manifest.json（需要 50000 上的 VoxCPM2）。"""
    from drama_studio.application.voice.zeroshot import ZeroShotError
    from drama_studio.application.film.voice import FilmVoiceError, synthesize_narration

    root = output_root()
    settings = load_production(_meta(project_dir(root, project)))
    allow = settings.voice_allow_noncommercial if allow_noncommercial is None else allow_noncommercial
    if allow:
        typer.echo("注意：正在使用非商用/含第三方表演成分的参考音，仅限本地研究，不得发布。")
    try:
        result = synthesize_narration(load_project(root, project), root,
                                      base_url=base_url, force=force,
                                      allow_noncommercial=allow)
    except (ZeroShotError, FilmVoiceError) as exc:
        typer.echo(f"TTS 失败：{exc}")
        typer.echo("确认 50000 上的 VoxCPM2 已 ready：scripts/cosyvoice_server.ps1 -Action status")
        raise typer.Exit(1)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@film_app.command("clips")
def film_clips(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
    policy: Annotated[str, typer.Option("--policy", help="hold_last / slow / trim")] = "hold_last",
    force: Annotated[bool, typer.Option("--force", help="重新编码")] = False,
) -> None:
    """把 Wan PNG 帧序列编码为镜头 MP4，并补齐到时间轴时长。"""
    root = output_root()
    loaded = load_project(root, project)
    timeline, settings = _timeline_for(loaded, root)
    directory = project_dir(root, project)
    try:
        result = build_clips(directory, loaded.storyboard, timeline, fps=settings.fps,
                             width=settings.width, height=settings.height,
                             policy=policy, force=force)
    except ClipError as exc:
        typer.echo(f"镜头编码失败：{exc}")
        raise typer.Exit(1)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@film_app.command("static")
def film_static(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
    force: Annotated[bool, typer.Option("--force", help="重跑已有报告")] = False,
) -> None:
    """逐镜静帧质量门：客观指标 + 人工语义清单（PENDING 不等于通过）。"""
    from drama_studio.application.film.static_gate import StaticGateError, run_static_gate

    root = output_root()
    loaded = load_project(root, project)
    try:
        result = run_static_gate(project_dir(root, project), loaded.storyboard,
                                 root=root, style_id=loaded.style_id, force=force)
    except StaticGateError as exc:
        typer.echo(f"静帧门失败：{exc}")
        raise typer.Exit(1)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@film_app.command("motion")
def film_motion(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
    force: Annotated[bool, typer.Option("--force", help="忽略已有 motion 构建")] = False,
    only: Annotated[str | None, typer.Option("--only", help="只渲染指定镜头，逗号分隔")] = None,
) -> None:
    """为静帧渲染确定性运镜（缓动/推拉/横移），输出到 shots/<id>/*_motion.mp4。"""
    root = output_root()
    loaded = load_project(root, project)
    timeline, settings = _timeline_for(loaded, root)
    directory = project_dir(root, project)
    assets = resolve_all(directory, [shot.shot_id for shot in loaded.storyboard.shots])
    selected = {item.strip() for item in only.split(",")} if only else None
    plan, info = build_motion_plan(directory, loaded.storyboard, timeline, root=root,
                                   style_id=loaded.style_id, settings=settings, assets=assets,
                                   only=selected)
    if plan is None:
        typer.echo(json.dumps({"skipped": info}, ensure_ascii=False, indent=2))
        raise typer.Exit(0)
    result = render_motion(directory, plan, root=root)
    typer.echo(json.dumps({"plan": info, "render": result}, ensure_ascii=False, indent=2))


@film_app.command("upscale")
def film_upscale(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
    shot: Annotated[str | None, typer.Option("--shot", help="只处理指定镜头")] = None,
    backend: Annotated[str | None, typer.Option("--backend", help="lanczos / realesrgan-ncnn")] = None,
    force: Annotated[bool, typer.Option("--force", help="覆盖已有 _sr.mp4")] = False,
    check: Annotated[bool, typer.Option("--check", help="只检测可用后端")] = False,
) -> None:
    """可选的学习型超分：低清 Wan 片段 → 1080x1920；默认 r3_build Lanczos。"""
    from drama_studio.application.film.upscale import UpscaleError, available_backends, upscale_wan_clips

    if check:
        typer.echo(json.dumps(available_backends(), ensure_ascii=False, indent=2))
        return
    root = output_root()
    loaded = load_project(root, project)
    settings = load_production(_meta(project_dir(root, project)))
    chosen = backend or settings.upscale_backend
    if chosen == "lanczos":
        typer.echo("lanczos 已由 r3_build 在合成时执行；要启用学习型超分请用 "
                   "--backend realesrgan-ncnn（需本地 ncnn 可执行文件与权重）")
        return
    shots = [shot] if shot else [item.shot_id for item in loaded.storyboard.shots]
    try:
        result = upscale_wan_clips(project_dir(root, project), shots, backend=chosen,
                                   force=force)
    except UpscaleError as exc:
        typer.echo(f"超分失败：{exc}")
        raise typer.Exit(1)
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2))


@film_app.command("assemble")
def film_assemble(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
    out: Annotated[Path | None, typer.Option("--out", help="构建目录（默认 renders/build-<time>）")] = None,
    bgm: Annotated[str | None, typer.Option("--bgm-id", help="覆盖项目 BGM asset_id")] = None,
    no_motion: Annotated[bool, typer.Option("--no-motion", help="不为静帧渲染运动")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="只准备输入并打印命令")] = False,
    allow_overwrite: Annotated[bool, typer.Option("--allow-overwrite", help="允许使用非空构建目录")] = False,
    force_clips: Annotated[bool, typer.Option("--force-clips", help="重新编码 Wan 帧")] = False,
    skip_static_gate: Annotated[bool, typer.Option("--skip-static-gate", help="显式跳过静帧质量门")] = False,
) -> None:
    """按 audio-first 时间轴合成成片（镜头/字幕/混音/响度由 r3_build 完成）。"""
    root = output_root()
    loaded = load_project(root, project)
    directory = project_dir(root, project)
    settings = load_production(_meta(directory))
    if bgm is not None:
        settings = settings.model_copy(update={"bgm_asset_id": bgm})
    try:
        result = run_assemble(loaded, root, out=out, settings=settings,
                              with_motion=not no_motion, force_clips=force_clips,
                              skip_static_gate=skip_static_gate,
                              dry_run=dry_run, allow_overwrite=allow_overwrite)
    except (AssembleError, AudioError, ClipError, UpscaleError) as exc:
        typer.echo(f"无法合成：{exc}")
        raise typer.Exit(1)
    typer.echo(json.dumps({k: v for k, v in result.items() if k != "plan"},
                          ensure_ascii=False, indent=2))


@film_app.command("status")
def film_status_cmd(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
    write: Annotated[bool, typer.Option("--write", help="写 qc/film_state.json")] = False,
) -> None:
    """从真实文件派生每个镜头的生产状态。"""
    root = output_root()
    loaded = load_project(root, project)
    payload = film_status(loaded, root)
    if write:
        path = write_state(project_dir(root, project), payload)
        payload["state_file"] = str(path)
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


@film_app.command("approve")
def film_approve(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
    kind: Annotated[str, typer.Option("--kind", help="keyframe / video / final")],
    decision: Annotated[str, typer.Option("--decision", help="approve / reject")] = "approve",
    shot: Annotated[str | None, typer.Option("--shot", help="镜头 id；final 不填")] = None,
    note: Annotated[str, typer.Option("--note", help="人工结论说明")] = "",
) -> None:
    """记录人工审核结论（H2 关键帧 / 镜头 / H3 成片）。"""
    if kind not in ("keyframe", "video", "final"):
        typer.echo("kind must be keyframe / video / final")
        raise typer.Exit(1)
    if decision not in ("approve", "reject"):
        typer.echo("decision must be approve / reject")
        raise typer.Exit(1)
    if kind != "final" and not shot:
        typer.echo("--shot is required for keyframe/video")
        raise typer.Exit(1)
    root = output_root()
    reviews = record_review(project_dir(root, project), kind=kind, decision=decision,
                            shot_id=shot, note=note)
    typer.echo(json.dumps(reviews, ensure_ascii=False, indent=2))


@film_app.command("qc")
def film_qc(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
    build: Annotated[Path | None, typer.Option("--build", help="指定构建目录")] = None,
) -> None:
    """对最近一次构建执行技术质量检查。"""
    from drama_studio import quality

    root = output_root()
    directory = project_dir(root, project)
    if build is None:
        candidates = sorted(directory.glob("renders/build-*/build_manifest.json"),
                            key=lambda item: item.stat().st_mtime)
        if not candidates:
            typer.echo("没有构建产物；先运行 film assemble")
            raise typer.Exit(1)
        manifest = candidates[-1]
    else:
        manifest = build if build.is_absolute() else (root / build)
        if manifest.is_dir():
            manifest = manifest / "build_manifest.json"
    report = quality.check_build(manifest, root=root)
    consistency = None
    timeline_path = manifest.parent / "film_timeline.json"
    if timeline_path.is_file():
        from drama_studio.application.film.assemble import AssembleError, verify_build
        from drama_studio.application.film.schemas import EditTimeline
        timeline = EditTimeline.model_validate(json.loads(timeline_path.read_text(encoding="utf-8")))
        try:
            consistency = verify_build(json.loads(manifest.read_text(encoding="utf-8")), timeline)
        except AssembleError as exc:
            typer.echo(f"一致性检查失败：{exc}")
            raise typer.Exit(1)
    typer.echo(json.dumps({"status": report.get("status"),
                           "report": str(manifest.parent / "quality_report.json"),
                           "final": (report.get("final") or {}).get("path"),
                           "consistency": consistency},
                          ensure_ascii=False, indent=2))
    raise typer.Exit(0 if report.get("status") == "PASS" else 1)


@film_app.command("contact-sheet")
def film_contact_sheet(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
    out: Annotated[Path | None, typer.Option("--out", help="输出 PNG")] = None,
    kind: Annotated[str, typer.Option("--kind", help="keyframe（H2）或 clip（H3）")] = "keyframe",
) -> None:
    """把关键帧或镜头首/中/尾帧拼成联排图，供 H2/H3 人工审片。"""
    from drama_studio.application.film.review import build_clip_contact_sheet, build_contact_sheet

    root = output_root()
    loaded = load_project(root, project)
    if loaded.storyboard is None:
        typer.echo("缺少 storyboard.json")
        raise typer.Exit(1)
    directory = project_dir(root, project)
    if kind not in ("keyframe", "clip"):
        typer.echo("kind must be keyframe or clip")
        raise typer.Exit(1)
    target = out or (directory / "qc" / (f"{kind}_contact_sheet.png"))
    path = (build_clip_contact_sheet if kind == "clip" else build_contact_sheet)(
        directory, loaded.storyboard, target)
    typer.echo(json.dumps({"contact_sheet": str(path)}, ensure_ascii=False, indent=2))


@film_app.command("run")
def film_run(
    project: Annotated[str, typer.Option("--project", help="projects/<project_id>")],
    skip_voice: Annotated[bool, typer.Option("--skip-voice", help="复用现有 audio_manifest")] = False,
    out: Annotated[Path | None, typer.Option("--out", help="构建目录")] = None,
    no_motion: Annotated[bool, typer.Option("--no-motion", help="不为静帧渲染运动")] = False,
) -> None:
    """完整 CPU 链路：配音（可选）→ 时间轴 → 镜头编码 → 运动 → 合成 → 质检。"""
    from drama_studio.application.voice.zeroshot import ZeroShotError
    from drama_studio.application.film.voice import FilmVoiceError, synthesize_narration

    root = output_root()
    loaded = load_project(root, project)
    directory = project_dir(root, project)
    audio_path = directory / "assets" / "audio" / "audio_manifest.json"
    settings = load_production(_meta(directory))
    if not skip_voice:
        try:
            synthesize_narration(loaded, root,
                                 allow_noncommercial=settings.voice_allow_noncommercial)
        except (ZeroShotError, FilmVoiceError) as exc:
            typer.echo(f"配音失败：{exc}")
            raise typer.Exit(1)
    elif not audio_path.is_file():
        typer.echo("没有 audio_manifest.json；去掉 --skip-voice 或先运行 film voice")
        raise typer.Exit(1)
    try:
        result = run_assemble(loaded, root, out=out, settings=settings,
                              with_motion=not no_motion)
    except (AssembleError, AudioError, ClipError, UpscaleError) as exc:
        typer.echo(f"合成失败：{exc}")
        raise typer.Exit(1)
    status = film_status(loaded, root)
    write_state(directory, status)
    typer.echo(json.dumps({**{k: v for k, v in result.items() if k != "plan"},
                           "status": status["counts"]}, ensure_ascii=False, indent=2))
