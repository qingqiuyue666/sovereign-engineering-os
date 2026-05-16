"""Failure quarantine artifacts for the Personal AI local CLI."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Mapping

from kernel.evidence.sealed_redaction_contract import (
    redacted_digest,
    validate_sealed_evidence_record,
)
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.job_package import validate_job_id

__all__ = [
    "FailureQuarantineResult",
    "build_failure_quarantine_sealed_evidence_payload",
    "write_failure_quarantine",
]

_MAX_ERROR_MESSAGE_LENGTH = 240
_SEALED_EVIDENCE_CONTRACT = "sealed_redaction_v1"
_SENSITIVE_TOKEN_MARKERS = (
    "SECRET",
    "SENTINEL",
    "TOKEN",
    "PASSWORD",
    "CREDENTIAL",
    "API_KEY",
    "BEARER",
    "COOKIE",
)

_BOUNDARIES = {
    "local_only": True,
    "no_runtime_authority": True,
    "no_execution_capability": True,
    "no_external_tool_control": True,
    "no_network": True,
    "no_api_calls": True,
    "no_subprocess": True,
    "no_adapter_implementation": True,
    "no_ai_classification": True,
    "no_semantic_classification": True,
    "no_spreadsheet_output_write": True,
    "no_input_file_mutation": True,
    "no_input_content_copy": True,
    "no_raw_cell_value_copy": True,
    "no_destructive_actions": True,
}


@dataclass(frozen=True)
class FailureQuarantineResult:
    output_root_dir: Path
    quarantine_dir: Path
    failure_manifest_path: Path
    job_id: str
    error_type: str
    error_message: str
    required_human_approval: bool


def write_failure_quarantine(
    output_root_dir: Path,
    *,
    job_id: str,
    error_type: str,
    error_message: str,
) -> FailureQuarantineResult:
    output_root_path = Path(output_root_dir)
    if not output_root_path.exists():
        raise ValueError("output_root_dir is missing")
    if not output_root_path.is_dir():
        raise ValueError("output_root_dir is not a directory")
    validate_job_id(job_id)

    safe_error_type = _safe_error_type(error_type)
    safe_error_message = _safe_error_message(error_message)
    failed_jobs_dir = output_root_path / "_failed_jobs"
    quarantine_dir = failed_jobs_dir / job_id
    failed_jobs_dir.mkdir(exist_ok=True)
    quarantine_dir.mkdir(exist_ok=True)
    failure_manifest_path = quarantine_dir / "failure_manifest.json"

    manifest = {
        "manifest_type": "personal_ai_local_v1_failure_quarantine",
        "authority": "non_authority",
        "execution_capability": "not_introduced",
        "required_human_approval": True,
        "job_id": job_id,
        "error_type": safe_error_type,
        "error_message": safe_error_message,
        "error_message_sha256": sha256(safe_error_message.encode("utf-8")).hexdigest(),
        "quarantine_dir": quarantine_dir.as_posix(),
        "failure_manifest": failure_manifest_path.as_posix(),
        "partial_job_deleted": False,
        "input_files_modified": False,
        "input_file_contents_copied": False,
        "raw_cell_values_copied": False,
        "traceback_copied": False,
        "raw_traceback_persisted": False,
        "raw_exception_dump_persisted": False,
        "secret_value_read": False,
        "secret_value_persisted": False,
        "secret_value_serialized": False,
        "runtime_execution_performed": False,
        "external_network_accessed": False,
        "subprocess_executed": False,
        "runtime_authority_granted": False,
        "boundaries": dict(_BOUNDARIES),
        "next_allowed_action": "human_review_only",
    }
    manifest["sealed_evidence_payload"] = build_failure_quarantine_sealed_evidence_payload(manifest)

    write_json_atomically(failure_manifest_path, manifest)

    return FailureQuarantineResult(
        output_root_dir=output_root_path,
        quarantine_dir=quarantine_dir,
        failure_manifest_path=failure_manifest_path,
        job_id=job_id,
        error_type=safe_error_type,
        error_message=safe_error_message,
        required_human_approval=True,
    )


def build_failure_quarantine_sealed_evidence_payload(
    manifest: Mapping[str, object]
) -> dict[str, object]:
    """Build a sealed evidence payload for a failure quarantine manifest."""

    job_id = _required_string(manifest, "job_id")
    evidence_payload = {
        "job_id": job_id,
        "manifest_type": _required_string(manifest, "manifest_type"),
        "error_type": _required_string(manifest, "error_type"),
        "error_message_sha256": _required_string(manifest, "error_message_sha256"),
        "authority": _required_string(manifest, "authority"),
        "execution_capability": _required_string(manifest, "execution_capability"),
        "boundaries": _required_mapping(manifest, "boundaries"),
        "partial_job_deleted": _required_false(manifest, "partial_job_deleted"),
        "input_files_modified": _required_false(manifest, "input_files_modified"),
        "input_file_contents_copied": _required_false(manifest, "input_file_contents_copied"),
        "raw_cell_values_copied": _required_false(manifest, "raw_cell_values_copied"),
        "traceback_copied": _required_false(manifest, "traceback_copied"),
        "raw_traceback_persisted": _required_false(manifest, "raw_traceback_persisted"),
        "raw_exception_dump_persisted": _required_false(manifest, "raw_exception_dump_persisted"),
        "secret_value_read": _required_false(manifest, "secret_value_read"),
        "secret_value_persisted": _required_false(manifest, "secret_value_persisted"),
        "secret_value_serialized": _required_false(manifest, "secret_value_serialized"),
        "runtime_execution_performed": _required_false(manifest, "runtime_execution_performed"),
        "external_network_accessed": _required_false(manifest, "external_network_accessed"),
        "subprocess_executed": _required_false(manifest, "subprocess_executed"),
        "runtime_authority_granted": _required_false(manifest, "runtime_authority_granted"),
        "required_human_approval": _required_true(manifest, "required_human_approval"),
    }
    evidence_record = {
        "evidence_id": "ev-failure-quarantine-" + job_id,
        "classification": "secret",
        "digest": redacted_digest(evidence_payload),
        "representation": "redacted_digest",
        "payload": evidence_payload,
    }
    validation = validate_sealed_evidence_record(evidence_record)
    if not validation.accepted:
        raise ValueError(
            "failure quarantine sealed evidence contract failed: "
            + "; ".join(validation.failures[:5])
        )
    return {
        "evidence_contract": _SEALED_EVIDENCE_CONTRACT,
        "evidence": evidence_record,
    }


def _safe_error_type(error_type):
    compact = "".join(
        character
        for character in str(error_type)
        if character.isalnum() or character in "._-"
    )
    return compact[:80] or "LocalMVPFailure"


def _safe_error_message(error_message):
    compact = " ".join(str(error_message).split())
    redacted_tokens = [
        _redact_token(token)
        for token in compact.split(" ")
    ]
    safe_message = " ".join(redacted_tokens)
    if len(safe_message) > _MAX_ERROR_MESSAGE_LENGTH:
        return safe_message[: _MAX_ERROR_MESSAGE_LENGTH - 3] + "..."
    return safe_message


def _redact_token(token):
    upper_token = token.upper()
    if any(marker in upper_token for marker in _SENSITIVE_TOKEN_MARKERS):
        return "[redacted-sensitive-token]"
    return token


def _required_string(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(key + " is required")
    return value


def _required_mapping(payload: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(key + " must be a mapping")
    return value


def _required_false(payload: Mapping[str, object], key: str) -> bool:
    value = payload.get(key)
    if value is not False:
        raise ValueError(key + " must be false")
    return False


def _required_true(payload: Mapping[str, object], key: str) -> bool:
    value = payload.get(key)
    if value is not True:
        raise ValueError(key + " must be true")
    return True
