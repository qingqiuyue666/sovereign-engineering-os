"""Generate the private code audit sample pack from caller-provided material only."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kernel.runtime.ai_worker_result_review_packet import (
    build_ai_worker_result_review_packet,
    render_ai_worker_result_review_packet_markdown,
)
from kernel.runtime.branch_audit_report import (
    build_branch_audit_report,
    render_branch_audit_report_markdown,
)
from kernel.runtime.code_audit_daily_report import (
    build_code_audit_daily_report,
    render_code_audit_daily_report_markdown,
)
from kernel.runtime.code_audit_operational_loop import (
    CODE_AUDIT_REQUIRED_LOOP_STEPS,
    build_code_audit_operational_loop,
    render_code_audit_operational_loop_markdown,
)
from kernel.runtime.merge_readiness_report import (
    build_merge_readiness_report,
    render_merge_readiness_report_markdown,
)
from kernel.runtime.post_merge_retrospective_report import (
    build_post_merge_retrospective_report,
    render_post_merge_retrospective_report_markdown,
)

OUTPUT_DIR = ROOT / "docs/operator/examples/code_audit"
OBSERVED_AT = "2026-05-19T00:00:00+08:00"


def _branch_audit_material() -> dict[str, object]:
    return {
        "report_id": "branch-audit-sample-pack-v1",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "base_branch": "main",
        "feature_branch": "codex-noncore-production-assets-v1",
        "base_commit": "15c09fe5b7a2d7d5e2bb53a873eceadd458f2e32",
        "head_commit": "25c09fe5b7a2d7d5e2bb53a873eceadd458f2e42",
        "changed_files": [
            "docs/operator/examples/code_audit/branch_audit_sample_material.json",
            "docs/operator/examples/code_audit/branch_audit_sample_report.md",
            "docs/operator/report_gallery.md",
        ],
        "added_files": [
            "docs/operator/examples/code_audit/branch_audit_sample_material.json",
            "docs/operator/examples/code_audit/branch_audit_sample_report.md",
        ],
        "modified_files": ["docs/operator/report_gallery.md"],
        "deleted_files": [],
        "test_matrix": {
            "sample_scope": "caller-provided synthetic example only",
            "verification_summary": "sample material demonstrates structure only and does not prove live verification",
        },
        "risk_matrix": [
            {
                "risk_id": "R-SAMPLE-1",
                "status": "watch",
                "summary": "sample claims must remain scoped to caller-provided synthetic material only",
            }
        ],
        "boundary_findings": [
            "caller-provided material only",
            "sample pack does not run git or tests internally",
            "no provider execution introduced",
        ],
        "forbidden_changes": [],
        "merge_blockers": [],
        "recommended_action": "defer",
        "rollback_plan": ["remove sample pack files as a unit if the private example set is rejected"],
        "policy_version": "branch-audit-report-v1",
        "code_version": "0.1.0",
    }


def _merge_readiness_material() -> dict[str, object]:
    return {
        "report_id": "merge-readiness-sample-pack-v1",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "source_branch": "codex-noncore-production-assets-v1",
        "target_branch": "main",
        "source_commit": "25c09fe5b7a2d7d5e2bb53a873eceadd458f2e42",
        "target_commit": "15c09fe5b7a2d7d5e2bb53a873eceadd458f2e32",
        "changed_files": [
            "docs/operator/examples/code_audit/merge_readiness_sample_material.json",
            "docs/operator/examples/code_audit/merge_readiness_sample_report.md",
            "docs/operator/forms/merge_readiness_form.md",
        ],
        "protected_files_status": {
            "Makefile": {"status": "unchanged", "safe": True},
            "root_README": {"status": "unchanged", "safe": True},
            "root_integrity_manifests": {"status": "unchanged", "safe": True},
            "health_gate_wiring": {"status": "unchanged", "safe": True},
            "governance_files": {"status": "unchanged", "safe": True},
            "schema_files": {"status": "unchanged", "safe": True},
        },
        "test_matrix": {
            "sample_scope": "caller-provided synthetic example only",
            "required_verification": "sample pack does not prove git diff, clean tree, or live merge readiness",
        },
        "clean_tree_status": {"status": "caller reported clean in sample scope"},
        "diff_check_status": {"status": "caller reported checked in sample scope"},
        "root_integrity_status": {"status": "caller reported preserved in sample scope"},
        "blocked_capability_status": {"violations": []},
        "merge_decision": "needs_human_review",
        "merge_blockers": [
            "sample pack is demonstrative only and must not be treated as an actual merge gate decision",
        ],
        "rollback_plan": ["remove sample merge readiness assets as a unit if the sample pack is not approved"],
        "policy_version": "merge-readiness-report-v1",
        "code_version": "0.1.0",
    }


def _ai_worker_result_review_material() -> dict[str, object]:
    return {
        "packet_id": "ai-worker-result-review-sample-pack-v1",
        "worker_name": "codex-sample-worker",
        "claimed_branch": "codex-noncore-production-assets-v1",
        "claimed_commit": "25c09fe5b7a2d7d5e2bb53a873eceadd458f2e42",
        "claimed_files_changed": [
            "docs/operator/examples/code_audit/ai_worker_result_review_sample_material.json",
            "docs/operator/examples/code_audit/ai_worker_result_review_sample_report.md",
        ],
        "claimed_tests_run": [
            "caller-provided sample verification summary only",
            "python3 -m unittest tests.tracer_bullet.test_code_audit_sample_pack -v",
        ],
        "claimed_results": [
            "sample report was rendered from synthetic caller-provided material only",
            "worker claims are not trusted without human review",
        ],
        "claimed_boundaries_preserved": [
            "no provider execution introduced",
            "no production autonomy introduced",
            "no protected root files changed",
        ],
        "claimed_risks": [
            "sample worker output must not be mistaken for live branch verification",
        ],
        "claimed_rollback_plan": [
            "remove sample worker review files as a unit if sample review artifacts are rejected",
        ],
        "missing_sections": [],
        "contradiction_findings": [],
        "review_decision": "requires_human_verification",
        "required_human_checks": [
            "confirm sample scope is explicit",
            "confirm no live verification is implied",
        ],
        "policy_version": "ai-worker-result-review-packet-v1",
        "code_version": "0.1.0",
    }


def _post_merge_retrospective_material() -> dict[str, object]:
    return {
        "report_id": "post-merge-retrospective-sample-pack-v1",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "merge_commit": "35c09fe5b7a2d7d5e2bb53a873eceadd458f2e52",
        "merged_branch": "codex-noncore-production-assets-v1",
        "merged_capabilities": [
            "private code audit sample pack example set",
            "operator report gallery navigation",
        ],
        "files_added": [
            "docs/operator/examples/code_audit/post_merge_retrospective_sample_material.json",
            "docs/operator/examples/code_audit/post_merge_retrospective_sample_report.md",
        ],
        "files_modified": ["docs/operator/report_gallery.md"],
        "files_deleted": [],
        "tests_after_merge": [
            "caller reported sample test pass in sample scope only",
        ],
        "risks_retained": [
            "sample retrospective remains synthetic and must not be treated as post-merge evidence",
        ],
        "blocked_capabilities_preserved": [
            "real provider execution remains blocked",
            "production autonomy remains blocked",
            "external actions remain blocked",
        ],
        "lessons_learned": [
            "sample-only reports should restate sample-only boundaries in every packet",
        ],
        "next_actions": [
            "use the sample pack as a formatting reference only",
        ],
        "rollback_route": [
            "remove sample retrospective files as a unit if the example set is revised or rejected",
        ],
        "policy_version": "post-merge-retrospective-report-v1",
        "code_version": "0.1.0",
    }


def _code_audit_daily_material() -> dict[str, object]:
    return {
        "daily_report_id": "code-audit-daily-sample-pack-2026-05-19",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_commit": "15c09fe5b7a2d7d5e2bb53a873eceadd458f2e32",
        "branch_state": {
            "branch": "codex-noncore-production-assets-v1",
            "source": "caller-provided synthetic example only",
        },
        "verification_matrix": {
            "sample_scope": "sample material uses caller-provided synthetic verification summaries only",
            "live_verification": "not performed by this sample pack",
        },
        "changed_capabilities": [
            "code audit sample pack examples",
            "operator forms and task intake templates",
        ],
        "risk_matrix": [
            {
                "risk_id": "R-SAMPLE-DAILY-1",
                "status": "watch",
                "summary": "daily sample can guide formatting but does not prove repository state",
            }
        ],
        "blocked_capabilities": [
            "real provider execution remains blocked",
            "production autonomy remains blocked",
            "financial execution remains blocked",
        ],
        "recommended_next_actions": [
            "treat the report as a sample-only output reference",
            "run required verification commands outside the builder for any real branch decision",
        ],
        "rollback_notes": [
            "remove daily report sample files as a unit if the code audit sample pack changes",
        ],
        "policy_version": "code-audit-daily-report-v1",
        "code_version": "0.1.0",
    }


def _code_audit_operational_loop_material() -> dict[str, object]:
    return {
        "loop_id": "code-audit-operational-loop-sample-pack-v1",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_commit": "15c09fe5b7a2d7d5e2bb53a873eceadd458f2e32",
        "loop_steps": list(CODE_AUDIT_REQUIRED_LOOP_STEPS),
        "required_reports": [
            "AI worker handoff packet",
            "AI worker result review packet",
            "branch audit report",
            "merge readiness report",
            "post-merge retrospective report",
            "code audit daily report",
        ],
        "required_verification": [
            "caller-provided sample verification summaries only",
            "human review before any real decision",
        ],
        "human_review_points": [
            "before sample formats are reused for real work",
            "before any merge or rollback decision",
        ],
        "blocked_actions": [
            "provider execution",
            "production autonomy",
            "external execution",
        ],
        "success_criteria": [
            "all required sample reports exist",
            "sample scope is explicit in every rendered report",
        ],
        "stop_conditions": [
            "missing sample evidence",
            "blocked capability language is weakened",
        ],
        "policy_version": "code-audit-operational-loop-v1",
        "code_version": "0.1.0",
    }


def _code_audit_readme() -> str:
    return """# Code Audit Sample Pack v1

This directory contains a private sample-only pack for the existing Code Audit operational workflow.

## Scope

- Sample-only.
- Caller-provided material only.
- Private-safe and public-safe synthetic content only.
- No secrets, no credentials, no tokens, and no raw prompts.
- No live repository verification is performed by these files.
- Nothing here proves live execution readiness, merge readiness, or post-merge truth.

## Contents

- `branch_audit_sample_material.json` and `branch_audit_sample_report.md`
- `merge_readiness_sample_material.json` and `merge_readiness_sample_report.md`
- `ai_worker_result_review_sample_material.json` and `ai_worker_result_review_sample_report.md`
- `post_merge_retrospective_sample_material.json` and `post_merge_retrospective_sample_report.md`
- `code_audit_daily_sample_material.json` and `code_audit_daily_sample_report.md`
- `code_audit_operational_loop_sample_material.json` and `code_audit_operational_loop_sample_report.md`

## Generation

The checked-in sample reports are generated locally from the matching JSON material by `tools/generate_code_audit_sample_pack.py`.

The generator is local-only and deterministic:

- It does not run git.
- It does not run tests.
- It does not inspect GitHub.
- It does not use network, subprocess, environment reads, or SQLite.
- It writes only the sample files in this directory.

## Use

Use this pack as a structural reference for future private operator reporting. For real branch or merge work, build fresh reports from caller-provided current material and run the required verification outside these sample assets.
"""


SAMPLE_SPECS = (
    {
        "material_name": "branch_audit_sample_material.json",
        "report_name": "branch_audit_sample_report.md",
        "material": _branch_audit_material,
        "builder": build_branch_audit_report,
        "renderer": render_branch_audit_report_markdown,
    },
    {
        "material_name": "merge_readiness_sample_material.json",
        "report_name": "merge_readiness_sample_report.md",
        "material": _merge_readiness_material,
        "builder": build_merge_readiness_report,
        "renderer": render_merge_readiness_report_markdown,
    },
    {
        "material_name": "ai_worker_result_review_sample_material.json",
        "report_name": "ai_worker_result_review_sample_report.md",
        "material": _ai_worker_result_review_material,
        "builder": build_ai_worker_result_review_packet,
        "renderer": render_ai_worker_result_review_packet_markdown,
    },
    {
        "material_name": "post_merge_retrospective_sample_material.json",
        "report_name": "post_merge_retrospective_sample_report.md",
        "material": _post_merge_retrospective_material,
        "builder": build_post_merge_retrospective_report,
        "renderer": render_post_merge_retrospective_report_markdown,
    },
    {
        "material_name": "code_audit_daily_sample_material.json",
        "report_name": "code_audit_daily_sample_report.md",
        "material": _code_audit_daily_material,
        "builder": build_code_audit_daily_report,
        "renderer": render_code_audit_daily_report_markdown,
    },
    {
        "material_name": "code_audit_operational_loop_sample_material.json",
        "report_name": "code_audit_operational_loop_sample_report.md",
        "material": _code_audit_operational_loop_material,
        "builder": build_code_audit_operational_loop,
        "renderer": render_code_audit_operational_loop_markdown,
    },
)

ALLOWED_OUTPUTS = {
    OUTPUT_DIR / "README.md",
    *{OUTPUT_DIR / spec["material_name"] for spec in SAMPLE_SPECS},
    *{OUTPUT_DIR / spec["report_name"] for spec in SAMPLE_SPECS},
}


def build_outputs() -> dict[Path, str]:
    outputs: dict[Path, str] = {OUTPUT_DIR / "README.md": _code_audit_readme()}
    for spec in SAMPLE_SPECS:
        material = deepcopy(spec["material"]())
        report = spec["builder"](material, observed_at=OBSERVED_AT)
        outputs[OUTPUT_DIR / spec["material_name"]] = json.dumps(
            material,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        ) + "\n"
        outputs[OUTPUT_DIR / spec["report_name"]] = spec["renderer"](report)
    _validate_output_targets(outputs)
    return outputs


def write_outputs() -> list[Path]:
    outputs = build_outputs()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for path, content in outputs.items():
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def _validate_output_targets(outputs: dict[Path, str]) -> None:
    paths = set(outputs)
    if paths != ALLOWED_OUTPUTS:
        raise ValueError("sample_pack_outputs_must_match_allowed_output_set")
    for path in paths:
        resolved = path.resolve()
        if resolved.parent != OUTPUT_DIR.resolve():
            raise ValueError("sample_pack_output_must_stay_inside_output_dir")


if __name__ == "__main__":
    for written_path in write_outputs():
        print(written_path.relative_to(ROOT))
