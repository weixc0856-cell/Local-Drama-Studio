"""Codex hooks enforcing Phase A of the Token Economy port (ADR-032).

Wired by ``.codex/hooks.json`` (see docs/TOKEN_ECONOMY_PORT.md §4):

- PreToolUse ``^(Bash|shell|unified_exec)$`` -> guard 1 (no foreground
  generation) stays OFF until ``produce.py`` gains a submit-and-return
  entry point (Phase B); Codex has no run_in_background. This handler
  also delivers queued guard-3 nudges (see below).
- PreToolUse ``^view_image$`` -> guard 2: board-first image review.
- PostModelRequest -> guard 3 detection: when context passes 150K tokens,
  queue a one-time phase-boundary nudge for the session.

Guard 3 is two-stage on purpose: a real-call probe (2026-11-21, codex-cli
0.171.0) showed that ``additionalContext`` returned on PostModelRequest is
silently dropped — the model never sees it. PreToolUse ``additionalContext``
is the schema-supported injection point, so detection happens on
PostModelRequest (the only event carrying token_usage) and delivery happens
on the next PreToolUse of any matched tool.

Field shapes verified from real calls on 2026-11-21 (codex-cli 0.171.0):
shell calls arrive as tool_name "Bash" with tool_input.command a STRING;
view_image uses tool_input.path (may be RELATIVE to payload.cwd);
PostModelRequest carries a flat token_usage {input_tokens (already
includes cached), output_tokens, total_tokens, ...} plus status/kind.
PreToolUse output accepts hookSpecificOutput.permissionDecision =
allow|deny|ask — the same shape as Claude's token_guard.deny().

Probe mode: while ``<tempdir>/drama-codex-hook-probe/enabled.flag`` exists,
every payload is dumped there (newest 60 kept) for re-verification after
CLI upgrades. Delete the flag when done — no config change, so no hook
re-trust is needed. ``DRAMA_TOKEN_NUDGE_TOKENS`` overrides the 150K nudge
threshold at runtime (used to verify guard 3 without editing the script).

Fails open: any internal error exits 0 with no output, so a guard bug
never blocks work.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

_HOOK_DIR = Path(__file__).resolve().parent
if str(_HOOK_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOK_DIR))

import token_guard as claude_guard  # noqa: E402  (sibling module, stdlib only)

CONTEXT_NUDGE_TOKENS = 150_000
IMAGE_SUFFIXES = claude_guard.IMAGE_SUFFIXES
SHELL_TOOLS = {"Bash", "PowerShell", "shell", "unified_exec", "execve", "local_shell"}

# view_image's path key is "path" (verified); the extra candidates and the
# suffix fallback keep the guard working if a future CLI version renames it.
_PATH_KEYS = ("path", "image_path", "file_path", "absolute_path",
              "image", "filename", "file", "url")


def find_boards(image_path: Path) -> Path | None:
    """Like claude_guard.find_boards, but boards may be png OR jpg/webp.

    (The atlas runs write .jpg contact boards; the Claude guard only globs
    *.png. Kept separate on purpose — the Claude side is out of scope.)
    """
    parts = [p.lower() for p in image_path.parts]
    if "experiments" not in parts:
        return None
    if "boards" in parts or "crop" in image_path.name.lower():
        return None
    for parent in image_path.parents:
        boards = parent / "boards"
        if boards.is_dir():
            for suffix in (".png", ".jpg", ".jpeg", ".webp"):
                if any(boards.glob(f"*{suffix}")):
                    return boards
        if parent.name.lower() == "experiments":
            break
    return None


def image_path_from(tool_input) -> str | None:
    if isinstance(tool_input, str):
        return tool_input if Path(tool_input).suffix.lower() in IMAGE_SUFFIXES else None
    if not isinstance(tool_input, dict):
        return None
    for key in _PATH_KEYS:
        value = tool_input.get(key)
        if isinstance(value, str) and Path(value).suffix.lower() in IMAGE_SUFFIXES:
            return value
    for value in tool_input.values():
        if isinstance(value, str) and Path(value).suffix.lower() in IMAGE_SUFFIXES:
            return value
    return None


def _usage_dicts(payload: dict) -> list[dict]:
    """Collect plausible per-request usage objects from the payload.

    Verified shape is a flat token_usage; the nested variants are kept as
    cheap insurance against CLI changes. Cumulative thread totals are
    ignored: the nudge is about current context size, not lifetime spend.
    """
    found: list[dict] = []

    def add(candidate) -> None:
        if isinstance(candidate, dict) and candidate and candidate not in found:
            found.append(candidate)

    usage = payload.get("token_usage")
    add(usage)
    if isinstance(usage, dict):
        for key in ("last", "last_token_usage", "info", "usage"):
            nested = usage.get(key)
            add(nested)
            if isinstance(nested, dict):
                add(nested.get("last_token_usage"))
                add(nested.get("last"))
    add(payload.get("usage"))
    add(payload.get("last_token_usage"))
    return found


def context_tokens(payload: dict) -> int:
    best = 0
    for usage in _usage_dicts(payload):
        inp = usage.get("input_tokens") or usage.get("prompt_tokens") or 0
        out = usage.get("output_tokens") or usage.get("completion_tokens") or 0
        total = usage.get("total_tokens") or 0
        # OpenAI-style input_tokens already includes the cached span;
        # never add cached_input_tokens on top (that was the 8.22x bug).
        try:
            candidate = max(int(inp) + int(out), int(total))
        except (TypeError, ValueError):
            continue
        best = max(best, candidate)
    return best


def nudge_threshold() -> int:
    """Runtime override for verification runs; default is the 150K rule."""
    try:
        return int(os.environ.get("DRAMA_TOKEN_NUDGE_TOKENS", CONTEXT_NUDGE_TOKENS))
    except ValueError:
        return CONTEXT_NUDGE_TOKENS


def _nudged_marker(session: str) -> Path:
    return Path(tempfile.gettempdir()) / f"drama-token-nudge-codex-{session}.flag"


def _pending_marker(session: str) -> Path:
    return Path(tempfile.gettempdir()) / f"drama-token-nudge-codex-pending-{session}.json"


def watchdog(payload: dict) -> None:
    """PostModelRequest: detect overflow, queue a nudge for the next PreToolUse.

    Returns nothing: additionalContext on PostModelRequest is silently
    dropped by codex-cli 0.171.0 (verified), so delivery is deferred.
    """
    if payload.get("status") not in (None, "completed"):
        return
    tokens = context_tokens(payload)
    if tokens < nudge_threshold():
        return
    session = payload.get("session_id", "unknown")
    if _nudged_marker(session).exists() or _pending_marker(session).exists():
        return
    try:
        _pending_marker(session).write_text(
            json.dumps({"tokens": tokens}), encoding="utf-8")
    except OSError:
        pass


def take_pending_nudge(payload: dict) -> dict | None:
    """PreToolUse: deliver a queued nudge once, as additionalContext."""
    session = payload.get("session_id", "unknown")
    pending = _pending_marker(session)
    if not pending.exists():
        return None
    try:
        tokens = int(json.loads(pending.read_text(encoding="utf-8")).get("tokens", 0))
        pending.unlink(missing_ok=True)
        _nudged_marker(session).touch()
    except (OSError, ValueError):
        return None
    text = (
        f"[token-guard] Context is ~{tokens // 1000}K tokens "
        f"(threshold {nudge_threshold() // 1000}K). If the current phase's "
        "deliverables are on disk, persist a short summary and /compact or "
        "start a fresh session now (AGENTS.md: one phase per session). "
        "Auto-compact fires near 180K."
    )
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": text,
        }
    }


def probe_dump(payload: dict) -> None:
    """While enabled.flag exists, dump raw payloads for schema verification."""
    try:
        probe_dir = Path(tempfile.gettempdir()) / "drama-codex-hook-probe"
        if not (probe_dir / "enabled.flag").exists():
            return
        probe_dir.mkdir(parents=True, exist_ok=True)
        event = payload.get("hook_event_name") or "event"
        tool = payload.get("tool_name") or "-"
        name = f"{event}__{tool}__{time.time_ns()}.json"
        (probe_dir / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        dumps = sorted(probe_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
        for old in dumps[:-60]:
            old.unlink(missing_ok=True)
    except Exception:
        pass


def decide(payload: dict) -> dict | None:
    event = payload.get("hook_event_name", "")
    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}

    if event == "PreToolUse":
        if tool == "view_image":
            path_str = image_path_from(tool_input)
            if path_str:
                path = Path(path_str)
                if not path.is_absolute():
                    cwd = payload.get("cwd")
                    if cwd:
                        path = Path(cwd) / path
                boards = find_boards(path)
                if boards is not None:
                    names = sorted(
                        p.name for p in boards.iterdir()
                        if p.suffix.lower() in IMAGE_SUFFIXES
                    )[:6]
                    return claude_guard.deny(
                        "Token Economy rule (AGENTS.md): board-first image review. "
                        f"View the run's contact board instead: {boards} "
                        f"(e.g. {', '.join(names)}). Open an individual full-res "
                        "image only to resolve a specific doubt — crop the region "
                        "of interest to a file with 'crop' in its name and view "
                        "that, or view the board first."
                    )
        # Guard 1 intentionally OFF in Phase A (port doc §0/§3); the shell
        # handler still delivers queued guard-3 nudges.
        return take_pending_nudge(payload)

    if event == "PostModelRequest":
        watchdog(payload)
        return None

    return None


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        probe_dump(payload)
        result = decide(payload)
        if result is not None:
            json.dump(result, sys.stdout)
    except Exception:
        pass


if __name__ == "__main__":
    main()