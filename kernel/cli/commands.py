"""Dry-run/read-only V12 CLI commands."""

from __future__ import annotations

from pathlib import Path
import json
import sys

from kernel.security.secret_scanner import CoreSecretScanner
from kernel.tasks.task_manifest import validate_task_manifest

from .status_reporter import cli_status_report

__all__ = ["dispatch"]


def dispatch(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        _emit({"ok": False, "error": "command_required"})
        return 2
    command = args[0]
    rest = args[1:]
    if command == "status":
        _emit(cli_status_report())
        return 0
    if command == "health-plan":
        from kernel.status.health_plan import ordered_health_plan

        _emit({"ok": True, "health_plan": ordered_health_plan()})
        return 0
    if command == "version":
        _emit({"ok": True, "version": "v12-foundation-draft"})
        return 0
    if command == "explain-gates":
        _emit(
            {
                "ok": True,
                "gates": [
                    "security_classification",
                    "secret_scanner",
                    "environment_sanitizer",
                    "anti_exfiltration_gate",
                    "ai_context_firewall",
                    "repository_hygiene",
                    "task_manifest",
                    "dry_run_runner",
                    "replay_verifier",
                    "audit_exporter",
                ],
            }
        )
        return 0
    if command == "security-scan-text":
        if len(rest) != 1:
            _emit({"ok": False, "error": "security_scan_text_requires_one_argument"})
            return 2
        result = CoreSecretScanner().scan_text(rest[0], path="cli:security-scan-text")
        _emit({"ok": result.clean, "finding_count": len(result.findings), "findings": [finding.kind for finding in result.findings]})
        return 0 if result.clean else 1
    if command == "validate-task":
        if len(rest) != 1:
            _emit({"ok": False, "error": "validate_task_requires_path"})
            return 2
        try:
            payload = json.loads(Path(rest[0]).read_text(encoding="utf-8"))
        except Exception as exc:
            _emit({"ok": False, "error": "task_file_unreadable_or_invalid_json", "detail": exc.__class__.__name__})
            return 2
        result = validate_task_manifest(payload)
        _emit({"ok": result.accepted, "task_id": result.manifest.get("task_id"), "failures": list(result.failures)})
        return 0 if result.accepted else 1
    _emit({"ok": False, "error": "unknown_command", "command": command})
    return 2


def _emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
