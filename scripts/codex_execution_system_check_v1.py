#!/usr/bin/env python3
"""Validate Codex end-to-end execution-system artifacts."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    Path("AGENTS.md"),
    Path("CODEX_EXECUTION_SYSTEM.md"),
    Path("CODEX_CONTINUOUS_EXECUTION_PROTOCOL.md"),
    Path("CODEX_DONE_CRITERIA.md"),
    Path("CODEX_RISK_DOWNGRADE_POLICY.md"),
    Path("CODEX_TASK_QUEUE.md"),
    Path("CODEX_PHASE_QUEUE.md"),
    Path("CODEX_VALIDATION_MATRIX.md"),
    Path("CODEX_DELIVERY_PROTOCOL.md"),
    Path("reports/checkpoints/continuous-execution-state.md"),
    Path("reports/checkpoints/skipped-risk-register.md"),
    Path("reports/checkpoints/execution-sample-v1.md"),
    Path("reports/checkpoints/failure-recovery-sample-v1.md"),
    Path("reports/checkpoints/end-to-end-execution-system-v1-final-report.md"),
    Path("CODEX_EXTERNAL_SOURCE_INTAKE_REGISTRY.md"),
    Path("CODEX_REAL_TASK_THROUGHPUT_LAYER.md"),
    Path("CODEX_ACCEPTANCE_CASE_LIBRARY.md"),
    Path("CODEX_STRONG_VALIDATION_LAYER.md"),
    Path("CODEX_EXTERNAL_PATTERN_ABSORPTION_LAYER.md"),
    Path("CODEX_PERMISSION_SECURITY_LAYER.md"),
    Path("CODEX_PRODUCT_DELIVERY_LAYER.md"),
    Path("CODEX_RUNTIME_STATE_MEMORY_LAYER.md"),
    Path("CODEX_REVIEW_ANTI_HYPE_LAYER.md"),
    Path("CODEX_ORGANIZATIONAL_OPERATING_LAYER.md"),
    Path("CODEX_OPERABILITY_READINESS_LAYER.md"),
    Path("CODEX_RUNTIME_CONTROL_MAP.md"),
    Path("CODEX_SOURCE_PRIORITIZATION_POLICY.md"),
    Path("CODEX_OBSERVABILITY_TOOLING_MAP.md"),
    Path("CODEX_SECURITY_AUTOMATION_GATE_MAP.md"),
    Path("CODEX_BENCHMARK_CONTAMINATION_POLICY.md"),
    Path("CODEX_ECONOMIC_VALUE_EVAL_QUEUE.md"),
    Path("CODEX_INDEPENDENT_REVIEW_GATE.md"),
    Path("CODEX_CI_REALITY_GATE.md"),
    Path("CODEX_RUNNABLE_PRODUCT_SLICE_GATE.md"),
    Path("CODEX_MERGE_RELEASE_GOVERNANCE_GATE.md"),
    Path("reports/checkpoints/eleven-core-delivery-layers-v1-final-report.md"),
    Path("reports/checkpoints/eleven-core-delivery-layers-scorecard-v1.md"),
    Path("reports/checkpoints/external-source-intake-ledger-v1.md"),
    Path("reports/checkpoints/global-source-freshness-audit-v1.md"),
    Path("reports/checkpoints/frontier-gap-search-audit-v1.md"),
    Path("reports/checkpoints/external-project-absorption-shortlist-v1.md"),
    Path("reports/checkpoints/prompt-consistency-world-class-source-audit-v1.md"),
    Path("reports/checkpoints/table-review-residue-closure-v1.md"),
    Path("reports/checkpoints/real-task-throughput-ledger-v1.md"),
    Path("reports/checkpoints/runtime-state-ledger-v1.md"),
    Path("reports/checkpoints/operability-readiness-review-v1.md"),
    Path("reports/checkpoints/real-delivery-benchmark-sample-plan-v1.md"),
    Path("reports/checkpoints/external-source-deep-review-queue-v1.md"),
    Path("reports/checkpoints/independent-review-simulation-v1.md"),
    Path("reports/checkpoints/100-point-maturity-closure-ladder-v1.md"),
    Path("reports/checkpoints/continuous-maturity-iteration-queue-v1.md"),
    Path("reports/checkpoints/real-world-proof-gap-ledger-v1.md"),
    Path("reports/checkpoints/whole-content-completion-checklist-v1.md"),
)

OPTIONAL_IMPLEMENTATION_FILES = (
    Path("scripts/codex_execution_system_check_v1.py"),
)

ELEVEN_LAYER_FILES = (
    Path("CODEX_REAL_TASK_THROUGHPUT_LAYER.md"),
    Path("CODEX_ACCEPTANCE_CASE_LIBRARY.md"),
    Path("CODEX_STRONG_VALIDATION_LAYER.md"),
    Path("CODEX_EXTERNAL_PATTERN_ABSORPTION_LAYER.md"),
    Path("CODEX_PERMISSION_SECURITY_LAYER.md"),
    Path("CODEX_PRODUCT_DELIVERY_LAYER.md"),
    Path("CODEX_RUNTIME_STATE_MEMORY_LAYER.md"),
    Path("CODEX_REVIEW_ANTI_HYPE_LAYER.md"),
    Path("CODEX_ORGANIZATIONAL_OPERATING_LAYER.md"),
    Path("CODEX_OPERABILITY_READINESS_LAYER.md"),
    Path("CODEX_EXTERNAL_SOURCE_INTAKE_REGISTRY.md"),
)

GAP_GATE_FILES = (
    Path("CODEX_RUNTIME_CONTROL_MAP.md"),
    Path("CODEX_SOURCE_PRIORITIZATION_POLICY.md"),
    Path("CODEX_OBSERVABILITY_TOOLING_MAP.md"),
    Path("CODEX_SECURITY_AUTOMATION_GATE_MAP.md"),
    Path("CODEX_BENCHMARK_CONTAMINATION_POLICY.md"),
    Path("CODEX_ECONOMIC_VALUE_EVAL_QUEUE.md"),
    Path("CODEX_INDEPENDENT_REVIEW_GATE.md"),
    Path("CODEX_CI_REALITY_GATE.md"),
    Path("CODEX_RUNNABLE_PRODUCT_SLICE_GATE.md"),
    Path("CODEX_MERGE_RELEASE_GOVERNANCE_GATE.md"),
)

REQUIRED_ELEVEN_LAYER_TERMS = (
    "REAL_TASK_THROUGHPUT_LAYER",
    "ACCEPTANCE_CASE_LIBRARY",
    "STRONG_VALIDATION_LAYER",
    "EXTERNAL_PATTERN_ABSORPTION_LAYER",
    "PERMISSION_SECURITY_LAYER",
    "PRODUCT_DELIVERY_LAYER",
    "RUNTIME_STATE_MEMORY_LAYER",
    "REVIEW_ANTI_HYPE_LAYER",
    "ORGANIZATIONAL_OPERATING_LAYER",
    "OPERABILITY_READINESS_LAYER",
    "EXTERNAL_SOURCE_INTAKE_REGISTRY",
)

REQUIRED_FLOW_TERMS = (
    "external source intake -> frontier gap search",
    "frontier gap search -> project absorption shortlist",
    "project absorption shortlist -> benchmark criteria",
    "benchmark criteria -> acceptance cases",
    "acceptance cases -> validation",
    "real task ledger -> runtime state ledger",
    "permission/security policy -> delivery protocol",
    "product delivery layer -> validation matrix",
    "review/anti-hype -> final report",
    "organizational operating -> reviewer/security/data/release/human responsibility queues",
    "operability readiness -> rollback",
    "100-point maturity ladder -> continuous maturity iteration queue",
)

REQUIRED_REPORT_TERMS = (
    "REAL_DELIVERY_BENCHMARK_RUN_01",
    "second safe micro-task",
    "table-review residue closure",
    "bounded source-freshness audit",
    "frontier gap search audit",
    "external project absorption shortlist",
    "real-world proof gap ledger",
    "prompt consistency audit",
    "100-point maturity closure ladder",
    "continuous maturity iteration queue",
    "whole-content completion checklist",
)

REQUIRED_SOURCE_CATEGORIES = (
    "coding-agent and repository-level benchmarks",
    "browser/OS/mobile benchmarks",
    "professional/economic-value benchmarks",
    "production agent runtimes",
    "runtime sandboxes",
    "agent identity/delegation protocols",
    "agentic AI security/governance",
    "supply-chain/security automation",
    "observability/telemetry",
    "benchmark contamination/license policy",
)

REQUIRED_MATURITY_VERDICTS = (
    "real production maturity",
    "external benchmark maturity",
    "long-term autonomous capability",
    "real independent reviewer",
    "runtime sandbox / enforcement",
    "production observability",
    "CI required checks / branch protection",
    "license / security / provenance review",
    "next-stage real pressure testing readiness",
)

REQUIRED_TERMS = (
    "END_TO_END_EXECUTION_SYSTEM_V1_INTERNAL_READY",
    "ELEVEN_CORE_DELIVERY_LAYERS_V1_READY",
    "current-state-first",
    "terminal-state",
    "no human relay",
    "risk downgrade",
    "skip-and-record",
    "evidence",
    "final report",
    "human responsibility",
    "production readiness",
    "external validation",
    "customer validation",
    "paid signal",
    "deployment completion",
    "real-world operation",
    "global maturity",
    "final platform completion",
    "bounded source-freshness audit",
    "reference-only",
    "human review required",
)

TASK_QUEUE_SECTIONS = (
    "## NOW",
    "## NEXT",
    "## BLOCKED",
    "## SKIPPED",
    "## DONE",
    "## EVIDENCE_REQUIRED",
    "## HUMAN_RESPONSIBILITY",
)

PHASE_TERMS = tuple(f"Phase {index}" for index in range(0, 11))

VALIDATION_COMMANDS = (
    "python3 scripts/codex_execution_system_check_v1.py",
    "git diff --check",
)

LOCAL_PATH_MARKERS = (
    "/Users/",
    "Documents/Codex",
    "files-mentioned-by-the-user",
)

FORBIDDEN_POSITIVE_CLAIMS = (
    "production ready achieved",
    "production-ready achieved",
    "externally validated achieved",
    "customer validation achieved",
    "paid signal achieved",
    "deployment completed",
    "real-world operation achieved",
    "global maturity achieved",
    "final platform complete",
    "externally benchmark-proven achieved",
    "runtime sandbox proven",
    "production observability proven",
    "independently validated achieved",
    "100/100 achieved",
)


def main() -> int:
    errors: list[str] = []
    texts = _load_required_files(errors)
    _check_optional_files(errors)
    _check_combined_terms(texts, errors)
    _check_task_queue(texts, errors)
    _check_phase_queue(texts, errors)
    _check_validation_matrix(texts, errors)
    _check_delivery_protocol(texts, errors)
    _check_samples(texts, errors)
    _check_final_report(texts, errors)
    _check_eleven_core_delivery(texts, errors)
    _check_text_safety(texts, errors)

    if errors:
        print("codex_execution_system_check_v1: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("codex_execution_system_check_v1: PASS")
    return 0


def _load_required_files(errors: list[str]) -> dict[Path, str]:
    texts: dict[Path, str] = {}
    for relative_path in REQUIRED_FILES:
        path = REPO_ROOT / relative_path
        if not path.exists():
            errors.append(f"missing required file: {relative_path.as_posix()}")
            continue
        texts[relative_path] = path.read_text(encoding="utf-8")
    return texts


def _check_optional_files(errors: list[str]) -> None:
    for relative_path in OPTIONAL_IMPLEMENTATION_FILES:
        if not (REPO_ROOT / relative_path).exists():
            errors.append(f"missing implementation file: {relative_path.as_posix()}")


def _check_combined_terms(texts: dict[Path, str], errors: list[str]) -> None:
    combined = "\n".join(texts.values()).lower()
    for term in REQUIRED_TERMS:
        if term.lower() not in combined:
            errors.append(f"missing execution-system term: {term}")


def _check_task_queue(texts: dict[Path, str], errors: list[str]) -> None:
    text = texts.get(Path("CODEX_TASK_QUEUE.md"), "")
    for section in TASK_QUEUE_SECTIONS:
        if section not in text:
            errors.append(f"task queue missing section: {section}")


def _check_phase_queue(texts: dict[Path, str], errors: list[str]) -> None:
    text = texts.get(Path("CODEX_PHASE_QUEUE.md"), "")
    for term in PHASE_TERMS:
        if term not in text:
            errors.append(f"phase queue missing term: {term}")


def _check_validation_matrix(texts: dict[Path, str], errors: list[str]) -> None:
    text = texts.get(Path("CODEX_VALIDATION_MATRIX.md"), "")
    for command in VALIDATION_COMMANDS:
        if command not in text:
            errors.append(f"validation matrix missing command: {command}")
    for phrase in ("Documentation / Protocol Changes", "Code Changes", "App Changes"):
        if phrase not in text:
            errors.append(f"validation matrix missing phrase: {phrase}")


def _check_delivery_protocol(texts: dict[Path, str], errors: list[str]) -> None:
    text = texts.get(Path("CODEX_DELIVERY_PROTOCOL.md"), "")
    for phrase in ("branch name", "commit SHA", "PR link", "no merge"):
        if phrase.lower() not in text.lower():
            errors.append(f"delivery protocol missing phrase: {phrase}")


def _check_samples(texts: dict[Path, str], errors: list[str]) -> None:
    execution = texts.get(Path("reports/checkpoints/execution-sample-v1.md"), "")
    for phrase in (
        "Task target",
        "Current state",
        "Risk classification",
        "Safe action",
        "Evidence",
        "Validation",
        "Final status",
    ):
        if phrase not in execution:
            errors.append(f"execution sample missing phrase: {phrase}")

    recovery = texts.get(Path("reports/checkpoints/failure-recovery-sample-v1.md"), "")
    for phrase in (
        "Failure",
        "Downgrade Attempt",
        "Recovery Action",
        "Evidence Recorded",
        "Resume Instruction",
        "Next Human Action",
    ):
        if phrase not in recovery:
            errors.append(f"failure recovery sample missing phrase: {phrase}")


def _check_final_report(texts: dict[Path, str], errors: list[str]) -> None:
    text = texts.get(Path("reports/checkpoints/end-to-end-execution-system-v1-final-report.md"), "")
    for phrase in (
        "Final Target State",
        "Final Status",
        "Branch",
        "Commits",
        "PR",
        "Files Created",
        "Files Modified",
        "Completion Matrix",
        "Evidence Collected",
        "Checks Run",
        "Checks Skipped",
        "Skipped-Risk Items",
        "Blocked Items",
        "Human-Responsibility Items",
        "Known Limitations",
        "Next Recommended Independent Target",
    ):
        if phrase not in text:
            errors.append(f"final report missing phrase: {phrase}")


def _check_eleven_core_delivery(texts: dict[Path, str], errors: list[str]) -> None:
    combined = "\n".join(texts.values())
    combined_lower = combined.lower()

    for relative_path in ELEVEN_LAYER_FILES:
        text = texts.get(relative_path, "")
        if "## Connected Loop" not in text:
            errors.append(
                f"eleven-layer file missing Connected Loop section: {relative_path.as_posix()}"
            )
        if "## Evidence Gate" not in text:
            errors.append(
                f"eleven-layer file missing Evidence Gate section: {relative_path.as_posix()}"
            )

    for relative_path in GAP_GATE_FILES:
        text = texts.get(relative_path, "")
        for phrase in ("## Gate", "## Evidence Path", "## Non-Claim Boundary"):
            if phrase not in text:
                errors.append(f"{relative_path.as_posix()} missing phrase: {phrase}")

    for term in REQUIRED_ELEVEN_LAYER_TERMS:
        if term.lower() not in combined_lower:
            errors.append(f"missing eleven-layer term: {term}")

    for term in REQUIRED_FLOW_TERMS:
        if term.lower() not in combined_lower:
            errors.append(f"missing connected delivery-loop flow: {term}")

    for term in REQUIRED_REPORT_TERMS:
        if term.lower() not in combined_lower:
            errors.append(f"missing eleven-core report term: {term}")

    freshness = texts.get(Path("reports/checkpoints/global-source-freshness-audit-v1.md"), "")
    for category in REQUIRED_SOURCE_CATEGORIES:
        if category not in freshness:
            errors.append(f"source freshness audit missing category: {category}")
    for phrase in (
        "Live search availability",
        "Search date/time",
        "Opened sources",
        "Verified sources",
        "Rejected sources",
        "Uncertain sources",
        "Categories not searched",
        "Do not claim exhaustive global search",
    ):
        if phrase not in freshness:
            errors.append(f"source freshness audit missing phrase: {phrase}")

    shortlist = texts.get(
        Path("reports/checkpoints/external-project-absorption-shortlist-v1.md"), ""
    )
    for decision in (
        "COPY_SMALL_PATTERN",
        "INTEGRATE_TOOL",
        "REFERENCE_ONLY",
        "NEEDS_REVIEW",
        "REJECT_FOR_NOW",
    ):
        if decision not in shortlist:
            errors.append(f"external absorption shortlist missing decision: {decision}")

    throughput = texts.get(Path("reports/checkpoints/real-task-throughput-ledger-v1.md"), "")
    for phrase in (
        "REAL_DELIVERY_BENCHMARK_RUN_01",
        "Task 1",
        "Task 2",
        "start state",
        "diff summary",
        "checks",
        "result",
    ):
        if phrase not in throughput:
            errors.append(f"real task throughput ledger missing phrase: {phrase}")

    real_world_gap = texts.get(Path("reports/checkpoints/real-world-proof-gap-ledger-v1.md"), "")
    for verdict in REQUIRED_MATURITY_VERDICTS:
        if verdict not in real_world_gap:
            errors.append(f"real-world proof gap ledger missing verdict: {verdict}")

    maturity_ladder = texts.get(
        Path("reports/checkpoints/100-point-maturity-closure-ladder-v1.md"), ""
    )
    for phrase in (
        "current evidence-backed score",
        "90/100 requirements",
        "100/100 requirements",
        "safe proof executed now",
        "required authority",
        "why the score is not 100",
    ):
        if phrase not in maturity_ladder:
            errors.append(f"100-point maturity ladder missing phrase: {phrase}")

    completion = texts.get(
        Path("reports/checkpoints/whole-content-completion-checklist-v1.md"), ""
    )
    for section in range(0, 10):
        if f"Section {section}" not in completion:
            errors.append(f"whole-content completion checklist missing Section {section}")
    for status in ("PASS", "PARTIAL", "BLOCKED"):
        if status not in completion:
            errors.append(f"whole-content completion checklist missing status: {status}")

    scorecard = texts.get(Path("reports/checkpoints/eleven-core-delivery-layers-scorecard-v1.md"), "")
    for phrase in REQUIRED_MATURITY_VERDICTS:
        if phrase not in scorecard:
            errors.append(f"scorecard missing maturity verdict: {phrase}")

    final_report = texts.get(
        Path("reports/checkpoints/eleven-core-delivery-layers-v1-final-report.md"), ""
    )
    for phrase in (
        "final status",
        "branch",
        "commit SHA",
        "PR link",
        "checks run",
        "checks skipped",
        "explicit non-claim statement",
    ):
        if phrase.lower() not in final_report.lower():
            errors.append(f"eleven-core final report missing phrase: {phrase}")


def _check_text_safety(texts: dict[Path, str], errors: list[str]) -> None:
    for relative_path, text in texts.items():
        for marker in LOCAL_PATH_MARKERS:
            if marker in text:
                errors.append(
                    f"{relative_path.as_posix()} contains local path marker: {marker}"
                )
        lower = " ".join(text.lower().split())
        for claim in FORBIDDEN_POSITIVE_CLAIMS:
            if claim in lower:
                errors.append(
                    f"{relative_path.as_posix()} contains forbidden positive claim: {claim}"
                )


if __name__ == "__main__":
    raise SystemExit(main())
