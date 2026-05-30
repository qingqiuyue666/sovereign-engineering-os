"""Local-first landing-ready workspace, evidence, and AI context helpers.

The helpers in this module intentionally stay deterministic, file-based, and
side-effect narrow. They provide an operator-facing path for the landing-ready
program without introducing a new runtime authority or external service.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping
import hashlib
import json
import os
import subprocess

from kernel.security.secret_scanner import CoreSecretScanner
from kernel.tasks.run_id import canonical_json
from kernel.tasks.task_contracts import create_operator_task_envelope

__all__ = [
    "approve_task",
    "build_context_bundle",
    "build_repo_map",
    "create_task",
    "evidence_show",
    "explain_failure",
    "explain_replay",
    "init_workspace",
    "list_receipts",
    "list_tasks",
    "reject_task",
    "release_check",
    "run_task",
    "show_receipt",
    "show_task",
    "status_report",
    "trace_task",
    "write_failure_bundle",
    "write_token_roi_report",
]

_VERSION = "landing_ready_program_v1"
_SAFE_SOURCE_SUFFIXES = {
    ".md",
    ".py",
    ".json",
    ".yaml",
    ".yml",
    ".txt",
    ".toml",
    ".ini",
}
_FORBIDDEN_SOURCE_NAMES = {
    ".env",
    ".netrc",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
}


def init_workspace(workspace: Path) -> dict[str, object]:
    root = Path(workspace).resolve()
    seos_dir = _seos_dir(root)
    for relative in (
        "tasks",
        "receipts",
        "evidence",
        "ai/context_bundles",
        "ai/repo_maps",
        "ai/failures",
        "reports",
    ):
        (seos_dir / relative).mkdir(parents=True, exist_ok=True)
    manifest_path = seos_dir / "workspace.json"
    if manifest_path.exists():
        manifest = _read_json(manifest_path)
        created = False
    else:
        manifest = {
            "schema": "seos_workspace_manifest_v1",
            "version": _VERSION,
            "workspace": root.as_posix(),
            "created_at": _now(),
            "local_first": True,
            "network_required": False,
            "secret_material_allowed": False,
            "runtime_authority_introduced": False,
            "human_approval_required_for_execution": True,
        }
        _write_json(manifest_path, manifest)
        created = True
    return {
        "ok": True,
        "created": created,
        "workspace": root.as_posix(),
        "seos_dir": seos_dir.as_posix(),
        "next_steps": [
            "seos task create --workspace PATH --title TITLE --objective OBJECTIVE",
            "seos approve --workspace PATH TASK_ID",
            "seos run --workspace PATH TASK_ID --dry-run",
            "seos evidence trace --workspace PATH TASK_ID",
        ],
    }


def status_report(workspace: Path, repo_root: Path | None = None) -> dict[str, object]:
    workspace_root = Path(workspace).resolve()
    repo = Path(repo_root or os.getcwd()).resolve()
    seos_dir = _seos_dir(workspace_root)
    tasks = list(_iter_json_files(seos_dir / "tasks"))
    receipts = list(_iter_json_files(seos_dir / "receipts"))
    release = release_check(workspace_root, repo, fail_closed=False)
    git = _git_status(repo)
    blockers: list[str] = []
    if not seos_dir.exists():
        blockers.append("workspace_not_initialized")
    if not release.get("release_ready"):
        blockers.extend(str(item) for item in release.get("blockers", []))
    return {
        "ok": True,
        "status": "V12 foundation status",
        "landing_ready_version": _VERSION,
        "workspace": workspace_root.as_posix(),
        "workspace_initialized": seos_dir.exists(),
        "task_count": len(tasks),
        "receipt_count": len(receipts),
        "git": git,
        "validation": {
            "baseline_required": [
                "PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/tracer_bullet",
                "PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s validation/tests/acceptance",
                "PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover tests",
                "make ci",
                "git diff --check",
                "git status --short",
            ],
            "last_result": release.get("validation_result", "unknown"),
        },
        "release_readiness": release,
        "known_blockers": sorted(set(blockers)),
    }


def create_task(
    workspace: Path,
    *,
    title: str,
    objective: str,
    task_id: str | None = None,
    task_type: str = "engineering_task",
    source_refs: Iterable[str] = (),
    capabilities: Iterable[str] = ("local_validation",),
    classification: str = "PUBLIC",
) -> dict[str, object]:
    root = _require_workspace(workspace)
    source_list = [str(item) for item in source_refs]
    descriptor = {
        "descriptor_type": "text",
        "content_digest": "sha256:" + _sha256_text(canonical_json({"title": title, "objective": objective, "source_refs": source_list})),
    }
    envelope_payload: dict[str, object] = {
        "objective": objective,
        "requested_capabilities": list(capabilities),
        "classification": classification,
        "policy_version": _VERSION,
        "code_version": _VERSION,
        "descriptor": descriptor,
    }
    if task_id:
        envelope_payload["task_id"] = task_id
    intake = create_operator_task_envelope(envelope_payload)
    if not intake.accepted:
        return {"ok": False, "error": "task_rejected", "failures": list(intake.failures)}
    resolved_task_id = str(intake.envelope["task_id"])
    path = _task_path(root, resolved_task_id)
    if path.exists():
        task = _read_json(path)
        return {"ok": True, "created": False, "task": task, "task_path": path.as_posix()}
    task = {
        "schema": "seos_task_contract_v1",
        "task_id": resolved_task_id,
        "title": title,
        "objective_summary": objective,
        "task_type": task_type,
        "classification": classification,
        "requested_capabilities": list(capabilities),
        "source_refs": source_list,
        "status": "CREATED",
        "approval_required": True,
        "created_at": _now(),
        "descriptor_digest": intake.envelope["descriptor_digest"],
        "task_manifest": intake.envelope["task_manifest"],
        "evidence_refs": [],
        "human_approval_gate": "required_before_run",
        "runtime_authority_introduced": False,
        "network_required": False,
        "secret_material_allowed": False,
    }
    _write_json(path, task, fail_if_exists=True)
    return {"ok": True, "created": True, "task": task, "task_path": path.as_posix()}


def list_tasks(workspace: Path) -> dict[str, object]:
    root = _require_workspace(workspace)
    tasks = [_read_json(path) for path in _iter_json_files(root / "tasks")]
    return {
        "ok": True,
        "tasks": [
            {
                "task_id": task.get("task_id"),
                "title": task.get("title"),
                "status": task.get("status"),
                "approval_required": task.get("approval_required"),
            }
            for task in tasks
        ],
    }


def show_task(workspace: Path, task_id: str) -> dict[str, object]:
    root = _require_workspace(workspace)
    path = _task_path(root, task_id)
    if not path.exists():
        return {"ok": False, "error": "task_not_found", "task_id": task_id}
    return {"ok": True, "task": _read_json(path), "task_path": path.as_posix()}


def approve_task(workspace: Path, task_id: str, *, reason: str = "operator_approved") -> dict[str, object]:
    return _decision_receipt(workspace, task_id, approved=True, reason=reason)


def reject_task(workspace: Path, task_id: str, *, reason: str = "operator_rejected") -> dict[str, object]:
    return _decision_receipt(workspace, task_id, approved=False, reason=reason)


def run_task(workspace: Path, task_id: str, *, dry_run: bool = True, command: str = "dry-run") -> dict[str, object]:
    root = _require_workspace(workspace)
    task_result = show_task(workspace, task_id)
    if not task_result.get("ok"):
        return task_result
    if not dry_run:
        return {"ok": False, "error": "real_execution_not_enabled", "task_id": task_id}
    approved = _latest_decision(root, task_id, approved=True)
    if approved is None:
        return {"ok": False, "error": "approval_required", "task_id": task_id}
    receipt = {
        "schema": "seos_execution_receipt_v1",
        "receipt_type": "execution",
        "task_id": task_id,
        "created_at": _now(),
        "approved_receipt_digest": approved["digest"],
        "dry_run": True,
        "execution_performed": False,
        "command": command,
        "network_accessed": False,
        "secret_value_read": False,
        "ai_provider_call_performed": False,
        "runtime_authority_introduced": False,
        "result": "DRY_RUN_RECEIPT_CREATED",
        "artifacts": [],
    }
    receipt["digest"] = _digest_payload(receipt)
    path = _receipt_path(root, task_id, "execution")
    _write_json(path, receipt, fail_if_exists=True)
    _update_task_status(root, task_id, "RUN_DRY_RUN_COMPLETE", path)
    return {"ok": True, "receipt": receipt, "receipt_path": path.as_posix()}


def trace_task(workspace: Path, task_id: str) -> dict[str, object]:
    root = _require_workspace(workspace)
    task_result = show_task(workspace, task_id)
    if not task_result.get("ok"):
        return task_result
    receipts = [
        {"path": path.as_posix(), "receipt": _read_json(path)}
        for path in _receipt_files_for_task(root, task_id)
    ]
    receipt_types = [str(item["receipt"].get("receipt_type")) for item in receipts]
    missing = []
    if "approval" not in receipt_types and "rejection" not in receipt_types:
        missing.append("approval_or_rejection_receipt")
    if "execution" not in receipt_types:
        missing.append("execution_receipt")
    return {
        "ok": not missing,
        "task": task_result["task"],
        "receipts": receipts,
        "missing_evidence": missing,
        "trace_status": "complete" if not missing else "incomplete",
    }


def evidence_show(workspace: Path, evidence_ref: str) -> dict[str, object]:
    root = _require_workspace(workspace)
    candidate = Path(evidence_ref)
    if not candidate.is_absolute():
        candidate = root / evidence_ref
    candidate = candidate.resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return {"ok": False, "error": "evidence_path_outside_workspace", "path": candidate.as_posix()}
    if not candidate.exists() or not candidate.is_file():
        return {"ok": False, "error": "evidence_not_found", "path": candidate.as_posix()}
    text = candidate.read_text(encoding="utf-8", errors="replace")
    scan = CoreSecretScanner().scan_text(text, path=candidate.as_posix())
    summary = _summarize_text(text if scan.clean else "[redacted: secret-like content detected]")
    return {
        "ok": True,
        "path": candidate.as_posix(),
        "sha256": _sha256_bytes(candidate.read_bytes()),
        "size_bytes": candidate.stat().st_size,
        "secret_like_content_detected": not scan.clean,
        "summary": summary,
    }


def list_receipts(workspace: Path) -> dict[str, object]:
    root = _require_workspace(workspace)
    receipts = []
    for path in _iter_json_files(root / "receipts"):
        payload = _read_json(path)
        receipts.append(
            {
                "path": path.as_posix(),
                "receipt_type": payload.get("receipt_type"),
                "task_id": payload.get("task_id"),
                "created_at": payload.get("created_at"),
                "digest": payload.get("digest"),
            }
        )
    receipts.sort(key=lambda item: str(item["created_at"]))
    return {"ok": True, "receipts": receipts}


def show_receipt(workspace: Path, receipt_ref: str = "latest") -> dict[str, object]:
    root = _require_workspace(workspace)
    receipts = list(_iter_json_files(root / "receipts"))
    if not receipts:
        return {"ok": False, "error": "receipt_not_found"}
    if receipt_ref == "latest":
        path = sorted(receipts)[-1]
    else:
        path = Path(receipt_ref)
        if not path.is_absolute():
            path = root / receipt_ref
        path = path.resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return {"ok": False, "error": "receipt_path_outside_workspace", "path": path.as_posix()}
    if not path.exists():
        return {"ok": False, "error": "receipt_not_found", "path": path.as_posix()}
    payload = _read_json(path)
    return {
        "ok": True,
        "path": path.as_posix(),
        "receipt": payload,
        "sha256": _sha256_bytes(path.read_bytes()),
    }


def explain_replay(workspace: Path, task_id: str) -> dict[str, object]:
    trace = trace_task(workspace, task_id)
    if not trace.get("ok"):
        return {
            "ok": False,
            "task_id": task_id,
            "replay_status": "incomplete",
            "can_reconstruct": False,
            "missing_evidence": trace.get("missing_evidence", [trace.get("error", "unknown")]),
        }
    receipt_types = [item["receipt"].get("receipt_type") for item in trace["receipts"]]
    return {
        "ok": True,
        "task_id": task_id,
        "replay_status": "dry_run_reconstructable",
        "can_reconstruct": True,
        "reconstructable_parts": ["task_contract", *receipt_types],
        "not_reconstructable_parts": ["real side effects were not performed by this dry-run receipt"],
    }


def write_failure_bundle(
    workspace: Path,
    *,
    command: str,
    exit_code: int,
    log_text: str,
    affected_files: Iterable[str] = (),
) -> dict[str, object]:
    root = _require_workspace(workspace)
    scan = CoreSecretScanner().scan_text(log_text, path="failure_bundle")
    redacted_log = log_text if scan.clean else "[redacted: secret-like content detected]"
    lines = redacted_log.splitlines()
    key_window = lines[:20] + (["..."] if len(lines) > 40 else []) + lines[-20:]
    bundle = {
        "schema": "seos_failure_bundle_v1",
        "created_at": _now(),
        "command": command,
        "exit_code": exit_code,
        "root_symptom": _root_symptom(lines),
        "affected_files": list(affected_files),
        "key_error_window": key_window,
        "raw_log_redacted": not scan.clean,
    }
    bundle["digest"] = _digest_payload(bundle)
    path = root / "ai" / "failures" / f"{_stamp()}_failure_bundle.json"
    _write_json(path, bundle, fail_if_exists=True)
    return {"ok": True, "failure_bundle": bundle, "path": path.as_posix()}


def explain_failure(workspace: Path, failure_ref: str = "latest") -> dict[str, object]:
    root = _require_workspace(workspace)
    failures = list(_iter_json_files(root / "ai" / "failures"))
    if not failures:
        return {"ok": False, "error": "failure_bundle_not_found"}
    if failure_ref == "latest":
        path = sorted(failures)[-1]
    else:
        path = Path(failure_ref)
        if not path.is_absolute():
            path = root / failure_ref
        path = path.resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return {"ok": False, "error": "failure_path_outside_workspace", "path": path.as_posix()}
    if not path.exists():
        return {"ok": False, "error": "failure_bundle_not_found", "path": path.as_posix()}
    bundle = _read_json(path)
    return {
        "ok": True,
        "path": path.as_posix(),
        "command": bundle.get("command"),
        "exit_code": bundle.get("exit_code"),
        "root_symptom": bundle.get("root_symptom"),
        "affected_files": bundle.get("affected_files", []),
        "next_suggested_evidence": "rerun the recorded command after the smallest fix and attach the new receipt",
        "failure_bundle": bundle,
    }


def build_context_bundle(
    workspace: Path,
    repo_root: Path,
    task_id: str,
    *,
    source_paths: Iterable[str] = (),
    budget_tokens: int = 4000,
) -> dict[str, object]:
    root = _require_workspace(workspace)
    task_result = show_task(workspace, task_id)
    if not task_result.get("ok"):
        return task_result
    repo = Path(repo_root).resolve()
    sources = []
    for source in source_paths:
        path = (repo / source).resolve()
        if not _safe_source_path(repo, path):
            return {"ok": False, "error": "unsafe_source_path", "path": path.as_posix()}
        sources.append(
            {
                "path": path.relative_to(repo).as_posix(),
                "sha256": _sha256_bytes(path.read_bytes()),
                "size_bytes": path.stat().st_size,
            }
        )
    bundle = {
        "schema": "seos_context_bundle_v1",
        "created_at": _now(),
        "task_id": task_id,
        "task_summary": {
            "title": task_result["task"].get("title"),
            "objective_summary": task_result["task"].get("objective_summary"),
            "classification": task_result["task"].get("classification"),
        },
        "source_digests": sources,
        "raw_file_contents_included": False,
        "provider_call_performed": False,
        "route": "deterministic_local_first",
        "budget_tokens": budget_tokens,
    }
    estimate = _token_estimate(canonical_json(bundle))
    bundle["estimated_input_tokens"] = estimate
    bundle["budget_decision"] = "accepted" if estimate <= budget_tokens else "rejected_over_budget"
    bundle["digest"] = _digest_payload(bundle)
    path = root / "ai" / "context_bundles" / f"{_stamp()}_{task_id}.json"
    _write_json(path, bundle, fail_if_exists=True)
    return {"ok": estimate <= budget_tokens, "context_bundle": bundle, "path": path.as_posix()}


def build_repo_map(repo_root: Path, output_root: Path, *, max_files: int = 500) -> dict[str, object]:
    repo = Path(repo_root).resolve()
    root = _require_workspace(output_root)
    indexed = []
    for path in sorted(repo.rglob("*")):
        if len(indexed) >= max_files:
            break
        if not path.is_file() or not _safe_source_path(repo, path):
            continue
        relative = path.relative_to(repo).as_posix()
        if relative.startswith((".git/", ".venv/", "__pycache__/")) or "/__pycache__/" in relative:
            continue
        indexed.append(
            {
                "path": relative,
                "suffix": path.suffix,
                "size_bytes": path.stat().st_size,
                "sha256": _sha256_bytes(path.read_bytes()),
            }
        )
    repo_map = {
        "schema": "seos_repo_map_v1",
        "created_at": _now(),
        "repo_root": repo.as_posix(),
        "file_count": len(indexed),
        "files": indexed,
        "raw_file_contents_included": False,
        "digest": _digest_payload(indexed),
    }
    path = root / "ai" / "repo_maps" / f"{_stamp()}_repo_map.json"
    _write_json(path, repo_map, fail_if_exists=True)
    return {"ok": True, "repo_map": repo_map, "path": path.as_posix()}


def write_token_roi_report(workspace: Path) -> dict[str, object]:
    root = _require_workspace(workspace)
    bundles = [_read_json(path) for path in _iter_json_files(root / "ai" / "context_bundles")]
    report = {
        "schema": "seos_token_roi_report_v1",
        "created_at": _now(),
        "bundle_count": len(bundles),
        "total_estimated_input_tokens": sum(int(bundle.get("estimated_input_tokens", 0)) for bundle in bundles),
        "routes": sorted(set(str(bundle.get("route", "unknown")) for bundle in bundles)),
        "decisions": [
            {
                "task_id": bundle.get("task_id"),
                "route": bundle.get("route"),
                "estimate": bundle.get("estimated_input_tokens"),
                "budget": bundle.get("budget_tokens"),
                "decision": bundle.get("budget_decision"),
                "accepted_result": bundle.get("budget_decision") == "accepted",
            }
            for bundle in bundles
        ],
    }
    report["digest"] = _digest_payload(report)
    path = root / "ai" / "token_roi_report.json"
    _write_json(path, report)
    return {"ok": True, "token_roi_report": report, "path": path.as_posix()}


def release_check(workspace: Path, repo_root: Path, *, fail_closed: bool = True) -> dict[str, object]:
    repo = Path(repo_root).resolve()
    candidates = [
        repo / "reports" / "landing_ready_v1" / "release_readiness_decision.json",
        _seos_dir(Path(workspace).resolve()) / "reports" / "release_readiness_decision.json",
    ]
    for path in candidates:
        if path.exists():
            decision = _read_json(path)
            release_ready = decision.get("verdict") == "RELEASE_ALLOWED"
            return {
                "ok": release_ready,
                "release_ready": release_ready,
                "decision_path": path.as_posix(),
                "verdict": decision.get("verdict"),
                "blockers": decision.get("blockers", []),
                "validation_result": decision.get("validation_result", "unknown"),
            }
    missing = "release_readiness_evidence_missing"
    return {
        "ok": not fail_closed,
        "release_ready": False,
        "decision_path": None,
        "verdict": "MISSING_EVIDENCE",
        "blockers": [missing],
        "validation_result": "unknown",
    }


def _decision_receipt(workspace: Path, task_id: str, *, approved: bool, reason: str) -> dict[str, object]:
    root = _require_workspace(workspace)
    task_result = show_task(workspace, task_id)
    if not task_result.get("ok"):
        return task_result
    receipt_type = "approval" if approved else "rejection"
    receipt = {
        "schema": f"seos_{receipt_type}_receipt_v1",
        "receipt_type": receipt_type,
        "task_id": task_id,
        "created_at": _now(),
        "approved": approved,
        "human_reviewed": True,
        "reason": reason,
        "task_contract_digest": _digest_payload(task_result["task"]),
        "network_accessed": False,
        "secret_value_read": False,
        "ai_provider_call_performed": False,
        "runtime_authority_introduced": False,
    }
    receipt["digest"] = _digest_payload(receipt)
    path = _receipt_path(root, task_id, receipt_type)
    _write_json(path, receipt, fail_if_exists=True)
    _update_task_status(root, task_id, "APPROVED" if approved else "REJECTED", path)
    return {"ok": True, "receipt": receipt, "receipt_path": path.as_posix()}


def _seos_dir(root: Path) -> Path:
    return Path(root).resolve() / ".seos"


def _require_workspace(workspace: Path) -> Path:
    root = _seos_dir(Path(workspace).resolve())
    if not (root / "workspace.json").exists():
        raise ValueError(f"SEOS workspace is not initialized: {Path(workspace).resolve().as_posix()}")
    return root


def _task_path(seos_root: Path, task_id: str) -> Path:
    _validate_id(task_id)
    return seos_root / "tasks" / f"{task_id}.json"


def _receipt_path(seos_root: Path, task_id: str, kind: str) -> Path:
    _validate_id(task_id)
    return seos_root / "receipts" / f"{_stamp()}_{task_id}_{kind}.json"


def _receipt_files_for_task(seos_root: Path, task_id: str) -> list[Path]:
    _validate_id(task_id)
    return sorted((seos_root / "receipts").glob(f"*_{task_id}_*.json"))


def _latest_decision(seos_root: Path, task_id: str, *, approved: bool) -> dict[str, object] | None:
    matches = []
    for path in _receipt_files_for_task(seos_root, task_id):
        payload = _read_json(path)
        if payload.get("receipt_type") == "approval" and payload.get("approved") is approved:
            matches.append(payload)
    return matches[-1] if matches else None


def _update_task_status(seos_root: Path, task_id: str, status: str, evidence_path: Path) -> None:
    path = _task_path(seos_root, task_id)
    task = _read_json(path)
    refs = list(task.get("evidence_refs", []))
    refs.append(evidence_path.relative_to(seos_root).as_posix())
    task["status"] = status
    task["updated_at"] = _now()
    task["evidence_refs"] = refs
    _write_json(path, task)


def _git_status(repo: Path) -> dict[str, object]:
    if not (repo / ".git").exists():
        return {"inside_work_tree": False, "head": None, "dirty": None, "short_status": []}
    head = _run_git(repo, "rev-parse", "HEAD")
    short = _run_git(repo, "status", "--short")
    branch = _run_git(repo, "branch", "--show-current")
    return {
        "inside_work_tree": True,
        "branch": branch["stdout"].strip(),
        "head": head["stdout"].strip() if head["returncode"] == 0 else None,
        "dirty": bool(short["stdout"].strip()),
        "short_status": short["stdout"].splitlines(),
    }


def _run_git(repo: Path, *args: str) -> dict[str, object]:
    completed = subprocess.run(
        ["git", "-C", repo.as_posix(), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _safe_source_path(repo: Path, path: Path) -> bool:
    try:
        relative = path.resolve().relative_to(repo.resolve())
    except ValueError:
        return False
    if any(part in {".git", ".venv", "venv", "__pycache__"} for part in relative.parts):
        return False
    if path.name in _FORBIDDEN_SOURCE_NAMES:
        return False
    if path.suffix not in _SAFE_SOURCE_SUFFIXES:
        return False
    return path.exists() and path.is_file()


def _iter_json_files(path: Path) -> Iterable[Path]:
    if not path.exists():
        return []
    return sorted(item for item in path.glob("*.json") if item.is_file())


def _write_json(path: Path, payload: Mapping[str, object], *, fail_if_exists: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fail_if_exists and path.exists():
        raise FileExistsError(path.as_posix())
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_id(value: str) -> None:
    if not value or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in value):
        raise ValueError("identifier must be non-empty and use letters, digits, underscore, or dash")


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ%f")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _digest_payload(payload: object) -> str:
    return "sha256:" + _sha256_text(canonical_json(payload))


def _token_estimate(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def _summarize_text(text: str) -> dict[str, object]:
    lines = text.splitlines()
    return {
        "line_count": len(lines),
        "first_lines": lines[:20],
        "truncated": len(lines) > 20,
    }


def _root_symptom(lines: list[str]) -> str:
    for line in lines:
        lowered = line.lower()
        if "error" in lowered or "failed" in lowered or "traceback" in lowered:
            return line[:240]
    return lines[-1][:240] if lines else "no output"
