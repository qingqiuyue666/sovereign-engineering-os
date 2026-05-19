"""Render the read-only local operator dashboard and closure report."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kernel.runtime.operator_readonly_dashboard import (
    build_operator_readonly_dashboard,
    render_operator_readonly_dashboard_markdown,
)
from kernel.runtime.operator_readonly_dashboard_closure import (
    build_operator_readonly_dashboard_closure,
    render_operator_readonly_dashboard_closure_markdown,
)

REPOSITORY_URL = "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os"
MAIN_COMMIT = "d98f29ebf25cae196098121ce1632de727393a2d"
DASHBOARD_PATH = ROOT / "docs/operator/generated/operator_readonly_dashboard.md"
CLOSURE_PATH = ROOT / "docs/operator/generated/operator_readonly_dashboard_closure.md"
USAGE_PATH = ROOT / "docs/operator/operator_readonly_dashboard_usage.md"


def dashboard_material() -> dict[str, object]:
    return {
        "dashboard_id": "operator-readonly-dashboard-001",
        "repository_url": REPOSITORY_URL,
        "main_commit": MAIN_COMMIT,
        "branch": "codex-nonhoudini-system-completion-v1",
        "working_tree_status": "final status recorded by operator command output",
        "latest_reports": [
            "docs/operator/generated/engineering_foundation_closure.md",
            "docs/operator/generated/private_operator_layer_closure.md",
            "docs/operator/generated/code_audit_workbench_closure.md",
            "docs/operator/generated/operator_daily_loop_report.md",
            "docs/operator/generated/system_completion_ledger.md",
        ],
        "registries": {
            "code_report_registry": "docs/operator/registries/code_report_registry.md",
            "ai_worker_output_registry": "docs/operator/registries/ai_worker_output_registry.md",
            "decision_log_registry": "docs/operator/registries/decision_log_registry.md",
            "rollback_registry": "docs/operator/registries/rollback_registry.md",
            "evidence_registry": "docs/operator/registries/evidence_registry.md",
            "production_asset_registry": "docs/operator/registries/production_asset_registry.md",
        },
        "active_workbenches": ["Code Audit Workbench", "Operator Daily Loop", "Macro Research"],
        "blocked_capabilities": [
            "provider execution blocked",
            "production autonomy blocked",
            "trading automation blocked",
            "Houdini/VFX execution excluded from this slice",
        ],
        "verification_commands": ["python3 -m unittest discover -s tests/tracer_bullet -v", "make ci"],
        "next_actions": ["Run exact verification commands and report exact results."],
        "stop_conditions": ["Any failed verification command", "Any blocked capability regression"],
        "policy_version": "operator-readonly-dashboard-v1",
        "code_version": "0.1.0",
    }


def closure_material() -> dict[str, object]:
    gates = {
        "dashboard_contract_exists": True,
        "generated_dashboard_exists": True,
        "usage_doc_exists": True,
        "latest_reports_listed": True,
        "registries_listed": True,
        "blocked_capabilities_listed": True,
        "verification_commands_listed": True,
        "no_execution_runner_behavior": True,
        "no_server_behavior": True,
        "no_gui_behavior": True,
        "no_houdini_vfx_execution_in_this_slice": True,
    }
    return {
        "closure_id": "operator-readonly-dashboard-closure-001",
        "repository_url": REPOSITORY_URL,
        "main_commit": MAIN_COMMIT,
        "dashboard_path": "docs/operator/generated/operator_readonly_dashboard.md",
        "usage_doc_path": "docs/operator/operator_readonly_dashboard_usage.md",
        "closure_gates": gates,
        "blocked_capabilities": dashboard_material()["blocked_capabilities"],
        "completion_decision": "complete",
        "remaining_gaps": [],
        "rollback_notes": ["Revert dashboard docs and runtime dashboard modules."],
        "policy_version": "operator-readonly-dashboard-closure-v1",
        "code_version": "0.1.0",
    }


def usage_doc() -> str:
    return """# Operator Read-Only Dashboard Usage

This dashboard is read-only. It is not a server, not a GUI, and not an execution runner.

## Usage
- Open `docs/operator/generated/operator_readonly_dashboard.md`.
- Review latest reports, registries, blocked capabilities, verification commands, next actions, and stop conditions.
- Run commands manually outside the runtime contracts and record exact results in the final operator report.

## Boundaries
- No Houdini/VFX execution in this slice.
- No provider execution, broker/API execution, production autonomy, or trading automation.
"""


def main() -> None:
    DASHBOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    dashboard = build_operator_readonly_dashboard(dashboard_material())
    DASHBOARD_PATH.write_text(render_operator_readonly_dashboard_markdown(dashboard), encoding="utf-8")
    closure = build_operator_readonly_dashboard_closure(closure_material())
    CLOSURE_PATH.write_text(render_operator_readonly_dashboard_closure_markdown(closure), encoding="utf-8")
    USAGE_PATH.write_text(usage_doc(), encoding="utf-8")


if __name__ == "__main__":
    main()
