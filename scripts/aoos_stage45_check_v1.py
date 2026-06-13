#!/usr/bin/env python3
"""Validate AOOS Stage 4/5 documentation and interface anchors."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    Path("docs/aoos/README.md"),
    Path("docs/aoos/core-module-map.md"),
    Path("docs/aoos/domain-packs.md"),
    Path("docs/aoos/stage-5-interfaces.md"),
    Path("templates/aoos/README.md"),
    Path("templates/aoos/evidence-report-template.md"),
    Path("templates/aoos/failure-learning-log-template.md"),
    Path("templates/aoos/incident-record-template.md"),
    Path("templates/aoos/reality-validation-log-template.md"),
    Path("templates/aoos/domain-acceptance-rubric-template.md"),
    Path("templates/aoos/tool-roi-review-template.md"),
    Path("templates/aoos/model-tool-routing-decision-template.md"),
    Path("reports/checkpoints/aoos-stage45-executable-skeleton-v1.md"),
)

REQUIRED_TERMS = (
    "Strategy / Portfolio Governance",
    "Truth / Evidence Governance",
    "Authority / Risk Governance",
    "Execution State Machine",
    "Observability / Audit",
    "Evaluator / Metrics",
    "Learning / Memory Lifecycle",
    "Tool / Complexity Governance",
    "Security / Threat Model",
    "Reality Validation",
    "Incident Response",
    "Anti-Goodhart / Anti-Delusion",
    "Engineering Pack",
    "DCC / Creative Pack",
    "Content Production Pack",
    "Trade / Sales Pack",
    "Business Validation Pack",
    "Research / Intelligence Pack",
    "Security / Compliance Pack",
    "Asset / Supply Chain Pack",
    "Operator UX Pack",
    "Model / Tool Routing Pack",
    "false_done_rate",
    "manual_intervention_rate",
    "retry_success_rate",
    "repeated_failure_rate",
    "cost_per_verified_task",
    "time_to_verified_done",
    "real_world_validation_rate",
    "USE_NOW",
    "USE_LATER",
    "REFERENCE_ONLY",
    "REJECT",
    "memory -> checklist -> playbook -> script -> CI / evaluator / policy",
)

REQUIRED_ROOT_TERMS = (
    ("AGENTS.md", "docs/aoos/"),
    ("README.md", "docs/aoos/"),
    ("ROADMAP.md", "AOOS"),
    ("VALIDATION_REPORT.md", "AOOS"),
)

FORBIDDEN_CLAIMS = (
    "AOOS_STAGE_6_COMPLETE",
    "AOOS_STAGE_7_COMPLETE",
    "customer validation confirmed",
    "paid signal confirmed",
    "production deployment confirmed",
)

LOCAL_PATH_MARKERS = (
    "/Users/",
    "Documents/Codex",
    "files-mentioned-by-the-user",
)


def main() -> int:
    errors: list[str] = []
    combined_parts: list[str] = []

    for relative_path in REQUIRED_FILES:
        path = REPO_ROOT / relative_path
        if not path.exists():
            errors.append(f"missing AOOS file: {relative_path.as_posix()}")
            continue
        combined_parts.append(path.read_text(encoding="utf-8"))

    combined = "\n".join(combined_parts)
    for term in REQUIRED_TERMS:
        if term not in combined:
            errors.append(f"missing AOOS term: {term}")

    for relative_path, term in REQUIRED_ROOT_TERMS:
        path = REPO_ROOT / relative_path
        if not path.exists():
            errors.append(f"missing root integration file: {relative_path}")
            continue
        if term not in path.read_text(encoding="utf-8"):
            errors.append(f"{relative_path} missing AOOS integration term: {term}")

    lower_combined = combined.lower()
    for forbidden in FORBIDDEN_CLAIMS:
        if forbidden.lower() in lower_combined:
            errors.append(f"forbidden AOOS claim present: {forbidden}")

    for marker in LOCAL_PATH_MARKERS:
        if marker in combined:
            errors.append(f"AOOS docs contain local path marker: {marker}")

    if errors:
        print("aoos_stage45_check_v1: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("aoos_stage45_check_v1: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
