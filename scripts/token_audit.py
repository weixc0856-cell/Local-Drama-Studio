"""Audit Claude Code token spend from the CC Switch proxy billing DB.

The proxy DB (``~/.cc-switch/cc-switch.db``, table ``proxy_request_logs``)
is the authoritative per-request record; transcript JSONL usage fields
are duplicated per content block and overcount 2-3x if summed naively.

Billable-input-equivalent weights (Anthropic pricing ratios):
    input x1 + cache_create x1.25 + cache_read x0.1 + output x5

Usage:
    python scripts/token_audit.py                     # sessions, last 7 days
    python scripts/token_audit.py --days 1
    python scripts/token_audit.py --session 45efe43c  # one session, prefix ok
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_DB = Path.home() / ".cc-switch" / "cc-switch.db"

SELECT = """
    SELECT session_id,
           COUNT(*)                AS requests,
           SUM(input_tokens)       AS input,
           SUM(output_tokens)      AS output,
           SUM(cache_read_tokens)  AS cache_read,
           SUM(cache_creation_tokens) AS cache_create,
           MIN(created_at)         AS first_ts,
           MAX(created_at)         AS last_ts
    FROM proxy_request_logs
"""


def equivalent(input_: int, output: int, cache_read: int, cache_create: int) -> float:
    return input_ + 1.25 * cache_create + 0.1 * cache_read + 5 * output


def fmt_ts(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone().strftime("%m-%d %H:%M")


def fmt_m(n: float) -> str:
    return f"{n / 1_000_000:.2f}M" if n >= 1_000_000 else f"{n / 1000:.0f}K"


def audit(db_path: Path, days: float, session: str | None) -> int:
    if not db_path.is_file():
        print(f"proxy DB not found: {db_path}", file=sys.stderr)
        return 1
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    since = int((datetime.now(tz=timezone.utc) - timedelta(days=days)).timestamp())

    if session:
        where = "WHERE session_id LIKE ?"
        params: tuple = (session + "%",)
    else:
        where = "WHERE created_at >= ?"
        params = (since,)

    rows = db.execute(
        SELECT + where + " GROUP BY session_id ORDER BY MAX(created_at) DESC", params
    ).fetchall()
    if not rows:
        print("no requests matched")
        return 0

    print(f"{'session':10} {'window':>14} {'reqs':>5} {'input':>7} {'output':>7} "
          f"{'cache_rd':>9} {'cache_cr':>9} {'equiv':>8}")
    total = 0.0
    for sid, reqs, inp, out, cr, cc, first, last in rows:
        eq = equivalent(inp, out, cr, cc)
        total += eq
        print(f"{(sid or '?')[:8]:10} {fmt_ts(first)}-{fmt_ts(last)[6:]:>8} "
              f"{reqs:>5} {fmt_m(inp):>7} {fmt_m(out):>7} {fmt_m(cr):>9} "
              f"{fmt_m(cc):>9} {fmt_m(eq):>8}")
    print(f"{'TOTAL':10} {'':>14} {'':>5} {'':>7} {'':>7} {'':>9} {'':>9} {fmt_m(total):>8}")

    if session:
        print("\nLargest cache writes (idle re-cache suspects, >100K):")
        big = db.execute(
            "SELECT created_at, cache_creation_tokens, cache_read_tokens "
            "FROM proxy_request_logs WHERE session_id LIKE ? "
            "AND cache_creation_tokens > 100000 "
            "ORDER BY cache_creation_tokens DESC LIMIT 10",
            params,
        ).fetchall()
        for ts, cc, cr in big:
            print(f"  {fmt_ts(ts)}  cache_create={fmt_m(cc)}  cache_read={fmt_m(cr)}")
        if not big:
            print("  none")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=float, default=7)
    parser.add_argument("--session", help="session id (prefix match)")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    sys.exit(audit(args.db, args.days, args.session))


if __name__ == "__main__":
    main()