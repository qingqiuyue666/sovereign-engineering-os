#!/usr/bin/env python3
"""Generate the public-safe mainline code audit report sample."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kernel.runtime.code_audit_workbench import build_code_audit_report, render_code_audit_markdown

REPORT_PATH = ROOT / "docs" / "reports" / "sovereign_engineering_os_mainline_audit_report.md"
MAIN_COMMIT = "3d219bc9efa961d315db48afbaec9f3d8c6bf458"
OBSERVED_AT = "2026-05-19T00:00:00+08:00"
VALID_DIGEST = "sha256:" + "1" * 64


def build_mainline_audit_material() -> dict[str, object]:
    """Return explicit structured report inputs for the current mainline sample."""

    return {
        "report_id": "sovereign-engineering-os-mainline-audit-report-v1",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_commit": MAIN_COMMIT,
        "branch_state": {
            "source": "latest mainline snapshot",
            "main_commit": MAIN_COMMIT,
            "tree_state": "clean at verified merge result",
            "branch": "main",
        },
        "merged_slices": [
            "durable operator decision store",
            "durable operator review store",
            "operator control-plane recovery",
            "operator audit export report",
            "read-only status surface",
            "operator work queue",
            "symbolic runbook shell",
            "provider worker boundary preflight",
            "system readiness matrix",
            "local runtime orchestration",
            "review packet",
            "promotion gate",
            "rollback plan",
            "operator review session host",
            "approval and rejection receipts",
            "decision ledger and snapshot",
            "audit hashchain and audit trail",
            "state machine and transitions",
            "retry and backoff",
            "circuit breaker and deadlock handling",
            "watchdog and daemon surface",
        ],
        "test_matrix": {
            "tracer_bullet": "5521 tests, 4 skipped, OK",
            "schemas": "70 tests, OK",
            "acceptance": "156 tests, OK",
            "make_ci": "passed",
            "git_diff_check": "passed",
            "clean_tree_guard": "passed",
        },
        "root_integrity_state": {
            "status": "verified",
            "manifest_policy": "root integrity manifest unchanged by this report asset",
            "verification_digest": VALID_DIGEST,
            "governance_posture": "fail-closed root integrity gate remains authoritative",
        },
        "durable_decision_store_state": {
            "status": "available",
            "mode": "local durable operator decision records",
            "mutation_policy": "report generator does not mutate durable stores",
        },
        "durable_review_store_state": {
            "status": "available",
            "mode": "local durable operator review records",
            "mutation_policy": "report generator does not mutate durable stores",
        },
        "recovery_state": {
            "status": "available",
            "mode": "operator control-plane recovery receipts",
            "failure_policy": "fail closed on invalid recovery material",
        },
        "audit_export_state": {
            "status": "available",
            "mode": "deterministic local audit export",
            "report_boundary": "public-safe Markdown only",
        },
        "status_surface_state": {
            "status": "available",
            "mode": "read-only operator status surface",
        },
        "work_queue_state": {
            "status": "available",
            "mode": "operator work queue present",
        },
        "runbook_shell_state": {
            "status": "available",
            "mode": "symbolic runbook shell only",
            "external_action_policy": "no real external actions enabled",
        },
        "provider_preflight_state": {
            "status": "available",
            "mode": "provider worker boundary preflight",
            "real_provider_execution": "blocked",
        },
        "readiness_matrix_state": {
            "status": "available",
            "real_provider_execution": "blocked",
            "production_autonomy": "blocked",
        },
        "blocked_capabilities": [
            "real provider execution remains blocked",
            "production autonomy remains blocked",
            "real external actions remain blocked",
        ],
        "risk_matrix": [
            {
                "risk_id": "R1",
                "risk": "caller-provided mainline inputs can be stale",
                "status": "controlled",
                "mitigation": "report states the provided main commit and verification matrix explicitly",
            },
            {
                "risk_id": "R2",
                "risk": "real provider execution is intentionally unavailable",
                "status": "blocked by design",
                "mitigation": "future activation requires a separate authorized slice",
            },
            {
                "risk_id": "R3",
                "risk": "production autonomy is intentionally unavailable",
                "status": "blocked by design",
                "mitigation": "future activation requires a separate authorized slice",
            },
        ],
        "next_actions": [
            "review the generated Markdown audit report",
            "keep real provider execution blocked until separately authorized",
            "keep production autonomy blocked until separately authorized",
            "use this report as the first repository-ready production-output asset",
        ],
        "rollback_plan": [
            "revert the code audit workbench module",
            "revert the report generator script",
            "remove the generated Markdown report sample",
            "rerun the required local verification commands",
        ],
        "public_safe_summary": (
            "Sovereign Engineering OS mainline has reached local durable operator-control-plane "
            "closure and can now produce a deterministic repository-ready engineering audit report. "
            "The report is local-only and read-only. Real provider execution remains blocked, and "
            "production autonomy remains blocked."
        ),
        "policy_version": "code-audit-workbench-v1",
        "code_version": "0.1.0",
    }


def generate_report_markdown() -> str:
    report = build_code_audit_report(build_mainline_audit_material(), observed_at=OBSERVED_AT)
    return render_code_audit_markdown(report)


def main() -> int:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(generate_report_markdown(), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
