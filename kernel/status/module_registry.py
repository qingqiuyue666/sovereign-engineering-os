"""Known V12 module registry."""

from __future__ import annotations

from pathlib import Path

__all__ = ["known_v12_modules"]

_MODULES = {
    "security": "kernel/security/secret_scanner.py",
    "truth_substrate": "kernel/security/taint_propagation.py",
    "tasks": "kernel/tasks/task_manifest.py",
    "cli": "kernel/cli/main.py",
    "dry_run_runtime": "kernel/runtime/dry_run_executor.py",
    "replay": "kernel/replay/replay_verifier.py",
    "audit": "kernel/audit/audit_exporter.py",
    "status": "kernel/status/status_reporter.py",
    "providers": "kernel/providers/mock_provider.py",
    "notifications": "kernel/notifications/telegram_mock.py",
    "vault": "kernel/vault/vault_contract.py",
    "daemon": "kernel/daemon/daemon_contract.py",
    "domain": "kernel/domain/osint_task_contract.py",
    "dashboard": "kernel/dashboard/dashboard_model.py",
}


def known_v12_modules(repo_root: str | Path = ".") -> dict[str, dict[str, object]]:
    root = Path(repo_root)
    return {
        name: {"path": path, "implemented": (root / path).is_file()}
        for name, path in sorted(_MODULES.items())
    }
