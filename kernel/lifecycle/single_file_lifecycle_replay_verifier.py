from collections.abc import Mapping
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json

__all__ = [
    "single_file_lifecycle_replay_verifier_manifest",
    "verify_single_file_patch_lifecycle_replay",
]

_SURFACE = "single_file_lifecycle_replay_verifier"
_VERSION = 1
_PACKAGE = "single-file-lifecycle-replay-verifier-v1"
_SOURCE_SURFACE = "single_file_patch_lifecycle"
_SOURCE_VERSION = 1
_MAX_IDENTIFIER_CHARS = 128
_MAX_STRING_CHARS = 4096
_MAX_TEXT_CHARS = 200000
_MAX_LIST_ITEMS = 25
_MAX_MAPPING_ITEMS = 25
_SAFE_PATCH_ID_CHARS = (
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    "_.-"
)
_BASE_ARTIFACT_FILES = (
    "proposal.json",
    "patch_body.txt",
    "preimage.txt",
    "validation_result.json",
    "final_seal.json",
)
_ROLLBACK_ARTIFACT_FILE = "rollback.json"
_KNOWN_ARTIFACT_FILES = _BASE_ARTIFACT_FILES + (_ROLLBACK_ARTIFACT_FILE,)
_ARTIFACT_KEYS = (
    "proposal",
    "patch_body",
    "preimage",
    "validation_result",
    "rollback",
    "final_seal",
)
_ARTIFACT_FILENAMES = {
    "proposal": "proposal.json",
    "patch_body": "patch_body.txt",
    "preimage": "preimage.txt",
    "validation_result": "validation_result.json",
    "rollback": "rollback.json",
    "final_seal": "final_seal.json",
}
_FINAL_STATUSES = ("applied", "rolled_back", "rollback_failed")

_MANIFEST = {
    "surface": _SURFACE,
    "version": _VERSION,
    "package": _PACKAGE,
    "source_surface": _SOURCE_SURFACE,
    "source_version": _SOURCE_VERSION,
    "read_only": True,
    "artifact_verifier": True,
    "target_mutation_authorized": False,
    "service_calls_authorized": False,
    "db_repository_uow_authorized": False,
    "evidence_audit_append_authorized": False,
    "executor_dispatch_authorized": False,
    "restore_service_authorized": False,
    "multi_file_lifecycle_authorized": False,
    "broad_physical_io_authorized": False,
    "authority_grant_usage_authorized": False,
    "capability_token_work_authorized": False,
    "network_authorized": False,
    "subprocess_authorized": False,
    "json_safe": True,
}


def single_file_lifecycle_replay_verifier_manifest():
    return deepcopy(_MANIFEST)


def verify_single_file_patch_lifecycle_replay(
    *,
    repo_root,
    artifact_root,
    patch_id,
):
    artifacts = _empty_artifacts()
    identity = _empty_identity()
    replay = _empty_replay()

    repo_ok, repo_path, repo_failure = _validate_repo_root(repo_root)
    if not repo_ok:
        return _verification_result(
            failures=[repo_failure],
            patch_id=None,
            target_path=None,
            artifacts=artifacts,
            identity=identity,
            replay=replay,
        )

    artifact_ok, artifact_path, artifact_failure = _validate_artifact_root(
        repo_path, artifact_root
    )
    if not artifact_ok:
        return _verification_result(
            failures=[artifact_failure],
            patch_id=None,
            target_path=None,
            artifacts=artifacts,
            identity=identity,
            replay=replay,
        )

    if not _safe_patch_id(patch_id):
        return _verification_result(
            failures=["patch_id_invalid"],
            patch_id=None,
            target_path=None,
            artifacts=artifacts,
            identity=identity,
            replay=replay,
        )

    safe_patch_id = patch_id
    artifact_dir = artifact_path / safe_patch_id
    subdir_ok, subdir_failure = _validate_artifact_subdir(
        artifact_dir, artifact_path
    )
    if not subdir_ok:
        return _verification_result(
            failures=[subdir_failure],
            patch_id=safe_patch_id,
            target_path=None,
            artifacts=artifacts,
            identity=identity,
            replay=replay,
        )

    file_failures = _inspect_artifact_files(artifact_dir, artifacts)
    if file_failures:
        return _verification_result(
            failures=file_failures,
            patch_id=safe_patch_id,
            target_path=None,
            artifacts=artifacts,
            identity=identity,
            replay=replay,
        )

    proposal_ok, proposal, proposal_failure = _read_json_object(
        artifact_dir / "proposal.json"
    )
    validation_ok, validation_result, validation_failure = _read_json_object(
        artifact_dir / "validation_result.json"
    )
    final_seal_ok, final_seal, final_seal_failure = _read_json_object(
        artifact_dir / "final_seal.json"
    )
    json_failures = []
    if not proposal_ok:
        json_failures.append(proposal_failure)
    if not validation_ok:
        json_failures.append(validation_failure)
    if not final_seal_ok:
        json_failures.append(final_seal_failure)
    if json_failures:
        return _verification_result(
            failures=_ordered_unique(json_failures),
            patch_id=safe_patch_id,
            target_path=None,
            artifacts=artifacts,
            identity=identity,
            replay=replay,
        )

    patch_text_ok, patch_body_text, patch_text_failure = _read_text_file(
        artifact_dir / "patch_body.txt"
    )
    preimage_ok, preimage_text, preimage_failure = _read_text_file(
        artifact_dir / "preimage.txt"
    )
    text_failures = []
    if not patch_text_ok:
        text_failures.append(patch_text_failure)
    if not preimage_ok:
        text_failures.append(preimage_failure)
    if text_failures:
        return _verification_result(
            failures=_ordered_unique(text_failures),
            patch_id=safe_patch_id,
            target_path=None,
            artifacts=artifacts,
            identity=identity,
            replay=replay,
        )

    failures = []
    proposal_values = _proposal_values(proposal)
    if not proposal_values:
        failures.append("proposal_invalid")

    seal_values = _seal_values(final_seal)
    if not seal_values:
        failures.append("final_seal_invalid")

    validation_values = _validation_values(validation_result)
    if not validation_values:
        failures.append("validation_result_invalid")

    if failures:
        return _verification_result(
            failures=_ordered_unique(failures),
            patch_id=safe_patch_id,
            target_path=None,
            artifacts=artifacts,
            identity=identity,
            replay=replay,
        )

    final_replay = seal_values["replay"]
    replay["final_status"] = _bounded_string_or_none(final_replay.get("final_status"))
    replay["validation_status"] = _bounded_string_or_none(
        final_replay.get("validation_status")
    )
    replay["rollback_status"] = _bounded_string_or_none(
        final_replay.get("rollback_status")
    )

    target_path = _bounded_string_or_none(proposal_values["target_path"])
    seal_target_path = seal_values["target"].get("path")
    replay_target_path = final_replay.get("target_path")
    final_status = final_replay.get("final_status")

    rollback_required = final_status in ("rolled_back", "rollback_failed")
    rollback_path = artifact_dir / "rollback.json"
    rollback_exists = rollback_path.exists() and rollback_path.is_file()
    if rollback_required:
        artifacts["rollback"] = bool(rollback_exists)
    elif rollback_exists:
        artifacts["rollback"] = True
    else:
        artifacts["rollback"] = None

    if final_status == "applied" and rollback_exists:
        failures.append("artifact_file_unexpected")
    if rollback_required and not rollback_exists:
        failures.append("artifact_file_missing")

    rollback = None
    if rollback_exists:
        rollback_ok, rollback, rollback_failure = _read_json_object(rollback_path)
        if not rollback_ok:
            failures.append(rollback_failure)
            rollback = None

    if proposal_values["patch_id"] != safe_patch_id:
        failures.append("patch_id_mismatch")
    if final_replay.get("patch_id") != safe_patch_id:
        failures.append("patch_id_mismatch")
    if final_replay.get("proposal_id") != proposal_values["proposal_id"]:
        failures.append("proposal_id_mismatch")
    if seal_target_path != proposal_values["target_path"]:
        failures.append("target_path_mismatch")
    if replay_target_path != proposal_values["target_path"]:
        failures.append("target_path_mismatch")

    if final_status not in _FINAL_STATUSES:
        failures.append("final_seal_invalid")
    seal_status = final_seal.get("status")
    if isinstance(seal_status, str) and seal_status != final_status:
        failures.append("final_status_mismatch")
    if final_status != replay["final_status"]:
        failures.append("final_status_mismatch")

    validation_status = final_replay.get("validation_status")
    expected_validation_status = "pass" if validation_values["ok"] else "fail"
    if validation_status != expected_validation_status:
        failures.append("validation_status_mismatch")
    seal_validation = seal_values["validation"]
    if seal_validation.get("ok") != validation_values["ok"]:
        failures.append("validation_status_mismatch")
    if seal_validation.get("reason_code") != validation_values["reason_code"]:
        failures.append("validation_status_mismatch")

    rollback_failure = _validate_rollback_consistency(
        final_status=final_status,
        replay=final_replay,
        seal_rollback=seal_values["rollback"],
        rollback=rollback,
    )
    if rollback_failure:
        failures.append(rollback_failure)

    computed_preimage_identity = _identity(preimage_text)
    preimage_values = (
        proposal.get("preimage_identity"),
        seal_values["target"].get("preimage_identity"),
        final_replay.get("preimage_identity"),
    )
    identity["preimage_identity_matches"] = all(
        value == computed_preimage_identity for value in preimage_values
    )
    if not identity["preimage_identity_matches"]:
        failures.append("preimage_identity_mismatch")

    computed_postimage_identity = _identity(patch_body_text)
    postimage_values = (
        seal_values["target"].get("postimage_identity"),
        final_replay.get("postimage_identity"),
    )
    present_postimage_values = [
        value for value in postimage_values if isinstance(value, str) and value
    ]
    if final_status == "applied":
        identity["postimage_identity_matches"] = all(
            value == computed_postimage_identity for value in postimage_values
        )
    elif present_postimage_values:
        identity["postimage_identity_matches"] = all(
            value == computed_postimage_identity for value in present_postimage_values
        )
    else:
        identity["postimage_identity_matches"] = None
    if identity["postimage_identity_matches"] is False:
        failures.append("postimage_identity_mismatch")

    if not _artifact_paths_safe(repo_path, artifact_dir, seal_values["artifacts"]):
        failures.append("artifact_path_unsafe")
    if not _replay_artifact_paths_safe(
        repo_path, artifact_dir, seal_values["artifacts"], final_replay
    ):
        failures.append("artifact_path_unsafe")

    return _verification_result(
        failures=_ordered_unique(failures),
        patch_id=safe_patch_id,
        target_path=target_path,
        artifacts=artifacts,
        identity=identity,
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
    if candidate.is_symlink() or not candidate.exists() or not candidate.is_dir():
        return False, None, "artifact_root_invalid"
    try:
        resolved = candidate.resolve(strict=True)
    except Exception:
        return False, None, "artifact_root_invalid"
    if not _is_inside(resolved, repo_path):
        return False, None, "artifact_root_invalid"
    return True, resolved, None


def _validate_artifact_subdir(artifact_dir, artifact_root):
    try:
        resolved = artifact_dir.resolve(strict=False)
    except Exception:
        return False, "artifact_subdir_invalid"
    if not _is_inside(resolved, artifact_root):
        return False, "artifact_subdir_invalid"
    if not artifact_dir.exists():
        return False, "artifact_subdir_missing"
    if artifact_dir.is_symlink() or not artifact_dir.is_dir():
        return False, "artifact_subdir_invalid"
    try:
        resolved = artifact_dir.resolve(strict=True)
    except Exception:
        return False, "artifact_subdir_invalid"
    if not _is_inside(resolved, artifact_root):
        return False, "artifact_subdir_invalid"
    return True, None


def _inspect_artifact_files(artifact_dir, artifacts):
    failures = []
    try:
        names = sorted(item.name for item in artifact_dir.iterdir())
    except Exception:
        return ["artifact_subdir_invalid"]
    for name in names:
        if name not in _KNOWN_ARTIFACT_FILES:
            failures.append("artifact_file_unexpected")
    for key in _ARTIFACT_KEYS:
        path = artifact_dir / _ARTIFACT_FILENAMES[key]
        exists = path.exists()
        if key == "rollback":
            artifacts[key] = True if exists else None
        else:
            artifacts[key] = bool(exists and path.is_file() and not path.is_symlink())
    for name in _BASE_ARTIFACT_FILES:
        path = artifact_dir / name
        if not path.exists():
            failures.append("artifact_file_missing")
        elif path.is_symlink() or not path.is_file():
            failures.append("artifact_file_invalid")
    rollback_path = artifact_dir / _ROLLBACK_ARTIFACT_FILE
    if rollback_path.exists() and (rollback_path.is_symlink() or not rollback_path.is_file()):
        failures.append("artifact_file_invalid")
    return _ordered_unique(failures)


def _read_json_object(path):
    try:
        text = path.read_text(encoding="utf-8")
        parsed = json.loads(text, parse_constant=_reject_json_constant)
    except Exception:
        return False, {}, "artifact_json_invalid"
    if not isinstance(parsed, Mapping):
        return False, {}, "artifact_json_invalid"
    return True, parsed, None


def _read_text_file(path):
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
    except Exception:
        return False, None, "artifact_text_invalid"
    if "\x00" in text or len(text) > _MAX_TEXT_CHARS:
        return False, None, "artifact_text_invalid"
    return True, text, None


def _reject_json_constant(_value):
    raise ValueError("invalid json constant")


def _proposal_values(proposal):
    if not isinstance(proposal, Mapping):
        return None
    if proposal.get("artifact_type") != "single_file_patch_proposal":
        return None
    if proposal.get("surface") != _SOURCE_SURFACE:
        return None
    if proposal.get("version") != _SOURCE_VERSION:
        return None
    proposal_id = proposal.get("proposal_id")
    patch_id = proposal.get("patch_id")
    target_path = proposal.get("target_path")
    if not _safe_identifier(proposal_id):
        return None
    if not _safe_patch_id(patch_id):
        return None
    if not _safe_relative_path(target_path):
        return None
    if not _non_empty_string(proposal.get("preimage_identity")):
        return None
    if proposal.get("json_safe") is not True:
        return None
    return {
        "proposal_id": proposal_id,
        "patch_id": patch_id,
        "target_path": target_path,
    }


def _validation_values(validation_result):
    if not isinstance(validation_result, Mapping):
        return None
    ok = validation_result.get("ok")
    reason_code = validation_result.get("reason_code")
    if type(ok) is not bool:
        return None
    if not _non_empty_string(reason_code):
        return None
    if validation_result.get("json_safe") is not True:
        return None
    return {"ok": ok, "reason_code": reason_code}


def _seal_values(final_seal):
    if not isinstance(final_seal, Mapping):
        return None
    if final_seal.get("artifact_type") != "single_file_patch_final_seal":
        return None
    if final_seal.get("surface") != _SOURCE_SURFACE:
        return None
    if final_seal.get("version") != _SOURCE_VERSION:
        return None
    if final_seal.get("json_safe") is not True:
        return None
    target = final_seal.get("target")
    artifacts = final_seal.get("artifacts")
    validation = final_seal.get("validation")
    rollback = final_seal.get("rollback")
    replay = final_seal.get("replay")
    approval = final_seal.get("approval")
    if not isinstance(target, Mapping):
        return None
    if not isinstance(artifacts, Mapping):
        return None
    if not isinstance(validation, Mapping):
        return None
    if not isinstance(rollback, Mapping):
        return None
    if not isinstance(replay, Mapping):
        return None
    if not isinstance(approval, Mapping):
        return None
    if not _safe_relative_path(target.get("path")):
        return None
    return {
        "target": target,
        "artifacts": artifacts,
        "validation": validation,
        "rollback": rollback,
        "replay": replay,
        "approval": approval,
    }


def _validate_rollback_consistency(*, final_status, replay, seal_rollback, rollback):
    rollback_status = replay.get("rollback_status")
    attempted = seal_rollback.get("attempted")
    ok = seal_rollback.get("ok")
    if final_status == "applied":
        if attempted is not False or ok is not None or rollback_status != "not_attempted":
            return "rollback_status_mismatch"
        return None
    if final_status == "rolled_back":
        if attempted is not True or ok is not True or rollback_status != "succeeded":
            return "rollback_status_mismatch"
        return _rollback_artifact_failure(rollback, expected_ok=True)
    if final_status == "rollback_failed":
        if attempted is not True or ok is not False or rollback_status != "failed":
            return "rollback_status_mismatch"
        return _rollback_artifact_failure(rollback, expected_ok=False)
    return None


def _rollback_artifact_failure(rollback, expected_ok):
    if not isinstance(rollback, Mapping):
        return "rollback_invalid"
    if rollback.get("artifact_type") != "single_file_patch_rollback":
        return "rollback_invalid"
    if rollback.get("attempted") is not True:
        return "rollback_invalid"
    if rollback.get("ok") is not expected_ok:
        return "rollback_status_mismatch"
    expected_reason = "rollback_succeeded" if expected_ok else "rollback_failed"
    if rollback.get("reason_code") != expected_reason:
        return "rollback_status_mismatch"
    if rollback.get("json_safe") is not True:
        return "rollback_invalid"
    return None


def _artifact_paths_safe(repo_path, artifact_dir, artifacts):
    if not isinstance(artifacts, Mapping):
        return False
    for key in _ARTIFACT_KEYS:
        if key not in artifacts:
            return False
        value = artifacts.get(key)
        expected = _display_path(repo_path, artifact_dir / _ARTIFACT_FILENAMES[key])
        if key == "rollback" and value is None:
            continue
        if not isinstance(value, str):
            return False
        if value != expected:
            return False
        if not _safe_display_path(repo_path, value):
            return False
    return True


def _replay_artifact_paths_safe(repo_path, artifact_dir, artifacts, replay):
    paths = replay.get("artifact_paths")
    if not isinstance(paths, list):
        return False
    expected_paths = []
    for key in _ARTIFACT_KEYS:
        value = artifacts.get(key)
        if isinstance(value, str) and value:
            expected_paths.append(value)
    if paths != expected_paths:
        return False
    for value in paths:
        if not isinstance(value, str):
            return False
        if not _safe_display_path(repo_path, value):
            return False
        expected_names = [
            _display_path(repo_path, artifact_dir / filename)
            for filename in _KNOWN_ARTIFACT_FILES
        ]
        if value not in expected_names:
            return False
    return True


def _safe_display_path(repo_path, value):
    if not _non_empty_string(value):
        return False
    if "\\" in value:
        return False
    path = Path(value)
    if path.is_absolute():
        return False
    if any(part == ".." for part in path.parts):
        return False
    try:
        resolved = (repo_path / path).resolve(strict=False)
    except Exception:
        return False
    return _is_inside(resolved, repo_path)


def _safe_relative_path(value):
    if not _non_empty_string(value):
        return False
    if "\\" in value:
        return False
    path = Path(value)
    if path.is_absolute():
        return False
    if any(part == ".." for part in path.parts):
        return False
    return "/".join(path.parts) == value


def _safe_patch_id(value):
    if not _safe_identifier(value):
        return False
    if value in (".", ".."):
        return False
    return all(char in _SAFE_PATCH_ID_CHARS for char in value)


def _safe_identifier(value):
    return _non_empty_string(value) and len(value) <= _MAX_IDENTIFIER_CHARS


def _non_empty_string(value):
    return isinstance(value, str) and value != ""


def _bounded_string_or_none(value):
    if isinstance(value, str):
        return _truncate(value)
    return None


def _identity(text):
    return sha256(text.encode("utf-8")).hexdigest()


def _is_inside(path, root):
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _display_path(repo_path, path):
    return path.resolve(strict=False).relative_to(repo_path).as_posix()


def _empty_artifacts():
    return {
        "proposal": False,
        "patch_body": False,
        "preimage": False,
        "validation_result": False,
        "rollback": None,
        "final_seal": False,
    }


def _empty_identity():
    return {
        "preimage_identity_matches": None,
        "postimage_identity_matches": None,
    }


def _empty_replay():
    return {
        "final_status": None,
        "validation_status": None,
        "rollback_status": None,
    }


def _authority():
    return {
        "service_calls_authorized": False,
        "db_repository_uow_authorized": False,
        "executor_dispatch_authorized": False,
        "multi_file_lifecycle_authorized": False,
        "evidence_audit_append_authorized": False,
        "broad_physical_io_authorized": False,
    }


def _verification_result(
    *,
    failures,
    patch_id,
    target_path,
    artifacts,
    identity,
    replay,
):
    failures = _ordered_unique(failures)
    ok = not failures
    payload = {
        "ok": ok,
        "status": "verified" if ok else "not_verified",
        "reason_code": "verified" if ok else "not_verified",
        "failures": failures,
        "patch_id": _bounded_string_or_none(patch_id),
        "target_path": _bounded_string_or_none(target_path),
        "artifacts": deepcopy(artifacts),
        "identity": deepcopy(identity),
        "replay": deepcopy(replay),
        "authority": _authority(),
        "json_safe": True,
    }
    try:
        json.dumps(payload, sort_keys=True, allow_nan=False)
    except Exception:
        payload = {
            "ok": False,
            "status": "not_verified",
            "reason_code": "not_verified",
            "failures": ["json_safety_failure"],
            "patch_id": None,
            "target_path": None,
            "artifacts": _empty_artifacts(),
            "identity": _empty_identity(),
            "replay": _empty_replay(),
            "authority": _authority(),
            "json_safe": True,
        }
    return payload


def _ordered_unique(values):
    ordered = []
    for value in values:
        if isinstance(value, str) and value not in ordered:
            ordered.append(value)
    return ordered


def _truncate(value):
    if len(value) <= _MAX_STRING_CHARS:
        return value
    return value[:_MAX_STRING_CHARS] + "...truncated"
