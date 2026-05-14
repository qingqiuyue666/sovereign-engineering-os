"""Validation reports for Personal AI local job packages."""

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "JobPackageValidationResult",
    "build_job_package_validation",
]

_VALIDATION_TYPE = "personal_ai_local_v1_job_package_validation"

_REQUIRED_JOB_FILES = {
    "input_snapshot": "input_snapshot.json",
    "intake_ledger": "intake_ledger.jsonl",
    "artifact_profile": "artifact_profile.json",
    "work_order_proposal": "work_order_proposal.json",
    "review_packet": "review_packet.json",
    "pipeline_manifest": "pipeline_manifest.json",
    "task_route": "task_route.json",
    "spreadsheet_processor_plan": "spreadsheet_processor_plan.json",
    "spreadsheet_readonly_inspection": "spreadsheet_readonly_inspection.json",
    "spreadsheet_report_plan": "spreadsheet_report_plan.json",
    "spreadsheet_structural_report_json": "spreadsheet_structural_report.json",
    "spreadsheet_structural_report_markdown": "spreadsheet_structural_report.md",
    "artifact_index": "artifact_index.json",
    "artifact_index_manifest": "artifact_index_manifest.json",
    "final_job_manifest": "final_job_manifest.json",
    "job_summary": "job_summary.json",
    "human_next_steps": "human_next_steps.md",
}

_REQUIRED_BOUNDARIES = {
    "no_runtime_authority",
    "no_execution_capability",
    "no_external_tool_control",
    "no_network",
    "no_api_calls",
    "no_subprocess",
    "no_adapter_implementation",
    "no_input_file_mutation",
    "no_input_content_copy",
    "no_raw_cell_value_copy",
    "no_spreadsheet_output_write",
    "no_destructive_actions",
}

_SPREADSHEET_OUTPUT_SUFFIXES = {
    ".xls",
    ".xlsm",
    ".xlsx",
}

_BOUNDARIES = {
    "local_only": True,
    "no_runtime_authority": True,
    "no_execution_capability": True,
    "no_external_tool_control": True,
    "no_network": True,
    "no_api_calls": True,
    "no_subprocess": True,
    "no_adapter_implementation": True,
    "no_input_file_mutation": True,
    "no_input_content_copy": True,
    "no_raw_cell_value_copy": True,
    "no_spreadsheet_output_write": True,
    "no_destructive_actions": True,
}


@dataclass(frozen=True)
class JobPackageValidationResult:
    job_dir: Path
    output_validation_path: Path
    complete: bool
    missing_artifacts: list[str]
    malformed_artifacts: list[str]
    artifact_hashes: dict[str, str]
    boundaries_verified: bool
    final_manifest_complete: bool
    artifact_index_manifest_verified: bool
    raw_sentinel_leakage_detected: bool
    spreadsheet_output_files: list[str]


def build_job_package_validation(
    job_dir: Path,
    output_validation_path: Path | None = None,
    *,
    raw_sentinel_values: list[str] | None = None,
) -> JobPackageValidationResult:
    job_path = Path(job_dir)
    validation_path = (
        job_path / "job_package_validation.json"
        if output_validation_path is None
        else Path(output_validation_path)
    )
    _validate_inputs(job_path, validation_path)

    missing_artifacts = _missing_required_artifacts(job_path)
    malformed_artifacts = _malformed_json_artifacts(job_path)
    artifact_hashes = _artifact_hashes(job_path)
    final_manifest = _read_json_object(job_path / "final_job_manifest.json")
    job_summary = _read_json_object(job_path / "job_summary.json")
    final_manifest_complete = _final_manifest_complete(final_manifest)
    final_manifest_presence_verified = _final_manifest_presence_verified(
        final_manifest,
    )
    artifact_index_manifest_verified = _artifact_index_manifest_verified(job_path)
    boundary_failures = _boundary_failures(final_manifest, job_summary)
    spreadsheet_output_files = _spreadsheet_output_files(job_path)
    raw_sentinel_leakage_detected = _raw_sentinel_leakage_detected(
        job_path,
        raw_sentinel_values or [],
        validation_path.name,
    )
    boundaries_verified = not boundary_failures
    complete = (
        not missing_artifacts
        and not malformed_artifacts
        and final_manifest_complete
        and final_manifest_presence_verified
        and artifact_index_manifest_verified
        and boundaries_verified
        and not spreadsheet_output_files
        and not raw_sentinel_leakage_detected
    )

    payload = {
        "validation_type": _VALIDATION_TYPE,
        "authority": "non_authority",
        "execution_capability": "not_introduced",
        "job_dir": job_path.as_posix(),
        "complete": complete,
        "required_artifacts": list(_REQUIRED_JOB_FILES.values()),
        "missing_artifacts": missing_artifacts,
        "malformed_artifacts": malformed_artifacts,
        "artifact_hashes": artifact_hashes,
        "final_manifest_complete": final_manifest_complete,
        "final_manifest_presence_verified": final_manifest_presence_verified,
        "artifact_index_manifest_verified": artifact_index_manifest_verified,
        "boundaries_verified": boundaries_verified,
        "boundary_failures": boundary_failures,
        "raw_sentinel_leakage_detected": raw_sentinel_leakage_detected,
        "raw_cell_values_copied": False,
        "input_mutation_performed": False,
        "spreadsheet_output_files": spreadsheet_output_files,
        "spreadsheet_output_written": bool(spreadsheet_output_files),
        "boundaries": dict(_BOUNDARIES),
        "next_allowed_action": "human_review_only",
    }
    write_json_atomically(validation_path, payload)

    return JobPackageValidationResult(
        job_dir=job_path,
        output_validation_path=validation_path,
        complete=complete,
        missing_artifacts=missing_artifacts,
        malformed_artifacts=malformed_artifacts,
        artifact_hashes=artifact_hashes,
        boundaries_verified=boundaries_verified,
        final_manifest_complete=final_manifest_complete,
        artifact_index_manifest_verified=artifact_index_manifest_verified,
        raw_sentinel_leakage_detected=raw_sentinel_leakage_detected,
        spreadsheet_output_files=spreadsheet_output_files,
    )


def _validate_inputs(job_path, validation_path):
    if not job_path.exists():
        raise ValueError("job_dir is missing")
    if not job_path.is_dir():
        raise ValueError("job_dir is not a directory")
    parent = Path(validation_path).parent
    if not parent.exists() or not parent.is_dir():
        raise ValueError("output_validation_path parent is missing")


def _missing_required_artifacts(job_path):
    missing = [
        artifact_file
        for artifact_file in _REQUIRED_JOB_FILES.values()
        if not (job_path / artifact_file).exists()
    ]
    missing.sort()
    return missing


def _malformed_json_artifacts(job_path):
    malformed = []
    for artifact_file in _REQUIRED_JOB_FILES.values():
        if not artifact_file.endswith(".json"):
            continue
        artifact_path = job_path / artifact_file
        if artifact_path.exists() and _read_json_object(artifact_path) is None:
            malformed.append(artifact_file)
    malformed.sort()
    return malformed


def _artifact_hashes(job_path):
    hashes = {
        artifact_name: sha256_file(job_path / artifact_file)
        for artifact_name, artifact_file in _REQUIRED_JOB_FILES.items()
        if (job_path / artifact_file).exists()
        and (job_path / artifact_file).is_file()
    }
    return {
        artifact_name: hashes[artifact_name]
        for artifact_name in sorted(hashes)
    }


def _read_json_object(path):
    artifact_path = Path(path)
    if not artifact_path.exists():
        return None
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _final_manifest_complete(final_manifest):
    return (
        isinstance(final_manifest, dict)
        and final_manifest.get("complete") is True
        and final_manifest.get("missing_artifacts") == []
    )


def _final_manifest_presence_verified(final_manifest):
    if not isinstance(final_manifest, dict):
        return False
    artifact_presence = final_manifest.get("artifact_presence")
    if not isinstance(artifact_presence, dict):
        return False
    return all(
        artifact_presence.get(artifact_name) is True
        for artifact_name in _REQUIRED_JOB_FILES
    )


def _artifact_index_manifest_verified(job_path):
    index_path = job_path / "artifact_index.json"
    manifest_path = job_path / "artifact_index_manifest.json"
    manifest = _read_json_object(manifest_path)
    index = _read_json_object(index_path)
    if not isinstance(manifest, dict) or not isinstance(index, dict):
        return False
    if manifest.get("artifact_index_sha256") != sha256_file(index_path):
        return False
    entries = index.get("entries")
    if not isinstance(entries, list):
        return False
    return manifest.get("indexed_artifacts") == len(entries)


def _boundary_failures(final_manifest, job_summary):
    failures = []
    for source_name, payload in (
        ("final_job_manifest", final_manifest),
        ("job_summary", job_summary),
    ):
        boundaries = payload.get("boundaries") if isinstance(payload, dict) else None
        if not isinstance(boundaries, dict):
            failures.append(f"{source_name}:boundaries_missing")
            continue
        for boundary_name in sorted(_REQUIRED_BOUNDARIES):
            if boundaries.get(boundary_name) is not True:
                failures.append(f"{source_name}:{boundary_name}")
    return failures


def _spreadsheet_output_files(job_path):
    output_files = [
        path.name
        for path in job_path.iterdir()
        if path.is_file() and path.suffix.lower() in _SPREADSHEET_OUTPUT_SUFFIXES
    ]
    output_files.sort()
    return output_files


def _raw_sentinel_leakage_detected(job_path, raw_sentinel_values, validation_name):
    sentinels = [
        value
        for value in raw_sentinel_values
        if isinstance(value, str) and value
    ]
    if not sentinels:
        return False
    for path in sorted(job_path.iterdir(), key=lambda candidate: candidate.name):
        if not path.is_file() or path.name == validation_name:
            continue
        if _file_contains_any(path, sentinels):
            return True
    return False


def _file_contains_any(path, sentinels):
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    return any(sentinel in content for sentinel in sentinels)
