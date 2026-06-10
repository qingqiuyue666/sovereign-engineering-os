#!/usr/bin/env python3
"""Validate Wave 5 security control evidence."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DOCS = (
    Path("docs/security/threat_model_v1.md"),
    Path("docs/security/abuse_case_catalog_v1.md"),
    Path("docs/security/security_control_matrix_v1.md"),
    Path("docs/security/secret_safety_policy_v1.md"),
    Path("docs/security/ai_context_safety_policy_v1.md"),
    Path("docs/operator/operator_safety_checklist_v1.md"),
    Path("docs/operator/ai_proposal_review_checklist_v1.md"),
)

REQUIRED_CONTROLS = (
    "AI approval bypass",
    "fake PASS",
    "receipt forgery",
    "missing evidence",
    "replay false success",
    "secret leakage",
    "context leakage",
    "provider response poisoning",
    "malicious PR/patch",
    "CI bypass",
    "dependency risk",
    "GitHub Actions risk",
    "operator misapproval",
    "tag mutation",
    "local path leakage",
)

LOCAL_PATH_MARKERS = (
    "/" + "Users" + "/" + "qqy",
    "Documents" + "/" + "Codex",
    "." + "codex",
    "files-mentioned" + "-by-the-user",
)

FORBIDDEN_CLAIMS = (
    "GLOBAL_RECOGNITION_CONFIRMED",
    "externally certified",
    "world class confirmed",
)


def main() -> int:
    errors: list[str] = []
    texts = _load_docs(errors)
    _check_controls(texts, errors)
    _check_public_safety(texts, errors)

    if errors:
        print("security_control_check_v1: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("security_control_check_v1: PASS")
    return 0


def _load_docs(errors: list[str]) -> dict[Path, str]:
    texts: dict[Path, str] = {}
    for relative_path in REQUIRED_DOCS:
        path = REPO_ROOT / relative_path
        if not path.exists():
            errors.append(f"missing required security doc: {relative_path.as_posix()}")
            continue
        texts[relative_path] = path.read_text(encoding="utf-8")
    return texts


def _check_controls(texts: dict[Path, str], errors: list[str]) -> None:
    matrix = texts.get(Path("docs/security/security_control_matrix_v1.md"), "")
    catalog = texts.get(Path("docs/security/abuse_case_catalog_v1.md"), "")
    threat_model = texts.get(Path("docs/security/threat_model_v1.md"), "")
    combined = "\n".join((matrix, catalog, threat_model))
    for control in REQUIRED_CONTROLS:
        if control not in combined:
            errors.append(f"missing required control coverage: {control}")
    for required_command in (
        "python3 scripts/adversarial_smoke_v1.py",
        "bash scripts/failure_path_smoke_v1.sh",
        "python3 scripts/secret_context_safety_check_v1.py",
        "python3 scripts/release_invariant_check_v1.py",
    ):
        if required_command not in combined:
            errors.append(f"security controls missing validation command: {required_command}")


def _check_public_safety(texts: dict[Path, str], errors: list[str]) -> None:
    for relative_path, text in texts.items():
        lower = text.lower()
        for marker in LOCAL_PATH_MARKERS:
            if marker in text:
                errors.append(f"{relative_path.as_posix()} contains local path marker: {marker}")
        for claim in FORBIDDEN_CLAIMS:
            if claim.lower() in lower:
                errors.append(f"{relative_path.as_posix()} contains forbidden claim: {claim}")
        if "external review" not in lower and relative_path.name in {
            "threat_model_v1.md",
            "abuse_case_catalog_v1.md",
            "security_control_matrix_v1.md",
        }:
            errors.append(f"{relative_path.as_posix()} missing external review boundary")


if __name__ == "__main__":
    raise SystemExit(main())
