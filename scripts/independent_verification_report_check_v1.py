#!/usr/bin/env python3
"""Validate the Codex-run independent verification execution report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORT_JSON = Path("reports/audits/independent_verification_execution_v1.json")
REPORT_MD = Path("reports/audits/independent_verification_execution_v1.md")
EXECUTE_SCRIPT = Path("scripts/independent_verification_execute_v1.sh")

EXPECTED_HEAD = "2f46520b9aa107d83689b86d3314919ad4bca7b8"
EXPECTED_TAG_TARGET = "9a363f95b85602ffc598db463dc6181a9bbbdf3c"
FINAL_STATUS = "CODEX_RUN_INDEPENDENT_VERIFICATION_EXECUTED"

REQUIRED_COMMAND_IDS = {
    "git_clone",
    "checkout_expected_head",
    "verify_starting_head",
    "verify_rc3_tag",
    "create_fresh_venv",
    "install_project",
    "clean_install_artifacts_after_install",
    "cli_help_seos",
    "cli_help_seos_local",
    "external_audit_packet_check",
    "claim_to_evidence_check",
    "security_control_check",
    "supply_chain_check",
    "secret_context_safety_check",
    "release_invariant_check",
    "ai_admission_check",
    "dogfood_evidence_check",
    "reliability_benchmark",
    "schema_compatibility_check",
    "observation_check",
    "failure_path_smoke",
    "adversarial_smoke",
    "make_verify",
    "clean_install_artifacts_before_ci",
    "make_ci",
}

REQUIRED_STATEMENTS = (
    "This is not a human third-party external audit.",
    "External recognition is not confirmed by Codex.",
    "Global top engineer signoff is not confirmed by Codex.",
    "Human or independent external review remains required.",
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
    _check_text_safety(
        report_texts=[markdown, json.dumps(payload or {}, sort_keys=True)],
        implementation_texts=[script],
        errors=errors,
    )

    if errors:
        print("independent_verification_report_check_v1: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("independent_verification_report_check_v1: PASS")
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
        errors.append(f"report JSON must be an object: {relative_path.as_posix()}")
        return None
    return loaded


def _load_text(relative_path: Path, errors: list[str]) -> str:
    path = REPO_ROOT / relative_path
    if not path.exists():
        errors.append(f"missing text artifact: {relative_path.as_posix()}")
        return ""
    return path.read_text(encoding="utf-8")


def _check_payload(payload: dict[str, Any], errors: list[str]) -> None:
    if payload.get("schema_version") != "independent_verification_execution_v1":
        errors.append("schema_version mismatch")
    if payload.get("reviewer_type") != "Codex-run local independent verification":
        errors.append("reviewer_type must identify Codex-run local independent verification")
    if payload.get("human_third_party_audit") is not False:
        errors.append("report must not claim a human third-party audit")
    if payload.get("external_signoff_confirmed") is not False:
        errors.append("report must not claim external signoff confirmed")
    if payload.get("global_recognition_claimed") is not False:
        errors.append("report must not claim global recognition")
    if payload.get("global_recognition_confirmed_by_codex") is not False:
        errors.append("Codex must not confirm global recognition")
    if payload.get("final_status") != FINAL_STATUS:
        errors.append("final_status mismatch")

    repository = payload.get("repository")
    if not isinstance(repository, dict):
        errors.append("repository must be an object")
    else:
        if repository.get("target_head") != EXPECTED_HEAD:
            errors.append("target HEAD mismatch")
        if repository.get("observed_head") != EXPECTED_HEAD:
            errors.append("observed HEAD mismatch")
        if repository.get("name") != "qqyqqyqqy666-wq/sovereign-engineering-os":
            errors.append("repository name mismatch")

    tag = payload.get("release_candidate_tag")
    if not isinstance(tag, dict):
        errors.append("release_candidate_tag must be an object")
    else:
        if tag.get("name") != "v0.1.0-rc3":
            errors.append("release-candidate tag name mismatch")
        if tag.get("expected_target") != EXPECTED_TAG_TARGET:
            errors.append("expected tag target mismatch")
        if tag.get("observed_target") != EXPECTED_TAG_TARGET:
            errors.append("observed tag target mismatch")
        if tag.get("moved_or_recreated_by_this_execution") is not False:
            errors.append("report must record that the rc3 tag was not moved")

    environment = payload.get("environment_summary")
    if not isinstance(environment, dict):
        errors.append("environment_summary must be an object")
    else:
        if environment.get("clean_clone") is not True:
            errors.append("environment_summary must record clean clone")
        if environment.get("fresh_venv") is not True:
            errors.append("environment_summary must record fresh venv")
        if environment.get("temp_workspace_path_recorded") is not False:
            errors.append("temp workspace absolute path must not be recorded")

    _check_commands(payload.get("commands"), errors)
    _check_findings(payload.get("findings"), errors)
    _check_required_list(payload.get("known_limitations"), "known_limitations", errors)
    statements = _check_required_list(payload.get("explicit_statements"), "explicit_statements", errors)
    if statements is not None:
        for statement in REQUIRED_STATEMENTS:
            if statement not in statements:
                errors.append(f"missing explicit statement: {statement}")


def _check_commands(commands: object, errors: list[str]) -> None:
    if not isinstance(commands, list):
        errors.append("commands must be a list")
        return
    seen: set[str] = set()
    for entry in commands:
        if not isinstance(entry, dict):
            errors.append("command entry must be an object")
            continue
        command_id = entry.get("id")
        if not isinstance(command_id, str):
            errors.append("command entry missing string id")
            continue
        seen.add(command_id)
        if entry.get("required") is not True:
            errors.append(f"{command_id} must be marked required")
        if entry.get("result") != "PASS":
            errors.append(f"{command_id} did not pass")
        if entry.get("exit_code") != 0:
            errors.append(f"{command_id} exit_code must be 0")
        if not entry.get("command"):
            errors.append(f"{command_id} missing command")
        if entry.get("cwd_policy") not in {"temporary_workspace", "clean_clone"}:
            errors.append(f"{command_id} cwd_policy invalid")
    missing = REQUIRED_COMMAND_IDS - seen
    if missing:
        errors.append(f"missing required command ids: {', '.join(sorted(missing))}")


def _check_findings(findings: object, errors: list[str]) -> None:
    if not isinstance(findings, list):
        errors.append("findings must be a list")
        return
    for finding in findings:
        if not isinstance(finding, dict):
            errors.append("finding entry must be an object")
            continue
        if finding.get("severity") in {"P0 blocker", "P1 blocker", "P0", "P1"}:
            errors.append(f"blocking finding remains open: {finding.get('finding_id')}")


def _check_required_list(value: object, name: str, errors: list[str]) -> list[str] | None:
    if not isinstance(value, list) or not value:
        errors.append(f"{name} must be a non-empty list")
        return None
    if not all(isinstance(item, str) and item for item in value):
        errors.append(f"{name} must contain non-empty strings")
        return None
    return value


def _check_markdown(markdown: str, errors: list[str]) -> None:
    required_terms = (
        "# Independent Verification Execution V1",
        FINAL_STATUS,
        "Codex-run local independent verification",
        "This is not a human third-party external audit.",
        "External recognition is not confirmed by Codex.",
        "Global top engineer signoff is not confirmed by Codex.",
        "## Commands",
        "## Findings",
        "## Known Limitations",
    )
    for term in required_terms:
        if term not in markdown:
            errors.append(f"markdown missing required term: {term}")


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
