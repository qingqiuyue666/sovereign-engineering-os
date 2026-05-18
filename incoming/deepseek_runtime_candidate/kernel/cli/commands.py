"""Legacy CLI command dispatch for V12 foundation commands."""

from __future__ import annotations

import json
import sys


def dispatch(argv: list[str] | None = None) -> int:
    """Dispatch legacy V12 foundation commands. Returns exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        _emit({"ok": True, "version": "v12-sovereign", "mode": "operator_cli_dry_run"})
        return 0

    command = args[0]

    if command in ("version",):
        _emit({"ok": True, "version": "v12.0.0", "codename": "sovereign", "dry_run_only": True})
        return 0

    if command == "status":
        _emit({"ok": True, "status": "operational", "dry_run_only": True, "active_daemons": 0, "uptime_seconds": 0})
        return 0

    if command == "explain-gates":
        _emit({"ok": True, "gates": ["integrity", "authz", "ledger", "network"], "dry_run_only": True})
        return 0

    if command == "health-plan":
        from kernel.status.health_plan import ordered_health_plan

        _emit({"ok": True, "plan": ["test-root-integrity", *ordered_health_plan()]})
        return 0

    if command == "security-scan-text":
        text = " ".join(args[1:]) if len(args) > 1 else ""
        _emit({"ok": True, "scan_type": "static_text", "input_length": len(text), "findings": []})
        return 0

    if command == "validate-task":
        if len(args) < 2:
            _emit({"ok": False, "error": "validate_task_requires_path"})
            return 2
        from pathlib import Path
        from kernel.tasks.task_manifest import validate_task_manifest

        try:
            payload = json.loads(Path(args[1]).read_text(encoding="utf-8"))
        except Exception as exc:
            _emit({"ok": False, "error": "file_unreadable", "detail": exc.__class__.__name__})
            return 2
        result = validate_task_manifest(payload)
        _emit({"ok": result.accepted, "task_id": result.manifest.get("task_id"), "failures": list(result.failures)})
        return 0 if result.accepted else 1

    _emit({"ok": False, "error": "unknown_legacy_command", "command": command})
    return 2


def _emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
