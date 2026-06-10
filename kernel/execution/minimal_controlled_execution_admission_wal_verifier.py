"""Admission, WAL, verifier, and replay evidence contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import hashlib
import json
from typing import Mapping, Sequence

from kernel.execution.minimal_controlled_execution_contract import (
    DEFERRED_COMMAND_IDS,
    INITIAL_COMMAND_REGISTRY,
    POLICY_VERSION,
    REGISTRY_VERSION,
    ExecutionPolicyDecision,
    ExecutionRequest,
    build_execution_request,
    command_registry_hash,
    decide_execution_request,
)

__all__ = [
    "EXECUTION_ADMISSION_RECORD_FIELDS",
    "EXECUTION_WAL_RECORD_FIELDS",
    "EXECUTION_WAL_RECORD_TYPES",
    "EXECUTION_VERIFIER_BINDING_FIELDS",
    "EXECUTION_REPLAY_EVIDENCE_MANIFEST_FIELDS",
    "EXECUTION_REPLAY_MANIFEST_STATUSES",
    "ExecutionAdmissionRecord",
    "ExecutionWalRecord",
    "ExecutionVerifierBinding",
    "ExecutionReplayEvidenceManifest",
    "build_execution_admission_record",
    "build_execution_wal_record",
    "build_execution_verifier_binding",
    "build_execution_replay_evidence_manifest",
    "admission_record_hash",
    "wal_record_hash",
    "verifier_binding_hash",
    "replay_manifest_hash",
]

EXECUTION_ADMISSION_RECORD_FIELDS = (
    "admission_record_id",
    "request_id",
    "task_id",
    "run_id",
    "command_id",
    "request_hash",
    "registry_entry_hash",
    "registry_hash",
    "policy_version",
    "registry_version",
    "accepted",
    "rejection_reasons",
    "approval_token_id",
    "execution_performed",
    "created_at",
    "admission_record_hash",
)

EXECUTION_WAL_RECORD_FIELDS = (
    "wal_record_id",
    "wal_record_type",
    "task_id",
    "run_id",
    "command_id",
    "request_hash",
    "decision_hash",
    "admission_record_hash",
    "failure_bundle_hash",
    "verifier_input_hash",
    "registry_entry_hash",
    "registry_hash",
    "execution_performed",
    "sequence",
    "created_at",
    "wal_record_hash",
)

EXECUTION_WAL_RECORD_TYPES = frozenset(
    {
        "EXECUTION_ADMISSION_ACCEPTED",
        "EXECUTION_ADMISSION_REJECTED",
        "EXECUTION_FAILURE_BUNDLE_CREATED",
        "EXECUTION_VERIFIER_INPUT_CREATED",
        "EXECUTION_NOT_ATTEMPTED",
    }
)

EXECUTION_VERIFIER_BINDING_FIELDS = (
    "verifier_binding_id",
    "request_hash",
    "decision_hash",
    "admission_record_hash",
    "receipt_hash",
    "failure_bundle_hash",
    "pre_snapshot_hash",
    "post_snapshot_hash",
    "registry_entry_hash",
    "registry_hash",
    "execution_performed",
    "verifier_policy_version",
    "verifier_binding_hash",
)

EXECUTION_REPLAY_EVIDENCE_MANIFEST_FIELDS = (
    "replay_manifest_id",
    "task_id",
    "run_id",
    "command_id",
    "request_hash",
    "decision_hash",
    "admission_record_hash",
    "wal_record_hashes",
    "failure_bundle_hash",
    "verifier_input_hash",
    "verifier_binding_hash",
    "registry_hash",
    "execution_performed",
    "manifest_status",
    "created_at",
    "replay_manifest_hash",
)

EXECUTION_REPLAY_MANIFEST_STATUSES = frozenset(
    {
        "CONTRACT_ONLY_ACCEPTED_NOT_EXECUTED",
        "CONTRACT_ONLY_REJECTED_NOT_EXECUTED",
        "CONTRACT_ONLY_FAILURE_NOT_EXECUTED",
    }
)

_RAW_EVIDENCE_FIELDS = frozenset(
    {
        "argv",
        "command",
        "command_line",
        "raw_stderr",
        "raw_stdout",
        "stderr",
        "stderr_text",
        "stdout",
        "stdout_text",
        "text_output",
    }
)


class _ContractDictMixin:
    def as_dict(self) -> dict[str, object]:
        return _contract_dict(self)


@dataclass(frozen=True)
class ExecutionAdmissionRecord(_ContractDictMixin):
    admission_record_id: str
    request_id: str
    task_id: str
    run_id: str
    command_id: str
    request_hash: str
    registry_entry_hash: str
    registry_hash: str
    policy_version: str
    registry_version: str
    accepted: bool
    rejection_reasons: tuple[str, ...]
    approval_token_id: str
    execution_performed: bool
    created_at: str
    admission_record_hash: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "rejection_reasons",
            _string_tuple(self.rejection_reasons, "rejection_reasons"),
        )
        _require_strings(
            self.as_dict(),
            (
                "admission_record_id",
                "request_id",
                "task_id",
                "run_id",
                "command_id",
                "request_hash",
                "registry_hash",
                "policy_version",
                "registry_version",
                "created_at",
            ),
        )
        if not isinstance(self.registry_entry_hash, str):
            raise ValueError("registry_entry_hash_must_be_string")
        if not isinstance(self.approval_token_id, str):
            raise ValueError("approval_token_id_must_be_string")
        _require_bool(self.accepted, "accepted")
        _require_bool(self.execution_performed, "execution_performed")
        if self.execution_performed:
            raise ValueError("execution_performed_must_be_false_in_contract_only_v1")
        if self.policy_version != POLICY_VERSION:
            raise ValueError("policy_version_mismatch")
        if self.registry_version != REGISTRY_VERSION:
            raise ValueError("registry_version_mismatch")
        if self.accepted and self.rejection_reasons:
            raise ValueError("accepted_admission_cannot_have_rejection_reasons")
        if not self.accepted and not self.rejection_reasons:
            raise ValueError("rejected_admission_requires_rejection_reasons")
        if self.accepted and not self.registry_entry_hash:
            raise ValueError("accepted_admission_requires_registry_entry_hash")
        if self.command_id in DEFERRED_COMMAND_IDS and self.accepted:
            raise ValueError("deferred_command_id_cannot_be_accepted")
        if self.command_id not in INITIAL_COMMAND_REGISTRY and self.accepted:
            raise ValueError("unknown_command_id_cannot_be_accepted")
        _install_or_verify_hash(self, "admission_record_hash", admission_record_hash)


@dataclass(frozen=True)
class ExecutionWalRecord(_ContractDictMixin):
    wal_record_id: str
    wal_record_type: str
    task_id: str
    run_id: str
    command_id: str
    request_hash: str
    decision_hash: str
    admission_record_hash: str
    failure_bundle_hash: str
    verifier_input_hash: str
    registry_entry_hash: str
    registry_hash: str
    execution_performed: bool
    sequence: int
    created_at: str
    wal_record_hash: str = ""

    def __post_init__(self) -> None:
        _require_strings(
            self.as_dict(),
            (
                "wal_record_id",
                "wal_record_type",
                "task_id",
                "run_id",
                "command_id",
                "request_hash",
                "registry_hash",
                "created_at",
            ),
        )
        for field_name in (
            "decision_hash",
            "admission_record_hash",
            "failure_bundle_hash",
            "verifier_input_hash",
            "registry_entry_hash",
        ):
            if not isinstance(getattr(self, field_name), str):
                raise ValueError(field_name + "_must_be_string")
        if self.wal_record_type not in EXECUTION_WAL_RECORD_TYPES:
            raise ValueError("wal_record_type_invalid")
        _require_bool(self.execution_performed, "execution_performed")
        if self.execution_performed:
            raise ValueError("execution_performed_must_be_false_in_contract_only_v1")
        _require_positive_int(self.sequence, "sequence")
        _install_or_verify_hash(self, "wal_record_hash", wal_record_hash)


@dataclass(frozen=True)
class ExecutionVerifierBinding(_ContractDictMixin):
    verifier_binding_id: str
    request_hash: str
    decision_hash: str
    admission_record_hash: str
    receipt_hash: str
    failure_bundle_hash: str
    pre_snapshot_hash: str
    post_snapshot_hash: str
    registry_entry_hash: str
    registry_hash: str
    execution_performed: bool
    verifier_policy_version: str
    verifier_binding_hash: str = ""

    def __post_init__(self) -> None:
        _require_strings(
            self.as_dict(),
            (
                "verifier_binding_id",
                "request_hash",
                "decision_hash",
                "admission_record_hash",
                "pre_snapshot_hash",
                "post_snapshot_hash",
                "registry_hash",
                "verifier_policy_version",
            ),
        )
        for field_name in ("receipt_hash", "failure_bundle_hash", "registry_entry_hash"):
            if not isinstance(getattr(self, field_name), str):
                raise ValueError(field_name + "_must_be_string")
        if not self.receipt_hash and not self.failure_bundle_hash:
            raise ValueError("receipt_or_failure_bundle_hash_required")
        _require_bool(self.execution_performed, "execution_performed")
        if self.execution_performed:
            raise ValueError("execution_performed_must_be_false_in_contract_only_v1")
        if self.verifier_policy_version != POLICY_VERSION:
            raise ValueError("verifier_policy_version_mismatch")
        _install_or_verify_hash(self, "verifier_binding_hash", verifier_binding_hash)


@dataclass(frozen=True)
class ExecutionReplayEvidenceManifest(_ContractDictMixin):
    replay_manifest_id: str
    task_id: str
    run_id: str
    command_id: str
    request_hash: str
    decision_hash: str
    admission_record_hash: str
    wal_record_hashes: tuple[str, ...]
    failure_bundle_hash: str
    verifier_input_hash: str
    verifier_binding_hash: str
    registry_hash: str
    execution_performed: bool
    manifest_status: str
    created_at: str
    replay_manifest_hash: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "wal_record_hashes",
            _string_tuple(self.wal_record_hashes, "wal_record_hashes"),
        )
        _require_strings(
            self.as_dict(),
            (
                "replay_manifest_id",
                "task_id",
                "run_id",
                "command_id",
                "request_hash",
                "decision_hash",
                "admission_record_hash",
                "registry_hash",
                "manifest_status",
                "created_at",
            ),
        )
        for field_name in (
            "failure_bundle_hash",
            "verifier_input_hash",
            "verifier_binding_hash",
        ):
            if not isinstance(getattr(self, field_name), str):
                raise ValueError(field_name + "_must_be_string")
        if not self.wal_record_hashes:
            raise ValueError("wal_record_hashes_required")
        if self.manifest_status not in EXECUTION_REPLAY_MANIFEST_STATUSES:
            raise ValueError("manifest_status_invalid")
        _require_bool(self.execution_performed, "execution_performed")
        if self.execution_performed:
            raise ValueError("execution_performed_must_be_false_in_contract_only_v1")
        _install_or_verify_hash(self, "replay_manifest_hash", replay_manifest_hash)


def build_execution_admission_record(
    request: ExecutionRequest | Mapping[str, object],
    *,
    admission_record_id: str,
    decision_id: str,
    created_at: str,
    decided_at: str | None = None,
    registry: Mapping[str, object] | None = None,
) -> ExecutionAdmissionRecord:
    normalized_request = (
        request if isinstance(request, ExecutionRequest) else build_execution_request(request)
    )
    command_registry = INITIAL_COMMAND_REGISTRY if registry is None else registry
    decision = decide_execution_request(
        normalized_request,
        command_registry,  # type: ignore[arg-type]
        decision_id=decision_id,
        decided_at=created_at if decided_at is None else decided_at,
    )
    _require_decision_for_request(normalized_request, decision)
    return ExecutionAdmissionRecord(
        admission_record_id=admission_record_id,
        request_id=normalized_request.request_id,
        task_id=normalized_request.task_id,
        run_id=normalized_request.run_id,
        command_id=normalized_request.command_id,
        request_hash=normalized_request.request_hash,
        registry_entry_hash=decision.registry_entry_hash,
        registry_hash=command_registry_hash(command_registry),  # type: ignore[arg-type]
        policy_version=POLICY_VERSION,
        registry_version=REGISTRY_VERSION,
        accepted=decision.accepted,
        rejection_reasons=decision.rejection_reasons,
        approval_token_id=normalized_request.approval_token_id,
        execution_performed=False,
        created_at=created_at,
    )


def build_execution_wal_record(payload: Mapping[str, object]) -> ExecutionWalRecord:
    data = _validated_payload(payload, ExecutionWalRecord, "wal_record")
    return ExecutionWalRecord(
        wal_record_id=_mapping_string(data, "wal_record_id"),
        wal_record_type=_mapping_string(data, "wal_record_type"),
        task_id=_mapping_string(data, "task_id"),
        run_id=_mapping_string(data, "run_id"),
        command_id=_mapping_string(data, "command_id"),
        request_hash=_mapping_string(data, "request_hash"),
        decision_hash=_mapping_string(data, "decision_hash", allow_empty=True),
        admission_record_hash=_mapping_string(
            data,
            "admission_record_hash",
            allow_empty=True,
        ),
        failure_bundle_hash=_mapping_string(data, "failure_bundle_hash", allow_empty=True),
        verifier_input_hash=_mapping_string(data, "verifier_input_hash", allow_empty=True),
        registry_entry_hash=_mapping_string(data, "registry_entry_hash", allow_empty=True),
        registry_hash=_mapping_string(data, "registry_hash"),
        execution_performed=_mapping_bool(data, "execution_performed"),
        sequence=_mapping_int(data, "sequence"),
        created_at=_mapping_string(data, "created_at"),
        wal_record_hash=_mapping_string(data, "wal_record_hash", allow_empty=True)
        if "wal_record_hash" in data
        else "",
    )


def build_execution_verifier_binding(
    payload: Mapping[str, object],
) -> ExecutionVerifierBinding:
    data = _validated_payload(payload, ExecutionVerifierBinding, "verifier_binding")
    return ExecutionVerifierBinding(
        verifier_binding_id=_mapping_string(data, "verifier_binding_id"),
        request_hash=_mapping_string(data, "request_hash"),
        decision_hash=_mapping_string(data, "decision_hash"),
        admission_record_hash=_mapping_string(data, "admission_record_hash"),
        receipt_hash=_mapping_string(data, "receipt_hash", allow_empty=True),
        failure_bundle_hash=_mapping_string(data, "failure_bundle_hash", allow_empty=True),
        pre_snapshot_hash=_mapping_string(data, "pre_snapshot_hash"),
        post_snapshot_hash=_mapping_string(data, "post_snapshot_hash"),
        registry_entry_hash=_mapping_string(data, "registry_entry_hash", allow_empty=True),
        registry_hash=_mapping_string(data, "registry_hash"),
        execution_performed=_mapping_bool(data, "execution_performed"),
        verifier_policy_version=_mapping_string(data, "verifier_policy_version"),
        verifier_binding_hash=_mapping_string(
            data,
            "verifier_binding_hash",
            allow_empty=True,
        )
        if "verifier_binding_hash" in data
        else "",
    )


def build_execution_replay_evidence_manifest(
    payload: Mapping[str, object],
) -> ExecutionReplayEvidenceManifest:
    data = _validated_payload(payload, ExecutionReplayEvidenceManifest, "replay_manifest")
    return ExecutionReplayEvidenceManifest(
        replay_manifest_id=_mapping_string(data, "replay_manifest_id"),
        task_id=_mapping_string(data, "task_id"),
        run_id=_mapping_string(data, "run_id"),
        command_id=_mapping_string(data, "command_id"),
        request_hash=_mapping_string(data, "request_hash"),
        decision_hash=_mapping_string(data, "decision_hash"),
        admission_record_hash=_mapping_string(data, "admission_record_hash"),
        wal_record_hashes=_mapping_string_tuple(data, "wal_record_hashes"),
        failure_bundle_hash=_mapping_string(data, "failure_bundle_hash", allow_empty=True),
        verifier_input_hash=_mapping_string(data, "verifier_input_hash", allow_empty=True),
        verifier_binding_hash=_mapping_string(
            data,
            "verifier_binding_hash",
            allow_empty=True,
        ),
        registry_hash=_mapping_string(data, "registry_hash"),
        execution_performed=_mapping_bool(data, "execution_performed"),
        manifest_status=_mapping_string(data, "manifest_status"),
        created_at=_mapping_string(data, "created_at"),
        replay_manifest_hash=_mapping_string(
            data,
            "replay_manifest_hash",
            allow_empty=True,
        )
        if "replay_manifest_hash" in data
        else "",
    )


def admission_record_hash(record: ExecutionAdmissionRecord | Mapping[str, object]) -> str:
    return _hash_contract(record, "admission_record_hash")


def wal_record_hash(record: ExecutionWalRecord | Mapping[str, object]) -> str:
    return _hash_contract(record, "wal_record_hash")


def verifier_binding_hash(binding: ExecutionVerifierBinding | Mapping[str, object]) -> str:
    return _hash_contract(binding, "verifier_binding_hash")


def replay_manifest_hash(
    manifest: ExecutionReplayEvidenceManifest | Mapping[str, object],
) -> str:
    return _hash_contract(manifest, "replay_manifest_hash")


def _require_decision_for_request(
    request: ExecutionRequest,
    decision: ExecutionPolicyDecision,
) -> None:
    if decision.request_id != request.request_id:
        raise ValueError("decision_request_id_mismatch")
    if decision.command_id != request.command_id:
        raise ValueError("decision_command_id_mismatch")
    if decision.execution_performed:
        raise ValueError("execution_performed_must_be_false_in_contract_only_v1")


def _validated_payload(
    payload: Mapping[str, object],
    contract_type: type[object],
    payload_name: str,
) -> dict[str, object]:
    data = dict(payload)
    raw_fields = sorted(_RAW_EVIDENCE_FIELDS.intersection(data))
    if raw_fields:
        raise ValueError(payload_name + "_raw_evidence_field_forbidden:" + ",".join(raw_fields))
    allowed = {field.name for field in fields(contract_type)}
    extra = sorted(set(data) - allowed)
    if extra:
        raise ValueError(payload_name + "_field_not_allowed:" + ",".join(extra))
    missing = sorted(field for field in allowed if not field.endswith("_hash") and field not in data)
    if missing:
        raise ValueError(payload_name + "_field_required:" + ",".join(missing))
    return data


def _install_or_verify_hash(target: object, field_name: str, hash_fn: object) -> None:
    expected = hash_fn(target)  # type: ignore[operator]
    current = getattr(target, field_name)
    if not current:
        object.__setattr__(target, field_name, expected)
        return
    if current != expected:
        raise ValueError(field_name + "_mismatch")


def _hash_contract(value: object, hash_field: str) -> str:
    data = _contract_dict(value)
    data.pop(hash_field, None)
    return "sha256:" + _sha256_hex(_canonical_json(data))


def _contract_dict(value: object) -> dict[str, object]:
    if hasattr(value, "__dataclass_fields__"):
        data = asdict(value)
    elif isinstance(value, Mapping):
        data = dict(value)
    else:
        raise TypeError("contract value must be a dataclass or mapping")
    return _json_ready(data)


def _json_ready(value: object) -> object:
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    return value


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _require_strings(payload: Mapping[str, object], field_names: Sequence[str]) -> None:
    for field_name in field_names:
        value = payload.get(field_name)
        if not isinstance(value, str) or not value:
            raise ValueError(field_name + "_required")


def _require_bool(value: object, field_name: str) -> None:
    if not isinstance(value, bool):
        raise ValueError(field_name + "_must_be_bool")


def _require_int(value: object, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(field_name + "_must_be_int")


def _require_positive_int(value: object, field_name: str) -> None:
    _require_int(value, field_name)
    if value <= 0:
        raise ValueError(field_name + "_must_be_positive")


def _string_tuple(values: Sequence[str], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)) or isinstance(values, (str, bytes)):
        raise ValueError(field_name + "_must_be_ordered_string_sequence")
    normalized = tuple(str(value) for value in values)
    if any(not value for value in normalized):
        raise ValueError(field_name + "_cannot_contain_empty_string")
    return normalized


def _mapping_string(
    payload: Mapping[str, object],
    field_name: str,
    *,
    allow_empty: bool = False,
) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str):
        raise ValueError(field_name + "_must_be_string")
    if not allow_empty and not value:
        raise ValueError(field_name + "_required")
    return value


def _mapping_int(payload: Mapping[str, object], field_name: str) -> int:
    value = payload.get(field_name)
    _require_int(value, field_name)
    return value


def _mapping_bool(payload: Mapping[str, object], field_name: str) -> bool:
    value = payload.get(field_name)
    _require_bool(value, field_name)
    return value


def _mapping_string_tuple(
    payload: Mapping[str, object],
    field_name: str,
) -> tuple[str, ...]:
    value = payload.get(field_name)
    if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
        raise ValueError(field_name + "_must_be_ordered_string_sequence")
    return _string_tuple(value, field_name)
