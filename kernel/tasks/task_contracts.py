"""Operator task envelope contracts for V12."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
import copy

from kernel.security.secret_scanner import CoreSecretScanner

from .run_id import digest_payload
from .task_manifest import validate_task_manifest

__all__ = ["OperatorTaskIntakeResult", "create_operator_task_envelope"]

_ALLOWED_DESCRIPTOR_TYPES = frozenset({"text", "file", "repo"})
_FORBIDDEN_KEYS = frozenset(
    {
        "env",
        "env_value",
        "raw_input",
        "raw_prompt",
        "raw_provider_response",
        "raw_response",
        "secret",
        "secret_value",
    }
)


@dataclass(frozen=True)
class OperatorTaskIntakeResult:
    accepted: bool
    envelope: dict[str, object]
    failures: tuple[str, ...]


def create_operator_task_envelope(payload: Mapping[str, object]) -> OperatorTaskIntakeResult:
    if not isinstance(payload, Mapping):
        return OperatorTaskIntakeResult(False, {}, ("task_payload_must_be_mapping",))

    source_descriptor = payload.get("descriptor")
    if not isinstance(source_descriptor, Mapping):
        return OperatorTaskIntakeResult(False, {}, ("descriptor_required",))
    descriptor = copy.deepcopy(dict(source_descriptor))
    failures = _validate_descriptor(descriptor)
    if payload.get("persist_raw_input") is True:
        failures.append("raw_input_persistence_forbidden")

    manifest_payload = {
        "objective": payload.get("objective"),
        "requested_capabilities": copy.deepcopy(payload.get("requested_capabilities")),
        "classification": payload.get("classification"),
        "policy_version": payload.get("policy_version"),
        "code_version": payload.get("code_version"),
        "input_digest": digest_payload(descriptor),
        "provider_bound": bool(payload.get("provider_bound")),
    }
    if isinstance(payload.get("task_id"), str) and payload.get("task_id"):
        manifest_payload["task_id"] = payload["task_id"]
    manifest_result = validate_task_manifest(manifest_payload)
    failures.extend(manifest_result.failures)

    scanner = CoreSecretScanner()
    scan_result = scanner.scan_text(digest_payload({"descriptor": descriptor, "manifest": manifest_result.manifest}))
    if not scan_result.clean:
        failures.append("leak_prevention_gate_failed")

    if failures:
        return OperatorTaskIntakeResult(False, {}, tuple(sorted(set(failures))))

    envelope = {
        "task_id": manifest_result.manifest["task_id"],
        "descriptor_type": descriptor["descriptor_type"],
        "descriptor_digest": manifest_payload["input_digest"],
        "task_manifest": manifest_result.manifest,
        "raw_input_persisted": False,
        "network_accessed": False,
        "secret_value_read": False,
        "ai_provider_call_performed": False,
        "sqlite_mutation_performed": False,
        "production_autonomy_enabled": False,
    }
    return OperatorTaskIntakeResult(True, envelope, ())


def _validate_descriptor(descriptor: Mapping[str, object]) -> list[str]:
    failures: list[str] = []
    descriptor_type = descriptor.get("descriptor_type")
    if descriptor_type not in _ALLOWED_DESCRIPTOR_TYPES:
        failures.append("descriptor_type_invalid")
    if _contains_forbidden_key(descriptor):
        failures.append("raw_or_secret_descriptor_field_forbidden")
    if descriptor_type == "text" and not isinstance(descriptor.get("content_digest"), str):
        failures.append("text_descriptor_digest_required")
    if descriptor_type == "file" and not isinstance(descriptor.get("path_ref"), str):
        failures.append("file_descriptor_path_ref_required")
    if descriptor_type == "repo" and not isinstance(descriptor.get("repo_ref"), str):
        failures.append("repo_descriptor_ref_required")
    return failures


def _contains_forbidden_key(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key) in _FORBIDDEN_KEYS:
                return True
            if _contains_forbidden_key(item):
                return True
    elif isinstance(value, list):
        return any(_contains_forbidden_key(item) for item in value)
    return False
