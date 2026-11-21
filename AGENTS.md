# AGENTS.md — Local-Drama-Studio

Shared instructions for Codex and Antigravity. Full project spec: `CLAUDE.md`.
Token-economy port plan and execution boundaries: `docs/TOKEN_ECONOMY_PORT.md` (ADR-032).

## Path invariants
- Never write drive letters or usernames into git-tracked files. Resolve paths via
  `config/local-paths.yaml` / `drama_studio.paths`; content output lives under `studio_data/`.
- Media binaries and generated outputs never enter git.

## Token economy (measured: one 15h session burned ~12.3M billable-input equiv)
Deliverables live on disk; context is only working memory. Keep it small:
1. **One phase per session.** Persist results (run report / findings doc / scores.csv),
   then `/compact` or start fresh from a short summary. Never drag >150K tokens of
   history into a new phase. Codex auto-compact backstop: 180K (`~/.codex/config.toml`).
2. **Board-first image review.** Judge style/purity from the run's `boards/` contact
   sheets. Open a single full-res image only to resolve a specific doubt — crop the
   region to a file with `crop` in its name first. Every image read stays in context
   and is re-billed on every later call.
3. **Bounded reads over shell peeking.** Prefer dedicated file read/search tools to
   `cat`/`sed`/`head` pipelines.
4. **No foreground waits on long jobs.** Claude: `run_in_background`. Codex/Antigravity:
   the submit-and-return CLI entry does not exist yet (port doc Phase B), so guard 1 is
   intentionally OFF — do not sleep/tail-poll; end the turn and resume on results.
5. **Audit spend from the billing DB** (authoritative; covers all three clients):
   `python scripts/token_audit.py --app claude|codex|agy --days 7`.
   Compare per-phase equivalents before/after a change; never claim savings without
   a baseline.

## Enforcement status
- Claude: `.claude/settings.json` PreToolUse guard, all three guards.
- Codex: `.codex/hooks.json` → `scripts/hooks/codex_token_guard.py`, guards 2+3 only.
  Hooks must be trusted via `/hooks` after any script change, or they silently fail open.
- Antigravity: no script hooks; rules only (port doc §5).
