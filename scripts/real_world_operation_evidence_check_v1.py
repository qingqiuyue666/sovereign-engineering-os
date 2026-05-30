#!/usr/bin/env python3
"""Validate the real-world operation evidence program foundation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
PROGRAM_MD = Path("docs/operations/real_world_operation_evidence_program_v1.md")
INDEX_JSON = Path("reports/operations/real_world_operation_evidence_index_v1.json")
INDEX_MD = Path("reports/operations/real_world_operation_evidence_index_v1.md")
DAY0_JSON = Path("reports/operations/operation_day_000_initialization_v1.json")
DAY0_MD = Path("reports/operations/operation_day_000_initialization_v1.md")

PROGRAM_STATUS = "REAL_WORLD_OPERATION_EVIDENCE_PROGRAM_INITIALIZED"
INITIALIZED_AT_UTC = "2026-05-30T14:08:49Z"
STARTING_MAIN_HEAD = "b7a0dce3f33d0ebb33ec8cacc97f1c4a3151f791"
EXPECTED_TAG_TARGET = "9a363f95b85602ffc598db463dc6181a9bbbdf3c"
ISO_UTC_RE = re.compile(r"^2026-05-30T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
PR_URL_RE = re.compile(r"^https://github\.com/qqyqqyqqy666-wq/sovereign-engineering-os/pull/[0-9]+$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")

REQUIRED_PROGRAM_TERMS = (
    "30-day minimum observation window",
    "90-day stronger observation window",
    "task evidence schema",
    "PR evidence schema",
    "failure evidence schema",
    "incident evidence schema",
    "rollback/recovery drill schema",
    "dependency/update drill schema",
    "validation command schema",
    "daily/weekly rollup schema",
    "stop conditions",
    "escalation conditions",
    "final operation evidence report requirements",
)

REQUIRED_MISSING_EVIDENCE = (
    "30-day minimum observation window",
    "90-day stronger observation window",
    "at least 10 real SEOS-governed tasks",
    "at least 5 real PRs governed by SEOS",
    "at least 3 real failure or exception cases",
    "at least 1 rollback/recovery drill",
    "at least 1 dependency/update or release drill",
    "repeated verification checks over time",
    "human or independent external review",
)

EXPECTED_OPERATIONS = {
    "OP-PR-549": {
        "pr_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os/pull/549",
        "merge_commit": "71a9744b2e84595627222c82c8155d2e537977ed",
        "merged_at_utc": "2026-05-30T13:17:29Z",
    },
    "OP-PR-550": {
        "pr_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os/pull/550",
        "merge_commit": "33032ef069830b4023bc994c722d86a087179268",
        "merged_at_utc": "2026-05-30T13:46:01Z",
    },
    "OP-PR-551": {
        "pr_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os/pull/551",
        "merge_commit": "b7a0dce3f33d0ebb33ec8cacc97f1c4a3151f791",
        "merged_at_utc": "2026-05-30T14:04:51Z",
    },
}

REQUIRED_STATEMENTS = (
    "External recognition is not confirmed by Codex.",
    "Global top engineer signoff is not confirmed by Codex.",
    "Human or independent external review remains required.",
    "30-90 day real-world operation evidence remains required.",
    "No elapsed-time evidence is fabricated.",
)

FORBIDDEN_SELF_CERT_WORDING = (
    "GLOBAL_RECOGNITION_CONFIRMED",
    "GLOBAL_TOP_ENGINEER_SIGNOFF_CONFIRMED",
    "TOP_TIER_SIGNED",
    "PERFECT",
    "FULLY_RECOGNIZED",
    "FINAL WORLD-CLASS CONFIRMED",
)

LOCAL_PATH_MARKERS = (
    "/" + "Users" + "/" + "qqy",
    "Documents" + "/" + "Codex",
    "." + "codex",
    "files-mentioned" + "-by-the-user",
)


def main() -> int:
    errors: list[str] = []
    program_md = _load_text(PROGRAM_MD, errors)
    index = _load_json(INDEX_JSON, errors)
    index_md = _load_text(INDEX_MD, errors)
    day0 = _load_json(DAY0_JSON, errors)
    day0_md = _load_text(DAY0_MD, errors)

    if program_md:
        _check_program_doc(program_md, errors)
    if index is not None:
        _check_index(index, errors)
    if day0 is not None:
        _check_day0(day0, errors)
    if index_md:
        _check_markdown(index_md, INDEX_MD, errors)
    if day0_md:
        _check_markdown(day0_md, DAY0_MD, errors)
    _check_makefile(errors)
    _check_text_safety(
        [
            program_md,
            index_md,
            day0_md,
            json.dumps(index or {}, sort_keys=True),
            json.dumps(day0 or {}, sort_keys=True),
        ],
        errors,
    )

    if errors:
        print("real_world_operation_evidence_check_v1: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("real_world_operation_evidence_check_v1: PASS")
    return 0


def _load_json(relative_path: Path, errors: list[str]) -> dict[str, Any] | None:
    path = REPO_ROOT / relative_path
    if not path.exists():
        errors.append(f"missing JSON artifact: {relative_path.as_posix()}")
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {relative_path.as_posix()}: {exc}")
        return None
    if not isinstance(loaded, dict):
        errors.append(f"JSON artifact must be object: {relative_path.as_posix()}")
        return None
    return loaded


def _load_text(relative_path: Path, errors: list[str]) -> str:
    path = REPO_ROOT / relative_path
    if not path.exists():
        errors.append(f"missing text artifact: {relative_path.as_posix()}")
        return ""
    return path.read_text(encoding="utf-8")


def _check_program_doc(markdown: str, errors: list[str]) -> None:
    lowered = markdown.lower()
    for term in REQUIRED_PROGRAM_TERMS:
        if term.lower() not in lowered:
            errors.append(f"program document missing required term: {term}")
    for statement in REQUIRED_STATEMENTS:
        if statement not in markdown:
            errors.append(f"program document missing statement: {statement}")
    if "Current day count at initialization: 0." not in markdown:
        errors.append("program document must record day count 0")


def _check_index(index: dict[str, Any], errors: list[str]) -> None:
    if index.get("schema_version") != "real_world_operation_evidence_index_v1":
        errors.append("index schema_version mismatch")
    _check_common_boundary_fields(index, errors)
    if index.get("program_document") != PROGRAM_MD.as_posix():
        errors.append("index program_document mismatch")
    records = index.get("records")
    if not isinstance(records, list) or len(records) != 1:
        errors.append("index must contain exactly one Day 000 record")
    else:
        record = records[0]
        if not isinstance(record, dict):
            errors.append("index record must be object")
        else:
            if record.get("record_id") != "OP-DAY-000":
                errors.append("index record_id mismatch")
            if record.get("json_path") != DAY0_JSON.as_posix():
                errors.append("index Day 000 json_path mismatch")
            if record.get("markdown_path") != DAY0_MD.as_posix():
                errors.append("index Day 000 markdown_path mismatch")
    requirements = index.get("minimum_future_evidence_requirements")
    if not isinstance(requirements, dict):
        errors.append("index minimum_future_evidence_requirements must be object")
    else:
        expected = {
            "real_seos_governed_tasks": 10,
            "real_prs_governed_by_seos": 5,
            "failure_or_exception_cases": 3,
            "rollback_or_recovery_drills": 1,
            "dependency_update_or_release_drills": 1,
            "repeated_verification_checks_over_time": True,
        }
        for key, value in expected.items():
            if requirements.get(key) != value:
                errors.append(f"index future requirement mismatch: {key}")
    _check_counts(index.get("current_evidence_counts"), errors)
    _check_missing_evidence(index.get("missing_external_time_evidence"), errors)
    _check_statements(index.get("explicit_statements"), "index", errors)


def _check_day0(day0: dict[str, Any], errors: list[str]) -> None:
    if day0.get("schema_version") != "operation_day_000_initialization_v1":
        errors.append("Day 000 schema_version mismatch")
    if day0.get("record_id") != "OP-DAY-000":
        errors.append("Day 000 record_id mismatch")
    _check_common_boundary_fields(day0, errors)
    states = day0.get("current_completed_readiness_states")
    if not isinstance(states, list):
        errors.append("Day 000 current_completed_readiness_states must be list")
    else:
        for state in (
            "CODEX_RUN_INDEPENDENT_VERIFICATION_EXECUTED",
            "CODEX_RUN_RED_TEAM_REVIEW_EXECUTED_NO_BLOCKER_FOUND",
            "FINDINGS_REMEDIATION_CLOSED_FOR_CODEX_RUN_VERIFICATION",
        ):
            if state not in states:
                errors.append(f"Day 000 missing completed readiness state: {state}")
    operations = day0.get("real_operations_recorded_current_run")
    if not isinstance(operations, list) or len(operations) != len(EXPECTED_OPERATIONS):
        errors.append("Day 000 must record the three real PR operations from this run")
    else:
        by_id = {entry.get("operation_id"): entry for entry in operations if isinstance(entry, dict)}
        for operation_id, expected in EXPECTED_OPERATIONS.items():
            entry = by_id.get(operation_id)
            if not isinstance(entry, dict):
                errors.append(f"Day 000 missing operation: {operation_id}")
                continue
            _check_operation(entry, expected, errors)
    _check_counts(day0.get("current_evidence_counts"), errors)
    _check_missing_evidence(day0.get("missing_external_time_evidence"), errors)
    _check_statements(day0.get("explicit_statements"), "Day 000", errors)


def _check_common_boundary_fields(payload: dict[str, Any], errors: list[str]) -> None:
    if payload.get("program_status") != PROGRAM_STATUS:
        errors.append("program_status mismatch")
    if payload.get("initialized_at_utc") != INITIALIZED_AT_UTC:
        errors.append("initialized_at_utc mismatch")
    if not ISO_UTC_RE.match(str(payload.get("initialized_at_utc", ""))):
        errors.append("initialized_at_utc must be UTC ISO-8601 for the current run date")
    if payload.get("current_day_count") != 0:
        errors.append("current_day_count must be 0 at initialization")
    if payload.get("global_recognition_claimed") is not False:
        errors.append("must not claim global recognition")
    if payload.get("external_signoff_confirmed") is not False:
        errors.append("must not claim external signoff")
    if payload.get("human_third_party_review") is not False:
        errors.append("must not claim human third-party review")
    if payload.get("starting_main_head") != STARTING_MAIN_HEAD:
        errors.append("starting_main_head mismatch")
    _check_tag(payload.get("release_candidate_tag"), errors)
    if payload.get("minimum_window_satisfied") is True:
        errors.append("minimum observation window must not be marked satisfied")
    if payload.get("stronger_window_satisfied") is True:
        errors.append("stronger observation window must not be marked satisfied")


def _check_tag(tag: object, errors: list[str]) -> None:
    if not isinstance(tag, dict):
        errors.append("release_candidate_tag must be object")
        return
    if tag.get("name") != "v0.1.0-rc3":
        errors.append("release-candidate tag name mismatch")
    if tag.get("expected_target") != EXPECTED_TAG_TARGET:
        errors.append("expected tag target mismatch")
    if tag.get("observed_target") != EXPECTED_TAG_TARGET:
        errors.append("observed tag target mismatch")
    if tag.get("moved_or_recreated_by_this_execution") is not False:
        errors.append("rc3 tag must be recorded as unchanged")


def _check_operation(entry: dict[str, Any], expected: dict[str, str], errors: list[str]) -> None:
    operation_id = str(entry.get("operation_id", ""))
    pr_url = str(entry.get("pr_url", ""))
    merge_commit = str(entry.get("merge_commit", ""))
    merged_at = str(entry.get("merged_at_utc", ""))
    if pr_url != expected["pr_url"] or not PR_URL_RE.match(pr_url):
        errors.append(f"{operation_id} PR URL mismatch")
    if merge_commit != expected["merge_commit"] or not COMMIT_RE.match(merge_commit):
        errors.append(f"{operation_id} merge commit mismatch")
    if merged_at != expected["merged_at_utc"] or not ISO_UTC_RE.match(merged_at):
        errors.append(f"{operation_id} merged_at_utc mismatch")
    artifacts = entry.get("evidence_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append(f"{operation_id} evidence_artifacts must be non-empty list")
    else:
        for artifact in artifacts:
            if not isinstance(artifact, str) or not (REPO_ROOT / artifact.split("#", 1)[0]).exists():
                errors.append(f"{operation_id} evidence artifact missing: {artifact}")
    if "canonical-health passed" not in str(entry.get("validation_summary", "")):
        errors.append(f"{operation_id} validation summary must reference canonical-health pass")


def _check_counts(counts: object, errors: list[str]) -> None:
    if not isinstance(counts, dict):
        errors.append("current_evidence_counts must be object")
        return
    expected_counts = {
        "real_seos_governed_tasks_recorded": 3,
        "real_prs_recorded": 3,
        "failure_or_exception_cases_recorded": 0,
        "rollback_or_recovery_drills_recorded": 0,
        "dependency_update_or_release_drills_recorded": 0,
        "observation_days_recorded": 0,
    }
    for key, value in expected_counts.items():
        if counts.get(key) != value:
            errors.append(f"current evidence count mismatch: {key}")


def _check_missing_evidence(value: object, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append("missing_external_time_evidence must be list")
        return
    for item in REQUIRED_MISSING_EVIDENCE:
        if item not in value:
            errors.append(f"missing external/time evidence item not recorded: {item}")


def _check_statements(value: object, name: str, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append(f"{name} explicit_statements must be list")
        return
    for statement in REQUIRED_STATEMENTS:
        if statement not in value:
            errors.append(f"{name} explicit statement missing: {statement}")


def _check_markdown(markdown: str, relative_path: Path, errors: list[str]) -> None:
    for term in (
        PROGRAM_STATUS,
        "Current day count: 0",
        "External recognition is not confirmed by Codex.",
        "No elapsed-time evidence is fabricated",
    ):
        if term not in markdown:
            errors.append(f"{relative_path.as_posix()} missing required term: {term}")


def _check_makefile(errors: list[str]) -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    for target in (
        "operation-evidence-check:",
        "test-real-world-operation-evidence-program:",
        "scripts/real_world_operation_evidence_check_v1.py",
        "tests.tracer_bullet.test_real_world_operation_evidence_program_v1",
    ):
        if target not in makefile:
            errors.append(f"Makefile missing operation evidence target/gate: {target}")


def _check_text_safety(texts: list[str], errors: list[str]) -> None:
    combined = "\n".join(texts)
    for wording in FORBIDDEN_SELF_CERT_WORDING:
        if wording in combined:
            errors.append(f"forbidden self-certification wording present: {wording}")
    for marker in LOCAL_PATH_MARKERS:
        if marker in combined:
            errors.append(f"local path marker present: {marker}")


if __name__ == "__main__":
    raise SystemExit(main())
