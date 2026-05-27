#!/usr/bin/env python3
"""Read-only CLI for OS engine replay traces."""

from __future__ import annotations

import argparse
from pathlib import Path

from kernel.os_engine.replay_browser import (
    ReplayBrowserFilter,
    browse_os_engine_replay,
    render_replay_browser_summary,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render read-only OS engine replay traces.")
    parser.add_argument("root", type=Path)
    parser.add_argument("--db-name", default="os_engine.sqlite3")
    parser.add_argument("--job-id")
    parser.add_argument("--status")
    parser.add_argument("--limit", type=int, default=50)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    summary = browse_os_engine_replay(
        args.root,
        ReplayBrowserFilter(job_id=args.job_id, status=args.status, limit=args.limit),
        db_name=args.db_name,
    )
    print(render_replay_browser_summary(summary), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
