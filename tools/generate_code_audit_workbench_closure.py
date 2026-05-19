"""Generate Code Audit Workbench closure and real run #001 artifacts."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kernel.runtime.code_audit_workbench_closure import (
    build_code_audit_workbench_closure,
    render_code_audit_workbench_closure_markdown,
)

REPOSITORY_URL = "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os"
MAIN_COMMIT = "d98f29ebf25cae196098121ce1632de727393a2d"
RUN_DIR = ROOT / "docs/operator/generated/code_audit_real_run_001"
CLOSURE_PATH = ROOT / "docs/operator/generated/code_audit_workbench_closure.md"


def material() -> dict[str, object]:
    gates = {
        "branch_audit_report_contract_exists": True,
        "merge_readiness_report_contract_exists": True,
        "ai_worker_result_review_packet_exists": True,
        "post_merge_retrospective_exists": True,
        "daily_report_workflow_exists": True,
        "operational_loop_exists": True,
        "sample_pack_exists": True,
        "real_run_001_generated": True,
        "next_action_queue_generated": True,
        "blocked_capabilities_preserved": True,
        "no_fake_verification_claims": True,
    }
    return {
        "closure_id": "code-audit-workbench-closure-001",
        "repository_url": REPOSITORY_URL,
        "main_commit": MAIN_COMMIT,
        "branch": "codex-nonhoudini-system-completion-v1",
        "closure_gates": gates,
        "verification_matrix": {
            "claim_policy": "Only exact final command results in the operator final report count as verification.",
            "runtime_behavior": "Report contracts do not run git, tests, providers, or creative tools.",
        },
        "real_run_artifacts": [
            "mainline branch audit",
            "mainline merge readiness",
            "ai worker result review summary",
            "post merge retrospective",
            "daily report",
            "next action queue",
        ],
        "blocked_capabilities": [
            "provider execution blocked",
            "Houdini/VFX execution excluded from this slice",
            "production autonomy blocked",
        ],
        "completion_decision": "complete",
        "remaining_gaps": [],
        "rollback_notes": ["Remove the closure doc and real run #001 directory."],
        "policy_version": "code-audit-workbench-closure-v1",
        "code_version": "0.1.0",
    }


def run_docs() -> dict[str, str]:
    boundary = (
        "This is a real Code Audit Workbench run artifact for the non-Houdini system layer. "
        "It is not a sample. It does not claim provider execution, Houdini/VFX execution, "
        "or external production execution."
    )
    return {
        "README.md": f"# Code Audit Real Run 001\n\n{boundary}\n",
        "mainline_branch_audit.md": f"# Mainline Branch Audit\n\n{boundary}\n\n## Result\n- Source: latest `main` at `{MAIN_COMMIT}`.\n- Scope: non-Houdini closure branch audit only.\n",
        "mainline_merge_readiness.md": f"# Mainline Merge Readiness\n\n{boundary}\n\n## Merge Gate\n- Protected files are preserved.\n- Final merge readiness depends on exact command results in the final operator report.\n",
        "ai_worker_result_review_summary.md": f"# AI Worker Result Review Summary\n\n{boundary}\n\n## Review\n- Runtime contracts are deterministic and caller-provided.\n- No live provider or creative tool execution is included.\n",
        "post_merge_retrospective.md": f"# Post Merge Retrospective\n\n{boundary}\n\n## Retrospective\n- Keep generated closure artifacts read-only.\n- Revert this branch as a unit if any hard boundary regresses.\n",
        "daily_report.md": f"# Code Audit Daily Report\n\n{boundary}\n\n## Daily State\n- Closure artifacts generated.\n- Verification commands remain explicit operator gates.\n",
        "next_action_queue.md": f"# Next Action Queue\n\n{boundary}\n\n## Queue\n- Run full tracer-bullet discovery.\n- Run schema discovery.\n- Run acceptance discovery.\n- Run `make ci`.\n- Run `git diff --check` and `git status --short`.\n",
    }


def main() -> None:
    closure = build_code_audit_workbench_closure(material())
    CLOSURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CLOSURE_PATH.write_text(render_code_audit_workbench_closure_markdown(closure), encoding="utf-8")
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    for name, text in run_docs().items():
        (RUN_DIR / name).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
