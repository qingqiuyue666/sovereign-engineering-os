#!/usr/bin/env python3
"""Validate Wave 5 supply-chain evidence."""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_DOCS = (
    Path("docs/supply_chain/supply_chain_integrity_policy_v1.md"),
    Path("docs/supply_chain/dependency_policy_v1.md"),
    Path("docs/supply_chain/github_actions_policy_v1.md"),
    Path("docs/supply_chain/provenance_and_checksum_policy_v1.md"),
    Path("docs/supply_chain/sbom_strategy_v1.md"),
)

REQUIRED_POLICY_TERMS = (
    "no `curl | bash`",
    "no uncontrolled network in tests",
    "minimal CI permissions",
    "GitHub Actions pinning policy",
    "dependency review policy",
    "artifact checksum",
    "tag immutability",
    "SBOM strategy",
)

FORBIDDEN_SHELL_PATTERNS = (
    re.compile(r"curl\s+[^|\n]*\|\s*bash"),
    re.compile(r"wget\s+[^|\n]*\|\s*bash"),
)


def main() -> int:
    errors: list[str] = []
    texts = _load_docs(errors)
    _check_policy_terms(texts, errors)
    _check_ci_policy(errors)
    _check_shell_scripts(errors)

    if errors:
        print("supply_chain_check_v1: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("supply_chain_check_v1: PASS")
    return 0


def _load_docs(errors: list[str]) -> dict[Path, str]:
    texts: dict[Path, str] = {}
    for relative_path in REQUIRED_DOCS:
        path = REPO_ROOT / relative_path
        if not path.exists():
            errors.append(f"missing supply-chain doc: {relative_path.as_posix()}")
            continue
        texts[relative_path] = path.read_text(encoding="utf-8")
    return texts


def _check_policy_terms(texts: dict[Path, str], errors: list[str]) -> None:
    combined = "\n".join(texts.values())
    for term in REQUIRED_POLICY_TERMS:
        if term not in combined:
            errors.append(f"missing supply-chain policy term: {term}")


def _check_ci_policy(errors: list[str]) -> None:
    ci_path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
    if not ci_path.exists():
        errors.append("missing CI workflow")
        return
    text = ci_path.read_text(encoding="utf-8")
    if "permissions:" not in text or "contents: read" not in text:
        errors.append("CI workflow missing minimal read-only permissions")
    if "pull_request_target" in text:
        errors.append("CI workflow must not use pull_request_target")
    for required in (
        "scripts/security_control_check_v1.py",
        "scripts/supply_chain_check_v1.py",
        "scripts/secret_context_safety_check_v1.py",
        "scripts/release_invariant_check_v1.py",
        "make ci",
    ):
        if required not in text:
            errors.append(f"CI workflow missing Wave 5 gate: {required}")


def _check_shell_scripts(errors: list[str]) -> None:
    for path in sorted((REPO_ROOT / "scripts").glob("*.sh")):
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_SHELL_PATTERNS:
            if pattern.search(text):
                errors.append(f"shell script contains pipe-to-bash pattern: {path.name}")


if __name__ == "__main__":
    raise SystemExit(main())
