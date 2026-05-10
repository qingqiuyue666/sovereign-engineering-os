from collections.abc import Callable, Mapping
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json

__all__ = [
    "single_file_patch_lifecycle_manifest",
    "run_single_file_patch_lifecycle",
]

_SURFACE = "single_file_patch_lifecycle"
_VERSION = 1
_MAX_TEXT_CHARS = 200000
_MAX_IDENTIFIER_CHARS = 128
_MAX_STRING_CHARS = 4096
_MAX_LIST_ITEMS = 25
_MAX_MAPPING_ITEMS = 25
_SAFE_PATCH_ID_CHARS = (
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    "_.-"
)

_ARTIFACT_KEYS = (
    "proposal",
    "patch_body",
    "preimage",
    "validation_result",
    "rollback",
    "final_seal",
)

_MANIFEST = {
    "surface": _SURFACE,
    "version": _VERSION,
    "package": "single-file-real-patch-lifecycle-foundation-v1",
    "repo_health_gate": "repo-ci-canonical-health-gate-v1",
    "input_shape": "single_repo_contained_text_file_patch_lifecycle",
    "target_file_count": 1,
    "artifact_model": "repo_contained_artifact_subdirectory",
    "validation_model": "caller_provided_callable_only",
    "content_identity": "sha256_hexdigest_for_local_file_integrity_only",
    "runtime_authorized": False,
    "service_calls_authorized": False,
    "db_repository_uow_authorized": False,
    "evidence_audit_append_authorized": False,
    "executor_dispatch_authorized": False,
    "restore_service_authorized": False,
    "subprocess_authorized": False,
    "network_authorized": False,
    "capability_tokens_authorized": False,
    "authority_grants_authorized": False,
    "json_safe": True,
}


def single_file_patch_lifecycle_manifest():
    return deepcopy(_MANIFEST)


def run_single_file_patch_lifecycle(
    *,
    repo_root,
    artifact_root,
    target_path,
    new_content,
    proposal,
    approval,
    validation_callable,
):
    artifacts = _empty_artifacts()
    target = _empty_target()
    approval_summary = _empty_approval()
    validation_summary = _empty_validation()
    rollback_summary = _empty_rollback()
    replay = _empty_replay()

    repo_ok, repo_path, repo_failure = _validate_repo_root(repo_root)
    if not repo_ok:
        return _result(
            ok=False,
            status="rejected",
            reason_code=repo_failure,
            failures=[repo_failure],
            target=target,
            artifacts=artifacts,
            approval=approval_summary,
            validation=validation_summary,
            rollback=rollback_summary,
            replay=replay,
        )

    artifact_ok, artifact_path, artifact_failure = _validate_artifact_root(
        repo_path, artifact_root
    )
    if not artifact_ok:
        return _result(
            ok=False,
            status="rejected",
            reason_code=artifact_failure,
            failures=[artifact_failure],
            target=target,
            artifacts=artifacts,
            approval=approval_summary,
            validation=validation_summary,
            rollback=rollback_summary,
            replay=replay,
        )

    target_ok, target_abs, target_rel, target_failure = _validate_target_path(
        repo_path, target_path
    )
    target["path"] = target_rel
    replay["target_path"] = target_rel
    if not target_ok:
        return _result(
            ok=False,
            status="rejected",
            reason_code=target_failure,
            failures=[target_failure],
            target=target,
            artifacts=artifacts,
            approval=approval_summary,
            validation=validation_summary,
            rollback=rollback_summary,
            replay=replay,
        )

    content_ok, new_content_failure = _validate_new_content(new_content)
    if not content_ok:
        return _rejected(
            new_content_failure,
            target,
            artifacts,
            approval_summary,
            validation_summary,
            rollback_summary,
            replay,
        )

    preimage_ok, preimage_text, preimage_failure = _read_text_target(target_abs)
    if not preimage_ok:
        return _rejected(
            preimage_failure,
            target,
            artifacts,
            approval_summary,
            validation_summary,
            rollback_summary,
            replay,
        )

    preimage_identity = _identity(preimage_text)
    target["preimage_identity"] = preimage_identity
    replay["preimage_identity"] = preimage_identity

    proposal_ok, proposal_data, proposal_failure = _validate_proposal(
        proposal, target_rel
    )
    if not proposal_ok:
        return _rejected(
            proposal_failure,
            target,
            artifacts,
            approval_summary,
            validation_summary,
            rollback_summary,
            replay,
        )

    replay["proposal_id"] = proposal_data["proposal_id"]
    replay["patch_id"] = proposal_data["patch_id"]

    approval_ok, approval_data, approval_failure = _validate_approval(
        approval,
        proposal_data,
        target_rel,
        preimage_identity,
    )
    approval_summary["approved"] = approval_ok
    approval_summary["proposal_id"] = approval_data.get("proposal_id")
    approval_summary["patch_id"] = approval_data.get("patch_id")
    replay["approval_status"] = "approved" if approval_ok else "rejected"
    if not approval_ok:
        return _rejected(
            approval_failure,
            target,
            artifacts,
            approval_summary,
            validation_summary,
            rollback_summary,
            replay,
        )

    if not isinstance(validation_callable, Callable):
        return _rejected(
            "validation_callable_invalid",
            target,
            artifacts,
            approval_summary,
            validation_summary,
            rollback_summary,
            replay,
        )

    artifact_dir = artifact_path / proposal_data["patch_id"]
    artifact_dir_resolved = artifact_dir.resolve(strict=False)
    if not _is_inside(artifact_dir_resolved, artifact_path.resolve(strict=True)):
        return _rejected(
            "artifact_root_invalid",
            target,
            artifacts,
            approval_summary,
            validation_summary,
            rollback_summary,
            replay,
        )
    if artifact_dir.exists():
        return _rejected(
            "artifact_destination_exists",
            target,
            artifacts,
            approval_summary,
            validation_summary,
            rollback_summary,
            replay,
        )

    try:
        artifact_dir.mkdir()
    except Exception:
        return _rejected(
            "artifact_write_failed",
            target,
            artifacts,
            approval_summary,
            validation_summary,
            rollback_summary,
            replay,
        )

    proposal_artifact = artifact_dir / "proposal.json"
    patch_body_artifact = artifact_dir / "patch_body.txt"
    preimage_artifact = artifact_dir / "preimage.txt"
    validation_artifact = artifact_dir / "validation_result.json"
    rollback_artifact = artifact_dir / "rollback.json"
    final_seal_artifact = artifact_dir / "final_seal.json"

    artifacts["proposal"] = _display_path(repo_path, proposal_artifact)
    artifacts["patch_body"] = _display_path(repo_path, patch_body_artifact)
    artifacts["preimage"] = _display_path(repo_path, preimage_artifact)
    replay["artifact_paths"] = _artifact_paths(artifacts)

    try:
        _write_json(
            proposal_artifact,
            {
                "artifact_type": "single_file_patch_proposal",
                "surface": _SURFACE,
                "version": _VERSION,
                "proposal_id": proposal_data["proposal_id"],
                "patch_id": proposal_data["patch_id"],
                "target_path": target_rel,
                "preimage_identity": preimage_identity,
                "json_safe": True,
            },
        )
        _write_text(patch_body_artifact, new_content)
        _write_text(preimage_artifact, preimage_text)
    except Exception:
        return _rejected(
            "artifact_write_failed",
            target,
            artifacts,
            approval_summary,
            validation_summary,
            rollback_summary,
            replay,
        )

    try:
        _write_text(target_abs, new_content)
    except Exception:
        rollback_summary["attempted"] = True
        rollback_ok = _restore_preimage(target_abs, preimage_text)
        rollback_summary["ok"] = rollback_ok
        rollback_status = "succeeded" if rollback_ok else "failed"
        replay["rollback_status"] = rollback_status
        return _finalize_after_mutation_failure(
            repo_path=repo_path,
            target=target,
            artifacts=artifacts,
            approval=approval_summary,
            validation=validation_summary,
            rollback=rollback_summary,
            replay=replay,
            rollback_artifact=rollback_artifact,
            final_seal_artifact=final_seal_artifact,
            failure_code="target_write_failed",
            rollback_ok=rollback_ok,
        )

    postimage_identity = _identity(new_content)
    target["postimage_identity"] = postimage_identity
    replay["postimage_identity"] = postimage_identity

    validation_result, validation_failure = _run_validation(
        validation_callable,
        {
            "surface": _SURFACE,
            "target_path": target_rel,
            "proposal_id": proposal_data["proposal_id"],
            "patch_id": proposal_data["patch_id"],
            "preimage_identity": preimage_identity,
            "postimage_identity": postimage_identity,
            "content": new_content,
        },
    )
    validation_summary["ok"] = validation_result["ok"]
    validation_summary["reason_code"] = validation_result["reason_code"]
    replay["validation_status"] = "pass" if validation_result["ok"] else "fail"

    artifacts["validation_result"] = _display_path(repo_path, validation_artifact)
    replay["artifact_paths"] = _artifact_paths(artifacts)
    try:
        _write_json(validation_artifact, validation_result)
    except Exception:
        validation_failure = "artifact_write_failed"
        validation_summary["ok"] = False
        validation_summary["reason_code"] = validation_failure
        replay["validation_status"] = "fail"

    if not validation_result["ok"] or validation_failure == "artifact_write_failed":
        rollback_summary["attempted"] = True
        rollback_ok = _restore_preimage(target_abs, preimage_text)
        rollback_summary["ok"] = rollback_ok
        rollback_status = "succeeded" if rollback_ok else "failed"
        replay["rollback_status"] = rollback_status
        artifacts["rollback"] = _display_path(repo_path, rollback_artifact)
        replay["artifact_paths"] = _artifact_paths(artifacts)
        return _finalize_after_mutation_failure(
            repo_path=repo_path,
            target=target,
            artifacts=artifacts,
            approval=approval_summary,
            validation=validation_summary,
            rollback=rollback_summary,
            replay=replay,
            rollback_artifact=rollback_artifact,
            final_seal_artifact=final_seal_artifact,
            failure_code=validation_failure,
            rollback_ok=rollback_ok,
        )

    replay["rollback_status"] = "not_attempted"
    replay["final_status"] = "applied"
    artifacts["final_seal"] = _display_path(repo_path, final_seal_artifact)
    replay["artifact_paths"] = _artifact_paths(artifacts)
    seal_payload = _seal_payload(
        target=target,
        artifacts=artifacts,
        approval=approval_summary,
        validation=validation_summary,
        rollback=rollback_summary,
        replay=replay,
    )
    try:
        _write_json(final_seal_artifact, seal_payload)
    except Exception:
        rollback_summary["attempted"] = True
        rollback_ok = _restore_preimage(target_abs, preimage_text)
        rollback_summary["ok"] = rollback_ok
        rollback_status = "succeeded" if rollback_ok else "failed"
        replay["rollback_status"] = rollback_status
        return _finalize_after_mutation_failure(
            repo_path=repo_path,
            target=target,
            artifacts=artifacts,
            approval=approval_summary,
            validation=validation_summary,
            rollback=rollback_summary,
            replay=replay,
            rollback_artifact=rollback_artifact,
            final_seal_artifact=final_seal_artifact,
            failure_code="artifact_write_failed",
            rollback_ok=rollback_ok,
        )

    return _result(
        ok=True,
        status="applied",
        reason_code="applied",
        failures=[],
        target=target,
        artifacts=artifacts,
        approval=approval_summary,
        validation=validation_summary,
        rollback=rollback_summary,
        replay=replay,
    )


def _validate_repo_root(repo_root):
    try:
        path = Path(repo_root)
    except Exception:
        return False, None, "repo_root_invalid"
    if path.is_symlink() or not path.exists() or not path.is_dir():
        return False, None, "repo_root_invalid"
    try:
        return True, path.resolve(strict=True), None
    except Exception:
        return False, None, "repo_root_invalid"


def _validate_artifact_root(repo_path, artifact_root):
    try:
        candidate = Path(artifact_root)
    except Exception:
        return False, None, "artifact_root_invalid"
    if not candidate.is_absolute():
        candidate = repo_path / candidate
    try:
        resolved = candidate.resolve(strict=False)
    except Exception:
        return False, None, "artifact_root_invalid"
    if not _is_inside(resolved, repo_path):
        return False, None, "artifact_root_invalid"
    if candidate.exists() and candidate.is_symlink():
        return False, None, "artifact_root_invalid"
    try:
        candidate.mkdir(parents=True, exist_ok=True)
    except Exception:
        return False, None, "artifact_root_invalid"
    if candidate.is_symlink() or not candidate.exists() or not candidate.is_dir():
        return False, None, "artifact_root_invalid"
    try:
        resolved = candidate.resolve(strict=True)
    except Exception:
        return False, None, "artifact_root_invalid"
    if not _is_inside(resolved, repo_path):
        return False, None, "artifact_root_invalid"
    return True, resolved, None


def _validate_target_path(repo_path, target_path):
    if not isinstance(target_path, str) or not target_path:
        return False, None, None, "target_path_invalid"
    if "\\" in target_path:
        return False, None, None, "target_path_invalid"
    relative = Path(target_path)
    if relative.is_absolute():
        return False, None, None, "target_path_invalid"
    if any(part == ".." for part in relative.parts):
        return False, None, None, "target_path_invalid"
    target_rel = "/".join(relative.parts)
    if not target_rel:
        return False, None, None, "target_path_invalid"
    candidate = repo_path / relative
    if candidate.is_symlink():
        return False, None, target_rel, "target_is_symlink"
    try:
        resolved = candidate.resolve(strict=False)
    except Exception:
        return False, None, target_rel, "target_path_invalid"
    if not _is_inside(resolved, repo_path):
        return False, None, target_rel, "target_outside_repo"
    if not candidate.exists():
        return False, None, target_rel, "target_missing"
    if not candidate.is_file():
        return False, None, target_rel, "target_not_file"
    return True, resolved, target_rel, None


def _validate_new_content(new_content):
    if not isinstance(new_content, str):
        return False, "new_content_invalid"
    if len(new_content) > _MAX_TEXT_CHARS or "\x00" in new_content:
        return False, "new_content_invalid"
    return True, None


def _read_text_target(target_abs):
    try:
        raw = target_abs.read_bytes()
    except Exception:
        return False, None, "target_not_text"
    if b"\x00" in raw:
        return False, None, "target_not_text"
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return False, None, "target_not_text"
    if len(text) > _MAX_TEXT_CHARS:
        return False, None, "target_not_text"
    return True, text, None


def _validate_proposal(proposal, target_rel):
    if not isinstance(proposal, Mapping):
        return False, {}, "proposal_invalid"
    copied = deepcopy(proposal)
    proposal_id = copied.get("proposal_id")
    patch_id = copied.get("patch_id")
    proposal_target = copied.get("target_path")
    if not _safe_identifier(proposal_id):
        return False, {}, "proposal_id_invalid"
    if not _safe_patch_id(patch_id):
        return False, {}, "patch_id_invalid"
    if not _single_target_list(copied, "target_paths", target_rel):
        return False, {}, "proposal_invalid"
    if not _single_target_list(copied, "target_file_ids", target_rel):
        return False, {}, "proposal_invalid"
    if proposal_target != target_rel:
        return False, {}, "proposal_target_mismatch"
    return (
        True,
        {
            "proposal_id": proposal_id,
            "patch_id": patch_id,
            "target_path": proposal_target,
        },
        None,
    )


def _validate_approval(approval, proposal_data, target_rel, preimage_identity):
    if not isinstance(approval, Mapping):
        return False, {}, "approval_invalid"
    copied = deepcopy(approval)
    approval_data = {
        "approved": False,
        "proposal_id": _bounded_identifier_or_none(copied.get("proposal_id")),
        "patch_id": _bounded_patch_id_or_none(copied.get("patch_id")),
        "target_path": copied.get("target_path"),
        "expected_preimage_identity": copied.get("expected_preimage_identity"),
    }
    if "approved" not in copied:
        return False, approval_data, "approval_invalid"
    approved = copied.get("approved")
    if type(approved) is not bool or approved is not True:
        return False, approval_data, "approval_not_true"
    approval_data["approved"] = True
    if approval_data["target_path"] != target_rel:
        return False, approval_data, "approval_target_mismatch"
    if approval_data["proposal_id"] != proposal_data["proposal_id"]:
        return False, approval_data, "approval_proposal_mismatch"
    if approval_data["patch_id"] != proposal_data["patch_id"]:
        return False, approval_data, "approval_patch_mismatch"
    if approval_data["expected_preimage_identity"] != preimage_identity:
        return False, approval_data, "preimage_identity_mismatch"
    return True, approval_data, None


def _run_validation(validation_callable, context):
    try:
        raw_result = validation_callable(deepcopy(context))
    except Exception as exc:
        return (
            {
                "ok": False,
                "reason_code": "validation_exception",
                "exception_type": _truncate(type(exc).__name__),
                "json_safe": True,
            },
            "validation_exception",
        )
    if not isinstance(raw_result, Mapping):
        return (
            {
                "ok": False,
                "reason_code": "validation_result_invalid",
                "json_safe": True,
            },
            "validation_result_invalid",
        )
    normalized = _sanitize_mapping(raw_result)
    ok_value = raw_result.get("ok")
    if type(ok_value) is not bool:
        normalized["ok"] = False
        normalized["reason_code"] = "validation_result_invalid"
        normalized["json_safe"] = True
        return normalized, "validation_result_invalid"
    normalized["ok"] = ok_value
    if ok_value is True:
        normalized["reason_code"] = _string_or_default(
            normalized.get("reason_code"), "validation_passed"
        )
        normalized["json_safe"] = True
        return normalized, None
    normalized["reason_code"] = _string_or_default(
        normalized.get("reason_code"), "validation_failed"
    )
    normalized["json_safe"] = True
    return normalized, "validation_failed"


def _finalize_after_mutation_failure(
    *,
    repo_path,
    target,
    artifacts,
    approval,
    validation,
    rollback,
    replay,
    rollback_artifact,
    final_seal_artifact,
    failure_code,
    rollback_ok,
):
    failures = [failure_code]
    status = "rolled_back" if rollback_ok else "rollback_failed"
    reason_code = failure_code if rollback_ok else "rollback_failed"
    if not rollback_ok:
        failures.append("rollback_failed")
    artifacts["rollback"] = _display_path(repo_path, rollback_artifact)
    replay["artifact_paths"] = _artifact_paths(artifacts)
    try:
        _write_json(
            rollback_artifact,
            {
                "artifact_type": "single_file_patch_rollback",
                "attempted": True,
                "ok": rollback_ok,
                "reason_code": "rollback_succeeded" if rollback_ok else "rollback_failed",
                "json_safe": True,
            },
        )
    except Exception:
        failures.append("artifact_write_failed")
    artifacts["final_seal"] = _display_path(repo_path, final_seal_artifact)
    replay["final_status"] = status
    replay["artifact_paths"] = _artifact_paths(artifacts)
    try:
        _write_json(
            final_seal_artifact,
            _seal_payload(
                target=target,
                artifacts=artifacts,
                approval=approval,
                validation=validation,
                rollback=rollback,
                replay=replay,
            ),
        )
    except Exception:
        artifacts["final_seal"] = None
        replay["artifact_paths"] = _artifact_paths(artifacts)
        failures.append("artifact_write_failed")
    return _result(
        ok=False,
        status=status,
        reason_code=reason_code,
        failures=_ordered_unique(failures),
        target=target,
        artifacts=artifacts,
        approval=approval,
        validation=validation,
        rollback=rollback,
        replay=replay,
    )


def _restore_preimage(target_abs, preimage_text):
    try:
        _write_text(target_abs, preimage_text)
    except Exception:
        return False
    return True


def _write_json(path, payload):
    text = json.dumps(
        _sanitize(payload),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    path.write_text(text + "\n", encoding="utf-8")


def _write_text(path, text):
    path.write_bytes(text.encode("utf-8"))


def _identity(text):
    return sha256(text.encode("utf-8")).hexdigest()


def _safe_patch_id(value):
    if not _safe_identifier(value):
        return False
    if value in (".", ".."):
        return False
    return all(char in _SAFE_PATCH_ID_CHARS for char in value)


def _safe_identifier(value):
    return _non_empty_string(value) and len(value) <= _MAX_IDENTIFIER_CHARS


def _bounded_identifier_or_none(value):
    if _safe_identifier(value):
        return value
    return None


def _bounded_patch_id_or_none(value):
    if _safe_patch_id(value):
        return value
    return None


def _single_target_list(mapping, key, target_rel):
    if key not in mapping:
        return True
    value = mapping.get(key)
    return isinstance(value, list) and value == [target_rel]


def _non_empty_string(value):
    return isinstance(value, str) and value != ""


def _string_or_default(value, default):
    if isinstance(value, str) and value:
        return _truncate(value)
    return default


def _is_inside(path, root):
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _display_path(repo_path, path):
    return path.resolve(strict=False).relative_to(repo_path).as_posix()


def _artifact_paths(artifacts):
    paths = []
    for key in _ARTIFACT_KEYS:
        value = artifacts.get(key)
        if isinstance(value, str) and value:
            paths.append(value)
    return paths


def _sanitize_mapping(mapping):
    sanitized = {}
    count = 0
    for key in sorted(mapping.keys(), key=lambda item: str(item)):
        if count >= _MAX_MAPPING_ITEMS:
            break
        if isinstance(key, str):
            safe_key = _truncate(key)
        else:
            safe_key = "unsupported_key"
        sanitized[safe_key] = _sanitize(mapping[key])
        count += 1
    return sanitized


def _sanitize(value):
    if value is None:
        return None
    if type(value) is bool:
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        try:
            json.dumps(value, allow_nan=False)
        except ValueError:
            return "unsupported_value"
        return value
    if isinstance(value, str):
        return _truncate(value)
    if isinstance(value, Mapping):
        return _sanitize_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in list(value)[:_MAX_LIST_ITEMS]]
    return "unsupported_value"


def _truncate(value):
    if len(value) <= _MAX_STRING_CHARS:
        return value
    return value[:_MAX_STRING_CHARS] + "...truncated"


def _ordered_unique(values):
    ordered = []
    for value in values:
        if value not in ordered:
            ordered.append(value)
    return ordered


def _empty_artifacts():
    return {
        "proposal": None,
        "patch_body": None,
        "preimage": None,
        "validation_result": None,
        "rollback": None,
        "final_seal": None,
    }


def _empty_target():
    return {
        "path": None,
        "preimage_identity": None,
        "postimage_identity": None,
    }


def _empty_approval():
    return {
        "approved": False,
        "proposal_id": None,
        "patch_id": None,
    }


def _empty_validation():
    return {
        "ok": None,
        "reason_code": None,
    }


def _empty_rollback():
    return {
        "attempted": False,
        "ok": None,
    }


def _empty_replay():
    return {
        "proposal_id": None,
        "patch_id": None,
        "target_path": None,
        "preimage_identity": None,
        "postimage_identity": None,
        "validation_status": None,
        "approval_status": None,
        "rollback_status": None,
        "final_status": "rejected",
        "artifact_paths": [],
    }


def _seal_payload(*, target, artifacts, approval, validation, rollback, replay):
    return {
        "artifact_type": "single_file_patch_final_seal",
        "surface": _SURFACE,
        "version": _VERSION,
        "target": deepcopy(target),
        "artifacts": deepcopy(artifacts),
        "approval": deepcopy(approval),
        "validation": deepcopy(validation),
        "rollback": deepcopy(rollback),
        "replay": deepcopy(replay),
        "json_safe": True,
    }


def _result(
    *,
    ok,
    status,
    reason_code,
    failures,
    target,
    artifacts,
    approval,
    validation,
    rollback,
    replay,
):
    replay = deepcopy(replay)
    replay["final_status"] = status
    replay["artifact_paths"] = _artifact_paths(artifacts)
    return {
        "ok": bool(ok),
        "status": status,
        "reason_code": reason_code,
        "failures": list(failures),
        "target": deepcopy(target),
        "artifacts": deepcopy(artifacts),
        "approval": deepcopy(approval),
        "validation": deepcopy(validation),
        "rollback": deepcopy(rollback),
        "replay": replay,
        "json_safe": True,
    }


def _rejected(
    failure,
    target,
    artifacts,
    approval,
    validation,
    rollback,
    replay,
):
    return _result(
        ok=False,
        status="rejected",
        reason_code=failure,
        failures=[failure],
        target=target,
        artifacts=artifacts,
        approval=approval,
        validation=validation,
        rollback=rollback,
        replay=replay,
    )
