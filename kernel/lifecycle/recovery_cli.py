"""
P0-6 phase 1 — recovery CLI / operator surface (read-only).

Constitutional anchors:
- v11 §22.1 WAL Durability and Recovery Contract
- v11 §22.5 Replay admission boundary
- v11 §22.10 invariant binding
- foundation §6 (P0 sealing + crash-window proofs)

A minimal argparse-based operator CLI that opens an existing SQLite
database, builds the standard `RecoveryGate` (P0-2 reader + P0-4
artifact-existence resolver + P0-5 classifier composition), and prints
a deterministic JSON evaluation for one `task_id`.

This is an operator surface, not runtime automation. It writes no
durable row, runs no `restore_task_from_snapshot`, and exits cleanly
on every recovery class — including UNRECOVERABLE / NEEDS_MANUAL_REVIEW
which are operator-actionable signals, not error states.

Exit codes:
- 0  successful evaluation (any recovery class)
- 2  invalid CLI arguments (argparse default)
- 3  database open / repository construction error
- 4  unexpected runtime error

Out of scope for this phase:
- restore execution (deferred; CLI is evaluation-only)
- multi-task batch mode
- streaming output
- any non-evaluate subcommand
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Sequence

from kernel.lifecycle.recovery_gate import (
    RecoveryGate,
    RecoveryGateResult,
    build_standard_recovery_gate,
)
from kernel.lifecycle.stage_types import Stage
from kernel.stores.sqlite.repositories import (
    ApprovalArtifactRepository,
    AuditRepository,
    ContextArtifactRepository,
    InferenceArtifactRepository,
    IntentAnchorRepository,
    PatchProposalRepository,
    ReplayAnchorRepository,
    ReviewArtifactRepository,
    RevisionRepository,
    ValidationReceiptRepository,
)
from kernel.stores.sqlite.wal_recovery import open_connection


# Exit codes - keep stable so operator scripts can rely on them.
EXIT_OK = 0
EXIT_INVALID_ARGS = 2
EXIT_DB_ERROR = 3
EXIT_UNEXPECTED = 4


@dataclass(frozen=True)
class _StandardRepositories:
    """Bundle of read-only repositories used by `build_standard_recovery_gate`."""

    audit: AuditRepository
    intent: IntentAnchorRepository
    context: ContextArtifactRepository
    inference: InferenceArtifactRepository
    patch_proposal: PatchProposalRepository
    validation_receipt: ValidationReceiptRepository
    review: ReviewArtifactRepository
    approval: ApprovalArtifactRepository
    revision: RevisionRepository
    replay_anchor: ReplayAnchorRepository


def build_parser() -> argparse.ArgumentParser:
    """Construct the operator CLI argument parser.

    Subcommands:
    - `evaluate` — run RecoveryGate.evaluate against a SQLite database
      and print the deterministic JSON verdict.
    """
    parser = argparse.ArgumentParser(
        prog="kernel.lifecycle.recovery_cli",
        description=(
            "Read-only recovery evaluation CLI. Opens an existing "
            "SQLite database, evaluates one task_id via the standard "
            "RecoveryGate, and prints a deterministic JSON verdict."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    evaluate = sub.add_parser(
        "evaluate",
        help="Evaluate one task_id and print JSON verdict.",
    )
    evaluate.add_argument(
        "--db",
        required=True,
        help="Path to the SQLite database file.",
    )
    evaluate.add_argument(
        "--task-id",
        required=True,
        help="task_id to evaluate.",
    )
    return parser


def _build_repositories(conn: sqlite3.Connection) -> _StandardRepositories:
    return _StandardRepositories(
        audit=AuditRepository(conn),
        intent=IntentAnchorRepository(conn),
        context=ContextArtifactRepository(conn),
        inference=InferenceArtifactRepository(conn),
        patch_proposal=PatchProposalRepository(conn),
        validation_receipt=ValidationReceiptRepository(conn),
        review=ReviewArtifactRepository(conn),
        approval=ApprovalArtifactRepository(conn),
        revision=RevisionRepository(conn),
        replay_anchor=ReplayAnchorRepository(conn),
    )


def _build_gate(repos: _StandardRepositories) -> RecoveryGate:
    return build_standard_recovery_gate(
        audit_repository=repos.audit,
        intent_anchor_repository=repos.intent,
        context_repository=repos.context,
        inference_repository=repos.inference,
        patch_proposal_repository=repos.patch_proposal,
        validation_receipt_repository=repos.validation_receipt,
        review_repository=repos.review,
        approval_repository=repos.approval,
        revision_repository=repos.revision,
        replay_anchor_repository=repos.replay_anchor,
    )


def evaluate_task(
    conn: sqlite3.Connection, task_id: str
) -> RecoveryGateResult:
    """Pure evaluation helper.

    Builds the standard RecoveryGate over `conn`'s repositories and
    invokes `RecoveryGate.evaluate(task_id)`. The connection is
    neither opened nor closed here; the caller owns the lifecycle.
    """
    repos = _build_repositories(conn)
    gate = _build_gate(repos)
    return gate.evaluate(task_id)


def _stage_str(stage: Optional[Stage]) -> Optional[str]:
    return stage.value if stage is not None else None


def render_result(result: RecoveryGateResult) -> dict[str, Any]:
    """Render a `RecoveryGateResult` to a deterministic JSON-ready dict.

    Field order is enforced at print time via `sort_keys=True`.
    Snapshot-derived numeric / string fields are `None` when no
    snapshot is present, so consumers can distinguish "task not in DB"
    from "task with zero artifacts" without ambiguity.
    """
    snap = result.snapshot
    snapshot_present = snap is not None
    return {
        "task_id": result.task_id,
        "recovery_class": result.recovery_class.value,
        "reason": result.reason,
        "restored": bool(result.restored),
        "snapshot_present": snapshot_present,
        "current_stage": _stage_str(snap.current_stage) if snap else None,
        "terminal_state": _stage_str(snap.terminal_state) if snap else None,
        "artifact_count": len(snap.artifact_ids) if snap else 0,
        "intent_anchor_count": snap.intent_anchor_count if snap else None,
        "malformed_event_count": snap.malformed_event_count if snap else None,
        "last_event_sequence": snap.last_event_sequence if snap else None,
    }


def _emit_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Operator entry point.

    Returns the process exit code. Does NOT call `sys.exit` itself
    (except via argparse on invalid arguments, which raises
    `SystemExit(2)` — caught and propagated). Does NOT call
    `restore_if_allowed`. Does NOT write durable rows.
    """
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # argparse exits 2 on invalid arguments; preserve that.
        code = exc.code if isinstance(exc.code, int) else EXIT_INVALID_ARGS
        return code if code is not None else EXIT_INVALID_ARGS

    if args.command != "evaluate":
        # `add_subparsers(required=True)` makes this unreachable for
        # the current parser shape, but guard anyway for forward
        # additions.
        print(
            f"unsupported command: {args.command!r}",
            file=sys.stderr,
        )
        return EXIT_INVALID_ARGS

    conn: Optional[sqlite3.Connection] = None
    try:
        # Read-only operator boundary: the CLI must not initialize a
        # new database as a side effect of a typo. `sqlite3.connect`
        # silently creates a new file when the path does not exist;
        # check first and fail closed with EXIT_DB_ERROR.
        db_path = Path(args.db)
        if not db_path.is_file():
            print(
                "database open / repository construction error: "
                f"database file does not exist: {db_path}",
                file=sys.stderr,
            )
            return EXIT_DB_ERROR
        try:
            conn = open_connection(db_path)
        except Exception as exc:
            print(
                f"database open / repository construction error: {exc}",
                file=sys.stderr,
            )
            return EXIT_DB_ERROR

        try:
            result = evaluate_task(conn, args.task_id)
        except Exception:
            traceback.print_exc(file=sys.stderr)
            return EXIT_UNEXPECTED

        sys.stdout.write(_emit_json(render_result(result)) + "\n")
        sys.stdout.flush()
        return EXIT_OK
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                # Best-effort close. Already past evaluation; do not
                # mask a successful exit code with a close-time error.
                pass


if __name__ == "__main__":  # pragma: no cover - exercised in tests via main()
    sys.exit(main())
