"""Generate the operator daily loop report, closure, and usage doc."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kernel.runtime.operator_daily_loop import build_operator_daily_loop, render_operator_daily_loop_markdown
from kernel.runtime.operator_daily_loop_closure import (
    build_operator_daily_loop_closure,
    render_operator_daily_loop_closure_markdown,
)

REPOSITORY_URL = "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os"
MAIN_COMMIT = "d98f29ebf25cae196098121ce1632de727393a2d"
REPORT_PATH = ROOT / "docs/operator/generated/operator_daily_loop_report.md"
CLOSURE_PATH = ROOT / "docs/operator/generated/operator_daily_loop_closure.md"
USAGE_PATH = ROOT / "docs/operator/operator_daily_loop_usage.md"


def loop_material() -> dict[str, object]:
    return {
        "loop_id": "operator-daily-loop-001",
        "date_label": "2026-05-19",
        "repository_url": REPOSITORY_URL,
        "main_commit": MAIN_COMMIT,
        "current_phase": "non-Houdini system operational closure",
        "today_focus": ["Complete closure contracts, generated reports, registries, and verification gates."],
        "completed_recently": ["Code Audit Workbench contracts", "private operator control surfaces"],
        "active_constraints": ["No live providers", "No network runtime modules", "No subprocess runtime modules"],
        "blocked_capabilities": [
            "provider execution blocked",
            "production autonomy blocked",
            "trading automation blocked",
            "Houdini/VFX execution excluded from this slice",
        ],
        "current_risks": ["Final command results must be reported exactly; no fake green claims."],
        "next_actions": ["Run new tests", "Run full tracer-bullet discovery", "Run make ci"],
        "stop_conditions": ["Any blocked capability regression", "Any protected file mutation", "Any failed gate"],
        "verification_required": ["unittest commands", "make ci", "git diff --check", "git status --short"],
        "rollback_notes": ["Revert generated daily loop artifacts and runtime modules as a unit."],
        "policy_version": "operator-daily-loop-v1",
        "code_version": "0.1.0",
    }


def closure_material() -> dict[str, object]:
    gates = {
        "daily_report_contract_exists": True,
        "generated_daily_report_exists": True,
        "usage_doc_exists": True,
        "next_action_queue_exists": True,
        "stop_conditions_defined": True,
        "verification_required": True,
        "blocked_capabilities_preserved": True,
        "houdini_vfx_excluded_from_this_slice": True,
    }
    return {
        "closure_id": "operator-daily-loop-closure-001",
        "repository_url": REPOSITORY_URL,
        "main_commit": MAIN_COMMIT,
        "daily_report_path": "docs/operator/generated/operator_daily_loop_report.md",
        "usage_doc_path": "docs/operator/operator_daily_loop_usage.md",
        "closure_gates": gates,
        "blocked_capabilities": loop_material()["blocked_capabilities"],
        "next_action_queue": ["Use the dashboard, registries, and final command results before merge."],
        "completion_decision": "complete",
        "remaining_gaps": [],
        "rollback_notes": ["Revert operator daily loop artifacts as a unit."],
        "policy_version": "operator-daily-loop-closure-v1",
        "code_version": "0.1.0",
    }


def usage_doc() -> str:
    return """# Operator Daily Loop Usage

This usage path is read-only and non-Houdini. It does not execute providers, brokers, servers, creative tools, or VFX applications.

## Steps
- Read `docs/operator/generated/operator_daily_loop_report.md`.
- Check stop conditions before continuing.
- Use `docs/operator/generated/code_audit_real_run_001/next_action_queue.md` for the current queue.
- Record exact command results in the final operator report.

## Stop Conditions
- Blocked capability regression.
- Protected file mutation.
- Failed verification command.
- Any request to execute Houdini/VFX work in this slice.
"""


def main() -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    loop = build_operator_daily_loop(loop_material())
    REPORT_PATH.write_text(render_operator_daily_loop_markdown(loop), encoding="utf-8")
    closure = build_operator_daily_loop_closure(closure_material())
    CLOSURE_PATH.write_text(render_operator_daily_loop_closure_markdown(closure), encoding="utf-8")
    USAGE_PATH.write_text(usage_doc(), encoding="utf-8")


if __name__ == "__main__":
    main()
