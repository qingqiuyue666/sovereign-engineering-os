#!/usr/bin/env python3
"""Validate Wave 7 dogfooding evidence records."""

from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_JSON = Path("reports/dogfood/dogfood_index_v1.json")

REQUIRED_CATEGORIES = {
    "repository_maturity_readme_docs_hardening",
    "failure_path_hardening",
    "installability_reproducibility_hardening",
    "ai_admission_safety_hardening",
    "security_supply_chain_threat_model_hardening",
}

REQUIRED_RECORD_FIELDS = (
    "schema_version",
    "record_id",
    "category",
    "historical_evidence_available",
    "task_contract",
    "approval_receipt",
    "dry_run_execution_receipt",
    "evidence_trace",
    "replay_explain",
    "pr_link_or_commit_reference",
    "validation_result",
    "post_merge_validation",
    "outcome",
    "residual_risk",
    "fabrication_guard",
)

REQUIRED_MARKDOWN_SECTIONS = (
    "## Task Contract",
    "## Approval Receipt",
    "## Dry-Run/Execution Receipt",
    "## Evidence Trace",
    "## Replay Explain",
    "## PR Or Commit Reference",
    "## Validation Result",
    "## Post-Merge Validation",
    "## Outcome",
    "## Residual Risk",
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

COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
PR_URL_RE = re.compile(r"^https://github\.com/qqyqqyqqy666-wq/sovereign-engineering-os/pull/[0-9]+$")
RUN_URL_RE = re.compile(r"^https://github\.com/qqyqqyqqy666-wq/sovereign-engineering-os/actions/runs/[0-9]+$")


def main() -> int:
    errors: list[str] = []
    index = _load_json(INDEX_JSON, errors)
    if index is not None:
        _check_index(index, errors)

    if errors:
        print("dogfood_evidence_check_v1: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("dogfood_evidence_check_v1: PASS")
    return 0


def _load_json(relative_path: Path, errors: list[str]) -> dict | None:
    path = REPO_ROOT / relative_path
    if not path.exists():
        errors.append(f"missing JSON file: {relative_path.as_posix()}")
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {relative_path.as_posix()}: {exc}")
        return None
    if not isinstance(payload, dict):
        errors.append(f"JSON must be object: {relative_path.as_posix()}")
        return None
    return payload


def _check_index(index: dict, errors: list[str]) -> None:
    if index.get("schema_version") != "dogfood_index_v1":
        errors.append("dogfood index schema_version mismatch")
    if index.get("external_review_required") is not True:
        errors.append("dogfood index must require external review")
    if index.get("global_recognition_claimed") is not False:
        errors.append("dogfood index must not claim global recognition")

    records = index.get("records")
    if not isinstance(records, list) or len(records) < 5:
        errors.append("dogfood index must contain at least five records")
        return

    categories = {str(record.get("category", "")) for record in records if isinstance(record, dict)}
    missing = REQUIRED_CATEGORIES - categories
    if missing:
        errors.append(f"dogfood index missing required categories: {', '.join(sorted(missing))}")

    seen_ids: set[str] = set()
    for entry in records:
        if not isinstance(entry, dict):
            errors.append("dogfood index record entry must be object")
            continue
        _check_record_entry(entry, seen_ids, errors)


def _check_record_entry(entry: dict, seen_ids: set[str], errors: list[str]) -> None:
    record_id = str(entry.get("record_id", ""))
    if not record_id:
        errors.append("dogfood record missing record_id in index")
    elif record_id in seen_ids:
        errors.append(f"duplicate dogfood record id: {record_id}")
    else:
        seen_ids.add(record_id)

    json_path = Path(str(entry.get("json_path", "")))
    markdown_path = Path(str(entry.get("markdown_path", "")))
    record = _load_json(json_path, errors)
    markdown_text = _load_markdown(markdown_path, errors)

    if record is not None:
        _check_record_payload(record, entry, json_path, errors)
    if markdown_text is not None:
        _check_markdown(markdown_text, markdown_path, errors)


def _load_markdown(relative_path: Path, errors: list[str]) -> str | None:
    path = REPO_ROOT / relative_path
    if not path.exists():
        errors.append(f"missing markdown file: {relative_path.as_posix()}")
        return None
    return path.read_text(encoding="utf-8")


def _check_record_payload(record: dict, entry: dict, relative_path: Path, errors: list[str]) -> None:
    for field in REQUIRED_RECORD_FIELDS:
        if field not in record:
            errors.append(f"{relative_path.as_posix()} missing field: {field}")

    if record.get("schema_version") != "dogfood_record_v1":
        errors.append(f"{relative_path.as_posix()} schema_version mismatch")
    if record.get("record_id") != entry.get("record_id"):
        errors.append(f"{relative_path.as_posix()} record_id does not match index")
    if record.get("category") != entry.get("category"):
        errors.append(f"{relative_path.as_posix()} category does not match index")
    if record.get("historical_evidence_available") is not True:
        errors.append(f"{relative_path.as_posix()} must mark historical evidence available")

    _check_refs_exist(record.get("task_contract", {}).get("source_refs", []), relative_path, errors)
    _check_refs_exist(record.get("evidence_trace", []), relative_path, errors)
    _check_receipts(record, relative_path, errors)
    _check_pr_and_validation(record, relative_path, errors)
    _check_text_safety(json.dumps(record, sort_keys=True), relative_path, errors)


def _check_refs_exist(refs: object, relative_path: Path, errors: list[str]) -> None:
    if not isinstance(refs, list) or not refs:
        errors.append(f"{relative_path.as_posix()} must include non-empty evidence refs")
        return
    for ref in refs:
        if not isinstance(ref, str) or not ref:
            errors.append(f"{relative_path.as_posix()} has invalid evidence ref: {ref!r}")
            continue
        if ref.startswith("http"):
            continue
        if not (REPO_ROOT / ref).exists():
            errors.append(f"{relative_path.as_posix()} evidence ref missing: {ref}")


def _check_receipts(record: dict, relative_path: Path, errors: list[str]) -> None:
    approval = record.get("approval_receipt", {})
    execution = record.get("dry_run_execution_receipt", {})
    if not isinstance(approval, dict) or not approval.get("receipt_id"):
        errors.append(f"{relative_path.as_posix()} missing approval receipt id")
    if approval.get("approval_boundary") != "merge_after_required_checks":
        errors.append(f"{relative_path.as_posix()} approval boundary must be merge_after_required_checks")
    if approval.get("separate_historical_approval_artifact_available") is not False:
        errors.append(f"{relative_path.as_posix()} must not invent separate historical approval artifacts")
    if not isinstance(execution, dict) or not execution.get("receipt_id"):
        errors.append(f"{relative_path.as_posix()} missing dry-run/execution receipt id")
    if execution.get("dry_run_first") is not True:
        errors.append(f"{relative_path.as_posix()} must record dry_run_first true")
    if execution.get("runtime_expansion_performed") is not False:
        errors.append(f"{relative_path.as_posix()} must record no runtime expansion")


def _check_pr_and_validation(record: dict, relative_path: Path, errors: list[str]) -> None:
    pr_ref = record.get("pr_link_or_commit_reference", {})
    post_merge = record.get("post_merge_validation", {})
    validation = record.get("validation_result", {})
    replay = record.get("replay_explain", {})

    if not PR_URL_RE.match(str(pr_ref.get("pr_url", ""))):
        errors.append(f"{relative_path.as_posix()} has invalid PR URL")
    if not COMMIT_RE.match(str(pr_ref.get("merge_commit", ""))):
        errors.append(f"{relative_path.as_posix()} has invalid merge commit")
    if validation.get("status") != "passed":
        errors.append(f"{relative_path.as_posix()} validation status must be passed")
    if post_merge.get("status") != "passed":
        errors.append(f"{relative_path.as_posix()} post-merge validation status must be passed")
    if not RUN_URL_RE.match(str(post_merge.get("github_actions_run", ""))):
        errors.append(f"{relative_path.as_posix()} has invalid GitHub Actions run URL")
    if record.get("outcome") != "merged_to_main":
        errors.append(f"{relative_path.as_posix()} outcome must be merged_to_main")
    if not isinstance(replay.get("commands"), list) or not replay.get("commands"):
        errors.append(f"{relative_path.as_posix()} replay commands must be non-empty")
    if "make ci" not in " ".join(str(command) for command in validation.get("commands", [])):
        errors.append(f"{relative_path.as_posix()} validation commands must include make ci")
    residual_risk = record.get("residual_risk")
    if not isinstance(residual_risk, list) or not residual_risk:
        errors.append(f"{relative_path.as_posix()} residual risk must be non-empty")
    guard = str(record.get("fabrication_guard", "")).lower()
    if "merged pr" not in guard or "not invented" not in guard:
        errors.append(f"{relative_path.as_posix()} fabrication guard must cite merged PR and non-invention")


def _check_markdown(markdown_text: str, relative_path: Path, errors: list[str]) -> None:
    for section in REQUIRED_MARKDOWN_SECTIONS:
        if section not in markdown_text:
            errors.append(f"{relative_path.as_posix()} missing markdown section: {section}")
    _check_text_safety(markdown_text, relative_path, errors)


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
