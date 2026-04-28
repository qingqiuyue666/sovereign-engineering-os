"""
P0-17 phase 1 - RecoverySessionHost operator CLI surface.

This module is intentionally separate from ``recovery_cli.py``. It
wraps the P0-15 factory result surface and P0-16 serialization helpers
for operator-facing factory-check and evaluate flows only.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Mapping

from kernel.lifecycle.recovery_session_host import (
    RecoverySessionHost,
    RecoverySessionHostFactoryResult,
    render_factory_result,
    render_recovery_gate_result,
    render_session_host_state,
    try_build_recovery_session_host_from_sqlite,
)


EXIT_OK = 0
EXIT_INVALID_ARGS = 2
EXIT_FACTORY_ERROR = 3
EXIT_UNEXPECTED = 4

SESSION_HOST_CLI_COMMANDS = frozenset({"factory-check", "evaluate"})

SESSION_HOST_CLI_EXIT_CODES = {
    "ok": EXIT_OK,
    "invalid_args": EXIT_INVALID_ARGS,
    "factory_error": EXIT_FACTORY_ERROR,
    "unexpected": EXIT_UNEXPECTED,
}

SESSION_HOST_CLI_TOP_LEVEL_KEYS = {
    "factory-check": frozenset({"command", "factory"}),
    "evaluate": frozenset(
        {"command", "factory", "host_state", "recovery"}
    ),
}

SESSION_HOST_CLI_FACTORY_KEYS = frozenset(
    {
        "ok",
        "db_path",
        "reason_code",
        "message",
        "details",
        "host_present",
        "host_closed",
    }
)

SESSION_HOST_CLI_HOST_STATE_KEYS = frozenset({"closed"})

SESSION_HOST_CLI_RECOVERY_KEYS = frozenset(
    {
        "task_id",
        "recovery_class",
        "reason",
        "restored",
        "snapshot_present",
        "current_stage",
        "terminal_state",
        "artifact_count",
        "intent_anchor_count",
        "malformed_event_count",
        "last_event_sequence",
    }
)

SESSION_HOST_CLI_STDIO_CONTRACT = {
    EXIT_OK: {"stdout_json": True, "stderr_empty": True},
    EXIT_FACTORY_ERROR: {"stdout_json": True, "stderr_empty": True},
    EXIT_INVALID_ARGS: {"stdout_json": False, "stderr_empty": False},
    EXIT_UNEXPECTED: {"stdout_json": False, "stderr_empty": False},
}


def session_host_cli_contract_manifest() -> dict[str, object]:
    """Return the read-only session-host CLI contract as JSON-safe data."""
    return {
        "commands": sorted(SESSION_HOST_CLI_COMMANDS),
        "exit_codes": dict(SESSION_HOST_CLI_EXIT_CODES),
        "top_level_keys": {
            command: sorted(keys)
            for command, keys in sorted(
                SESSION_HOST_CLI_TOP_LEVEL_KEYS.items()
            )
        },
        "factory_keys": sorted(SESSION_HOST_CLI_FACTORY_KEYS),
        "host_state_keys": sorted(SESSION_HOST_CLI_HOST_STATE_KEYS),
        "recovery_keys": sorted(SESSION_HOST_CLI_RECOVERY_KEYS),
        "stdio_contract": {
            str(code): dict(contract)
            for code, contract in sorted(
                SESSION_HOST_CLI_STDIO_CONTRACT.items()
            )
        },
        "restore_supported": False,
        "durable_writes": False,
        "legacy_recovery_cli_modified": False,
    }


def build_parser() -> argparse.ArgumentParser:
    """Build the session-host operator CLI parser."""
    parser = argparse.ArgumentParser(
        prog="kernel.lifecycle.recovery_session_host_cli",
        description=(
            "RecoverySessionHost operator CLI. Builds a session host "
            "from an existing SQLite database and emits deterministic "
            "JSON for factory-check or read-only evaluation."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    factory_check = sub.add_parser(
        "factory-check",
        help="Build a session host, close it, and print factory JSON.",
    )
    factory_check.add_argument(
        "--db",
        required=True,
        help="Path to the existing SQLite database file.",
    )

    evaluate = sub.add_parser(
        "evaluate",
        help="Build a session host, evaluate one task_id, and print JSON.",
    )
    evaluate.add_argument(
        "--db",
        required=True,
        help="Path to the existing SQLite database file.",
    )
    evaluate.add_argument(
        "--task-id",
        required=True,
        help="task_id to evaluate.",
    )

    return parser


def _print_json(payload: Mapping[str, object]) -> None:
    sys.stdout.write(json.dumps(payload, sort_keys=True) + "\n")
    sys.stdout.flush()


def _require_host(
    result: RecoverySessionHostFactoryResult,
) -> RecoverySessionHost:
    host = result.host
    if host is None:
        raise RuntimeError("factory result was ok but host was absent")
    return host


def _render_factory_check(db_path: str | Path) -> tuple[int, dict[str, object]]:
    result = try_build_recovery_session_host_from_sqlite(db_path=db_path)
    if not result.ok:
        return EXIT_FACTORY_ERROR, {
            "command": "factory-check",
            "factory": render_factory_result(result),
        }

    host = _require_host(result)
    try:
        pass
    finally:
        if not host.closed:
            host.close()

    return EXIT_OK, {
        "command": "factory-check",
        "factory": render_factory_result(result),
    }


def _render_evaluate(
    db_path: str | Path, task_id: str
) -> tuple[int, dict[str, object]]:
    result = try_build_recovery_session_host_from_sqlite(db_path=db_path)
    if not result.ok:
        return EXIT_FACTORY_ERROR, {
            "command": "evaluate",
            "factory": render_factory_result(result),
            "host_state": None,
            "recovery": None,
        }

    host = _require_host(result)
    try:
        recovery_result = host.evaluate_task(task_id)
    finally:
        if not host.closed:
            host.close()

    return EXIT_OK, {
        "command": "evaluate",
        "factory": render_factory_result(result),
        "host_state": render_session_host_state(host),
        "recovery": render_recovery_gate_result(recovery_result),
    }


def main(argv: list[str] | None = None) -> int:
    """Run the session-host operator CLI and return an exit code."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else EXIT_INVALID_ARGS
        return code if code is not None else EXIT_INVALID_ARGS

    try:
        if args.command == "factory-check":
            code, payload = _render_factory_check(args.db)
        elif args.command == "evaluate":
            code, payload = _render_evaluate(args.db, args.task_id)
        else:
            return EXIT_INVALID_ARGS
        _print_json(payload)
        return code
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return EXIT_UNEXPECTED


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
