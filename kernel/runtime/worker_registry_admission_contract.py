"""Worker registry admission contract v1.

This module defines a digest-only worker admission boundary. It proves that a
worker declaration and task request are eligible for queue admission, but it
does not dispatch, execute, start background work, call providers, open browsers, or read
environment state. Timestamps are metadata and excluded from content hashes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_bool, strict_digest, strict_nonempty_string

__all__ = [
    "WorkerAdmissionDeclaration",
    "WorkerAdmissionRequest",
    "WorkerAdmissionReceipt",
    "WorkerRegistryAdmissionManifest",
    "build_worker_admission_declaration",
    "build_worker_admission_request",
    "admit_worker_request",
    "build_worker_registry_admission_manifest",
    "validate_worker_admission_declaration",
    "validate_worker_admission_request",
    "validate_worker_admission_receipt",
    "validate_worker_registry_admission_manifest",
]

_CONTRACT_VERSION = "worker-registry-admission-contract-v1"
_CODE_VERSION = "0.1.0"

_ALLOWED_WORKER_KINDS = frozenset(
    {
        "local_deterministic",
        "provider_stub",
        "review_only",
        "artifact_indexer",
    }
)
_ALLOWED_ADMISSION_STATES = frozenset(
    {
        "queue_admission_allowed",
        "human_approval_required",
        "policy_rejected",
    }
)
_FORBIDDEN_EXACT_KEYS = frozenset(
    {
        "argv",
        "body",
        "command",
        "content",
        "cwd",
        "env",
        "executable",
        "filesystem_path",
        "output",
        "path",
        "payload",
        "prompt",
        "stderr",
        "stdout",
        "text",
        "timeout",
        "value",
    }
)
_FORBIDDEN_KEY_FRAGMENTS = (
    "api_key",
    "browser",
    "credential",
    "dcc",
    "mcp",
    "network",
    "private_key",
    "provider_response",
    "raw",
    "secret",
)
_CONTROL_FLAG_KEYS = frozenset(
    {
        "browser_enabled",
        "dcc_enabled",
        "mcp_enabled",
        "network_enabled",
    }
)


@dataclass(frozen=True)
class WorkerAdmissionDeclaration:
    """Digest-only declaration for a worker that may be admitted to a queue."""

    worker_id: str
    worker_kind: str
    task_classes: tuple[str, ...]
    input_contract_hash: str
    output_contract_hash: str
    policy_hash: str
    capability_hashes: tuple[str, ...]
    evidence_requirement_hashes: tuple[str, ...]
    human_approval_required: bool
    live_execution_enabled: bool
    provider_calls_enabled: bool
    network_enabled: bool
    browser_enabled: bool
    dcc_enabled: bool
    mcp_enabled: bool
    contract_version: str = _CONTRACT_VERSION
    code_version: str = _CODE_VERSION
    declaration_hash: str = ""
    declared_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "browser_enabled": self.browser_enabled,
            "capability_hashes": self.capability_hashes,
            "code_version": self.code_version,
            "contract_version": self.contract_version,
            "dcc_enabled": self.dcc_enabled,
            "evidence_requirement_hashes": self.evidence_requirement_hashes,
            "human_approval_required": self.human_approval_required,
            "input_contract_hash": self.input_contract_hash,
            "live_execution_enabled": self.live_execution_enabled,
            "mcp_enabled": self.mcp_enabled,
            "network_enabled": self.network_enabled,
            "output_contract_hash": self.output_contract_hash,
            "policy_hash": self.policy_hash,
            "provider_calls_enabled": self.provider_calls_enabled,
            "task_classes": self.task_classes,
            "worker_id": self.worker_id,
            "worker_kind": self.worker_kind,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["declaration_hash"] = self.declaration_hash
        payload["declared_at"] = self.declared_at
        return payload


@dataclass(frozen=True)
class WorkerAdmissionRequest:
    """Digest-only request to admit a worker for a task/run."""

    admission_request_id: str
    worker_id: str
    task_id: str
    run_id: str
    requested_task_class: str
    queue_job_hash: str
    task_descriptor_hash: str
    idempotency_key_hash: str
    wal_head_hash: str
    artifact_manifest_hash: str
    approval_receipt_hash: str | None
    human_invoked: bool
    contract_version: str = _CONTRACT_VERSION
    code_version: str = _CODE_VERSION
    request_hash: str = ""
    requested_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "admission_request_id": self.admission_request_id,
            "approval_receipt_hash": self.approval_receipt_hash,
            "artifact_manifest_hash": self.artifact_manifest_hash,
            "code_version": self.code_version,
            "contract_version": self.contract_version,
            "human_invoked": self.human_invoked,
            "idempotency_key_hash": self.idempotency_key_hash,
            "queue_job_hash": self.queue_job_hash,
            "requested_task_class": self.requested_task_class,
            "run_id": self.run_id,
            "task_descriptor_hash": self.task_descriptor_hash,
            "task_id": self.task_id,
            "wal_head_hash": self.wal_head_hash,
            "worker_id": self.worker_id,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["request_hash"] = self.request_hash
        payload["requested_at"] = self.requested_at
        return payload


@dataclass(frozen=True)
class WorkerAdmissionReceipt:
    """Deterministic receipt for worker queue admission."""

    admission_request_hash: str
    worker_declaration_hash: str
    worker_id: str
    task_id: str
    run_id: str
    admitted: bool
    admission_state: str
    failure_reasons: tuple[str, ...]
    wal_record_hash: str
    contract_version: str = _CONTRACT_VERSION
    code_version: str = _CODE_VERSION
    receipt_hash: str = ""
    admitted_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "admission_request_hash": self.admission_request_hash,
            "admission_state": self.admission_state,
            "admitted": self.admitted,
            "code_version": self.code_version,
            "contract_version": self.contract_version,
            "failure_reasons": self.failure_reasons,
            "run_id": self.run_id,
            "task_id": self.task_id,
            "wal_record_hash": self.wal_record_hash,
            "worker_declaration_hash": self.worker_declaration_hash,
            "worker_id": self.worker_id,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["admitted_at"] = self.admitted_at
        payload["receipt_hash"] = self.receipt_hash
        return payload


@dataclass(frozen=True)
class WorkerRegistryAdmissionManifest:
    """Deterministic manifest for admitted worker declarations."""

    manifest_id: str
    registry_policy_hash: str
    wal_head_hash: str
    declaration_hashes: tuple[str, ...]
    admitted_worker_ids: tuple[str, ...]
    registry_root_hash: str
    contract_version: str = _CONTRACT_VERSION
    code_version: str = _CODE_VERSION
    manifest_hash: str = ""
    created_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "admitted_worker_ids": self.admitted_worker_ids,
            "code_version": self.code_version,
            "contract_version": self.contract_version,
            "declaration_hashes": self.declaration_hashes,
            "manifest_id": self.manifest_id,
            "registry_policy_hash": self.registry_policy_hash,
            "registry_root_hash": self.registry_root_hash,
            "wal_head_hash": self.wal_head_hash,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["created_at"] = self.created_at
        payload["manifest_hash"] = self.manifest_hash
        return payload


def build_worker_admission_declaration(
    payload: Mapping[str, Any],
    *,
    declared_at: str | None = None,
) -> WorkerAdmissionDeclaration:
    """Build a validated worker admission declaration."""

    _require_mapping(payload)
    _reject_forbidden_material(payload)

    worker_id = _string_field(payload, "worker_id")
    worker_kind = _string_field(payload, "worker_kind")
    task_classes = _string_tuple(payload, "task_classes")
    capability_hashes = _digest_tuple(payload, "capability_hashes")
    evidence_requirement_hashes = _digest_tuple(payload, "evidence_requirement_hashes")
    human_approval_required = _bool_field(payload, "human_approval_required")
    live_execution_enabled = _bool_field(payload, "live_execution_enabled")
    provider_calls_enabled = _bool_field(payload, "provider_calls_enabled")
    network_enabled = _bool_field(payload, "network_enabled")
    browser_enabled = _bool_field(payload, "browser_enabled")
    dcc_enabled = _bool_field(payload, "dcc_enabled")
    mcp_enabled = _bool_field(payload, "mcp_enabled")

    if worker_kind not in _ALLOWED_WORKER_KINDS:
        raise ValueError("worker_kind_not_allowed")
    if not task_classes:
        raise ValueError("task_classes_must_be_nonempty")
    if len(set(task_classes)) != len(task_classes):
        raise ValueError("duplicate_task_class")
    if not capability_hashes:
        raise ValueError("capability_hashes_must_be_nonempty")
    if len(set(capability_hashes)) != len(capability_hashes):
        raise ValueError("duplicate_capability_hash")
    if not evidence_requirement_hashes:
        raise ValueError("evidence_requirement_hashes_must_be_nonempty")
    if len(set(evidence_requirement_hashes)) != len(evidence_requirement_hashes):
        raise ValueError("duplicate_evidence_requirement_hash")
    _reject_enabled_surface(
        live_execution_enabled=live_execution_enabled,
        provider_calls_enabled=provider_calls_enabled,
        network_enabled=network_enabled,
        browser_enabled=browser_enabled,
        dcc_enabled=dcc_enabled,
        mcp_enabled=mcp_enabled,
    )

    material = {
        "browser_enabled": browser_enabled,
        "capability_hashes": capability_hashes,
        "code_version": _CODE_VERSION,
        "contract_version": _CONTRACT_VERSION,
        "dcc_enabled": dcc_enabled,
        "evidence_requirement_hashes": evidence_requirement_hashes,
        "human_approval_required": human_approval_required,
        "input_contract_hash": _digest_field(payload, "input_contract_hash"),
        "live_execution_enabled": live_execution_enabled,
        "mcp_enabled": mcp_enabled,
        "network_enabled": network_enabled,
        "output_contract_hash": _digest_field(payload, "output_contract_hash"),
        "policy_hash": _digest_field(payload, "policy_hash"),
        "provider_calls_enabled": provider_calls_enabled,
        "task_classes": task_classes,
        "worker_id": worker_id,
        "worker_kind": worker_kind,
    }
    observed = _observed_at(declared_at)
    return WorkerAdmissionDeclaration(
        worker_id=worker_id,
        worker_kind=worker_kind,
        task_classes=task_classes,
        input_contract_hash=str(material["input_contract_hash"]),
        output_contract_hash=str(material["output_contract_hash"]),
        policy_hash=str(material["policy_hash"]),
        capability_hashes=capability_hashes,
        evidence_requirement_hashes=evidence_requirement_hashes,
        human_approval_required=human_approval_required,
        live_execution_enabled=live_execution_enabled,
        provider_calls_enabled=provider_calls_enabled,
        network_enabled=network_enabled,
        browser_enabled=browser_enabled,
        dcc_enabled=dcc_enabled,
        mcp_enabled=mcp_enabled,
        declaration_hash=digest_payload(material),
        declared_at=observed,
    )


def build_worker_admission_request(
    payload: Mapping[str, Any],
    *,
    requested_at: str | None = None,
) -> WorkerAdmissionRequest:
    """Build a validated worker admission request."""

    _require_mapping(payload)
    _reject_forbidden_material(payload)

    approval_receipt_hash = _optional_digest_field(payload, "approval_receipt_hash")
    human_invoked = _bool_field(payload, "human_invoked")
    if human_invoked is not True:
        raise ValueError("worker_admission_request_must_be_human_invoked")

    material = {
        "admission_request_id": _string_field(payload, "admission_request_id"),
        "approval_receipt_hash": approval_receipt_hash,
        "artifact_manifest_hash": _digest_field(payload, "artifact_manifest_hash"),
        "code_version": _CODE_VERSION,
        "contract_version": _CONTRACT_VERSION,
        "human_invoked": human_invoked,
        "idempotency_key_hash": _digest_field(payload, "idempotency_key_hash"),
        "queue_job_hash": _digest_field(payload, "queue_job_hash"),
        "requested_task_class": _string_field(payload, "requested_task_class"),
        "run_id": _string_field(payload, "run_id"),
        "task_descriptor_hash": _digest_field(payload, "task_descriptor_hash"),
        "task_id": _string_field(payload, "task_id"),
        "wal_head_hash": _digest_field(payload, "wal_head_hash"),
        "worker_id": _string_field(payload, "worker_id"),
    }
    observed = _observed_at(requested_at)
    return WorkerAdmissionRequest(
        admission_request_id=str(material["admission_request_id"]),
        worker_id=str(material["worker_id"]),
        task_id=str(material["task_id"]),
        run_id=str(material["run_id"]),
        requested_task_class=str(material["requested_task_class"]),
        queue_job_hash=str(material["queue_job_hash"]),
        task_descriptor_hash=str(material["task_descriptor_hash"]),
        idempotency_key_hash=str(material["idempotency_key_hash"]),
        wal_head_hash=str(material["wal_head_hash"]),
        artifact_manifest_hash=str(material["artifact_manifest_hash"]),
        approval_receipt_hash=approval_receipt_hash,
        human_invoked=human_invoked,
        request_hash=digest_payload(material),
        requested_at=observed,
    )


def admit_worker_request(
    declaration: WorkerAdmissionDeclaration,
    request: WorkerAdmissionRequest,
    *,
    wal_record_hash: str,
    admitted_at: str | None = None,
) -> WorkerAdmissionReceipt:
    """Evaluate a declaration/request pair and emit a deterministic receipt."""

    if not validate_worker_admission_declaration(declaration):
        raise ValueError("worker_admission_declaration_invalid")
    if not validate_worker_admission_request(request):
        raise ValueError("worker_admission_request_invalid")
    if not strict_digest(wal_record_hash):
        raise ValueError("wal_record_hash_must_be_valid_digest")

    failures: list[str] = []
    if request.worker_id != declaration.worker_id:
        failures.append("worker_id_mismatch")
    if request.requested_task_class not in declaration.task_classes:
        failures.append("requested_task_class_not_declared")
    if declaration.human_approval_required and request.approval_receipt_hash is None:
        failures.append("approval_receipt_hash_required")
    if not declaration.human_approval_required and request.approval_receipt_hash is not None:
        failures.append("approval_receipt_hash_unexpected")
    _append_surface_failures(declaration, failures)

    admitted = not failures
    if admitted:
        state = "queue_admission_allowed"
    elif "approval_receipt_hash_required" in failures:
        state = "human_approval_required"
    else:
        state = "policy_rejected"
    material = {
        "admission_request_hash": request.request_hash,
        "admission_state": state,
        "admitted": admitted,
        "code_version": _CODE_VERSION,
        "contract_version": _CONTRACT_VERSION,
        "failure_reasons": tuple(failures),
        "run_id": request.run_id,
        "task_id": request.task_id,
        "wal_record_hash": wal_record_hash,
        "worker_declaration_hash": declaration.declaration_hash,
        "worker_id": request.worker_id,
    }
    observed = _observed_at(admitted_at)
    return WorkerAdmissionReceipt(
        admission_request_hash=request.request_hash,
        worker_declaration_hash=declaration.declaration_hash,
        worker_id=request.worker_id,
        task_id=request.task_id,
        run_id=request.run_id,
        admitted=admitted,
        admission_state=state,
        failure_reasons=tuple(failures),
        wal_record_hash=wal_record_hash,
        receipt_hash=digest_payload(material),
        admitted_at=observed,
    )


def build_worker_registry_admission_manifest(
    *,
    manifest_id: str,
    registry_policy_hash: str,
    wal_head_hash: str,
    declarations: Sequence[WorkerAdmissionDeclaration],
    created_at: str | None = None,
) -> WorkerRegistryAdmissionManifest:
    """Build a deterministic registry manifest from validated declarations."""

    if not strict_nonempty_string(manifest_id):
        raise ValueError("manifest_id_must_be_nonempty_string")
    if not strict_digest(registry_policy_hash):
        raise ValueError("registry_policy_hash_must_be_valid_digest")
    if not strict_digest(wal_head_hash):
        raise ValueError("wal_head_hash_must_be_valid_digest")
    if not isinstance(declarations, Sequence) or not declarations:
        raise ValueError("worker_declarations_must_be_nonempty_sequence")

    worker_ids: list[str] = []
    declaration_hashes: list[str] = []
    for declaration in declarations:
        if not validate_worker_admission_declaration(declaration):
            raise ValueError("worker_admission_declaration_invalid")
        if declaration.worker_id in worker_ids:
            raise ValueError("duplicate_worker_id")
        if declaration.declaration_hash in declaration_hashes:
            raise ValueError("duplicate_worker_declaration_hash")
        worker_ids.append(declaration.worker_id)
        declaration_hashes.append(declaration.declaration_hash)

    registry_root_hash = digest_payload({"declaration_hashes": tuple(declaration_hashes)})
    material = {
        "admitted_worker_ids": tuple(worker_ids),
        "code_version": _CODE_VERSION,
        "contract_version": _CONTRACT_VERSION,
        "declaration_hashes": tuple(declaration_hashes),
        "manifest_id": manifest_id,
        "registry_policy_hash": registry_policy_hash,
        "registry_root_hash": registry_root_hash,
        "wal_head_hash": wal_head_hash,
    }
    observed = _observed_at(created_at)
    return WorkerRegistryAdmissionManifest(
        manifest_id=manifest_id,
        registry_policy_hash=registry_policy_hash,
        wal_head_hash=wal_head_hash,
        declaration_hashes=tuple(declaration_hashes),
        admitted_worker_ids=tuple(worker_ids),
        registry_root_hash=registry_root_hash,
        manifest_hash=digest_payload(material),
        created_at=observed,
    )


def validate_worker_admission_declaration(declaration: WorkerAdmissionDeclaration) -> bool:
    if not isinstance(declaration, WorkerAdmissionDeclaration):
        return False
    if not strict_nonempty_string(declaration.worker_id):
        return False
    if declaration.worker_kind not in _ALLOWED_WORKER_KINDS:
        return False
    if not _nonempty_unique_strings(declaration.task_classes):
        return False
    if not _nonempty_unique_digests(declaration.capability_hashes):
        return False
    if not _nonempty_unique_digests(declaration.evidence_requirement_hashes):
        return False
    for value in (
        declaration.input_contract_hash,
        declaration.output_contract_hash,
        declaration.policy_hash,
    ):
        if not strict_digest(value):
            return False
    for value in (
        declaration.human_approval_required,
        declaration.live_execution_enabled,
        declaration.provider_calls_enabled,
        declaration.network_enabled,
        declaration.browser_enabled,
        declaration.dcc_enabled,
        declaration.mcp_enabled,
    ):
        if not strict_bool(value):
            return False
    if _surface_enabled(declaration):
        return False
    if not strict_nonempty_string(declaration.contract_version):
        return False
    if not strict_nonempty_string(declaration.code_version):
        return False
    return declaration.declaration_hash == digest_payload(declaration.deterministic_material())


def validate_worker_admission_request(request: WorkerAdmissionRequest) -> bool:
    if not isinstance(request, WorkerAdmissionRequest):
        return False
    for value in (
        request.admission_request_id,
        request.worker_id,
        request.task_id,
        request.run_id,
        request.requested_task_class,
        request.contract_version,
        request.code_version,
    ):
        if not strict_nonempty_string(value):
            return False
    for value in (
        request.queue_job_hash,
        request.task_descriptor_hash,
        request.idempotency_key_hash,
        request.wal_head_hash,
        request.artifact_manifest_hash,
    ):
        if not strict_digest(value):
            return False
    if request.approval_receipt_hash is not None and not strict_digest(request.approval_receipt_hash):
        return False
    if request.human_invoked is not True:
        return False
    return request.request_hash == digest_payload(request.deterministic_material())


def validate_worker_admission_receipt(receipt: WorkerAdmissionReceipt) -> bool:
    if not isinstance(receipt, WorkerAdmissionReceipt):
        return False
    if not strict_digest(receipt.admission_request_hash):
        return False
    if not strict_digest(receipt.worker_declaration_hash):
        return False
    if not strict_nonempty_string(receipt.worker_id):
        return False
    if not strict_nonempty_string(receipt.task_id):
        return False
    if not strict_nonempty_string(receipt.run_id):
        return False
    if not strict_bool(receipt.admitted):
        return False
    if receipt.admission_state not in _ALLOWED_ADMISSION_STATES:
        return False
    if receipt.admitted and receipt.failure_reasons:
        return False
    if not receipt.admitted and not receipt.failure_reasons:
        return False
    if receipt.admission_state == "queue_admission_allowed" and receipt.admitted is not True:
        return False
    if not strict_digest(receipt.wal_record_hash):
        return False
    if not all(strict_nonempty_string(reason) for reason in receipt.failure_reasons):
        return False
    if not strict_nonempty_string(receipt.contract_version):
        return False
    if not strict_nonempty_string(receipt.code_version):
        return False
    return receipt.receipt_hash == digest_payload(receipt.deterministic_material())


def validate_worker_registry_admission_manifest(
    manifest: WorkerRegistryAdmissionManifest,
) -> bool:
    if not isinstance(manifest, WorkerRegistryAdmissionManifest):
        return False
    if not strict_nonempty_string(manifest.manifest_id):
        return False
    if not strict_digest(manifest.registry_policy_hash):
        return False
    if not strict_digest(manifest.wal_head_hash):
        return False
    if not _nonempty_unique_digests(manifest.declaration_hashes):
        return False
    if not _nonempty_unique_strings(manifest.admitted_worker_ids):
        return False
    if len(manifest.declaration_hashes) != len(manifest.admitted_worker_ids):
        return False
    if manifest.registry_root_hash != digest_payload(
        {"declaration_hashes": manifest.declaration_hashes}
    ):
        return False
    if not strict_nonempty_string(manifest.contract_version):
        return False
    if not strict_nonempty_string(manifest.code_version):
        return False
    return manifest.manifest_hash == digest_payload(manifest.deterministic_material())


def _require_mapping(payload: Mapping[str, Any]) -> None:
    if not isinstance(payload, Mapping):
        raise ValueError("worker_admission_payload_must_be_mapping")


def _string_field(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not strict_nonempty_string(value):
        raise ValueError(f"{field}_must_be_nonempty_string")
    return str(value)


def _digest_field(payload: Mapping[str, Any], field: str) -> str:
    value = payload.get(field)
    if not strict_digest(value):
        raise ValueError(f"{field}_must_be_valid_digest")
    return str(value)


def _optional_digest_field(payload: Mapping[str, Any], field: str) -> str | None:
    value = payload.get(field)
    if value is None:
        return None
    if not strict_digest(value):
        raise ValueError(f"{field}_must_be_valid_digest")
    return str(value)


def _bool_field(payload: Mapping[str, Any], field: str) -> bool:
    value = payload.get(field)
    if not strict_bool(value):
        raise ValueError(f"{field}_must_be_bool")
    return bool(value)


def _string_tuple(payload: Mapping[str, Any], field: str) -> tuple[str, ...]:
    value = payload.get(field)
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field}_must_be_sequence")
    result = tuple(str(item) for item in value if strict_nonempty_string(item))
    if len(result) != len(value):
        raise ValueError(f"{field}_must_contain_nonempty_strings")
    return result


def _digest_tuple(payload: Mapping[str, Any], field: str) -> tuple[str, ...]:
    value = payload.get(field)
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field}_must_be_sequence")
    result: list[str] = []
    for item in value:
        if not strict_digest(item):
            raise ValueError(f"{field}_must_contain_valid_digests")
        result.append(str(item))
    return tuple(result)


def _reject_enabled_surface(**flags: bool) -> None:
    for field, value in flags.items():
        if value is not False:
            raise ValueError(f"{field}_must_be_false")


def _append_surface_failures(
    declaration: WorkerAdmissionDeclaration,
    failures: list[str],
) -> None:
    if declaration.live_execution_enabled:
        failures.append("live_execution_enabled")
    if declaration.provider_calls_enabled:
        failures.append("provider_calls_enabled")
    if declaration.network_enabled:
        failures.append("network_enabled")
    if declaration.browser_enabled:
        failures.append("browser_enabled")
    if declaration.dcc_enabled:
        failures.append("dcc_enabled")
    if declaration.mcp_enabled:
        failures.append("mcp_enabled")


def _surface_enabled(declaration: WorkerAdmissionDeclaration) -> bool:
    return any(
        (
            declaration.live_execution_enabled,
            declaration.provider_calls_enabled,
            declaration.network_enabled,
            declaration.browser_enabled,
            declaration.dcc_enabled,
            declaration.mcp_enabled,
        )
    )


def _nonempty_unique_strings(values: tuple[str, ...]) -> bool:
    return bool(values) and len(set(values)) == len(values) and all(
        strict_nonempty_string(value) for value in values
    )


def _nonempty_unique_digests(values: tuple[str, ...]) -> bool:
    return bool(values) and len(set(values)) == len(values) and all(
        strict_digest(value) for value in values
    )


def _reject_forbidden_material(value: Any, *, path: str = "") -> None:
    if isinstance(value, Mapping):
        for raw_key, nested in value.items():
            if not isinstance(raw_key, str):
                raise ValueError("worker_admission_keys_must_be_strings")
            key = raw_key.lower()
            key_path = f"{path}.{raw_key}" if path else raw_key
            if key in _CONTROL_FLAG_KEYS:
                _reject_forbidden_material(nested, path=key_path)
                continue
            if key in _FORBIDDEN_EXACT_KEYS:
                raise ValueError(f"forbidden_worker_material_field_{key_path}")
            if any(fragment in key for fragment in _FORBIDDEN_KEY_FRAGMENTS):
                raise ValueError(f"forbidden_worker_material_field_{key_path}")
            _reject_forbidden_material(nested, path=key_path)
    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _reject_forbidden_material(nested, path=f"{path}[{index}]")


def _observed_at(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not strict_nonempty_string(value):
        raise ValueError("timestamp_must_be_nonempty_string")
    return value
