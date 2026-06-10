#!/usr/bin/env python3
"""Validate Real Operation Observation Period V1 deliverables."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    Path("docs/runbooks/real_operation_observation_period_v1.md"),
    Path("reports/observation/real_operation_observation_log_v1.md"),
    Path("reports/observation/real_operation_observation_log_v1.json"),
    Path("governance/policy/observation_period_change_policy_v1.md"),
    Path("scripts/observation_check_v1.py"),
    Path("tests/tracer_bullet/test_real_operation_observation_period_v1.py"),
)

REQUIRED_JSON_KEYS = (
    "schema_version",
    "observation_period_id",
    "start_state",
    "main_head",
    "release_candidate_tag",
    "mode",
    "active_development_allowed",
    "allowed_change_classes",
    "forbidden_change_classes",
    "hard_evidence_blocker_types",
    "observations",
    "current_verdict",
)

STATE_ANCHORS = (
    "LANDING_READY_NO_FURTHER_STAGE_REQUIRED",
    "MAIN_MERGED",
    "POST_MERGE_VALIDATED",
    "FINAL_RC_TAGGED",
    "DRAFT_RELEASE_CREATED",
)

MAIN_HEAD = "9a363f95b85602ffc598db463dc6181a9bbbdf3c"
RELEASE_CANDIDATE_TAG = "v0.1.0-rc3"
MODE = "real_operation_observation"
CURRENT_VERDICT = "NO_HARD_EVIDENCE_BLOCKER_RECORDED"
NO_HARD_BLOCKER_STATEMENT = (
    "No hard evidence blocker is currently recorded at observation start."
)
SECURITY_BOUNDARY = (
    "SEOS is a governance-level control plane, not an OS-level sandbox, "
    "container, VM, EDR, filesystem permission boundary, RPA system, "
    "computer-control system, or secret manager."
)

PATH_LEAK_MARKERS = (
    "/" + "Users" + "/" + "qqy",
    "/" + "Users" + "/",
    "Documents" + "/" + "Codex",
    "." + "codex",
    "files-mentioned" + "-by-the-user",
)

BAD_OS_SANDBOX_CLAIMS = (
    "seos is an os-level sandbox",
    "seos is an os sandbox",
    "seos provides an os-level sandbox",
    "seos provides os-level sandbox",
    "seos acts as an os-level sandbox",
    "seos is a container",
    "seos is a vm",
    "seos is an edr",
    "seos is a filesystem permission boundary",
)


def main() -> int:
    errors: list[str] = []

    texts: dict[Path, str] = {}
    for relative_path in REQUIRED_FILES:
        path = REPO_ROOT / relative_path
        if not path.exists():
            errors.append(f"missing required file: {relative_path.as_posix()}")
            continue
        texts[relative_path] = path.read_text(encoding="utf-8")

    observation_json = _load_observation_json(errors)
    if observation_json is not None:
        _check_observation_json(observation_json, errors)

    _check_path_leaks(texts, errors)
    _check_required_anchors(texts, errors)
    _check_item_28_not_allowed(texts, errors)
    _check_security_boundary(texts, errors)
    _check_observation_log_statement(texts, errors)

    if errors:
        print("observation_check_v1: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("observation_check_v1: PASS")
    return 0


def _load_observation_json(errors: list[str]) -> dict[str, object] | None:
    path = REPO_ROOT / "reports/observation/real_operation_observation_log_v1.json"
    if not path.exists():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid observation JSON: {exc}")
        return None
    if not isinstance(loaded, dict):
        errors.append("observation JSON root must be an object")
        return None
    return loaded


def _check_observation_json(
    observation_json: dict[str, object], errors: list[str]
) -> None:
    for key in REQUIRED_JSON_KEYS:
        if key not in observation_json:
            errors.append(f"observation JSON missing key: {key}")

    if observation_json.get("mode") != MODE:
        errors.append("observation JSON mode must be real_operation_observation")
    if observation_json.get("active_development_allowed") is not False:
        errors.append("observation JSON active_development_allowed must be false")
    if not observation_json.get("current_verdict"):
        errors.append("observation JSON current_verdict must exist")
    if observation_json.get("current_verdict") != CURRENT_VERDICT:
        errors.append(
            "observation JSON current_verdict must be "
            "NO_HARD_EVIDENCE_BLOCKER_RECORDED"
        )


def _check_path_leaks(texts: dict[Path, str], errors: list[str]) -> None:
    for relative_path, text in texts.items():
        for marker in PATH_LEAK_MARKERS:
            if marker in text:
                errors.append(
                    f"local path leak marker {marker!r} found in "
                    f"{relative_path.as_posix()}"
                )


def _check_required_anchors(texts: dict[Path, str], errors: list[str]) -> None:
    combined = "\n".join(texts.values())
    for anchor in STATE_ANCHORS:
        if anchor not in combined:
            errors.append(f"missing state anchor: {anchor}")
    if MAIN_HEAD not in combined:
        errors.append(f"missing final main HEAD anchor: {MAIN_HEAD}")
    if RELEASE_CANDIDATE_TAG not in combined:
        errors.append(f"missing release candidate tag anchor: {RELEASE_CANDIDATE_TAG}")


def _check_item_28_not_allowed(texts: dict[Path, str], errors: list[str]) -> None:
    for relative_path, text in texts.items():
        for line_number, line in enumerate(text.splitlines(), start=1):
            lower = line.lower()
            if "item 28" not in lower:
                continue
            if "allow" not in lower and "allowed" not in lower:
                continue
            if any(word in lower for word in ("no", "not", "forbid", "reject")):
                continue
            errors.append(
                "forbidden item continuation appears as allowed language in "
                f"{relative_path.as_posix()}:{line_number}"
            )


def _check_security_boundary(texts: dict[Path, str], errors: list[str]) -> None:
    combined = "\n".join(texts.values())
    if SECURITY_BOUNDARY not in combined:
        errors.append("required security boundary wording is missing")
    checked_paths = (
        Path("docs/runbooks/real_operation_observation_period_v1.md"),
        Path("governance/policy/observation_period_change_policy_v1.md"),
    )
    for relative_path in checked_paths:
        text = texts.get(relative_path, "")
        lower = " ".join(text.lower().split())
        for bad_claim in BAD_OS_SANDBOX_CLAIMS:
            if bad_claim in lower:
                errors.append(
                    f"OS-sandbox claim found in {relative_path.as_posix()}: "
                    f"{bad_claim}"
                )


def _check_observation_log_statement(
    texts: dict[Path, str], errors: list[str]
) -> None:
    log_path = Path("reports/observation/real_operation_observation_log_v1.md")
    if NO_HARD_BLOCKER_STATEMENT not in texts.get(log_path, ""):
        errors.append("observation log missing required no-hard-blocker statement")


if __name__ == "__main__":
    raise SystemExit(main())
