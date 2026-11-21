"""Tests for the token-economy PreToolUse guard and the proxy-DB audit script."""

import importlib.util
import json
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_module(name, relpath):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / relpath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


guard = load_module("token_guard", "scripts/hooks/token_guard.py")
audit = load_module("token_audit", "scripts/token_audit.py")


# --------------------------------------------------------------- foreground guard
def test_foreground_image_generation_denied():
    result = guard.decide({
        "tool_name": "Bash",
        "tool_input": {"command": "python src/produce.py image --project p --type portrait --prompt x"},
    })
    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_foreground_video_generation_denied():
    result = guard.decide({
        "tool_name": "PowerShell",
        "tool_input": {"command": "python src/produce.py video --project p --image a.png"},
    })
    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_background_generation_allowed():
    assert guard.decide({
        "tool_name": "Bash",
        "tool_input": {
            "command": "python src/produce.py image --project p --type portrait --prompt x",
            "run_in_background": True,
        },
    }) is None


def test_foreground_override_comment_allowed():
    assert guard.decide({
        "tool_name": "Bash",
        "tool_input": {
            "command": "python src/produce.py image --project p --type portrait --prompt x  # token-guard: allow-foreground",
        },
    }) is None


def test_live_benchmark_denied_offline_allowed():
    live = guard.decide({
        "tool_name": "Bash",
        "tool_input": {"command": "python src/produce.py atlas benchmark --all --seeds 42 --live"},
    })
    assert live["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert guard.decide({
        "tool_name": "Bash",
        "tool_input": {"command": "python src/produce.py atlas benchmark --all --seeds 42"},
    }) is None


def test_fast_commands_untouched():
    for command in (
        "python src/produce.py status",
        "python src/produce.py atlas list -c C",
        "python src/produce.py atlas score --run-dir r --style s --mode recipe --seed 42 --purity 4",
        "git status",
        ".venv\\Scripts\\python.exe -m pytest",
    ):
        assert guard.decide({"tool_name": "Bash", "tool_input": {"command": command}}) is None


# --------------------------------------------------------------- board-first guard
def make_run(tmp_path, with_boards=True):
    run = tmp_path / "studio_data" / "experiments" / "z_image_styles" / "run1"
    images = run / "images"
    images.mkdir(parents=True)
    image = images / "styleA_seed42.png"
    image.write_bytes(b"png")
    if with_boards:
        boards = run / "boards"
        boards.mkdir()
        (boards / "board_C.png").write_bytes(b"png")
    return image


def test_experiment_image_steered_to_board(tmp_path):
    image = make_run(tmp_path)
    result = guard.decide({"tool_name": "Read", "tool_input": {"file_path": str(image)}})
    assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "boards" in result["hookSpecificOutput"]["permissionDecisionReason"]


def test_experiment_image_allowed_without_boards(tmp_path):
    image = make_run(tmp_path, with_boards=False)
    assert guard.decide({"tool_name": "Read", "tool_input": {"file_path": str(image)}}) is None


def test_board_and_crop_reads_allowed(tmp_path):
    image = make_run(tmp_path)
    board = image.parent.parent / "boards" / "board_C.png"
    crop = image.parent / "styleA_seed42_crop_eyes.png"
    crop.write_bytes(b"png")
    for path in (board, crop):
        assert guard.decide({"tool_name": "Read", "tool_input": {"file_path": str(path)}}) is None


def test_non_experiment_image_allowed(tmp_path):
    image = tmp_path / "studio_data" / "deliver" / "p" / "anchor.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"png")
    assert guard.decide({"tool_name": "Read", "tool_input": {"file_path": str(image)}}) is None


def test_text_reads_untouched(tmp_path):
    assert guard.decide({
        "tool_name": "Read",
        "tool_input": {"file_path": str(REPO_ROOT / "CLAUDE.md")},
    }) is None


# ------------------------------------------------------------------- watchdog
def write_transcript(path, tokens):
    entry = {"message": {"usage": {
        "input_tokens": 10,
        "cache_read_input_tokens": tokens - 10,
        "cache_creation_input_tokens": 0,
    }}}
    path.write_text(json.dumps(entry) + "\n", encoding="utf-8")


def test_watchdog_nudges_once_above_threshold(tmp_path, monkeypatch):
    monkeypatch.setattr(guard.tempfile, "gettempdir", lambda: str(tmp_path))
    transcript = tmp_path / "session.jsonl"
    write_transcript(transcript, 160_000)
    payload = {"tool_name": "Bash", "tool_input": {"command": "ls"},
               "transcript_path": str(transcript), "session_id": "s1"}
    first = guard.decide(payload)
    assert "additionalContext" in first["hookSpecificOutput"]
    assert guard.decide(payload) is None


def test_watchdog_quiet_below_threshold(tmp_path, monkeypatch):
    monkeypatch.setattr(guard.tempfile, "gettempdir", lambda: str(tmp_path))
    transcript = tmp_path / "session.jsonl"
    write_transcript(transcript, 90_000)
    assert guard.decide({"tool_name": "Bash", "tool_input": {"command": "ls"},
                         "transcript_path": str(transcript), "session_id": "s2"}) is None


def test_guard_fails_open_on_garbage():
    # decide() with malformed payload must not raise
    assert guard.decide({}) is None
    assert guard.decide({"tool_name": "Read", "tool_input": {"file_path": ""}}) is None


# --------------------------------------------------------------------- audit
def test_equivalent_weights():
    assert audit.equivalent(1000, 100, 10_000, 1000) == 1000 + 500 + 1000 + 1250


def test_equivalent_openai_semantics_subtracts_cached_span():
    # OpenAI-style input_tokens already contains cache_read; counting it twice
    # inflated Codex spend ~8x before this was corrected.
    assert audit.equivalent(6000, 100, 5000, 0, semantics=1) == 1000 + 500 + 500
    assert audit.equivalent(6000, 100, 5000, 0, semantics=2) == 6000 + 500 + 500


def make_db(tmp_path):
    db_path = tmp_path / "cc-switch.db"
    db = sqlite3.connect(db_path)
    db.execute("""CREATE TABLE proxy_request_logs (
        session_id TEXT, app_type TEXT, input_token_semantics INTEGER,
        input_tokens INTEGER, output_tokens INTEGER,
        cache_read_tokens INTEGER, cache_creation_tokens INTEGER, created_at INTEGER)""")
    return db_path, db


def test_audit_reads_proxy_db(tmp_path, capsys):
    db_path, db = make_db(tmp_path)
    db.execute("INSERT INTO proxy_request_logs VALUES ('abc12345-x','claude',2,100,200,50000,200000,1763600000)")
    db.execute("INSERT INTO proxy_request_logs VALUES ('abc12345-x','claude',2,100,200,50000,50000,1763603600)")
    db.commit()
    db.close()
    assert audit.audit(db_path, days=36500, session="abc12345") == 0
    out = capsys.readouterr().out
    assert "abc12345" in out
    assert "claude" in out
    assert "TOTAL" in out
    assert "idle re-cache" in out


def test_audit_codex_rows_not_double_counted(tmp_path, capsys):
    db_path, db = make_db(tmp_path)
    db.execute("INSERT INTO proxy_request_logs VALUES ('cdx12345-x','codex',1,6000,100,5000,0,1763600000)")
    db.commit()
    db.close()
    assert audit.audit(db_path, days=36500, session=None, app="codex") == 0
    out = capsys.readouterr().out
    assert "2K" in out
    assert "7K" not in out