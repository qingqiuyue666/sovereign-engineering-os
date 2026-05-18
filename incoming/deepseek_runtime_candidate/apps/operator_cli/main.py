"""Local operator CLI for V12 foundation commands."""

from __future__ import annotations

from pathlib import Path
import json
import sys

from kernel.cli.commands import dispatch as legacy_dispatch
from kernel.status.health_plan import ordered_health_plan
from kernel.tasks.task_contracts import create_operator_task_envelope
from kernel.tasks.task_manifest import validate_task_manifest

__all__ = ["main"]

_LEGACY_COMMANDS = {
    "explain-gates",
    "health-plan",
    "security-scan-text",
    "status",
    "validate-task",
    "version",
}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        return legacy_dispatch(args)
    command = args[0]
    if command in _LEGACY_COMMANDS:
        return legacy_dispatch(args)
    if command == "health":
        _emit({"ok": True, "dry_run_only": True, "health_plan": ["test-root-integrity", *ordered_health_plan()]})
        return 0
    if command == "task":
        return _task(args[1:])
    if command == "run-ledger":
        return _run_ledger(args[1:])
    if command == "audit":
        return _audit(args[1:])
    _emit({"ok": False, "error": "unknown_command", "command": command})
    return 2


def _task(args: list[str]) -> int:
    if not args:
        _emit({"ok": False, "error": "task_subcommand_required"})
        return 2
    subcommand = args[0]
    rest = args[1:]
    if subcommand == "validate":
        if len(rest) != 1:
            _emit({"ok": False, "error": "task_validate_requires_path"})
            return 2
        try:
            payload = json.loads(Path(rest[0]).read_text(encoding="utf-8"))
        except Exception as exc:
            _emit({"ok": False, "error": "task_file_unreadable_or_invalid_json", "detail": exc.__class__.__name__})
            return 2
        result = validate_task_manifest(payload)
        _emit({"ok": result.accepted, "task_id": result.manifest.get("task_id"), "failures": list(result.failures)})
        return 0 if result.accepted else 1
    if subcommand == "create":
        if rest != ["--dry-run"]:
            _emit({"ok": False, "error": "task_create_is_dry_run_only"})
            return 2
        payload = {
            "objective": "operator cli dry run",
            "requested_capabilities": ["local_validation"],
            "classification": "PUBLIC",
            "policy_version": "v12",
            "code_version": "operator-cli",
            "descriptor": {"descriptor_type": "text", "content_digest": "sha256:operator-cli-dry-run"},
        }
        result = create_operator_task_envelope(payload)
        _emit({"ok": result.accepted, "dry_run": True, "task_id": result.envelope.get("task_id"), "failures": list(result.failures)})
        return 0 if result.accepted else 1
    _emit({"ok": False, "error": "unknown_task_subcommand", "subcommand": subcommand})
    return 2


def _run_ledger(args: list[str]) -> int:
    if args != ["create", "--dry-run"]:
        _emit({"ok": False, "error": "run_ledger_create_is_dry_run_only"})
        return 2
    _emit(
        {
            "ok": True,
            "dry_run": True,
            "ledger_write_performed": False,
            "network_accessed": False,
            "secret_value_read": False,
            "ai_provider_call_performed": False,
            "sqlite_mutation_performed": False,
            "production_autonomy_enabled": False,
        }
    )
    return 0


def _audit(args: list[str]) -> int:
    if args != ["summary"]:
        _emit({"ok": False, "error": "audit_summary_required"})
        return 2
    _emit(
        {
            "ok": True,
            "summary_type": "operator_cli_audit_summary_v1",
            "dry_run_only": True,
            "forbidden_runtime_surfaces_absent": True,
        }
    )
    return 0


def _emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
