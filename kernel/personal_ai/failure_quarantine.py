"""Failure quarantine artifacts for the Personal AI local CLI."""

from dataclasses import dataclass
from pathlib import Path

from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.job_package import validate_job_id

__all__ = [
    "FailureQuarantineResult",
    "write_failure_quarantine",
]

_MAX_ERROR_MESSAGE_LENGTH = 240
_SENSITIVE_TOKEN_MARKERS = (
    "SECRET",
    "SENTINEL",
    "TOKEN",
    "PASSWORD",
    "CREDENTIAL",
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

    write_json_atomically(
        failure_manifest_path,
        {
            "manifest_type": "personal_ai_local_v1_failure_quarantine",
            "authority": "non_authority",
            "execution_capability": "not_introduced",
            "required_human_approval": True,
            "job_id": job_id,
            "error_type": safe_error_type,
            "error_message": safe_error_message,
            "quarantine_dir": quarantine_dir.as_posix(),
            "failure_manifest": failure_manifest_path.as_posix(),
            "partial_job_deleted": False,
            "input_files_modified": False,
            "input_file_contents_copied": False,
            "raw_cell_values_copied": False,
            "traceback_copied": False,
            "boundaries": dict(_BOUNDARIES),
            "next_allowed_action": "human_review_only",
        },
    )

    return FailureQuarantineResult(
        output_root_dir=output_root_path,
        quarantine_dir=quarantine_dir,
        failure_manifest_path=failure_manifest_path,
        job_id=job_id,
        error_type=safe_error_type,
        error_message=safe_error_message,
        required_human_approval=True,
    )


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
