#!/usr/bin/env python3
"""Validate Wave 3 public contract documents."""

from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

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

REQUIRED_SECTIONS = (
    "Purpose",
    "Required Fields",
    "Optional Fields",
    "Version",
    "Immutability Rule",
    "Unknown Field Policy",
    "Compatibility Rule",
    "Migration/Deprecation Rule",
    "Valid Example",
    "Invalid Example",
    "Failure Behavior",
)

FORBIDDEN_CLAIMS = (
    "GLOBAL_RECOGNITION_CONFIRMED",
    "TOP_TIER_SIGNED",
    "FULLY_RECOGNIZED",
    "final world-class confirmed",
    "externally certified",
)

LOCAL_PATH_MARKERS = (
    "/" + "Users" + "/" + "qqy",
    "Documents" + "/" + "Codex",
    "." + "codex",
    "files-mentioned" + "-by-the-user",
)


def main() -> int:
    errors: list[str] = []
    for relative_path in CONTRACT_FILES:
        _check_contract_file(relative_path, errors)

    if errors:
        print("contract_check_v1: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("contract_check_v1: PASS")
    return 0


def _check_contract_file(relative_path: Path, errors: list[str]) -> None:
    path = REPO_ROOT / relative_path
    if not path.exists():
        errors.append(f"missing contract file: {relative_path.as_posix()}")
        return

    text = path.read_text(encoding="utf-8")
    contract_version = relative_path.stem

    if not text.startswith("# "):
        errors.append(f"{relative_path.as_posix()} missing H1 title")
    if contract_version not in text:
        errors.append(
            f"{relative_path.as_posix()} missing version token {contract_version}"
        )

    for section in REQUIRED_SECTIONS:
        if f"## {section}" not in text:
            errors.append(f"{relative_path.as_posix()} missing section: {section}")

    lower = " ".join(text.lower().split())
    for required_phrase in (
        "fail closed",
        "reject unknown fields",
        "must not be mutated",
        "migration requires",
    ):
        if required_phrase not in lower:
            errors.append(
                f"{relative_path.as_posix()} missing phrase: {required_phrase}"
            )

    for claim in FORBIDDEN_CLAIMS:
        if claim.lower() in lower:
            errors.append(
                f"{relative_path.as_posix()} contains forbidden claim: {claim}"
            )

    for marker in LOCAL_PATH_MARKERS:
        if marker in text:
            errors.append(
                f"{relative_path.as_posix()} contains local path marker: {marker}"
            )

    json_blocks = _extract_json_blocks(text)
    if len(json_blocks) < 2:
        errors.append(f"{relative_path.as_posix()} needs valid and invalid JSON")
        return

    for index, block in enumerate(json_blocks[:2], start=1):
        try:
            payload = json.loads(block)
        except json.JSONDecodeError as exc:
            errors.append(
                f"{relative_path.as_posix()} JSON example {index} invalid: {exc}"
            )
            continue
        if not isinstance(payload, dict):
            errors.append(
                f"{relative_path.as_posix()} JSON example {index} must be object"
            )
            continue
        if index == 1 and payload.get("contract_version") != contract_version:
            errors.append(
                f"{relative_path.as_posix()} valid example version mismatch"
            )


def _extract_json_blocks(text: str) -> list[str]:
    pattern = re.compile(r"```json\n(.*?)\n```", re.DOTALL)
    return [match.group(1) for match in pattern.finditer(text)]


if __name__ == "__main__":
    raise SystemExit(main())
