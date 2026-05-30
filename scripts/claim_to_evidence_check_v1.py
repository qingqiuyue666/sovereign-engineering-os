#!/usr/bin/env python3
"""Validate Wave 3 claim-to-evidence matrix artifacts."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MATRIX_JSON = Path("reports/audits/claim_to_evidence_matrix_v1.json")
MATRIX_MD = Path("docs/audits/claim_to_evidence_matrix_v1.md")

REQUIRED_CLAIM_FIELDS = (
    "claim_id",
    "claim",
    "allowed_public_wording",
    "evidence_refs",
    "validation_refs",
    "status",
    "limitations",
    "forbidden_wording",
)

ALLOWED_STATUSES = {
    "supported_by_repository_evidence",
    "bounded_by_repository_evidence",
    "requires_external_review",
}

FORBIDDEN_FINAL_WORDING = (
    "global recognition confirmed",
    "globally recognized",
    "externally certified",
    "world class confirmed",
    "top tier signed",
)

LOCAL_PATH_MARKERS = (
    "/" + "Users" + "/" + "qqy",
    "Documents" + "/" + "Codex",
    "." + "codex",
    "files-mentioned" + "-by-the-user",
)


def main() -> int:
    errors: list[str] = []
    payload = _load_matrix(errors)
    md_text = _load_markdown(errors)

    if payload is not None:
        _check_matrix_payload(payload, md_text, errors)
    if md_text is not None:
        _check_markdown(md_text, errors)

    if errors:
        print("claim_to_evidence_check_v1: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("claim_to_evidence_check_v1: PASS")
    return 0


def _load_matrix(errors: list[str]) -> dict | None:
    path = REPO_ROOT / MATRIX_JSON
    if not path.exists():
        errors.append(f"missing matrix JSON: {MATRIX_JSON.as_posix()}")
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"matrix JSON invalid: {exc}")
        return None
    if not isinstance(payload, dict):
        errors.append("matrix JSON must be object")
        return None
    return payload


def _load_markdown(errors: list[str]) -> str | None:
    path = REPO_ROOT / MATRIX_MD
    if not path.exists():
        errors.append(f"missing matrix markdown: {MATRIX_MD.as_posix()}")
        return None
    return path.read_text(encoding="utf-8")


def _check_matrix_payload(
    payload: dict, md_text: str | None, errors: list[str]
) -> None:
    if payload.get("schema_version") != "claim_to_evidence_matrix_v1":
        errors.append("matrix schema_version mismatch")
    if payload.get("external_review_required") is not True:
        errors.append("matrix must require external review")
    if payload.get("global_recognition_claimed") is not False:
        errors.append("matrix must not claim global recognition")

    claims = payload.get("claims")
    if not isinstance(claims, list) or len(claims) < 6:
        errors.append("matrix must contain at least six claims")
        return

    seen_ids: set[str] = set()
    for index, claim in enumerate(claims, start=1):
        if not isinstance(claim, dict):
            errors.append(f"claim {index} must be object")
            continue
        _check_claim(claim, seen_ids, md_text, errors)


def _check_claim(
    claim: dict, seen_ids: set[str], md_text: str | None, errors: list[str]
) -> None:
    claim_id = str(claim.get("claim_id", ""))
    if not claim_id:
        errors.append("claim missing claim_id")
    elif claim_id in seen_ids:
        errors.append(f"duplicate claim_id: {claim_id}")
    else:
        seen_ids.add(claim_id)

    for field in REQUIRED_CLAIM_FIELDS:
        if field not in claim:
            errors.append(f"{claim_id or '<unknown>'} missing field: {field}")

    if claim.get("status") not in ALLOWED_STATUSES:
        errors.append(f"{claim_id} has invalid status: {claim.get('status')}")

    for list_field in (
        "evidence_refs",
        "validation_refs",
        "limitations",
        "forbidden_wording",
    ):
        value = claim.get(list_field)
        if not isinstance(value, list) or not value:
            errors.append(f"{claim_id} field must be non-empty list: {list_field}")

    for evidence_ref in claim.get("evidence_refs", []):
        evidence_path = REPO_ROOT / evidence_ref
        if not evidence_path.exists():
            errors.append(f"{claim_id} evidence ref missing: {evidence_ref}")

    text_blob = " ".join(
        str(claim.get(field, "")) for field in ("claim", "allowed_public_wording")
    ).lower()
    for forbidden in FORBIDDEN_FINAL_WORDING:
        if forbidden in text_blob:
            errors.append(f"{claim_id} contains forbidden final wording: {forbidden}")

    forbidden_wording = " ".join(claim.get("forbidden_wording", [])).lower()
    if "global recognition" not in forbidden_wording:
        errors.append(f"{claim_id} forbidden_wording must include global recognition")

    if md_text is not None and claim_id and claim_id not in md_text:
        errors.append(f"markdown matrix missing claim id: {claim_id}")


def _check_markdown(md_text: str, errors: list[str]) -> None:
    for required in (
        "# Claim To Evidence Matrix V1",
        "External review required",
        "No global recognition claim",
    ):
        if required not in md_text:
            errors.append(f"markdown matrix missing phrase: {required}")
    lower = md_text.lower()
    for forbidden in FORBIDDEN_FINAL_WORDING:
        if forbidden in lower and f"not claim {forbidden}" not in lower:
            errors.append(f"markdown matrix contains forbidden wording: {forbidden}")
    for marker in LOCAL_PATH_MARKERS:
        if marker in md_text:
            errors.append(f"markdown matrix contains local path marker: {marker}")


if __name__ == "__main__":
    raise SystemExit(main())
