#!/usr/bin/env python3
"""Read-only CLI for artifact ledger summaries."""

from __future__ import annotations

import argparse
from pathlib import Path

from kernel.evidence.artifact_ledger_viewer import (
    ArtifactLedgerFilter,
    list_artifact_ledger,
    render_artifact_ledger_summary,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a read-only artifact ledger summary.")
    parser.add_argument("root", type=Path)
    parser.add_argument("--task-id")
    parser.add_argument("--run-id")
    parser.add_argument("--milestone")
    parser.add_argument(
        "--artifact-kind",
        choices=("artifact", "receipt", "failure_bundle", "replay_manifest"),
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    summary = list_artifact_ledger(
        args.root,
        ArtifactLedgerFilter(
            task_id=args.task_id,
            run_id=args.run_id,
            milestone=args.milestone,
            artifact_kind=args.artifact_kind,
        ),
    )
    print(render_artifact_ledger_summary(summary), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
