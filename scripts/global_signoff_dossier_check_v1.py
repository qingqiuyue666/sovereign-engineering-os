#!/usr/bin/env python3
"""Validate the global signoff candidate dossier foundation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DOSSIER_JSON = Path("reports/audits/global_top_engineer_signoff_dossier_v1.json")
DOSSIER_MD = Path("docs/audits/global_top_engineer_signoff_dossier_v1.md")

EXPECTED_VERDICT = "GLOBAL_TOP_ENGINEER_SIGNOFF_CANDIDATE_FOUNDATION_READY"
EXPECTED_MAIN_HEAD = "0952722911ca880b75511b7ef7718051a060d2de"
EXPECTED_TAG_TARGET = "9a363f95b85602ffc598db463dc6181a9bbbdf3c"
PR_URL_RE = re.compile(r"^https://github\.com/qqyqqyqqy666-wq/sovereign-engineering-os/pull/[0-9]+$")
CI_URL_RE = re.compile(r"^https://github\.com/qqyqqyqqy666-wq/sovereign-engineering-os/actions/runs/[0-9]+$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")

REQUIRED_REFERENCE_KEYS = (
    "external_audit_packet",
    "external_audit_packet_markdown",
    "independent_verification_execution_report",
    "red_team_execution_report",
    "findings_register",
    "findings_remediation_log",
    "real_world_operation_evidence_program",
    "real_world_operation_evidence_index",
    "accepted_risk_register",
    "residual_risk_register",
    "final_blocker_table",
)

REQUIRED_VALIDATION_COMMANDS = (
    "python3 scripts/global_signoff_dossier_check_v1.py",
    "PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.tracer_bullet.test_global_signoff_dossier_v1",
    "python3 scripts/independent_verification_report_check_v1.py",
    "python3 scripts/red_team_report_check_v1.py",
    "python3 scripts/findings_register_check_v1.py",
    "python3 scripts/real_world_operation_evidence_check_v1.py",
    "make verify",
    "make ci",
    "git diff --check",
    "git status --short",
)

REQUIRED_STATEMENTS = (
    "This is not final global recognition.",
    "This is not human external signoff confirmed.",
    "Human or independent external review remains required.",
    "30-90 day real-world operation remains required.",
    "Final recognition requires evidence beyond Codex.",
    "External recognition is not confirmed by Codex.",
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
    dossier = _load_json(DOSSIER_JSON, errors)
    markdown = _load_text(DOSSIER_MD, errors)

    if dossier is not None:
        _check_dossier(dossier, errors)
    if markdown:
        _check_markdown(markdown, errors)
    _check_source_reports(errors)
    _check_makefile(errors)
    _check_text_safety([json.dumps(dossier or {}, sort_keys=True), markdown], errors)

    if errors:
        print("global_signoff_dossier_check_v1: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("global_signoff_dossier_check_v1: PASS")
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


def _check_dossier(dossier: dict[str, Any], errors: list[str]) -> None:
    if dossier.get("schema_version") != "global_top_engineer_signoff_dossier_v1":
        errors.append("dossier schema_version mismatch")
    if dossier.get("dossier_status") != EXPECTED_VERDICT:
        errors.append("dossier_status mismatch")
    if dossier.get("final_verdict") != EXPECTED_VERDICT:
        errors.append("final_verdict mismatch")
    if dossier.get("final_main_head") != EXPECTED_MAIN_HEAD:
        errors.append("final_main_head mismatch")
    if "post-Wave-5 main head" not in str(dossier.get("final_main_head_scope", "")):
        errors.append("final_main_head_scope must preserve post-merge reporting boundary")
    _check_tag(dossier.get("release_candidate_tag"), errors)
    for key in (
        "global_recognition_confirmed",
        "human_external_signoff_confirmed",
        "codex_self_certifying_final_signoff",
        "human_third_party_review_completed",
        "thirty_to_ninety_day_operation_completed",
    ):
        if dossier.get(key) is not False:
            errors.append(f"dossier must keep {key}=false")
    _check_conditions(dossier.get("conditions_for_candidate_foundation"), errors)
    _check_prior_summary(dossier.get("prior_wave_1_to_9_readiness_summary"), errors)
    _check_current_program_prs(dossier.get("current_program_prs"), errors)
    _check_required_references(dossier.get("required_references"), errors)
    _check_required_list(dossier.get("validation_commands"), "validation_commands", REQUIRED_VALIDATION_COMMANDS, errors)
    _check_required_list(dossier.get("explicit_statements"), "explicit_statements", REQUIRED_STATEMENTS, errors)
    if not isinstance(dossier.get("known_limitations"), list) or not dossier["known_limitations"]:
        errors.append("known_limitations must be non-empty list")
    remaining = dossier.get("remaining_required_external_steps")
    if not isinstance(remaining, list) or len(remaining) < 5:
        errors.append("remaining_required_external_steps must list external steps")
    else:
        for term in ("human or independent external verification", "30-90 day real-world operation evidence collection"):
            if term not in remaining:
                errors.append(f"remaining required step missing: {term}")


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


def _check_conditions(conditions: object, errors: list[str]) -> None:
    if not isinstance(conditions, dict):
        errors.append("conditions_for_candidate_foundation must be object")
        return
    expected = {
        "codex_run_independent_verification_executed": True,
        "red_team_execution_completed": True,
        "p0_p1_findings_fixed_or_none_found": True,
        "operation_evidence_program_initialized": True,
        "dossier_check_passes": True,
        "forbidden_claims_made": False,
    }
    for key, value in expected.items():
        if conditions.get(key) != value:
            errors.append(f"candidate condition mismatch: {key}")


def _check_prior_summary(summary: object, errors: list[str]) -> None:
    if not isinstance(summary, dict):
        errors.append("prior_wave_1_to_9_readiness_summary must be object")
        return
    if summary.get("terminal_state") != "GLOBAL_RECOGNITION_READINESS_READY_FOR_EXTERNAL_REVIEW":
        errors.append("prior readiness terminal state mismatch")
    if summary.get("final_prior_pr") != "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os/pull/548":
        errors.append("prior final PR reference mismatch")
    for key in ("external_audit_packet", "external_audit_packet_markdown"):
        ref = summary.get(key)
        if not isinstance(ref, str) or not (REPO_ROOT / ref).exists():
            errors.append(f"prior summary missing artifact: {key}")


def _check_current_program_prs(prs: object, errors: list[str]) -> None:
    if not isinstance(prs, list) or len(prs) != 4:
        errors.append("current_program_prs must contain Waves 1-4")
        return
    expected_commits = {
        1: "71a9744b2e84595627222c82c8155d2e537977ed",
        2: "33032ef069830b4023bc994c722d86a087179268",
        3: "b7a0dce3f33d0ebb33ec8cacc97f1c4a3151f791",
        4: "0952722911ca880b75511b7ef7718051a060d2de",
    }
    seen: set[int] = set()
    for entry in prs:
        if not isinstance(entry, dict):
            errors.append("current_program_prs entry must be object")
            continue
        wave = entry.get("wave")
        if not isinstance(wave, int):
            errors.append("current_program_prs entry missing integer wave")
            continue
        seen.add(wave)
        if entry.get("merge_commit") != expected_commits.get(wave) or not COMMIT_RE.match(str(entry.get("merge_commit", ""))):
            errors.append(f"wave {wave} merge_commit mismatch")
        if not PR_URL_RE.match(str(entry.get("pr_url", ""))):
            errors.append(f"wave {wave} PR URL invalid")
        if entry.get("ci_status") != "canonical-health passed":
            errors.append(f"wave {wave} CI status mismatch")
        if not CI_URL_RE.match(str(entry.get("ci_url", ""))):
            errors.append(f"wave {wave} CI URL invalid")
    if seen != {1, 2, 3, 4}:
        errors.append("current_program_prs wave coverage mismatch")


def _check_required_references(references: object, errors: list[str]) -> None:
    if not isinstance(references, dict):
        errors.append("required_references must be object")
        return
    for key in REQUIRED_REFERENCE_KEYS:
        ref = references.get(key)
        if not isinstance(ref, str):
            errors.append(f"required reference missing: {key}")
            continue
        if not (REPO_ROOT / ref).exists():
            errors.append(f"required reference path missing: {ref}")


def _check_required_list(value: object, name: str, required: tuple[str, ...], errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append(f"{name} must be list")
        return
    for item in required:
        if item not in value:
            errors.append(f"{name} missing: {item}")


def _check_markdown(markdown: str, errors: list[str]) -> None:
    for term in (
        "# Global Top Engineer Signoff Dossier V1",
        EXPECTED_VERDICT,
        "This is not final global recognition.",
        "This is not human external signoff confirmed.",
        "Human or independent external review remains required.",
        "30-90 day real-world operation remains required.",
        "Final recognition requires evidence beyond Codex.",
        "## Required References",
        "## Validation Commands",
        "## Remaining Required External Steps",
    ):
        if term not in markdown:
            errors.append(f"dossier markdown missing required term: {term}")


def _check_source_reports(errors: list[str]) -> None:
    independent = _load_json(Path("reports/audits/independent_verification_execution_v1.json"), errors)
    red_team = _load_json(Path("reports/audits/red_team_execution_report_v1.json"), errors)
    findings = _load_json(Path("reports/audits/findings_register_v1.json"), errors)
    operation = _load_json(Path("reports/operations/real_world_operation_evidence_index_v1.json"), errors)
    if independent is not None and independent.get("final_status") != "CODEX_RUN_INDEPENDENT_VERIFICATION_EXECUTED":
        errors.append("independent verification final status mismatch")
    if red_team is not None:
        if red_team.get("final_status") != "CODEX_RUN_RED_TEAM_REVIEW_EXECUTED_NO_BLOCKER_FOUND":
            errors.append("red-team final status mismatch")
        summary = red_team.get("summary", {})
        if summary.get("p0_p1_findings") != []:
            errors.append("red-team P0/P1 findings must be empty for candidate foundation")
    if findings is not None and findings.get("summary", {}).get("terminal_status") != "FINDINGS_REMEDIATION_CLOSED_FOR_CODEX_RUN_VERIFICATION":
        errors.append("findings register terminal status mismatch")
    if operation is not None and operation.get("program_status") != "REAL_WORLD_OPERATION_EVIDENCE_PROGRAM_INITIALIZED":
        errors.append("operation evidence program status mismatch")


def _check_makefile(errors: list[str]) -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    for target in (
        "global-signoff-dossier-check:",
        "test-global-signoff-dossier:",
        "external-verification-program-check:",
        "scripts/global_signoff_dossier_check_v1.py",
        "tests.tracer_bullet.test_global_signoff_dossier_v1",
    ):
        if target not in makefile:
            errors.append(f"Makefile missing global signoff target/gate: {target}")


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
