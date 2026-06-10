#!/usr/bin/env python3
"""Validate the Codex-run findings register and remediation log."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTER_JSON = Path("reports/audits/findings_register_v1.json")
REGISTER_MD = Path("reports/audits/findings_register_v1.md")
LOG_JSON = Path("reports/audits/findings_remediation_log_v1.json")
LOG_MD = Path("reports/audits/findings_remediation_log_v1.md")
INDEPENDENT_JSON = Path("reports/audits/independent_verification_execution_v1.json")
RED_TEAM_JSON = Path("reports/audits/red_team_execution_report_v1.json")

EXPECTED_STARTING_HEAD = "33032ef069830b4023bc994c722d86a087179268"
EXPECTED_TAG_TARGET = "9a363f95b85602ffc598db463dc6181a9bbbdf3c"
FINAL_STATUS = "FINDINGS_REMEDIATION_CLOSED_FOR_CODEX_RUN_VERIFICATION"
INDEPENDENT_STATUS = "CODEX_RUN_INDEPENDENT_VERIFICATION_EXECUTED"
RED_TEAM_STATUS = "CODEX_RUN_RED_TEAM_REVIEW_EXECUTED_NO_BLOCKER_FOUND"
REQUIRED_FINDINGS = {"FND-IV-001", "FND-RT-001", "FND-RT-017"}
ALLOWED_SOURCES = {
    "independent_verification",
    "red_team_execution",
    "local_validation",
    "CI",
    "external_human_review",
}
ALLOWED_SEVERITIES = {"P0", "P1", "P2", "accepted_risk", "informational"}
ALLOWED_STATUSES = {"open", "fixed", "accepted", "deferred_requires_human"}
PR_URL_RE = re.compile(r"^https://github\.com/qqyqqyqqy666-wq/sovereign-engineering-os/pull/[0-9]+$")

REQUIRED_STATEMENTS = (
    "External recognition is not confirmed by Codex.",
    "Global top engineer signoff is not confirmed by Codex.",
    "Human or independent external review remains required.",
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
    register = _load_json(REGISTER_JSON, errors)
    log = _load_json(LOG_JSON, errors)
    independent = _load_json(INDEPENDENT_JSON, errors)
    red_team = _load_json(RED_TEAM_JSON, errors)
    register_md = _load_text(REGISTER_MD, errors)
    log_md = _load_text(LOG_MD, errors)

    if register is not None:
        _check_register(register, independent, red_team, errors)
    if log is not None:
        _check_log(log, register, errors)
    if register_md:
        _check_register_markdown(register_md, errors)
    if log_md:
        _check_log_markdown(log_md, errors)
    _check_makefile(errors)
    _check_text_safety(
        [
            json.dumps(register or {}, sort_keys=True),
            json.dumps(log or {}, sort_keys=True),
            register_md,
            log_md,
        ],
        errors,
    )

    if errors:
        print("findings_register_check_v1: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("findings_register_check_v1: PASS")
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


def _check_register(
    register: dict[str, Any],
    independent: dict[str, Any] | None,
    red_team: dict[str, Any] | None,
    errors: list[str],
) -> None:
    if register.get("schema_version") != "findings_register_v1":
        errors.append("findings register schema_version mismatch")
    if register.get("reviewer_type") != "Codex-run local findings remediation closure":
        errors.append("findings register reviewer_type mismatch")
    for key in ("human_third_party_review", "external_signoff_confirmed", "global_recognition_claimed", "final_recognition_claimed"):
        if register.get(key) is not False:
            errors.append(f"findings register must keep {key}=false")
    if register.get("starting_main_head") != EXPECTED_STARTING_HEAD:
        errors.append("findings register starting_main_head mismatch")
    _check_tag(register.get("release_candidate_tag"), errors)
    _check_source_reports(register.get("source_reports"), independent, red_team, errors)
    _check_findings(register.get("findings"), red_team, errors)
    _check_summary(register.get("summary"), errors)
    _check_required_list(register.get("known_limitations"), "known_limitations", errors)
    statements = _check_required_list(register.get("explicit_statements"), "explicit_statements", errors)
    if statements is not None:
        for statement in REQUIRED_STATEMENTS:
            if statement not in statements:
                errors.append(f"findings register missing explicit statement: {statement}")


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
        errors.append("findings register must record that rc3 tag was not moved")


def _check_source_reports(
    reports: object,
    independent: dict[str, Any] | None,
    red_team: dict[str, Any] | None,
    errors: list[str],
) -> None:
    if not isinstance(reports, list) or len(reports) != 2:
        errors.append("source_reports must contain independent and red-team entries")
        return
    by_source = {entry.get("source"): entry for entry in reports if isinstance(entry, dict)}
    independent_entry = by_source.get("independent_verification")
    red_team_entry = by_source.get("red_team_execution")
    if not isinstance(independent_entry, dict) or not isinstance(red_team_entry, dict):
        errors.append("source_reports missing required source entries")
        return
    if independent_entry.get("final_status") != INDEPENDENT_STATUS:
        errors.append("independent source status mismatch")
    if red_team_entry.get("final_status") != RED_TEAM_STATUS:
        errors.append("red-team source status mismatch")
    if independent is not None:
        if independent.get("final_status") != INDEPENDENT_STATUS:
            errors.append("independent verification report final_status mismatch")
        if independent.get("findings") != []:
            errors.append("independent verification report no longer supports zero findings")
        if independent_entry.get("findings_count") != len(independent.get("findings", [])):
            errors.append("independent findings_count does not match source report")
    if red_team is not None:
        summary = red_team.get("summary")
        if red_team.get("final_status") != RED_TEAM_STATUS:
            errors.append("red-team report final_status mismatch")
        if not isinstance(summary, dict):
            errors.append("red-team report summary missing")
        else:
            if summary.get("p0_p1_findings") != []:
                errors.append("red-team report no longer supports zero P0/P1 findings")
            if summary.get("p2_findings") != []:
                errors.append("red-team report no longer supports zero P2 findings")
            if summary.get("inconclusive_scenarios") != []:
                errors.append("red-team report no longer supports zero inconclusive scenarios")
            if summary.get("accepted_risks") != ["RT-017"]:
                errors.append("red-team accepted risk list mismatch")
        if red_team_entry.get("scenario_count") != red_team.get("scenario_count"):
            errors.append("red-team scenario_count does not match source report")


def _check_findings(findings: object, red_team: dict[str, Any] | None, errors: list[str]) -> None:
    if not isinstance(findings, list):
        errors.append("findings must be list")
        return
    seen: set[str] = set()
    for finding in findings:
        if not isinstance(finding, dict):
            errors.append("finding entry must be object")
            continue
        _check_finding_entry(finding, errors)
        finding_id = str(finding.get("finding_id", ""))
        seen.add(finding_id)
    missing = REQUIRED_FINDINGS - seen
    if missing:
        errors.append(f"missing required findings: {', '.join(sorted(missing))}")
    if red_team is not None and "FND-RT-017" in seen:
        scenario = _red_team_scenario(red_team, "RT-017")
        if scenario is None:
            errors.append("RT-017 source scenario missing")
        elif scenario.get("finding_severity") != "accepted risk":
            errors.append("FND-RT-017 is not supported by RT-017 accepted risk")


def _check_finding_entry(finding: dict[str, Any], errors: list[str]) -> None:
    required_fields = (
        "finding_id",
        "source",
        "severity",
        "title",
        "description",
        "evidence",
        "affected_files",
        "remediation_pr",
        "validation_command",
        "status",
        "residual_risk",
    )
    for field in required_fields:
        if field not in finding:
            errors.append(f"finding missing field: {field}")
    finding_id = str(finding.get("finding_id", ""))
    source = finding.get("source")
    severity = finding.get("severity")
    status = finding.get("status")
    if source not in ALLOWED_SOURCES:
        errors.append(f"{finding_id} has invalid source")
    if severity not in ALLOWED_SEVERITIES:
        errors.append(f"{finding_id} has invalid severity")
    if status not in ALLOWED_STATUSES:
        errors.append(f"{finding_id} has invalid status")
    if severity in {"P0", "P1"} and status != "fixed":
        errors.append(f"{finding_id} blocking severity must be fixed")
    if severity == "accepted_risk":
        if status != "accepted":
            errors.append(f"{finding_id} accepted_risk must have accepted status")
        if not finding.get("acceptance_rationale"):
            errors.append(f"{finding_id} accepted_risk missing acceptance_rationale")
    if not _is_non_empty_string_list(finding.get("evidence")):
        errors.append(f"{finding_id} evidence must be non-empty string list")
    if not _is_non_empty_string_list(finding.get("affected_files")):
        errors.append(f"{finding_id} affected_files must be non-empty string list")
    remediation_pr = finding.get("remediation_pr")
    if not isinstance(remediation_pr, str) or not PR_URL_RE.match(remediation_pr):
        errors.append(f"{finding_id} remediation_pr must be a repository PR URL")
    if not isinstance(finding.get("validation_command"), str) or not finding["validation_command"]:
        errors.append(f"{finding_id} validation_command must be a non-empty string")


def _red_team_scenario(red_team: dict[str, Any], scenario_id: str) -> dict[str, Any] | None:
    scenarios = red_team.get("scenarios")
    if not isinstance(scenarios, list):
        return None
    for scenario in scenarios:
        if isinstance(scenario, dict) and scenario.get("scenario_id") == scenario_id:
            return scenario
    return None


def _check_summary(summary: object, errors: list[str]) -> None:
    if not isinstance(summary, dict):
        errors.append("summary must be object")
        return
    if summary.get("terminal_status") != FINAL_STATUS:
        errors.append("summary terminal_status mismatch")
    for key in ("p0_p1_open", "p2_open", "deferred_requires_human", "blocker_findings_requiring_repair_pr"):
        if summary.get(key) != []:
            errors.append(f"summary {key} must be empty")
    if summary.get("accepted_risks") != ["FND-RT-017"]:
        errors.append("summary accepted_risks mismatch")
    if summary.get("fixed_findings") != ["FND-IV-001", "FND-RT-001"]:
        errors.append("summary fixed_findings mismatch")


def _check_log(log: dict[str, Any], register: dict[str, Any] | None, errors: list[str]) -> None:
    if log.get("schema_version") != "findings_remediation_log_v1":
        errors.append("remediation log schema_version mismatch")
    if log.get("terminal_status") != FINAL_STATUS:
        errors.append("remediation log terminal_status mismatch")
    for key in ("global_recognition_claimed", "external_signoff_confirmed", "human_third_party_review"):
        if log.get(key) is not False:
            errors.append(f"remediation log must keep {key}=false")
    if log.get("source_register") != REGISTER_JSON.as_posix():
        errors.append("remediation log source_register mismatch")
    if log.get("fixes_required") is not False:
        errors.append("remediation log must record no required repair fixes")
    if log.get("minimal_repair_prs_created") != []:
        errors.append("remediation log must not invent repair PRs")
    entries = log.get("entries")
    if not isinstance(entries, list) or len(entries) != 3:
        errors.append("remediation log entries must contain three closure entries")
    else:
        entry_findings = {entry.get("finding_id") for entry in entries if isinstance(entry, dict)}
        if entry_findings != REQUIRED_FINDINGS:
            errors.append("remediation log finding coverage mismatch")
        for entry in entries:
            if isinstance(entry, dict):
                if not _is_non_empty_string_list(entry.get("validation_commands")):
                    errors.append(f"{entry.get('entry_id')} validation_commands must be non-empty string list")
                remediation_pr = entry.get("remediation_pr")
                if not isinstance(remediation_pr, str) or not PR_URL_RE.match(remediation_pr):
                    errors.append(f"{entry.get('entry_id')} remediation_pr must be a repository PR URL")
    required_validation = _check_required_list(log.get("required_wave_validation"), "required_wave_validation", errors)
    if required_validation is not None:
        for command in (
            "python3 scripts/findings_register_check_v1.py",
            "PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.tracer_bullet.test_findings_register_v1",
            "python3 scripts/independent_verification_report_check_v1.py",
            "python3 scripts/red_team_report_check_v1.py",
            "make verify",
            "make ci",
        ):
            if command not in required_validation:
                errors.append(f"remediation log missing validation command: {command}")
    if register is not None and register.get("summary", {}).get("terminal_status") != FINAL_STATUS:
        errors.append("remediation log source register has wrong terminal status")


def _check_register_markdown(markdown: str, errors: list[str]) -> None:
    for term in (
        "# Findings Register V1",
        FINAL_STATUS,
        "Codex-run local findings remediation closure",
        "External recognition is not confirmed by Codex.",
        "## Source Reports",
        "## Findings",
        "## Closure Summary",
        "FND-RT-017",
    ):
        if term not in markdown:
            errors.append(f"findings register markdown missing required term: {term}")


def _check_log_markdown(markdown: str, errors: list[str]) -> None:
    for term in (
        "# Findings Remediation Log V1",
        FINAL_STATUS,
        "## Remediation Entries",
        "## Repair PRs",
        "## Required Validation",
        "External recognition is not confirmed by Codex.",
    ):
        if term not in markdown:
            errors.append(f"remediation log markdown missing required term: {term}")


def _check_makefile(errors: list[str]) -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    for target in (
        "findings-check:",
        "test-findings-register:",
        "scripts/findings_register_check_v1.py",
        "tests.tracer_bullet.test_findings_register_v1",
    ):
        if target not in makefile:
            errors.append(f"Makefile missing findings target/gate: {target}")


def _check_required_list(value: object, name: str, errors: list[str]) -> list[str] | None:
    if not isinstance(value, list) or not value:
        errors.append(f"{name} must be non-empty list")
        return None
    if not all(isinstance(item, str) and item for item in value):
        errors.append(f"{name} must contain non-empty strings")
        return None
    return value


def _is_non_empty_string_list(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(item, str) and item for item in value)


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
