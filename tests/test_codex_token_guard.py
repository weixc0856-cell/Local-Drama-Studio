"""Tests for the Codex Phase-A token-economy hook (ADR-032 port).

Companion to tests/test_token_guard.py (Claude side). Phase A deliberately
does NOT block foreground generation (guard 1) — see docs/TOKEN_ECONOMY_PORT.md.
Guard 3 is two-stage: PostModelRequest detects overflow and queues a nudge;
the next PreToolUse delivers it as additionalContext (PostModelRequest
additionalContext is silently dropped by codex-cli 0.171.0, verified).
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = REPO_ROOT / "scripts" / "hooks"
SCRIPT = HOOKS_DIR / "codex_token_guard.py"
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))


def load_module(name, relpath):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / relpath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


guard = load_module("codex_token_guard", "scripts/hooks/codex_token_guard.py")


def pre(tool, tool_input, session="s"):
    return {"hook_event_name": "PreToolUse", "tool_name": tool,
            "tool_input": tool_input, "session_id": session}


def post(tokens, session="s", **extra):
    payload = {"hook_event_name": "PostModelRequest", "session_id": session,
               "status": "completed",
               "token_usage": {"input_tokens": tokens, "output_tokens": 100}}
    payload.update(extra)
    return payload


def make_run(tmp_path, board_suffix=".jpg", with_boards=True):
    run = tmp_path / "studio_data" / "experiments" / "z_image_styles" / "run1"
    images = run / "images"
    images.mkdir(parents=True)
    image = images / "styleA_seed42.png"
    image.write_bytes(b"png")
    if with_boards:
        boards = run / "boards"
        boards.mkdir()
        (boards / f"board_C{board_suffix}").write_bytes(b"board")
    return image


# ---------------------------------------------------- guard 1 stays OFF (Phase A)
def test_phase_a_foreground_generation_not_blocked():
    for tool in ("Bash", "shell", "unified_exec"):
        for command in (
            "python src/produce.py image --project p --type portrait --prompt x",
            ["python", "src/produce.py", "video", "--project", "p", "--image", "a.png"],
        ):
            assert guard.decide(pre(tool, {"command": command})) is None


# ----------------------------------------------------------- guard 2: board-first
def test_view_image_steered_to_board(tmp_path):
    image = make_run(tmp_path)  # .jpg boards — the real atlas format
    for key in ("path", "image_path", "file_path", "absolute_path"):
        result = guard.decide(pre("view_image", {key: str(image)}))
        assert result["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "boards" in result["hookSpecificOutput"]["permissionDecisionReason"]


def test_png_boards_also_recognized(tmp_path):
    image = make_run(tmp_path, board_suffix=".png")
    result = guard.decide(pre("view_image", {"path": str(image)}))
    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_unknown_path_key_fallback(tmp_path):
    image = make_run(tmp_path)
    result = guard.decide(pre("view_image", {"weird_key": str(image)}))
    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_board_crop_and_non_experiment_allowed(tmp_path):
    image = make_run(tmp_path)
    board = image.parent.parent / "boards" / "board_C.jpg"
    crop = image.parent / "styleA_seed42_crop_eyes.png"
    crop.write_bytes(b"png")
    other = tmp_path / "studio_data" / "deliver" / "p" / "anchor.png"
    other.parent.mkdir(parents=True)
    other.write_bytes(b"png")
    for path in (board, crop, other):
        assert guard.decide(pre("view_image", {"path": str(path)})) is None


def test_experiment_image_allowed_without_boards(tmp_path):
    image = make_run(tmp_path, with_boards=False)
    assert guard.decide(pre("view_image", {"path": str(image)})) is None


def test_relative_path_resolved_against_cwd(tmp_path):
    make_run(tmp_path)
    rel = "studio_data/experiments/z_image_styles/run1/images/styleA_seed42.png"
    result = guard.decide({"hook_event_name": "PreToolUse", "tool_name": "view_image",
                           "cwd": str(tmp_path), "tool_input": {"path": rel}})
    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"


# ------------------------------------- guard 3: detect on PostModelRequest,
# ------------------------------------- deliver once on the next PreToolUse
def test_watchdog_queues_then_delivers_once(tmp_path, monkeypatch):
    monkeypatch.setattr(guard.tempfile, "gettempdir", lambda: str(tmp_path))
    # OpenAI-style input already includes cached: ~160K, not ~310K.
    payload = post(160_000, session="cx1",
                   token_usage={"input_tokens": 160_000, "cached_input_tokens": 150_000,
                                "output_tokens": 500})
    assert guard.decide(payload) is None  # detection returns no output
    assert guard._pending_marker("cx1").exists()
    guard.decide(payload)  # already queued: no duplicate
    delivered = guard.decide(pre("Bash", {"command": "ls"}, session="cx1"))
    assert delivered["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert "~160K" in delivered["hookSpecificOutput"]["additionalContext"]
    assert not guard._pending_marker("cx1").exists()
    assert guard._nudged_marker("cx1").exists()
    # one nudge per session, even if context keeps growing
    assert guard.decide(post(200_000, session="cx1")) is None
    assert guard.decide(pre("Bash", {"command": "ls"}, session="cx1")) is None


def test_watchdog_quiet_below_threshold(tmp_path, monkeypatch):
    monkeypatch.setattr(guard.tempfile, "gettempdir", lambda: str(tmp_path))
    assert guard.decide(post(90_000, session="cx2")) is None
    assert not guard._pending_marker("cx2").exists()
    assert guard.decide(pre("Bash", {"command": "ls"}, session="cx2")) is None


def test_watchdog_nested_usage_shapes(tmp_path, monkeypatch):
    monkeypatch.setattr(guard.tempfile, "gettempdir", lambda: str(tmp_path))
    shapes = (
        {"last_token_usage": {"input_tokens": 151_000, "output_tokens": 100}},
        {"info": {"last_token_usage": {"input_tokens": 151_000, "output_tokens": 100}}},
        {"last": {"total_tokens": 152_000}},
    )
    for i, usage in enumerate(shapes):
        assert guard.decide(post(0, session="shape%d" % i, token_usage=usage)) is None
        assert guard._pending_marker("shape%d" % i).exists()


def test_watchdog_ignores_cumulative_thread_totals(tmp_path, monkeypatch):
    monkeypatch.setattr(guard.tempfile, "gettempdir", lambda: str(tmp_path))
    guard.decide(post(0, session="cx3", token_usage={
        "total_token_usage": {"input_tokens": 900_000, "output_tokens": 50_000},
        "last_token_usage": {"input_tokens": 20_000, "output_tokens": 100},
    }))
    assert not guard._pending_marker("cx3").exists()


def test_env_threshold_override(tmp_path, monkeypatch):
    monkeypatch.setattr(guard.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setenv("DRAMA_TOKEN_NUDGE_TOKENS", "5000")
    guard.decide(post(6000, session="envth"))
    assert guard._pending_marker("envth").exists()


def test_watchdog_skips_failed_requests(tmp_path, monkeypatch):
    monkeypatch.setattr(guard.tempfile, "gettempdir", lambda: str(tmp_path))
    guard.decide(post(200_000, session="failed1", status="failed"))
    assert not guard._pending_marker("failed1").exists()


def test_nudge_delivered_on_view_image_too(tmp_path, monkeypatch):
    monkeypatch.setattr(guard.tempfile, "gettempdir", lambda: str(tmp_path))
    guard.decide(post(160_000, session="vi"))
    image = tmp_path / "studio_data" / "deliver" / "p" / "anchor.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"png")
    result = guard.decide(pre("view_image", {"path": str(image)}, session="vi"))
    assert "additionalContext" in result["hookSpecificOutput"]


# ------------------------------------------------------------------- robustness
def test_guard_fails_open_on_garbage():
    assert guard.decide({}) is None
    assert guard.decide(pre("view_image", None)) is None
    assert guard.decide({"hook_event_name": "PostModelRequest", "token_usage": "garbage"}) is None


def test_probe_dumps_only_when_enabled(tmp_path, monkeypatch):
    monkeypatch.setattr(guard.tempfile, "gettempdir", lambda: str(tmp_path))
    payload = pre("shell", {"command": "ls"})
    guard.probe_dump(payload)
    probe_dir = tmp_path / "drama-codex-hook-probe"
    assert not probe_dir.exists() or not list(probe_dir.glob("*.json"))
    probe_dir.mkdir(parents=True, exist_ok=True)
    (probe_dir / "enabled.flag").touch()
    guard.probe_dump(payload)
    dumps = list(probe_dir.glob("*.json"))
    assert len(dumps) == 1
    assert json.loads(dumps[0].read_text(encoding="utf-8")) == payload


def test_main_stdin_stdout_contract(tmp_path):
    image = make_run(tmp_path)
    payload = pre("view_image", {"path": str(image)})
    proc = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(payload),
                          capture_output=True, text=True, timeout=60, cwd=str(tmp_path))
    assert proc.returncode == 0
    out = json.loads(proc.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_main_fails_open_on_garbage_stdin():
    proc = subprocess.run([sys.executable, str(SCRIPT)], input="not json",
                          capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0
    assert proc.stdout == ""