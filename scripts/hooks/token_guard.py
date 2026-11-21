"""PreToolUse hook enforcing the Token Economy rules in CLAUDE.md.

Reads the hook JSON on stdin, prints a hook decision JSON on stdout.
Fails open: any internal error exits 0 with no output so tool calls
are never blocked by a bug in this guard.

Guards:
1. Long generation jobs (produce.py image/video, live atlas benchmarks)
   must run with run_in_background=true, never as foreground waits.
2. Individual experiment images are steered to the run's contact boards
   (board-first review) when boards exist.
3. One nudge per session when context passes 150K tokens (phase boundary).

Escape hatches: `# token-guard: allow-foreground` in a command,
`crop` in an image filename, or reading the boards themselves.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

CONTEXT_NUDGE_TOKENS = 150_000
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}

GENERATION_PATTERNS = [
    re.compile(r"produce\.py\s+(image|video)\b"),
    re.compile(r"atlas\s+benchmark\b"),
    re.compile(r"run_z_image_style_atlas\.py[^\n]*\bbenchmark\b"),
]


def is_foreground_generation(tool_input: dict) -> bool:
    command = tool_input.get("command", "") or ""
    if tool_input.get("run_in_background"):
        return False
    if "token-guard: allow-foreground" in command:
        return False
    for pattern in GENERATION_PATTERNS:
        if pattern.search(command):
            # Offline benchmark planning (no --live) is fast; allow it.
            if "benchmark" in command and "--live" not in command:
                continue
            return True
    return False


def find_boards(image_path: Path) -> Path | None:
    parts = [p.lower() for p in image_path.parts]
    if "experiments" not in parts:
        return None
    if "boards" in parts or "crop" in image_path.name.lower():
        return None
    for parent in image_path.parents:
        boards = parent / "boards"
        if boards.is_dir() and any(boards.glob("*.png")):
            return boards
        if parent.name.lower() == "experiments":
            break
    return None


def deny(reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def context_tokens(transcript_path: Path) -> int:
    """Approximate current context size from the last usage entry."""
    with transcript_path.open("rb") as fh:
        fh.seek(0, 2)
        size = fh.tell()
        fh.seek(max(0, size - 262_144))
        tail = fh.read().decode("utf-8", errors="replace")
    for line in reversed(tail.splitlines()):
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        usage = (entry.get("message") or {}).get("usage")
        if usage:
            return (
                usage.get("input_tokens", 0)
                + usage.get("cache_read_input_tokens", 0)
                + usage.get("cache_creation_input_tokens", 0)
            )
    return 0


def watchdog(payload: dict) -> dict | None:
    transcript = payload.get("transcript_path")
    session = payload.get("session_id", "unknown")
    if not transcript:
        return None
    path = Path(transcript)
    if not path.is_file():
        return None
    marker = Path(tempfile.gettempdir()) / f"drama-token-nudge-{session}.flag"
    if marker.exists():
        return None
    tokens = context_tokens(path)
    if tokens < CONTEXT_NUDGE_TOKENS:
        return None
    marker.touch()
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": (
                f"[token-guard] Context is ~{tokens // 1000}K tokens "
                f"(threshold {CONTEXT_NUDGE_TOKENS // 1000}K). If the current "
                "phase's deliverables are on disk, persist a short summary and "
                "start a fresh session or /compact now (CLAUDE.md: one phase "
                "per session). Auto-compact fires near 180K."
            ),
        },
        "systemMessage": f"token-guard: context ~{tokens // 1000}K — consider a phase boundary",
    }


def decide(payload: dict) -> dict | None:
    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}

    if tool in ("Bash", "PowerShell") and is_foreground_generation(tool_input):
        return deny(
            "Token Economy rule (CLAUDE.md): long generation jobs must run in "
            "background. Re-issue this call with run_in_background=true and end "
            "the turn; resume on the completion notification. No foreground "
            "blocking waits or polling loops. Override for a deliberate "
            "one-off: append `# token-guard: allow-foreground` to the command."
        )

    if tool == "Read":
        file_path = tool_input.get("file_path", "") or ""
        path = Path(file_path)
        if path.suffix.lower() in IMAGE_SUFFIXES:
            boards = find_boards(path)
            if boards is not None:
                names = sorted(p.name for p in boards.glob("*.png"))[:6]
                return deny(
                    "Token Economy rule (CLAUDE.md): board-first image review. "
                    f"Read the run's contact board instead: {boards} "
                    f"(e.g. {', '.join(names)}). Read an individual full-res "
                    "image only to resolve a specific doubt — crop the region "
                    "of interest to a file with 'crop' in its name and read "
                    "that, or read the board first."
                )

    return watchdog(payload)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        result = decide(payload)
        if result is not None:
            json.dump(result, sys.stdout)
    except Exception:
        pass


if __name__ == "__main__":
    main()