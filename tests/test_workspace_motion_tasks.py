from __future__ import annotations

import sys
from pathlib import Path

from conftest import make_video_episode


def test_motion_and_audio_tasks_wire_the_production_cli(workspace) -> None:
    created = make_video_episode(workspace)
    episode_id = created["episode"]["id"]
    root: Path = workspace.root
    base = root / "artifacts" / "ep1"
    (base / "production_script.json").write_text("{}", encoding="utf-8")
    image = base / "assets" / "images" / "shot_001" / "out.png"
    image.parent.mkdir(parents=True, exist_ok=True)
    image.write_bytes((base / "scene.png").read_bytes())
    (base / "motion_shots.json").write_text('{"style_id": "ink_wash", "shots": []}', encoding="utf-8")

    workspace.tasks.TaskRunner(workspace.store)

    plan = workspace.tasks.MotionPlanParams(episode_id=episode_id, style="ink_wash")
    plan_argv = workspace.tasks._motion_plan_argv(plan, "task_test")
    assert plan_argv[:3] == [sys.executable, "-m", "drama_studio.production"]
    assert "--motion-plan" in plan_argv
    assert plan_argv[plan_argv.index("--style") + 1] == "ink_wash"
    assert "--align-audio" in plan_argv
    assert "--leading-ms" in plan_argv and "--gap-ms" in plan_argv
    assert "--skip-static-gate" not in plan_argv
    skipped = workspace.tasks.MotionPlanParams(
        episode_id=episode_id, style="ink_wash", skip_static_gate=True)
    assert "--skip-static-gate" in workspace.tasks._motion_plan_argv(skipped, "task_test")

    render = workspace.tasks.MotionRenderParams(episode_id=episode_id)
    render_argv = workspace.tasks._motion_render_argv(render, "task_test")
    assert render_argv[1].endswith("scripts/motion_build.py")
    assert "artifacts/ep1/motion_shots.json" in render_argv

    audio = workspace.tasks.AudioQAParams(episode_id=episode_id)
    audio_argv = workspace.tasks._audio_qa_argv(audio, "task_test")
    assert audio_argv[1:] == ["-m", "drama_studio.quality", "--audio-manifest", "artifacts/ep1/audio_manifest.json"]

    aesthetic = workspace.tasks.AestheticPlanParams(episode_id=episode_id, style="ink_wash")
    aesthetic_argv = workspace.tasks._aesthetic_plan_argv(aesthetic, "task_test")
    assert aesthetic_argv[1] == "scripts/aesthetic_plan.py"
    assert "--snapshot-root" in aesthetic_argv
    assert "artifacts/ep1/aesthetic/aesthetic_plan.json" in aesthetic_argv
