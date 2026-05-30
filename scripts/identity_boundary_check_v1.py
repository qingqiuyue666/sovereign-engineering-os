#!/usr/bin/env python3
"""Validate Wave 1 public identity and repository boundary claims."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    Path("README.md"),
    Path("docs/identity/system_identity_v1.md"),
    Path("docs/identity/non_goals_v1.md"),
    Path("SECURITY.md"),
    Path("CHANGELOG.md"),
    Path("docs/quickstart/local_first_quickstart_v1.md"),
    Path("docs/architecture/seos_control_plane_v1.md"),
    Path("examples/README.md"),
    Path("scripts/identity_boundary_check_v1.py"),
    Path("tests/tracer_bullet/test_identity_boundary_v1.py"),
    Path("docs/current_phase.md"),
)

PUBLIC_IDENTITY_FILES = (
    Path("README.md"),
    Path("docs/identity/system_identity_v1.md"),
    Path("docs/identity/non_goals_v1.md"),
    Path("SECURITY.md"),
    Path("CHANGELOG.md"),
    Path("docs/quickstart/local_first_quickstart_v1.md"),
    Path("docs/architecture/seos_control_plane_v1.md"),
    Path("examples/README.md"),
    Path("docs/current_phase.md"),
)

REQUIRED_STATUS_ANCHORS = (
    "SYSTEM_LANDED",
    "REAL_OPERATION_OBSERVATION_PERIOD_ACTIVE",
    "LOCAL_REAL_USE_VALIDATED",
    "APPROVAL_GATE_VALIDATED",
    "CLEAN_CLONE_VALIDATED",
    "NO_HARD_EVIDENCE_BLOCKER_RECORDED",
)

REQUIRED_README_TOPICS = (
    "What SEOS Solves",
    "What SEOS Is Not",
    "Quickstart",
    "Validation",
    "Observation Mode",
    "Evidence Model",
    "Security Boundary",
    "Known Limitations",
    "External Audit Readiness",
)

STALE_CURRENT_STATE_MARKERS = (
    "Current phase/state: Personal AI Execution OS final product-completion",
    "Current phase: Personal AI Execution OS final product-completion candidate",
    "FINAL_PRODUCT_COMPLETION_READY_FOR_REVIEW",
    "Personal AI Execution OS final product-completion candidate",
)

FORBIDDEN_FINAL_CLAIMS = (
    "GLOBAL_RECOGNITION_CONFIRMED",
    "TOP_TIER_SIGNED",
    "FULLY_RECOGNIZED",
    "FINAL WORLD-CLASS CONFIRMED",
)

LOCAL_PATH_MARKERS = (
    "/" + "Users" + "/" + "qqy",
    "Documents" + "/" + "Codex",
    "." + "codex",
    "files-mentioned" + "-by-the-user",
)

POSITIVE_FORBIDDEN_CLAIMS = (
    "seos is an os-level sandbox",
    "seos is an os sandbox",
    "seos provides os-level isolation",
    "seos provides an os-level sandbox",
    "seos is rpa",
    "seos is a rpa",
    "seos is a computer-control framework",
    "seos is a computer control framework",
    "seos is an autonomous ai executor",
    "seos is a commercial saas",
    "seos is a secret manager",
)

REQUIRED_NON_GOAL_PHRASES = (
    "not an OS-level sandbox",
    "not RPA",
    "not a computer-control framework",
    "not an autonomous AI executor",
    "not a commercial SaaS platform",
    "not a secret manager",
)

EVIDENCE_CHAIN_TERMS = (
    "Claim",
    "Risk",
    "Control",
    "Implementation",
    "Validation command",
    "Gate",
    "Evidence artifact",
    "Residual risk",
)


def main() -> int:
    errors: list[str] = []
    texts = _load_required_files(errors)
    _check_readme(texts, errors)
    _check_public_identity_texts(texts, errors)
    _check_repository_path_leaks(errors)
    _check_item_continuation_language(texts, errors)
    _check_evidence_chains(texts, errors)

    if errors:
        print("identity_boundary_check_v1: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("identity_boundary_check_v1: PASS")
    return 0


def _load_required_files(errors: list[str]) -> dict[Path, str]:
    texts: dict[Path, str] = {}
    for relative_path in REQUIRED_FILES:
        path = REPO_ROOT / relative_path
        if not path.exists():
            errors.append(f"missing required file: {relative_path.as_posix()}")
            continue
        texts[relative_path] = path.read_text(encoding="utf-8")
    return texts


def _check_readme(texts: dict[Path, str], errors: list[str]) -> None:
    readme = texts.get(Path("README.md"), "")
    for anchor in REQUIRED_STATUS_ANCHORS:
        if anchor not in readme:
            errors.append(f"README missing status anchor: {anchor}")
    for topic in REQUIRED_README_TOPICS:
        if topic not in readme:
            errors.append(f"README missing topic: {topic}")
    for phrase in REQUIRED_NON_GOAL_PHRASES:
        if phrase not in readme:
            errors.append(f"README missing non-goal phrase: {phrase}")
    if "v0.1.0-rc3" not in readme:
        errors.append("README missing release-candidate tag")


def _check_public_identity_texts(
    texts: dict[Path, str], errors: list[str]
) -> None:
    for relative_path in PUBLIC_IDENTITY_FILES:
        text = texts.get(relative_path, "")
        lower = " ".join(text.lower().split())
        for marker in STALE_CURRENT_STATE_MARKERS:
            if marker in text:
                errors.append(
                    f"stale current-state marker in {relative_path.as_posix()}: "
                    f"{marker}"
                )
        for claim in FORBIDDEN_FINAL_CLAIMS:
            if claim in text:
                errors.append(
                    f"forbidden final recognition claim in "
                    f"{relative_path.as_posix()}: {claim}"
                )
        for claim in POSITIVE_FORBIDDEN_CLAIMS:
            if claim in lower:
                errors.append(
                    f"positive forbidden capability claim in "
                    f"{relative_path.as_posix()}: {claim}"
                )


def _check_repository_path_leaks(errors: list[str]) -> None:
    checked_suffixes = {".md", ".txt", ".yml", ".yaml", ".toml"}
    roots = (
        REPO_ROOT / "README.md",
        REPO_ROOT / "SECURITY.md",
        REPO_ROOT / "CHANGELOG.md",
        REPO_ROOT / "docs",
        REPO_ROOT / "examples",
        REPO_ROOT / ".github",
        REPO_ROOT / "pyproject.toml",
    )
    for path in _iter_text_paths(roots, checked_suffixes):
        text = path.read_text(encoding="utf-8")
        for marker in LOCAL_PATH_MARKERS:
            if marker in text:
                errors.append(
                    f"local path leak marker {marker!r} found in "
                    f"{path.relative_to(REPO_ROOT).as_posix()}"
                )


def _iter_text_paths(
    roots: tuple[Path, ...], checked_suffixes: set[str]
) -> list[Path]:
    paths: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        if root.is_file():
            paths.append(root)
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in checked_suffixes:
                paths.append(path)
    return paths


def _check_item_continuation_language(
    texts: dict[Path, str], errors: list[str]
) -> None:
    for relative_path in PUBLIC_IDENTITY_FILES:
        for line_number, line in enumerate(
            texts.get(relative_path, "").splitlines(), start=1
        ):
            lower = line.lower()
            if not any(item in lower for item in ("item 28", "item 29", "item 30")):
                continue
            if not any(word in lower for word in ("allow", "allowed", "next")):
                continue
            if any(word in lower for word in ("no", "not", "forbid", "reject")):
                continue
            errors.append(
                "forbidden continuation language in "
                f"{relative_path.as_posix()}:{line_number}"
            )


def _check_evidence_chains(texts: dict[Path, str], errors: list[str]) -> None:
    for relative_path in (
        Path("docs/identity/system_identity_v1.md"),
        Path("docs/identity/non_goals_v1.md"),
        Path("docs/quickstart/local_first_quickstart_v1.md"),
        Path("docs/architecture/seos_control_plane_v1.md"),
        Path("examples/README.md"),
    ):
        text = texts.get(relative_path, "")
        for term in EVIDENCE_CHAIN_TERMS:
            if term not in text:
                errors.append(
                    f"{relative_path.as_posix()} missing evidence chain term: {term}"
                )


if __name__ == "__main__":
    raise SystemExit(main())
