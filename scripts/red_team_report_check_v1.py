#!/usr/bin/env python3
"""Validate the Codex-run red-team execution report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON = Path("reports/audits/red_team_execution_report_v1.json")
REPORT_MD = Path("reports/audits/red_team_execution_report_v1.md")
EXECUTE_SCRIPT = Path("scripts/red_team_execute_v1.py")

EXPECTED_STARTING_HEAD = "71a9744b2e84595627222c82c8155d2e537977ed"
EXPECTED_TAG_TARGET = "9a363f95b85602ffc598db463dc6181a9bbbdf3c"
FINAL_STATUS = "CODEX_RUN_RED_TEAM_REVIEW_EXECUTED_NO_BLOCKER_FOUND"
REQUIRED_SCENARIOS = {f"RT-{index:03d}" for index in range(1, 19)}

REQUIRED_STATEMENTS = (
    "This is not a human third-party external audit.",
    "External recognition is not confirmed by Codex.",
    "Global top engineer signoff is not confirmed by Codex.",
    "30-90 day real-world operation evidence remains required.",
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
    payload = _load_json(REPORT_JSON, errors)
    markdown = _load_text(REPORT_MD, errors)
    script = _load_text(EXECUTE_SCRIPT, errors)

    if payload is not None:
        _check_payload(payload, errors)
    if markdown:
        _check_markdown(markdown, errors)
    _check_makefile(errors)
    _check_text_safety(
        report_texts=[markdown, json.dumps(payload or {}, sort_keys=True)],
        implementation_texts=[script],
        errors=errors,
    )

    if errors:
        print("red_team_report_check_v1: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("red_team_report_check_v1: PASS")
    return 0


def _load_json(relative_path: Path, errors: list[str]) -> dict[str, Any] | None:
    path = REPO_ROOT / relative_path
    if not path.exists():
        errors.append(f"missing report JSON: {relative_path.as_posix()}")
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {relative_path.as_posix()}: {exc}")
        return None
    if not isinstance(loaded, dict):
        errors.append(f"report JSON must be object: {relative_path.as_posix()}")
        return None
    return loaded


def _load_text(relative_path: Path, errors: list[str]) -> str:
    path = REPO_ROOT / relative_path
    if not path.exists():
        errors.append(f"missing text artifact: {relative_path.as_posix()}")
        return ""
    return path.read_text(encoding="utf-8")


def _check_payload(payload: dict[str, Any], errors: list[str]) -> None:
    if payload.get("schema_version") != "red_team_execution_report_v1":
        errors.append("schema_version mismatch")
    if payload.get("reviewer_type") != "Codex-run local red-team execution":
        errors.append("reviewer_type mismatch")
    if payload.get("human_third_party_review") is not False:
        errors.append("report must not claim human third-party review")
    if payload.get("global_recognition_claimed") is not False:
        errors.append("report must not claim global recognition")
    if payload.get("external_signoff_confirmed") is not False:
        errors.append("report must not claim external signoff confirmed")
    if payload.get("starting_main_head") != EXPECTED_STARTING_HEAD:
        errors.append("starting main HEAD mismatch")
    if payload.get("final_status") != FINAL_STATUS:
        errors.append("final_status mismatch")
    tag = payload.get("release_candidate_tag")
    if not isinstance(tag, dict):
        errors.append("release_candidate_tag must be object")
    else:
        if tag.get("name") != "v0.1.0-rc3":
            errors.append("release-candidate tag name mismatch")
        if tag.get("expected_target") != EXPECTED_TAG_TARGET:
            errors.append("expected tag target mismatch")
        if tag.get("observed_target") != EXPECTED_TAG_TARGET:
            errors.append("observed tag target mismatch")
        if tag.get("moved_or_recreated_by_this_execution") is not False:
            errors.append("report must record that rc3 tag was not moved")
    _check_scenarios(payload.get("scenarios"), errors)
    _check_summary(payload.get("summary"), errors)
    statements = _check_required_list(payload.get("explicit_statements"), "explicit_statements", errors)
    if statements is not None:
        for statement in REQUIRED_STATEMENTS:
            if statement not in statements:
                errors.append(f"missing explicit statement: {statement}")
    _check_required_list(payload.get("known_limitations"), "known_limitations", errors)


def _check_scenarios(scenarios: object, errors: list[str]) -> None:
    if not isinstance(scenarios, list):
        errors.append("scenarios must be list")
        return
    if len(scenarios) != 18:
        errors.append("scenario count must be 18")
    seen: set[str] = set()
    required_fields = (
        "scenario_id",
        "attack_objective",
        "command_or_procedure",
        "expected_safe_behavior",
        "actual_behavior",
        "result",
        "finding_severity",
        "remediation_required",
        "evidence_artifact",
    )
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            errors.append("scenario entry must be object")
            continue
        for field in required_fields:
            if field not in scenario:
                errors.append(f"scenario missing field: {field}")
        scenario_id = str(scenario.get("scenario_id", ""))
        seen.add(scenario_id)
        if scenario.get("result") != "PASS":
            errors.append(f"scenario did not pass: {scenario_id}")
        if scenario.get("finding_severity") in {"P0 blocker", "P1 blocker"}:
            errors.append(f"scenario has blocker severity: {scenario_id}")
        if scenario.get("remediation_required") is not False:
            errors.append(f"scenario unexpectedly requires remediation: {scenario_id}")
    missing = REQUIRED_SCENARIOS - seen
    if missing:
        errors.append(f"missing scenarios: {', '.join(sorted(missing))}")


def _check_summary(summary: object, errors: list[str]) -> None:
    if not isinstance(summary, dict):
        errors.append("summary must be object")
        return
    for key in ("p0_p1_findings", "p2_findings", "accepted_risks", "inconclusive_scenarios"):
        if not isinstance(summary.get(key), list):
            errors.append(f"summary {key} must be list")
    if summary.get("p0_p1_findings") != []:
        errors.append("summary must have no P0/P1 findings")
    if summary.get("p2_findings") != []:
        errors.append("summary must have no P2 findings")
    if summary.get("inconclusive_scenarios") != []:
        errors.append("summary must have no inconclusive scenarios")
    if summary.get("blocker_count") != 0:
        errors.append("summary blocker_count must be 0")
    if "RT-017" not in summary.get("accepted_risks", []):
        errors.append("summary must reference accepted risk scenario RT-017")


def _check_required_list(value: object, name: str, errors: list[str]) -> list[str] | None:
    if not isinstance(value, list) or not value:
        errors.append(f"{name} must be non-empty list")
        return None
    if not all(isinstance(item, str) and item for item in value):
        errors.append(f"{name} must contain non-empty strings")
        return None
    return value


def _check_markdown(markdown: str, errors: list[str]) -> None:
    for term in (
        "# Red-Team Execution Report V1",
        FINAL_STATUS,
        "Codex-run local red-team execution",
        "This is not a human third-party external audit.",
        "External recognition is not confirmed by Codex.",
        "## Scenario Results",
        "## Findings Summary",
    ):
        if term not in markdown:
            errors.append(f"markdown missing required term: {term}")


def _check_makefile(errors: list[str]) -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    for target in (
        "red-team-check:",
        "test-red-team-execution:",
        "scripts/red_team_report_check_v1.py",
        "tests.adversarial.test_red_team_execution_v1",
    ):
        if target not in makefile:
            errors.append(f"Makefile missing red-team target/gate: {target}")


def _check_text_safety(
    report_texts: list[str],
    implementation_texts: list[str],
    errors: list[str],
) -> None:
    report_combined = "\n".join(report_texts)
    for wording in FORBIDDEN_SELF_CERT_WORDING:
        if wording in report_combined:
            errors.append(f"forbidden self-certification wording present: {wording}")
    combined = report_combined + "\n" + "\n".join(implementation_texts)
    for marker in LOCAL_PATH_MARKERS:
        if marker in combined:
            errors.append(f"local path marker present: {marker}")


if __name__ == "__main__":
    raise SystemExit(main())
