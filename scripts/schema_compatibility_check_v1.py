#!/usr/bin/env python3
"""Validate Wave 8 schema compatibility policy and frozen schema posture."""

from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = Path("docs/compatibility/schema_versioning_policy_v1.md")
SCHEMA_FREEZE_TAG = "v11-slice1"

CONTRACT_FILES = (
    Path("docs/contracts/task_contract_v1.md"),
    Path("docs/contracts/approval_receipt_v1.md"),
    Path("docs/contracts/rejection_receipt_v1.md"),
    Path("docs/contracts/execution_receipt_v1.md"),
    Path("docs/contracts/evidence_trace_v1.md"),
    Path("docs/contracts/replay_explain_v1.md"),
    Path("docs/contracts/failure_bundle_v1.md"),
    Path("docs/contracts/observation_log_v1.md"),
    Path("docs/contracts/ai_context_bundle_v1.md"),
    Path("docs/contracts/token_roi_v1.md"),
    Path("docs/contracts/provider_request_envelope_v1.md"),
    Path("docs/contracts/provider_response_receipt_v1.md"),
    Path("docs/contracts/release_check_v1.md"),
    Path("docs/contracts/audit_packet_v1.md"),
)

REQUIRED_POLICY_TERMS = (
    "schema_version",
    "contract_version",
    "backward-compatible",
    "forward-compatible",
    "additive change",
    "breaking change",
    "migration mapping",
    "deprecation window",
    "version tuple hash",
    "frozen schema pack",
    "v11-slice1",
    "fail closed",
    "reject unknown fields",
    "no silent downgrade",
    "deterministic replay",
    "external review",
)

FORBIDDEN_FINAL_WORDING = (
    "GLOBAL_RECOGNITION_CONFIRMED",
    "globally recognized",
    "externally certified",
    "world class confirmed",
)

LOCAL_PATH_MARKERS = (
    "/" + "Users" + "/" + "qqy",
    "Documents" + "/" + "Codex",
    "." + "codex",
    "files-mentioned" + "-by-the-user",
)


def main() -> int:
    errors: list[str] = []
    _check_policy_doc(errors)
    _check_frozen_schema_pack(errors)
    _check_contract_docs(errors)
    _check_ci_gate(errors)

    if errors:
        print("schema_compatibility_check_v1: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("schema_compatibility_check_v1: PASS")
    return 0


def _check_policy_doc(errors: list[str]) -> None:
    path = REPO_ROOT / POLICY_PATH
    if not path.exists():
        errors.append(f"missing schema versioning policy: {POLICY_PATH.as_posix()}")
        return
    text = path.read_text(encoding="utf-8")
    lower = " ".join(text.lower().split())
    for term in REQUIRED_POLICY_TERMS:
        if term.lower() not in lower:
            errors.append(f"{POLICY_PATH.as_posix()} missing term: {term}")
    _check_text_safety(text, POLICY_PATH, errors)


def _check_frozen_schema_pack(errors: list[str]) -> None:
    init_path = REPO_ROOT / "kernel/schemas/__init__.py"
    init_text = init_path.read_text(encoding="utf-8") if init_path.exists() else ""
    if f'SCHEMA_FREEZE_TAG = "{SCHEMA_FREEZE_TAG}"' not in init_text:
        errors.append("kernel schema freeze tag mismatch")

    schema_paths = sorted((REPO_ROOT / "kernel/schemas").glob("*.schema.json"))
    if not schema_paths:
        errors.append("no frozen JSON schemas found")
        return
    for path in schema_paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{path.relative_to(REPO_ROOT).as_posix()} invalid JSON: {exc}")
            continue
        if payload.get("schema_version") != SCHEMA_FREEZE_TAG:
            errors.append(f"{path.relative_to(REPO_ROOT).as_posix()} schema_version mismatch")
        if payload.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            errors.append(f"{path.relative_to(REPO_ROOT).as_posix()} JSON Schema draft mismatch")


def _check_contract_docs(errors: list[str]) -> None:
    for relative_path in CONTRACT_FILES:
        path = REPO_ROOT / relative_path
        if not path.exists():
            errors.append(f"missing contract doc: {relative_path.as_posix()}")
            continue
        text = path.read_text(encoding="utf-8")
        lower = " ".join(text.lower().split())
        contract_version = relative_path.stem
        if contract_version not in text:
            errors.append(f"{relative_path.as_posix()} missing contract version token")
        for required in (
            "## Compatibility Rule",
            "## Migration/Deprecation Rule",
            "reject unknown fields",
            "migration requires",
            "fail closed",
        ):
            if required.lower() not in lower:
                errors.append(f"{relative_path.as_posix()} missing compatibility phrase: {required}")
        for block in _extract_json_blocks(text)[:1]:
            try:
                payload = json.loads(block)
            except json.JSONDecodeError as exc:
                errors.append(f"{relative_path.as_posix()} invalid JSON example: {exc}")
                continue
            if payload.get("contract_version") != contract_version:
                errors.append(f"{relative_path.as_posix()} valid example contract_version mismatch")
        _check_text_safety(text, relative_path, errors)


def _extract_json_blocks(text: str) -> list[str]:
    pattern = re.compile(r"```json\n(.*?)\n```", re.DOTALL)
    return [match.group(1) for match in pattern.finditer(text)]


def _check_ci_gate(errors: list[str]) -> None:
    ci_text = (REPO_ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    makefile_text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    token = "scripts/schema_compatibility_check_v1.py"
    if token not in ci_text:
        errors.append(".github/workflows/ci.yml missing schema compatibility gate")
    if token not in makefile_text:
        errors.append("Makefile missing schema compatibility gate")


def _check_text_safety(text: str, relative_path: Path, errors: list[str]) -> None:
    lower = text.lower()
    for forbidden in FORBIDDEN_FINAL_WORDING:
        if forbidden.lower() in lower:
            errors.append(f"{relative_path.as_posix()} contains forbidden final wording: {forbidden}")
    for marker in LOCAL_PATH_MARKERS:
        if marker in text:
            errors.append(f"{relative_path.as_posix()} contains local path marker: {marker}")


if __name__ == "__main__":
    raise SystemExit(main())
