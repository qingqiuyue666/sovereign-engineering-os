#!/usr/bin/env python3
"""Validate the Wave 9 external audit packet."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]

PACKET_JSON = Path("reports/audits/external_audit_packet_v1.json")
PACKET_MD = Path("docs/audits/external_audit_packet_v1.md")
ACCEPTED_RISK_JSON = Path("reports/audits/accepted_risk_register_v1.json")
RESIDUAL_RISK_JSON = Path("reports/audits/residual_risk_register_v1.json")
FINAL_BLOCKER_JSON = Path("reports/audits/final_blocker_table_v1.json")

FINAL_VERDICT = "GLOBAL_RECOGNITION_READINESS_READY_FOR_EXTERNAL_REVIEW"
MAIN_HEAD_AT_PACKET_GENERATION = "260f05b2956d0158cee49472c815c04aa0fb7bbc"
RC3_TARGET = "9a363f95b85602ffc598db463dc6181a9bbbdf3c"

EXPECTED_WAVE_PRS = {
    1: 540,
    2: 541,
    3: 542,
    4: 543,
    5: 544,
    6: 545,
    7: 546,
    8: 547,
    9: 548,
}

EXPECTED_MERGE_COMMITS = {
    1: "cc55f3699890c33fce469b0fa776f24e5dd455b7",
    2: "bbbe7a688f579c807bbd0ee5716f9a82c77adab8",
    3: "c502c402b0a63e1cd408eb38a7dc81ca427211bd",
    4: "1809326b68d3a1b2befe14d306be6f027d1acbfa",
    5: "d6c5da73f4914baa69b58a8638999caa0224ddc6",
    6: "eb57085b9c1c2bd1a5feffef91feef8b605c0ba4",
    7: "68c7b2741e5b779bff600ce584dcb0ac9d3b5ba7",
    8: "260f05b2956d0158cee49472c815c04aa0fb7bbc",
}

REQUIRED_DOCS = (
    Path("docs/audits/external_audit_packet_v1.md"),
    Path("docs/audits/independent_verification_runbook_v1.md"),
    Path("docs/audits/red_team_checklist_v1.md"),
    Path("docs/audits/accepted_risk_register_v1.md"),
    Path("docs/audits/residual_risk_register_v1.md"),
    Path("docs/audits/final_blocker_table_v1.md"),
)

REQUIRED_JSON_REPORTS = (
    PACKET_JSON,
    ACCEPTED_RISK_JSON,
    RESIDUAL_RISK_JSON,
    FINAL_BLOCKER_JSON,
)

REQUIRED_PACKET_TERMS = (
    "current main head",
    "v0.1.0-rc3",
    "claim-to-evidence matrix",
    "engineering evidence",
    "security evidence",
    "supply-chain evidence",
    "reliability evidence",
    "dogfooding evidence",
    "AI governance evidence",
    "known limitations",
    "accepted risks",
    "residual risks",
    "non-goals",
    "red-team checklist",
    "independent verification runbook",
    "final blocker table",
)

REQUIRED_STATEMENTS = (
    "External recognition has not yet been confirmed.",
    "External verification is still required.",
    "Real-world 30-90 day operation evidence is still required for global recognition.",
    "Codex is not self-certifying final signoff.",
)

REQUIRED_VALIDATION_COMMANDS = (
    "python3 scripts/external_audit_packet_check_v1.py",
    "python3 scripts/claim_to_evidence_check_v1.py",
    "python3 scripts/security_control_check_v1.py",
    "python3 scripts/supply_chain_check_v1.py",
    "python3 scripts/ai_admission_check_v1.py",
    "python3 scripts/dogfood_evidence_check_v1.py",
    "python3 scripts/reliability_benchmark_v1.py",
    "make verify",
    "make ci",
)

FORBIDDEN_SELF_CERT_WORDING = (
    "GLOBAL_RECOGNITION_CONFIRMED",
    "globally recognized",
    "externally certified",
    "world class confirmed",
    "codex certified final signoff",
)

LOCAL_PATH_MARKERS = (
    "/" + "Users" + "/" + "qqy",
    "Documents" + "/" + "Codex",
    "." + "codex",
    "files-mentioned" + "-by-the-user",
)

COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
PR_URL_RE = re.compile(r"^https://github\.com/qqyqqyqqy666-wq/sovereign-engineering-os/pull/[0-9]+$")


def main() -> int:
    errors: list[str] = []
    docs = _load_docs(errors)
    reports = _load_reports(errors)

    packet = reports.get(PACKET_JSON)
    if packet is not None:
        _check_packet(packet, docs.get(PACKET_MD, ""), errors)
    _check_risk_registers(reports, docs, errors)
    _check_final_blockers(reports, docs, errors)
    _check_ci_and_makefile(errors)
    _check_text_safety_for_all(docs, reports, errors)

    if errors:
        print("external_audit_packet_check_v1: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("external_audit_packet_check_v1: PASS")
    return 0


def _load_docs(errors: list[str]) -> dict[Path, str]:
    docs: dict[Path, str] = {}
    for relative_path in REQUIRED_DOCS:
        path = REPO_ROOT / relative_path
        if not path.exists():
            errors.append(f"missing audit doc: {relative_path.as_posix()}")
            continue
        docs[relative_path] = path.read_text(encoding="utf-8")
    return docs


def _load_reports(errors: list[str]) -> dict[Path, dict[str, Any]]:
    reports: dict[Path, dict[str, Any]] = {}
    for relative_path in REQUIRED_JSON_REPORTS:
        path = REPO_ROOT / relative_path
        if not path.exists():
            errors.append(f"missing audit report: {relative_path.as_posix()}")
            continue
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON in {relative_path.as_posix()}: {exc}")
            continue
        if not isinstance(loaded, dict):
            errors.append(f"audit report must be object: {relative_path.as_posix()}")
            continue
        reports[relative_path] = loaded
    return reports


def _check_packet(packet: dict[str, Any], packet_md: str, errors: list[str]) -> None:
    if packet.get("schema_version") != "external_audit_packet_v1":
        errors.append("external audit packet schema_version mismatch")
    if packet.get("final_verdict") != FINAL_VERDICT:
        errors.append("external audit packet final verdict mismatch")
    if FINAL_VERDICT not in packet_md:
        errors.append("external audit packet markdown missing final verdict")
    if packet.get("external_review_required") is not True:
        errors.append("external audit packet must require external review")
    if packet.get("global_recognition_claimed") is not False:
        errors.append("external audit packet must not claim global recognition")
    if packet.get("external_recognition_confirmed") is not False:
        errors.append("external recognition must not be confirmed")
    if packet.get("external_verification_required") is not True:
        errors.append("external verification must remain required")
    if packet.get("real_world_30_90_day_operation_evidence_required_for_global_recognition") is not True:
        errors.append("30-90 day operation evidence requirement missing")
    if packet.get("codex_self_certifying_final_signoff") is not False:
        errors.append("Codex must not self-certify final signoff")
    if packet.get("current_main_head_at_packet_generation") != MAIN_HEAD_AT_PACKET_GENERATION:
        errors.append("packet main head at generation mismatch")
    tag = packet.get("release_candidate_tag", {})
    if not isinstance(tag, dict) or tag.get("name") != "v0.1.0-rc3":
        errors.append("packet release candidate tag name mismatch")
    if tag.get("target_commit") != RC3_TARGET:
        errors.append("packet release candidate tag target mismatch")
    if tag.get("moved_or_recreated_by_packet") is not False:
        errors.append("packet must record that rc3 tag was not moved")

    _check_wave_prs(packet.get("wave_prs"), errors)
    _check_validation_commands(packet.get("validation_commands"), errors)
    _check_evidence_groups(packet.get("evidence_groups"), errors)
    _check_required_statements(packet, packet_md, errors)
    _check_packet_markdown(packet_md, errors)


def _check_wave_prs(wave_prs: object, errors: list[str]) -> None:
    if not isinstance(wave_prs, list) or len(wave_prs) != 9:
        errors.append("packet must list exactly nine wave PR entries")
        return
    seen_waves: set[int] = set()
    for entry in wave_prs:
        if not isinstance(entry, dict):
            errors.append("wave PR entry must be object")
            continue
        wave = entry.get("wave")
        if not isinstance(wave, int):
            errors.append("wave PR entry missing integer wave")
            continue
        seen_waves.add(wave)
        if entry.get("pr_number") != EXPECTED_WAVE_PRS.get(wave):
            errors.append(f"wave {wave} PR number mismatch")
        if not PR_URL_RE.match(str(entry.get("pr_url", ""))):
            errors.append(f"wave {wave} PR URL invalid")
        expected_commit = EXPECTED_MERGE_COMMITS.get(wave)
        merge_commit = str(entry.get("merge_commit", ""))
        if expected_commit is not None and merge_commit != expected_commit:
            errors.append(f"wave {wave} merge commit mismatch")
        if wave == 9 and merge_commit != "assigned_after_merge":
            errors.append("wave 9 merge commit must remain assigned_after_merge before merge")
        if not entry.get("purpose"):
            errors.append(f"wave {wave} missing purpose")
    if seen_waves != set(EXPECTED_WAVE_PRS):
        errors.append("wave PR ledger must cover waves 1 through 9")


def _check_validation_commands(commands: object, errors: list[str]) -> None:
    if not isinstance(commands, list) or not commands:
        errors.append("packet validation_commands must be non-empty list")
        return
    command_text = "\n".join(str(command) for command in commands)
    for command in REQUIRED_VALIDATION_COMMANDS:
        if command not in command_text:
            errors.append(f"packet missing validation command: {command}")


def _check_evidence_groups(groups: object, errors: list[str]) -> None:
    if not isinstance(groups, dict):
        errors.append("packet evidence_groups must be object")
        return
    for group_name in (
        "engineering_evidence",
        "security_evidence",
        "supply_chain_evidence",
        "reliability_evidence",
        "dogfooding_evidence",
        "ai_governance_evidence",
    ):
        refs = groups.get(group_name)
        if not isinstance(refs, list) or not refs:
            errors.append(f"packet missing evidence group: {group_name}")
            continue
        for ref in refs:
            if not isinstance(ref, str) or not ref:
                errors.append(f"{group_name} has invalid ref: {ref!r}")
                continue
            if not (REPO_ROOT / ref).exists():
                errors.append(f"{group_name} evidence ref missing: {ref}")


def _check_required_statements(packet: dict[str, Any], packet_md: str, errors: list[str]) -> None:
    statements = packet.get("explicit_statements")
    if not isinstance(statements, list):
        errors.append("packet explicit_statements must be list")
        return
    for statement in REQUIRED_STATEMENTS:
        if statement not in statements:
            errors.append(f"packet JSON missing required statement: {statement}")
        if statement not in packet_md:
            errors.append(f"packet markdown missing required statement: {statement}")


def _check_packet_markdown(packet_md: str, errors: list[str]) -> None:
    lower = packet_md.lower()
    for term in REQUIRED_PACKET_TERMS:
        if term.lower() not in lower:
            errors.append(f"packet markdown missing term: {term}")
    for pr_number in EXPECTED_WAVE_PRS.values():
        if f"/pull/{pr_number}" not in packet_md:
            errors.append(f"packet markdown missing PR #{pr_number}")


def _check_risk_registers(
    reports: dict[Path, dict[str, Any]],
    docs: dict[Path, str],
    errors: list[str],
) -> None:
    accepted = reports.get(ACCEPTED_RISK_JSON)
    residual = reports.get(RESIDUAL_RISK_JSON)
    if accepted is not None:
        if accepted.get("schema_version") != "accepted_risk_register_v1":
            errors.append("accepted risk register schema mismatch")
        _check_risk_list(accepted.get("risks"), "accepted risk", errors)
        for risk in accepted.get("risks", []):
            if isinstance(risk, dict) and risk.get("not_accepted_for_final_recognition") is not True:
                errors.append(f"accepted risk must not be accepted for final recognition: {risk.get('risk_id')}")
    if residual is not None:
        if residual.get("schema_version") != "residual_risk_register_v1":
            errors.append("residual risk register schema mismatch")
        _check_risk_list(residual.get("risks"), "residual risk", errors)
        for risk in residual.get("risks", []):
            if isinstance(risk, dict) and risk.get("status") != "open_for_external_review":
                errors.append(f"residual risk must remain open for external review: {risk.get('risk_id')}")

    for doc_path in (
        Path("docs/audits/accepted_risk_register_v1.md"),
        Path("docs/audits/residual_risk_register_v1.md"),
    ):
        text = docs.get(doc_path, "")
        if "External review required" not in text:
            errors.append(f"{doc_path.as_posix()} missing external review boundary")


def _check_risk_list(risks: object, label: str, errors: list[str]) -> None:
    if not isinstance(risks, list) or len(risks) < 3:
        errors.append(f"{label} register must include at least three risks")
        return
    seen: set[str] = set()
    for risk in risks:
        if not isinstance(risk, dict):
            errors.append(f"{label} entry must be object")
            continue
        risk_id = str(risk.get("risk_id", ""))
        if not risk_id:
            errors.append(f"{label} missing risk_id")
        elif risk_id in seen:
            errors.append(f"{label} duplicate risk_id: {risk_id}")
        seen.add(risk_id)
        if not risk.get("title"):
            errors.append(f"{label} {risk_id} missing title")


def _check_final_blockers(
    reports: dict[Path, dict[str, Any]],
    docs: dict[Path, str],
    errors: list[str],
) -> None:
    blockers = reports.get(FINAL_BLOCKER_JSON)
    if blockers is None:
        return
    if blockers.get("schema_version") != "final_blocker_table_v1":
        errors.append("final blocker table schema mismatch")
    if blockers.get("final_verdict") != FINAL_VERDICT:
        errors.append("final blocker table final verdict mismatch")
    if blockers.get("blockers_for_external_review_packet") != []:
        errors.append("external-review packet blocker list must be empty")
    recognition_blockers = blockers.get("blockers_for_final_recognition_analysis")
    if not isinstance(recognition_blockers, list) or len(recognition_blockers) < 3:
        errors.append("final recognition blocker list must retain open blockers")
    text = docs.get(Path("docs/audits/final_blocker_table_v1.md"), "")
    if FINAL_VERDICT not in text:
        errors.append("final blocker markdown missing final verdict")
    for statement in REQUIRED_STATEMENTS[1:3]:
        if statement not in text:
            errors.append(f"final blocker markdown missing retained blocker: {statement}")


def _check_ci_and_makefile(errors: list[str]) -> None:
    ci_text = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    makefile_text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    for token in (
        "scripts/external_audit_packet_check_v1.py",
        "external-audit-check",
        "test-external-audit-packet",
        "final-audit-check",
        "security-check",
        "dogfood-check",
    ):
        if token == "scripts/external_audit_packet_check_v1.py" and token not in ci_text:
            errors.append(".github/workflows/ci.yml missing external audit packet gate")
        if token not in makefile_text:
            errors.append(f"Makefile missing target or gate: {token}")


def _check_text_safety_for_all(
    docs: dict[Path, str],
    reports: dict[Path, dict[str, Any]],
    errors: list[str],
) -> None:
    for relative_path, text in docs.items():
        _check_text_safety(text, relative_path, errors)
    for relative_path, payload in reports.items():
        _check_text_safety(json.dumps(payload, sort_keys=True), relative_path, errors)


def _check_text_safety(text: str, relative_path: Path, errors: list[str]) -> None:
    lower = text.lower()
    for forbidden in FORBIDDEN_SELF_CERT_WORDING:
        if forbidden.lower() in lower:
            errors.append(f"{relative_path.as_posix()} contains forbidden self-cert wording: {forbidden}")
    for marker in LOCAL_PATH_MARKERS:
        if marker in text:
            errors.append(f"{relative_path.as_posix()} contains local path marker: {marker}")


if __name__ == "__main__":
    raise SystemExit(main())
