#!/usr/bin/env python3
"""Validate release-candidate invariants for readiness waves."""

from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RC_TAG = "v0.1.0-rc3"
EXPECTED_TARGET = "9a363f95b85602ffc598db463dc6181a9bbbdf3c"

REQUIRED_REFERENCES = (
    Path("CHANGELOG.md"),
    Path("SECURITY.md"),
    Path("docs/current_phase.md"),
    Path("docs/supply_chain/provenance_and_checksum_policy_v1.md"),
    Path("docs/supply_chain/supply_chain_integrity_policy_v1.md"),
)


def main() -> int:
    errors: list[str] = []
    _check_tag_target(errors)
    _check_documents(errors)

    if errors:
        print("release_invariant_check_v1: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("release_invariant_check_v1: PASS")
    return 0


def _check_tag_target(errors: list[str]) -> None:
    completed = subprocess.run(
        ["git", "rev-parse", f"{RC_TAG}^{{}}"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        errors.append(f"missing release-candidate tag: {RC_TAG}")
        return
    actual = completed.stdout.strip()
    if actual != EXPECTED_TARGET:
        errors.append(f"{RC_TAG} target changed: {actual}")


def _check_documents(errors: list[str]) -> None:
    for relative_path in REQUIRED_REFERENCES:
        path = REPO_ROOT / relative_path
        if not path.exists():
            errors.append(f"missing release invariant reference: {relative_path.as_posix()}")
            continue
        text = path.read_text(encoding="utf-8")
        if RC_TAG not in text:
            errors.append(f"{relative_path.as_posix()} missing {RC_TAG}")
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if "unchanged for this readiness program" not in changelog:
        errors.append("CHANGELOG missing tag immutability wording")


if __name__ == "__main__":
    raise SystemExit(main())
