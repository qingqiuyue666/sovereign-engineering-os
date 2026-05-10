"""A controlled single-file lifecycle demonstration."""

from pathlib import Path
from hashlib import sha256

from kernel.lifecycle.single_file_patch_lifecycle import run_single_file_patch_lifecycle
from kernel.lifecycle.single_file_lifecycle_replay_verifier import (
    verify_single_file_patch_lifecycle_replay,
)


_DEMO = "controlled single-file lifecycle demonstration"
_DESCRIPTION = "controlled single-file lifecycle demonstration"
_ORIGINAL = "controlled demo original content\n"
_PATCHED = "controlled demo patched content\n"
_APPLY_TARGET = "controlled_demo/apply_target.txt"
_ROLLBACK_TARGET = "controlled_demo/rollback_target.txt"
_APPLY_PATCH_ID = "controlled-demo-apply"
_ROLLBACK_PATCH_ID = "controlled-demo-rollback"


def run_controlled_single_file_lifecycle_demo(*, repo_root, artifact_root):
    repo_path = Path(repo_root)
    artifact_path = Path(artifact_root)
    if not artifact_path.is_absolute():
        artifact_path = repo_path / artifact_path
    apply_path = repo_path / _APPLY_TARGET
    rollback_path = repo_path / _ROLLBACK_TARGET

    _ensure_repo_contained(repo_path, apply_path)
    _ensure_repo_contained(repo_path, rollback_path)
    _ensure_repo_contained(repo_path, artifact_path)

    apply_path.parent.mkdir(parents=True, exist_ok=True)
    apply_path.write_text(_ORIGINAL, encoding="utf-8")
    rollback_path.write_text(_ORIGINAL, encoding="utf-8")

    apply_result = _run_path(
        repo_root=repo_path,
        artifact_root=artifact_path,
        target_path=_APPLY_TARGET,
        proposal_id="controlled-demo-apply-proposal",
        patch_id=_APPLY_PATCH_ID,
        validation_callable=_validation_pass,
    )
    rollback_result = _run_path(
        repo_root=repo_path,
        artifact_root=artifact_path,
        target_path=_ROLLBACK_TARGET,
        proposal_id="controlled-demo-rollback-proposal",
        patch_id=_ROLLBACK_PATCH_ID,
        validation_callable=_validation_fail,
    )

    apply_verifier = verify_single_file_patch_lifecycle_replay(
        repo_root=repo_path,
        artifact_root=artifact_path,
        patch_id=_APPLY_PATCH_ID,
    )
    rollback_verifier = verify_single_file_patch_lifecycle_replay(
        repo_root=repo_path,
        artifact_root=artifact_path,
        patch_id=_ROLLBACK_PATCH_ID,
    )

    apply_observed = apply_path.read_text(encoding="utf-8")
    rollback_observed = rollback_path.read_text(encoding="utf-8")
    authority = _hard_false_authority()
    apply_ok = (
        apply_result.get("status") == "applied"
        and apply_verifier.get("ok") is True
        and apply_observed == _PATCHED
    )
    rollback_ok = (
        rollback_result.get("status") == "rolled_back"
        and rollback_verifier.get("ok") is True
        and rollback_observed == _ORIGINAL
    )
    ok = apply_ok and rollback_ok and all(value is False for value in authority.values())

    return {
        "demo": _DEMO,
        "description": _DESCRIPTION,
        "ok": ok,
        "paths": {
            "apply": _path_summary(apply_result),
            "rollback": _path_summary(rollback_result),
        },
        "apply": {
            "lifecycle_status": _bounded_string(apply_result.get("status")),
            "verifier_ok": apply_verifier.get("ok") is True,
            "verifier_status": _bounded_string(apply_verifier.get("status")),
            "target_content_observed": _bounded_string(apply_observed),
        },
        "rollback": {
            "lifecycle_status": _bounded_string(rollback_result.get("status")),
            "verifier_ok": rollback_verifier.get("ok") is True,
            "verifier_status": _bounded_string(rollback_verifier.get("status")),
            "target_content_observed": _bounded_string(rollback_observed),
        },
        "verifier": {
            "apply": _verifier_summary(apply_verifier),
            "rollback": _verifier_summary(rollback_verifier),
        },
        "authority": authority,
        "json_safe": True,
    }


def _run_path(
    *,
    repo_root,
    artifact_root,
    target_path,
    proposal_id,
    patch_id,
    validation_callable,
):
    proposal = {
        "proposal_id": proposal_id,
        "patch_id": patch_id,
        "target_path": target_path,
    }
    approval = {
        "approved": True,
        "proposal_id": proposal_id,
        "patch_id": patch_id,
        "target_path": target_path,
        "expected_preimage_identity": _identity(_ORIGINAL),
    }
    return run_single_file_patch_lifecycle(
        repo_root=repo_root,
        artifact_root=artifact_root,
        target_path=target_path,
        new_content=_PATCHED,
        proposal=proposal,
        approval=approval,
        validation_callable=validation_callable,
    )


def _validation_pass(_context):
    return {
        "ok": True,
        "reason_code": "controlled_demo_validation_passed",
        "json_safe": True,
    }


def _validation_fail(_context):
    return {
        "ok": False,
        "reason_code": "controlled_demo_validation_failed",
        "json_safe": True,
    }


def _identity(text):
    return sha256(text.encode("utf-8")).hexdigest()


def _path_summary(lifecycle_result):
    return {
        "target": _bounded_string(lifecycle_result.get("target", {}).get("path")),
        "patch_id": _bounded_string(lifecycle_result.get("replay", {}).get("patch_id")),
        "artifacts": _artifact_summary(lifecycle_result.get("artifacts", {})),
    }


def _artifact_summary(artifacts):
    summary = {}
    for key in (
        "proposal",
        "patch_body",
        "preimage",
        "validation_result",
        "rollback",
        "final_seal",
    ):
        value = artifacts.get(key)
        summary[key] = _bounded_string(value) if isinstance(value, str) else None
    return summary


def _verifier_summary(verifier_result):
    return {
        "ok": verifier_result.get("ok") is True,
        "status": _bounded_string(verifier_result.get("status")),
        "final_status": _bounded_string(
            verifier_result.get("replay", {}).get("final_status")
        ),
        "validation_status": _bounded_string(
            verifier_result.get("replay", {}).get("validation_status")
        ),
        "rollback_status": _bounded_string(
            verifier_result.get("replay", {}).get("rollback_status")
        ),
    }


def _hard_false_authority():
    return {
        "service_calls_authorized": False,
        "db_repository_uow_authorized": False,
        "executor_dispatch_authorized": False,
        "multi_file_lifecycle_authorized": False,
        "evidence_audit_append_authorized": False,
        "broad_physical_io_authorized": False,
    }


def _bounded_string(value):
    if not isinstance(value, str):
        return ""
    if len(value) <= 4096:
        return value
    return value[:4096] + "...truncated"


def _ensure_repo_contained(repo_path, candidate):
    repo_resolved = repo_path.resolve(strict=True)
    candidate.resolve(strict=False).relative_to(repo_resolved)
