"""Fail-closed validation for execution permits."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any

from execution_plane.permits.builder import EXECUTION_PERMIT_SCHEMA_VERSION, parse_utc
from execution_plane.permits.digest import compute_permit_digest

SUPPORTED_ADAPTER_ACTIONS = {
    "fake_dcc": frozenset({"smoke_generate_file"}),
    "houdini_hython": frozenset({"houdini_generate_geometry_cache"}),
}

REQUIRED_FIELDS = (
    "schema_version",
    "permit_id",
    "task_id",
    "operator_approval_id",
    "created_at",
    "expires_at",
    "allowed_adapter",
    "allowed_action",
    "allowed_input_roots",
    "allowed_output_root",
    "write_scope",
    "network_allowed",
    "destructive_action_allowed",
    "max_runtime_seconds",
    "max_output_bytes",
    "max_files",
    "required_outputs",
    "evidence_required",
    "policy_version",
    "permit_digest",
)


class ExecutionPermitValidationError(ValueError):
    """Raised when a permit fails closed."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("execution permit validation failed: " + ", ".join(errors))


def validate_execution_permit(
    permit: Mapping[str, Any],
    *,
    now: datetime | None = None,
    expected_adapter: str | None = None,
    expected_action: str | None = None,
) -> dict[str, Any]:
    errors = list(validate_execution_permit_errors(
        permit,
        now=now,
        expected_adapter=expected_adapter,
        expected_action=expected_action,
    ))
    if errors:
        raise ExecutionPermitValidationError(errors)
    return dict(permit)


def validate_execution_permit_errors(
    permit: Mapping[str, Any],
    *,
    now: datetime | None = None,
    expected_adapter: str | None = None,
    expected_action: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(permit, Mapping):
        return ["permit_must_be_mapping"]

    for field in REQUIRED_FIELDS:
        if field not in permit:
            errors.append(f"missing_required_field:{field}")
    if errors:
        return errors

    _require_string(permit, "schema_version", errors)
    _require_string(permit, "permit_id", errors)
    _require_string(permit, "task_id", errors)
    _require_string(permit, "operator_approval_id", errors)
    _require_string(permit, "created_at", errors)
    _require_string(permit, "expires_at", errors)
    _require_string(permit, "allowed_adapter", errors)
    _require_string(permit, "allowed_action", errors)
    _require_string(permit, "allowed_output_root", errors)
    _require_string(permit, "write_scope", errors)
    _require_string(permit, "policy_version", errors)
    _require_string(permit, "permit_digest", errors)
    _require_bool(permit, "network_allowed", errors)
    _require_bool(permit, "destructive_action_allowed", errors)
    _require_bool(permit, "evidence_required", errors)
    _require_positive_int(permit, "max_runtime_seconds", errors)
    _require_positive_int(permit, "max_output_bytes", errors)
    _require_positive_int(permit, "max_files", errors)

    if permit.get("schema_version") != EXECUTION_PERMIT_SCHEMA_VERSION:
        errors.append("schema_version_not_supported")
    if not str(permit.get("operator_approval_id", "")).strip():
        errors.append("operator_approval_id_required")
    adapter = str(permit.get("allowed_adapter", ""))
    action = str(permit.get("allowed_action", ""))
    if adapter not in SUPPORTED_ADAPTER_ACTIONS:
        errors.append("unsupported_adapter")
    elif action not in SUPPORTED_ADAPTER_ACTIONS[adapter]:
        errors.append("unsupported_action_for_adapter")
    if expected_adapter is not None and adapter != expected_adapter:
        errors.append("adapter_mismatch")
    if expected_action is not None and action != expected_action:
        errors.append("action_mismatch")
    if permit.get("write_scope") != "single_output_directory":
        errors.append("unsupported_write_scope")
    if permit.get("network_allowed") is not False:
        errors.append("network_must_default_false")
    if permit.get("destructive_action_allowed") is not False:
        errors.append("destructive_action_must_default_false")
    if permit.get("evidence_required") is not True:
        errors.append("evidence_required_must_be_true")

    input_roots = permit.get("allowed_input_roots")
    if not isinstance(input_roots, list):
        errors.append("allowed_input_roots_must_be_list")
    else:
        for root in input_roots:
            if not isinstance(root, str) or not root.strip():
                errors.append("allowed_input_roots_must_be_strings")
            elif _has_path_traversal(root):
                errors.append("allowed_input_root_path_traversal")

    output_root = permit.get("allowed_output_root")
    if isinstance(output_root, str) and _has_path_traversal(output_root):
        errors.append("allowed_output_root_path_traversal")

    required_outputs = permit.get("required_outputs")
    if not isinstance(required_outputs, list) or not required_outputs:
        errors.append("required_outputs_must_be_nonempty_list")
    else:
        for item in required_outputs:
            if not isinstance(item, Mapping):
                errors.append("required_output_must_be_mapping")
                continue
            if not isinstance(item.get("kind"), str) or not item.get("kind"):
                errors.append("required_output_kind_required")
            path = item.get("path")
            if not isinstance(path, str) or not path:
                errors.append("required_output_path_required")
            elif _has_path_traversal(path) or PurePosixPath(path).is_absolute():
                errors.append("required_output_path_must_be_relative")

    try:
        expires_at = parse_utc(str(permit.get("expires_at")))
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        if expires_at <= current.astimezone(timezone.utc):
            errors.append("permit_expired")
    except ValueError:
        errors.append("expires_at_invalid")
    try:
        parse_utc(str(permit.get("created_at")))
    except ValueError:
        errors.append("created_at_invalid")

    if permit.get("permit_digest") != compute_permit_digest(permit):
        errors.append("permit_digest_mismatch")
    return errors


def _require_string(permit: Mapping[str, Any], field: str, errors: list[str]) -> None:
    value = permit.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field}_must_be_nonempty_string")


def _require_bool(permit: Mapping[str, Any], field: str, errors: list[str]) -> None:
    if not isinstance(permit.get(field), bool):
        errors.append(f"{field}_must_be_bool")


def _require_positive_int(permit: Mapping[str, Any], field: str, errors: list[str]) -> None:
    value = permit.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        errors.append(f"{field}_must_be_positive_int")


def _has_path_traversal(value: str) -> bool:
    normalized = value.replace("\\", "/")
    return ".." in PurePosixPath(normalized).parts

