"""Static runtime tool admission register validation for Personal AI v2."""

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.adapters.adapter_contract import (
    AdapterAdmissionStatus,
    AdapterMode,
)

__all__ = [
    "RuntimeToolAdmissionValidationResult",
    "load_runtime_tool_admission_register",
    "validate_runtime_tool_admission_register",
    "validate_runtime_tool_admission_register_file",
]

_REGISTER_TYPE = "personal_ai_execution_os_v2_runtime_tool_admission_register"

_REQUIRED_ENTRY_FIELDS = (
    "project_id",
    "project_name",
    "repo_url",
    "capability_category",
    "primary_capability",
    "license",
    "source_trust_level",
    "local_execution_possible",
    "network_required",
    "filesystem_write_risk",
    "subprocess_risk",
    "credential_risk",
    "destructive_action_risk",
    "adapter_mode",
    "proposed_seos_adapter",
    "required_controls",
    "admission_status",
    "rejection_reason",
    "notes",
)

_CAPABILITY_CATEGORIES = {
    "agent_runtime_reference",
    "browser",
    "creative",
    "model_structured_output",
    "observability_evaluation",
    "orchestration",
    "validation_provenance",
    "xlsx_local_data",
}

_SOURCE_TRUST_LEVELS = {
    "established_project",
    "official_vendor",
    "reference_only",
    "standards_or_spec",
}

_RISK_LEVELS = {
    "none",
    "controlled",
    "possible",
    "required",
    "high",
}

_BASELINE_REQUIRED_CONTROLS = {
    "human_approval",
    "capability_token",
    "manifest",
    "evidence_capture",
    "quarantine",
    "output_hashing",
    "no_source_vendoring",
}

_FORBIDDEN_CONTROLS = {
    "direct_source_vendoring",
    "unrestricted_runtime",
    "unrestricted_network",
    "unrestricted_subprocess",
    "unrestricted_external_tool_control",
}


@dataclass(frozen=True)
class RuntimeToolAdmissionValidationResult:
    register_path: Path | None
    entry_count: int
    accepted: bool
    failures: tuple[str, ...]
    admitted_projects: tuple[str, ...]
    deferred_projects: tuple[str, ...]


def load_runtime_tool_admission_register(register_path: Path) -> dict[str, object]:
    path = Path(register_path)
    if not path.exists():
        raise ValueError("runtime_tool_admission_register_path is missing")
    if not path.is_file():
        raise ValueError("runtime_tool_admission_register_path is not a file")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(
            "runtime_tool_admission_register must be JSON-compatible YAML"
        ) from error
    if not isinstance(payload, dict):
        raise ValueError("runtime_tool_admission_register must be an object")
    return payload


def validate_runtime_tool_admission_register_file(
    register_path: Path,
) -> RuntimeToolAdmissionValidationResult:
    path = Path(register_path)
    payload = load_runtime_tool_admission_register(path)
    result = validate_runtime_tool_admission_register(payload)
    return RuntimeToolAdmissionValidationResult(
        register_path=path,
        entry_count=result.entry_count,
        accepted=result.accepted,
        failures=result.failures,
        admitted_projects=result.admitted_projects,
        deferred_projects=result.deferred_projects,
    )


def validate_runtime_tool_admission_register(
    register: dict[str, object],
) -> RuntimeToolAdmissionValidationResult:
    failures = []
    if register.get("register_type") != _REGISTER_TYPE:
        failures.append("register_type_mismatch")
    entries = register.get("entries")
    if not isinstance(entries, list):
        failures.append("entries_missing_or_malformed")
        entries = []

    project_ids = []
    admitted_projects = []
    deferred_projects = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            failures.append(f"entry_{index}_malformed")
            continue
        failures.extend(_validate_entry(index, entry))
        project_id = str(entry.get("project_id", ""))
        if project_id:
            project_ids.append(project_id)
        if entry.get("admission_status") == AdapterAdmissionStatus.ADMITTED.value:
            admitted_projects.append(project_id)
        if entry.get("admission_status") in (
            AdapterAdmissionStatus.DEFERRED.value,
            AdapterAdmissionStatus.REFERENCE_ONLY.value,
        ):
            deferred_projects.append(project_id)

    if len(project_ids) != len(set(project_ids)):
        failures.append("project_id_duplicate")

    return RuntimeToolAdmissionValidationResult(
        register_path=None,
        entry_count=len(entries),
        accepted=not failures,
        failures=tuple(sorted(failures)),
        admitted_projects=tuple(sorted(admitted_projects)),
        deferred_projects=tuple(sorted(deferred_projects)),
    )


def _validate_entry(index, entry):
    failures = []
    missing_fields = [
        field_name
        for field_name in _REQUIRED_ENTRY_FIELDS
        if field_name not in entry
    ]
    if missing_fields:
        failures.append(f"entry_{index}_missing_required_fields")
        return failures

    _validate_string_field(failures, index, entry, "project_id")
    _validate_string_field(failures, index, entry, "project_name")
    _validate_string_field(failures, index, entry, "repo_url")
    _validate_string_field(failures, index, entry, "primary_capability")
    _validate_string_field(failures, index, entry, "license")
    _validate_string_field(failures, index, entry, "proposed_seos_adapter")
    _validate_string_field(failures, index, entry, "notes")

    if entry["capability_category"] not in _CAPABILITY_CATEGORIES:
        failures.append(f"entry_{index}_unknown_capability_category")
    if entry["source_trust_level"] not in _SOURCE_TRUST_LEVELS:
        failures.append(f"entry_{index}_unknown_source_trust_level")
    for field_name in (
        "filesystem_write_risk",
        "subprocess_risk",
        "credential_risk",
        "destructive_action_risk",
    ):
        if entry[field_name] not in _RISK_LEVELS:
            failures.append(f"entry_{index}_unknown_{field_name}")
    if entry["adapter_mode"] not in {mode.value for mode in AdapterMode}:
        failures.append(f"entry_{index}_unknown_adapter_mode")
    if entry["admission_status"] not in {
        status.value for status in AdapterAdmissionStatus
    }:
        failures.append(f"entry_{index}_unknown_admission_status")
    for field_name in ("local_execution_possible", "network_required"):
        if type(entry[field_name]) is not bool:
            failures.append(f"entry_{index}_{field_name}_not_boolean")

    controls = entry["required_controls"]
    if not isinstance(controls, list) or not all(
        isinstance(control, str) and control for control in controls
    ):
        failures.append(f"entry_{index}_required_controls_malformed")
        controls = []
    missing_controls = sorted(_BASELINE_REQUIRED_CONTROLS.difference(controls))
    if missing_controls:
        failures.append(f"entry_{index}_missing_required_controls")
    if _FORBIDDEN_CONTROLS.intersection(controls):
        failures.append(f"entry_{index}_forbidden_runtime_control")
    if "direct_source_vendoring" in controls:
        failures.append(f"entry_{index}_direct_source_vendoring_posture")

    admission_status = entry["admission_status"]
    if admission_status == AdapterAdmissionStatus.ADMITTED.value:
        failures.extend(_validate_admitted_entry(index, entry, controls))
    if admission_status in (
        AdapterAdmissionStatus.REJECTED.value,
        AdapterAdmissionStatus.DEFERRED.value,
    ) and not str(entry["rejection_reason"]).strip():
        failures.append(f"entry_{index}_missing_rejection_reason")
    return failures


def _validate_admitted_entry(index, entry, controls):
    failures = []
    if "future_admission_required" in controls:
        failures.append(f"entry_{index}_unrestricted_runtime_admission")
    if entry["adapter_mode"] in (
        AdapterMode.FUTURE_EXTERNAL.value,
        AdapterMode.POLICY_ONLY.value,
        AdapterMode.REFERENCE_ONLY.value,
    ):
        failures.append(f"entry_{index}_unrestricted_runtime_admission")
    if entry["network_required"]:
        failures.append(f"entry_{index}_network_required_executable_admission")
    if entry["destructive_action_risk"] != "none":
        failures.append(f"entry_{index}_destructive_risk_executable_admission")
    if entry["credential_risk"] in ("required", "possible"):
        failures.append(f"entry_{index}_credential_risk_executable_admission")
    return failures


def _validate_string_field(failures, index, entry, field_name):
    if not isinstance(entry[field_name], str) or not entry[field_name].strip():
        failures.append(f"entry_{index}_{field_name}_missing")
