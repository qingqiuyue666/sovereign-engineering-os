#!/usr/bin/env python3
"""Validate Wave 5 secret and AI context safety policy."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    Path("SECURITY.md"),
    Path("docs/security/secret_safety_policy_v1.md"),
    Path("docs/security/ai_context_safety_policy_v1.md"),
    Path("docs/contracts/ai_context_bundle_v1.md"),
    Path("docs/contracts/provider_request_envelope_v1.md"),
    Path("docs/contracts/provider_response_receipt_v1.md"),
    Path("scripts/adversarial_smoke_v1.py"),
)

REQUIRED_TERMS = (
    "Do not put secrets",
    "must not include real secrets",
    "digest-bound",
    "secret_values_present",
    "raw_response_stored",
    "prompt injection",
    "provider response poisoning",
)

FORBIDDEN_REPOSITORY_SNIPPETS = (
    "cat .env",
    "printenv",
    "gh secret",
)


def main() -> int:
    errors: list[str] = []
    combined_parts: list[str] = []
    for relative_path in REQUIRED_FILES:
        path = REPO_ROOT / relative_path
        if not path.exists():
            errors.append(f"missing secret/context safety file: {relative_path.as_posix()}")
            continue
        combined_parts.append(path.read_text(encoding="utf-8"))
    combined = "\n".join(combined_parts)
    for term in REQUIRED_TERMS:
        if term not in combined:
            errors.append(f"missing secret/context safety term: {term}")
    _check_forbidden_snippets(errors)

    if errors:
        print("secret_context_safety_check_v1: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("secret_context_safety_check_v1: PASS")
    return 0


def _check_forbidden_snippets(errors: list[str]) -> None:
    checked_paths = [
        *(REPO_ROOT / "scripts").glob("*.sh"),
        *((REPO_ROOT / ".github" / "workflows").glob("*.yml")),
        *((REPO_ROOT / ".github" / "workflows").glob("*.yaml")),
    ]
    for path in checked_paths:
        text = path.read_text(encoding="utf-8")
        for snippet in FORBIDDEN_REPOSITORY_SNIPPETS:
            if snippet in text:
                errors.append(
                    f"forbidden secret handling snippet {snippet!r} in "
                    f"{path.relative_to(REPO_ROOT).as_posix()}"
                )


if __name__ == "__main__":
    raise SystemExit(main())
