"""Generate the private operator layer closure and control pack."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kernel.runtime.private_operator_layer_closure import (
    build_private_operator_layer_closure,
    render_private_operator_layer_closure_markdown,
)

REPOSITORY_URL = "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os"
MAIN_COMMIT = "d98f29ebf25cae196098121ce1632de727393a2d"
CLOSURE_PATH = ROOT / "docs/operator/generated/private_operator_layer_closure.md"
PACK_PATH = ROOT / "docs/operator/generated/current_operator_control_pack.md"


def material() -> dict[str, object]:
    return {
        "closure_id": "private-operator-layer-closure-001",
        "repository_url": REPOSITORY_URL,
        "main_commit": MAIN_COMMIT,
        "operator_docs": [
            {"title": "operator command center", "path": "docs/operator/operator_command_center.md"},
            {"title": "current state", "path": "docs/operator/current_state.md"},
            {"title": "operating rules", "path": "docs/operator/operating_rules.md"},
            {"title": "blocked capabilities", "path": "docs/operator/blocked_capabilities.md"},
            {"title": "report gallery", "path": "docs/operator/report_gallery.md"},
            {"title": "knowledge base index", "path": "docs/operator/knowledge_base/README.md"},
            {"title": "workspace hygiene", "path": "docs/operator/workspace_hygiene.md"},
            {"title": "current operator control pack", "path": "docs/operator/generated/current_operator_control_pack.md"},
        ],
        "operator_rules": ["Private operator only; deterministic artifacts; no external execution."],
        "handoff_packets": ["docs/operator/ai_worker_handoff_packet.md"],
        "review_forms": ["docs/operator/forms/branch_review_form.md", "docs/operator/forms/merge_readiness_form.md"],
        "task_intake_templates": ["docs/operator/task_intake/code_audit_task_intake.md"],
        "knowledge_indexes": ["docs/operator/knowledge_base/README.md"],
        "sprint_artifacts": ["docs/operator/sprints/README.md"],
        "blocked_capabilities": [
            "provider execution remains blocked",
            "production autonomy remains blocked",
            "trading automation remains blocked",
            "Houdini/VFX execution remains excluded from this slice",
        ],
        "daily_usage_path": "docs/operator/operator_daily_loop_usage.md",
        "completion_decision": "complete",
        "remaining_gaps": [],
        "rollback_notes": ["Remove generated closure/control pack docs and runtime closure module."],
        "policy_version": "private-operator-layer-closure-v1",
        "code_version": "0.1.0",
    }


def control_pack_markdown() -> str:
    return """# Current Operator Control Pack

This pack is private operator control material for the non-Houdini Sovereign Production OS layer.

## Daily Usage Path
- Start with `docs/operator/operator_daily_loop_usage.md`.
- Review `docs/operator/generated/operator_daily_loop_report.md`.
- Check `docs/operator/generated/operator_readonly_dashboard.md`.
- Use registries under `docs/operator/registries/` for evidence and rollback lookup.

## Required Boundaries
- Provider execution remains blocked.
- Production autonomy remains blocked.
- Financial execution remains blocked.
- Trading automation remains blocked.
- Houdini/VFX execution is excluded from this slice.
- No raw prompts, raw provider responses, secrets, or exception dumps are persisted.

## Control Surfaces
- Operator command center: `docs/operator/operator_command_center.md`
- Current state: `docs/operator/current_state.md`
- Operating rules: `docs/operator/operating_rules.md`
- Blocked capabilities: `docs/operator/blocked_capabilities.md`
- Report gallery: `docs/operator/report_gallery.md`
- Knowledge base index: `docs/operator/knowledge_base/README.md`
- Workspace hygiene: `docs/operator/workspace_hygiene.md`
"""


def main() -> None:
    closure = build_private_operator_layer_closure(material())
    CLOSURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CLOSURE_PATH.write_text(render_private_operator_layer_closure_markdown(closure), encoding="utf-8")
    PACK_PATH.write_text(control_pack_markdown(), encoding="utf-8")


if __name__ == "__main__":
    main()
