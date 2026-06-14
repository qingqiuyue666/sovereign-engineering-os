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
)

OPTIONAL_IMPLEMENTATION_FILES = (
    Path("scripts/codex_execution_system_check_v1.py"),
)

REQUIRED_TERMS = (
    "END_TO_END_EXECUTION_SYSTEM_V1_INTERNAL_READY",
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
    "externally validated achieved",
    "customer validation achieved",
    "paid signal achieved",
    "deployment completed",
    "real-world operation achieved",
    "global maturity achieved",
    "final platform complete",
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
