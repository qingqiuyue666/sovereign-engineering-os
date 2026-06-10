"""Minimal controlled execution contracts.

This module defines immutable data contracts for a future allowlisted local
execution kernel. It only validates supplied data and computes canonical hashes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import hashlib
import json
from types import MappingProxyType
from typing import Mapping, Sequence

__all__ = [
    "POLICY_VERSION",
    "REGISTRY_VERSION",
    "COMMAND_REGISTRY_HASH",
    "COMMAND_REGISTRY_ENTRY_FIELDS",
    "DEFERRED_COMMAND_IDS",
    "EXECUTION_REQUEST_FIELDS",
    "EXECUTION_REQUEST_FORBIDDEN_FIELDS",
    "EXECUTION_POLICY_DECISION_FIELDS",
    "EXECUTION_RECEIPT_FIELDS",
    "EXECUTION_FAILURE_BUNDLE_FIELDS",
    "EXECUTION_FAILURE_TYPES",
    "EXECUTION_SNAPSHOT_REF_FIELDS",
    "EXECUTION_SNAPSHOT_TYPES",
    "EXECUTION_VERIFIER_INPUT_FIELDS",
    "FORBIDDEN_SURFACE_FLAGS_FALSE",
    "INITIAL_COMMAND_REGISTRY",
    "ExecutionCommandRegistryEntry",
    "ExecutionRequest",
    "ExecutionPolicyDecision",
    "ExecutionReceipt",
    "ExecutionFailureBundle",
    "ExecutionSnapshotRef",
    "ExecutionVerifierInput",
    "build_execution_request",
    "build_execution_receipt",
    "command_registry_hash",
    "decide_execution_request",
    "registry_entry_hash",
    "request_hash",
    "decision_hash",
    "receipt_hash",
    "failure_bundle_hash",
    "snapshot_hash",
    "verifier_input_hash",
]

POLICY_VERSION = "minimal_controlled_execution_contract_only_v1"
REGISTRY_VERSION = "minimal_controlled_execution_registry_v1"

COMMAND_REGISTRY_ENTRY_FIELDS = (
    "command_id",
    "argv",
    "command_class",
    "read_only_expectation",
    "allowed_verifier",
    "registry_version",
    "cwd_policy",
    "env_policy",
    "executable_policy",
    "timeout_ms",
    "output_limit_bytes",
    "allowed_exit_codes",
    "risk_class",
    "requires_human_approval",
    "requires_clean_worktree",
    "network_policy",
    "mutation_policy",
    "command_semantics",
    "registry_entry_hash",
)

EXECUTION_REQUEST_FIELDS = (
    "request_id",
    "task_id",
    "run_id",
    "command_id",
    "approval_token_id",
    "requested_at",
    "requester",
    "policy_version",
    "use_case_ids",
    "snapshot_ref",
    "caller_intent",
    "request_hash",
)

EXECUTION_REQUEST_FORBIDDEN_FIELDS = frozenset(
    {
        "argv",
        "command",
        "command_line",
        "shell",
        "cwd",
        "env",
        "executable",
        "path",
        "timeout",
        "network",
        "provider",
        "browser",
        "plugin",
        "dcc",
        "comfyui",
        "mcp",
    }
)

DEFERRED_COMMAND_IDS = frozenset({"unittest_discover_tests", "make_ci"})

FORBIDDEN_SURFACE_FLAG_NAMES = (
    "argv_allowed",
    "cwd_allowed",
    "env_allowed",
    "path_allowed",
    "executable_allowed",
    "timeout_allowed",
    "command_allowed",
    "command_line_allowed",
    "shell_allowed",
    "network_allowed",
    "provider_allowed",
    "browser_allowed",
    "plugin_allowed",
    "dcc_allowed",
    "comfyui_allowed",
    "mcp_allowed",
    "subprocess_allowed",
    "os_system_allowed",
    "popen_allowed",
    "exec_eval_allowed",
    "runner_allowed",
    "launcher_allowed",
    "cli_allowed",
    "daemon_allowed",
    "scheduler_allowed",
    "task_graph_execution_allowed",
    "auto_reexecution_allowed",
    "credentials_allowed",
    "package_install_allowed",
    "file_deletion_allowed",
    "asset_mutation_allowed",
)

FORBIDDEN_SURFACE_FLAGS_FALSE = tuple(
    (flag_name, False) for flag_name in FORBIDDEN_SURFACE_FLAG_NAMES
)

EXECUTION_POLICY_DECISION_FIELDS = (
    "decision_id",
    "request_id",
    "command_id",
    "accepted",
    "rejection_reasons",
    "required_approval_token_id",
    "registry_entry_hash",
    "policy_version",
    "registry_version",
    "registry_hash",
    "forbidden_surface_flags",
    "execution_performed",
    "decided_at",
    "decision_hash",
)

EXECUTION_RECEIPT_FIELDS = (
    "receipt_id",
    "request_id",
    "command_id",
    "receipt_status",
    "started_at",
    "finished_at",
    "exit_code",
    "stdout_digest",
    "stderr_digest",
    "stdout_truncated",
    "stderr_truncated",
    "output_limit_bytes",
    "pre_snapshot_hash",
    "post_snapshot_hash",
    "registry_entry_hash",
    "policy_decision_hash",
    "execution_performed",
    "receipt_hash",
)

EXECUTION_FAILURE_BUNDLE_FIELDS = (
    "failure_bundle_id",
    "request_id",
    "command_id",
    "failure_type",
    "failure_reasons",
    "policy_decision_hash",
    "registry_entry_hash",
    "pre_snapshot_hash",
    "post_snapshot_hash",
    "execution_performed",
    "failure_bundle_hash",
)

EXECUTION_FAILURE_TYPES = frozenset(
    {
        "POLICY_REJECTED",
        "APPROVAL_MISSING",
        "UNKNOWN_COMMAND_ID",
        "DEFERRED_COMMAND_ID",
        "FORBIDDEN_REQUEST_FIELD",
        "WORKTREE_NOT_CLEAN",
        "EXECUTION_TIMEOUT",
        "NONZERO_EXIT",
        "OUTPUT_LIMIT_EXCEEDED",
        "SNAPSHOT_DRIFT",
        "RECEIPT_VERIFICATION_FAILED",
        "WAL_APPEND_FAILED",
        "EXECUTION_NOT_ATTEMPTED",
    }
)

EXECUTION_SNAPSHOT_REF_FIELDS = (
    "snapshot_id",
    "task_id",
    "run_id",
    "command_id",
    "snapshot_type",
    "root_hash",
    "captured_at",
    "execution_performed",
    "snapshot_hash",
)

EXECUTION_SNAPSHOT_TYPES = frozenset({"PRE", "POST"})

EXECUTION_VERIFIER_INPUT_FIELDS = (
    "verifier_input_id",
    "request_hash",
    "decision_hash",
    "registry_entry_hash",
    "receipt_hash",
    "pre_snapshot_hash",
    "post_snapshot_hash",
    "verifier_policy_version",
    "execution_performed",
    "verifier_input_hash",
)

_RAW_OUTPUT_FIELDS = frozenset(
    {"stdout", "stderr", "stdout_text", "stderr_text", "raw_stdout", "raw_stderr"}
)


class _ContractDictMixin:
    def as_dict(self) -> dict[str, object]:
        return _contract_dict(self)


@dataclass(frozen=True)
class ExecutionCommandRegistryEntry(_ContractDictMixin):
    command_id: str
    argv: tuple[str, ...]
    command_class: str
    read_only_expectation: bool
    allowed_verifier: str
    registry_version: str
    cwd_policy: str
    env_policy: str
    executable_policy: str
    timeout_ms: int
    output_limit_bytes: int
    allowed_exit_codes: tuple[int, ...]
    risk_class: str
    requires_human_approval: bool
    requires_clean_worktree: bool
    network_policy: str
    mutation_policy: str
    command_semantics: str
    registry_entry_hash: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "argv", _string_tuple(self.argv, "argv"))
        object.__setattr__(
            self,
            "allowed_exit_codes",
            _int_tuple(self.allowed_exit_codes, "allowed_exit_codes"),
        )
        _require_strings(
            self.as_dict(),
            (
                "command_id",
                "command_class",
                "allowed_verifier",
                "registry_version",
                "cwd_policy",
                "env_policy",
                "executable_policy",
                "risk_class",
                "network_policy",
                "mutation_policy",
                "command_semantics",
            ),
        )
        _require_bool(self.read_only_expectation, "read_only_expectation")
        if not self.read_only_expectation:
            raise ValueError("read_only_expectation_must_be_true")
        if self.registry_version != REGISTRY_VERSION:
            raise ValueError("registry_version_mismatch")
        _require_positive_int(self.timeout_ms, "timeout_ms")
        _require_positive_int(self.output_limit_bytes, "output_limit_bytes")
        _require_bool(self.requires_human_approval, "requires_human_approval")
        _require_bool(self.requires_clean_worktree, "requires_clean_worktree")
        if not self.argv:
            raise ValueError("argv_required")
        if not self.allowed_exit_codes:
            raise ValueError("allowed_exit_codes_required")
        _install_or_verify_hash(self, "registry_entry_hash", registry_entry_hash)


@dataclass(frozen=True)
class ExecutionRequest(_ContractDictMixin):
    request_id: str
    task_id: str
    run_id: str
    command_id: str
    approval_token_id: str
    requested_at: str
    requester: str
    policy_version: str
    use_case_ids: tuple[str, ...]
    snapshot_ref: str
    caller_intent: str
    request_hash: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "use_case_ids",
            _string_tuple(self.use_case_ids, "use_case_ids"),
        )
        _require_strings(
            self.as_dict(),
            (
                "request_id",
                "task_id",
                "run_id",
                "command_id",
                "requested_at",
                "requester",
                "policy_version",
                "snapshot_ref",
                "caller_intent",
            ),
        )
        if not isinstance(self.approval_token_id, str):
            raise ValueError("approval_token_id_must_be_string")
        if self.policy_version != POLICY_VERSION:
            raise ValueError("policy_version_mismatch")
        if not self.use_case_ids:
            raise ValueError("use_case_ids_required")
        _install_or_verify_hash(self, "request_hash", request_hash)


@dataclass(frozen=True)
class ExecutionPolicyDecision(_ContractDictMixin):
    decision_id: str
    request_id: str
    command_id: str
    accepted: bool
    rejection_reasons: tuple[str, ...]
    required_approval_token_id: str
    registry_entry_hash: str
    policy_version: str
    registry_version: str
    registry_hash: str
    forbidden_surface_flags: tuple[tuple[str, bool], ...]
    execution_performed: bool
    decided_at: str
    decision_hash: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "rejection_reasons",
            _string_tuple(self.rejection_reasons, "rejection_reasons"),
        )
        object.__setattr__(
            self,
            "forbidden_surface_flags",
            _bool_pair_tuple(self.forbidden_surface_flags, "forbidden_surface_flags"),
        )
        _require_strings(
            self.as_dict(),
            (
                "decision_id",
                "request_id",
                "command_id",
                "policy_version",
                "registry_version",
                "registry_hash",
                "decided_at",
            ),
        )
        _require_bool(self.accepted, "accepted")
        _require_bool(self.execution_performed, "execution_performed")
        if self.execution_performed:
            raise ValueError("execution_performed_must_be_false_in_contract_only_v1")
        if self.policy_version != POLICY_VERSION:
            raise ValueError("policy_version_mismatch")
        if self.registry_version != REGISTRY_VERSION:
            raise ValueError("registry_version_mismatch")
        if dict(self.forbidden_surface_flags) != dict(FORBIDDEN_SURFACE_FLAGS_FALSE):
            raise ValueError("forbidden_surface_flags_must_all_be_false")
        if not isinstance(self.required_approval_token_id, str):
            raise ValueError("required_approval_token_id_must_be_string")
        if not isinstance(self.registry_entry_hash, str):
            raise ValueError("registry_entry_hash_must_be_string")
        if self.accepted and self.rejection_reasons:
            raise ValueError("accepted_decision_cannot_have_rejection_reasons")
        if not self.accepted and "POLICY_REJECTED" not in self.rejection_reasons:
            raise ValueError("rejected_decision_requires_policy_rejected_reason")
        _install_or_verify_hash(self, "decision_hash", decision_hash)


@dataclass(frozen=True)
class ExecutionReceipt(_ContractDictMixin):
    receipt_id: str
    request_id: str
    command_id: str
    receipt_status: str
    started_at: str
    finished_at: str
    exit_code: int
    stdout_digest: str
    stderr_digest: str
    stdout_truncated: bool
    stderr_truncated: bool
    output_limit_bytes: int
    pre_snapshot_hash: str
    post_snapshot_hash: str
    registry_entry_hash: str
    policy_decision_hash: str
    execution_performed: bool
    receipt_hash: str = ""

    def __post_init__(self) -> None:
        _require_strings(
            self.as_dict(),
            (
                "receipt_id",
                "request_id",
                "command_id",
                "receipt_status",
                "started_at",
                "finished_at",
                "stdout_digest",
                "stderr_digest",
                "pre_snapshot_hash",
                "post_snapshot_hash",
                "registry_entry_hash",
                "policy_decision_hash",
            ),
        )
        _require_int(self.exit_code, "exit_code")
        _require_bool(self.stdout_truncated, "stdout_truncated")
        _require_bool(self.stderr_truncated, "stderr_truncated")
        _require_bool(self.execution_performed, "execution_performed")
        if self.receipt_status != "CONTRACT_ONLY_NOT_EXECUTED":
            raise ValueError("receipt_status_must_be_contract_only_not_executed")
        if self.execution_performed:
            raise ValueError("execution_performed_must_be_false_in_contract_only_v1")
        _require_positive_int(self.output_limit_bytes, "output_limit_bytes")
        _install_or_verify_hash(self, "receipt_hash", receipt_hash)


@dataclass(frozen=True)
class ExecutionFailureBundle(_ContractDictMixin):
    failure_bundle_id: str
    request_id: str
    command_id: str
    failure_type: str
    failure_reasons: tuple[str, ...]
    policy_decision_hash: str
    registry_entry_hash: str
    pre_snapshot_hash: str
    post_snapshot_hash: str
    execution_performed: bool
    failure_bundle_hash: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "failure_reasons",
            _string_tuple(self.failure_reasons, "failure_reasons"),
        )
        _require_strings(
            self.as_dict(),
            (
                "failure_bundle_id",
                "request_id",
                "command_id",
                "failure_type",
                "policy_decision_hash",
                "registry_entry_hash",
                "pre_snapshot_hash",
                "post_snapshot_hash",
            ),
        )
        if self.failure_type not in EXECUTION_FAILURE_TYPES:
            raise ValueError("failure_type_invalid")
        if not self.failure_reasons:
            raise ValueError("failure_reasons_required")
        _require_bool(self.execution_performed, "execution_performed")
        if self.execution_performed:
            raise ValueError("execution_performed_must_be_false_in_contract_only_v1")
        _install_or_verify_hash(self, "failure_bundle_hash", failure_bundle_hash)


@dataclass(frozen=True)
class ExecutionSnapshotRef(_ContractDictMixin):
    snapshot_id: str
    task_id: str
    run_id: str
    command_id: str
    snapshot_type: str
    root_hash: str
    captured_at: str
    execution_performed: bool
    snapshot_hash: str = ""

    def __post_init__(self) -> None:
        _require_strings(
            self.as_dict(),
            (
                "snapshot_id",
                "task_id",
                "run_id",
                "command_id",
                "snapshot_type",
                "root_hash",
                "captured_at",
            ),
        )
        if self.snapshot_type not in EXECUTION_SNAPSHOT_TYPES:
            raise ValueError("snapshot_type_invalid")
        _require_bool(self.execution_performed, "execution_performed")
        if self.execution_performed:
            raise ValueError("execution_performed_must_be_false_in_contract_only_v1")
        _install_or_verify_hash(self, "snapshot_hash", snapshot_hash)


@dataclass(frozen=True)
class ExecutionVerifierInput(_ContractDictMixin):
    verifier_input_id: str
    request_hash: str
    decision_hash: str
    registry_entry_hash: str
    receipt_hash: str
    pre_snapshot_hash: str
    post_snapshot_hash: str
    verifier_policy_version: str
    execution_performed: bool
    verifier_input_hash: str = ""

    def __post_init__(self) -> None:
        _require_strings(
            self.as_dict(),
            (
                "verifier_input_id",
                "request_hash",
                "decision_hash",
                "registry_entry_hash",
                "receipt_hash",
                "pre_snapshot_hash",
                "post_snapshot_hash",
                "verifier_policy_version",
            ),
        )
        _require_bool(self.execution_performed, "execution_performed")
        if self.verifier_policy_version != POLICY_VERSION:
            raise ValueError("verifier_policy_version_mismatch")
        if self.execution_performed:
            raise ValueError("execution_performed_must_be_false_in_contract_only_v1")
        _install_or_verify_hash(self, "verifier_input_hash", verifier_input_hash)


def build_execution_request(payload: Mapping[str, object]) -> ExecutionRequest:
    """Build a request that can reference a command ID but cannot provide command material."""

    data = dict(payload)
    forbidden = sorted(EXECUTION_REQUEST_FORBIDDEN_FIELDS.intersection(data))
    if forbidden:
        raise ValueError("forbidden_request_field:" + ",".join(forbidden))

    allowed = set(EXECUTION_REQUEST_FIELDS)
    extra = sorted(set(data) - allowed)
    if extra:
        raise ValueError("request_field_not_allowed:" + ",".join(extra))

    required_without_hash = set(EXECUTION_REQUEST_FIELDS) - {"request_hash"}
    missing = sorted(field for field in required_without_hash if field not in data)
    if missing:
        raise ValueError("request_field_required:" + ",".join(missing))

    return ExecutionRequest(
        request_id=_mapping_string(data, "request_id"),
        task_id=_mapping_string(data, "task_id"),
        run_id=_mapping_string(data, "run_id"),
        command_id=_mapping_string(data, "command_id"),
        approval_token_id=_mapping_string(data, "approval_token_id", allow_empty=True),
        requested_at=_mapping_string(data, "requested_at"),
        requester=_mapping_string(data, "requester"),
        policy_version=_mapping_string(data, "policy_version"),
        use_case_ids=_mapping_string_tuple(data, "use_case_ids"),
        snapshot_ref=_mapping_string(data, "snapshot_ref"),
        caller_intent=_mapping_string(data, "caller_intent"),
        request_hash=_mapping_string(data, "request_hash", allow_empty=True)
        if "request_hash" in data
        else "",
    )


def build_execution_receipt(payload: Mapping[str, object]) -> ExecutionReceipt:
    """Build a receipt from digest metadata only."""

    data = dict(payload)
    raw_fields = sorted(_RAW_OUTPUT_FIELDS.intersection(data))
    if raw_fields:
        raise ValueError("raw_output_field_forbidden:" + ",".join(raw_fields))

    allowed = {field.name for field in fields(ExecutionReceipt)}
    extra = sorted(set(data) - allowed)
    if extra:
        raise ValueError("receipt_field_not_allowed:" + ",".join(extra))
    missing = sorted(field for field in allowed - {"receipt_hash"} if field not in data)
    if missing:
        raise ValueError("receipt_field_required:" + ",".join(missing))

    return ExecutionReceipt(
        receipt_id=_mapping_string(data, "receipt_id"),
        request_id=_mapping_string(data, "request_id"),
        command_id=_mapping_string(data, "command_id"),
        receipt_status=_mapping_string(data, "receipt_status"),
        started_at=_mapping_string(data, "started_at"),
        finished_at=_mapping_string(data, "finished_at"),
        exit_code=_mapping_int(data, "exit_code"),
        stdout_digest=_mapping_string(data, "stdout_digest"),
        stderr_digest=_mapping_string(data, "stderr_digest"),
        stdout_truncated=_mapping_bool(data, "stdout_truncated"),
        stderr_truncated=_mapping_bool(data, "stderr_truncated"),
        output_limit_bytes=_mapping_int(data, "output_limit_bytes"),
        pre_snapshot_hash=_mapping_string(data, "pre_snapshot_hash"),
        post_snapshot_hash=_mapping_string(data, "post_snapshot_hash"),
        registry_entry_hash=_mapping_string(data, "registry_entry_hash"),
        policy_decision_hash=_mapping_string(data, "policy_decision_hash"),
        execution_performed=_mapping_bool(data, "execution_performed"),
        receipt_hash=_mapping_string(data, "receipt_hash", allow_empty=True)
        if "receipt_hash" in data
        else "",
    )


def decide_execution_request(
    request: ExecutionRequest | Mapping[str, object],
    registry: Mapping[str, ExecutionCommandRegistryEntry] | None = None,
    *,
    decision_id: str,
    decided_at: str,
    policy_version: str = POLICY_VERSION,
) -> ExecutionPolicyDecision:
    """Return a deterministic contract admission decision for a request."""

    normalized_request = request if isinstance(request, ExecutionRequest) else build_execution_request(request)
    command_registry = INITIAL_COMMAND_REGISTRY if registry is None else registry
    entry = command_registry.get(normalized_request.command_id)

    rejection_reasons: list[str] = []
    required_approval_token_id = ""
    entry_hash = ""
    if entry is None:
        if normalized_request.command_id in DEFERRED_COMMAND_IDS:
            rejection_reasons.extend(("POLICY_REJECTED", "DEFERRED_COMMAND_ID"))
        else:
            rejection_reasons.extend(("POLICY_REJECTED", "UNKNOWN_COMMAND_ID"))
    else:
        entry_hash = entry.registry_entry_hash
        if entry.requires_human_approval and not normalized_request.approval_token_id:
            rejection_reasons.extend(("POLICY_REJECTED", "APPROVAL_MISSING"))
            required_approval_token_id = _approval_token_id(normalized_request)

    return ExecutionPolicyDecision(
        decision_id=decision_id,
        request_id=normalized_request.request_id,
        command_id=normalized_request.command_id,
        accepted=not rejection_reasons,
        rejection_reasons=tuple(sorted(set(rejection_reasons))),
        required_approval_token_id=required_approval_token_id,
        registry_entry_hash=entry_hash,
        policy_version=policy_version,
        registry_version=REGISTRY_VERSION,
        registry_hash=command_registry_hash(command_registry),
        forbidden_surface_flags=FORBIDDEN_SURFACE_FLAGS_FALSE,
        execution_performed=False,
        decided_at=decided_at,
    )


def registry_entry_hash(entry: ExecutionCommandRegistryEntry | Mapping[str, object]) -> str:
    return _hash_contract(entry, "registry_entry_hash")


def request_hash(request: ExecutionRequest | Mapping[str, object]) -> str:
    return _hash_contract(request, "request_hash")


def decision_hash(decision: ExecutionPolicyDecision | Mapping[str, object]) -> str:
    return _hash_contract(decision, "decision_hash")


def receipt_hash(receipt: ExecutionReceipt | Mapping[str, object]) -> str:
    return _hash_contract(receipt, "receipt_hash")


def failure_bundle_hash(bundle: ExecutionFailureBundle | Mapping[str, object]) -> str:
    return _hash_contract(bundle, "failure_bundle_hash")


def snapshot_hash(snapshot: ExecutionSnapshotRef | Mapping[str, object]) -> str:
    return _hash_contract(snapshot, "snapshot_hash")


def verifier_input_hash(verifier_input: ExecutionVerifierInput | Mapping[str, object]) -> str:
    return _hash_contract(verifier_input, "verifier_input_hash")


def command_registry_hash(
    registry: Mapping[str, ExecutionCommandRegistryEntry] | None = None,
) -> str:
    command_registry = INITIAL_COMMAND_REGISTRY if registry is None else registry
    entries = [
        _contract_dict(entry)
        for command_id, entry in sorted(command_registry.items())
        if command_id not in DEFERRED_COMMAND_IDS
    ]
    return "sha256:" + _sha256_hex(
        _canonical_json(
            {
                "registry_version": REGISTRY_VERSION,
                "entries": entries,
            }
        )
    )


def _registry_entry(
    *,
    command_id: str,
    argv: Sequence[str],
    command_semantics: str,
    allowed_verifier: str,
) -> ExecutionCommandRegistryEntry:
    return ExecutionCommandRegistryEntry(
        command_id=command_id,
        argv=tuple(argv),
        command_class="REPOSITORY_READ_ONLY_CHECK",
        read_only_expectation=True,
        allowed_verifier=allowed_verifier,
        registry_version=REGISTRY_VERSION,
        cwd_policy="REPOSITORY_ROOT_ONLY",
        env_policy="NO_PAYLOAD_ENV",
        executable_policy="ALLOWLISTED_EXECUTABLE_NAME_ONLY",
        timeout_ms=30000,
        output_limit_bytes=65536,
        allowed_exit_codes=(0,),
        risk_class="READ_ONLY_REPOSITORY_CHECK",
        requires_human_approval=False,
        requires_clean_worktree=False,
        network_policy="NETWORK_FORBIDDEN",
        mutation_policy="READ_ONLY_NO_MUTATION",
        command_semantics=command_semantics,
    )


def _approval_token_id(request: ExecutionRequest) -> str:
    material = {
        "request_id": request.request_id,
        "task_id": request.task_id,
        "run_id": request.run_id,
        "command_id": request.command_id,
        "policy_version": POLICY_VERSION,
    }
    return "approval:" + _sha256_hex(_canonical_json(material))


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
    if isinstance(values, str):
        raise ValueError(field_name + "_must_be_string_sequence")
    normalized = tuple(str(value) for value in values)
    if any(not value for value in normalized):
        raise ValueError(field_name + "_cannot_contain_empty_string")
    return normalized


def _int_tuple(values: Sequence[int], field_name: str) -> tuple[int, ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError(field_name + "_must_be_int_sequence")
    normalized = tuple(values)
    if any(not isinstance(value, int) or isinstance(value, bool) for value in normalized):
        raise ValueError(field_name + "_cannot_contain_non_int")
    return normalized


def _bool_pair_tuple(
    values: Sequence[tuple[str, bool]],
    field_name: str,
) -> tuple[tuple[str, bool], ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError(field_name + "_must_be_pair_sequence")
    normalized: list[tuple[str, bool]] = []
    for item in values:
        if not isinstance(item, tuple) or len(item) != 2:
            raise ValueError(field_name + "_must_contain_pairs")
        flag_name, flag_value = item
        if not isinstance(flag_name, str) or not flag_name:
            raise ValueError(field_name + "_flag_name_invalid")
        if not isinstance(flag_value, bool):
            raise ValueError(field_name + "_flag_value_must_be_bool")
        normalized.append((flag_name, flag_value))
    return tuple(sorted(normalized))


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
        raise ValueError(field_name + "_must_be_string_sequence")
    return _string_tuple(value, field_name)


_INITIAL_REGISTRY_ENTRIES = (
    _registry_entry(
        command_id="git_status_short",
        argv=("git", "status", "--short"),
        command_semantics="read-only working tree status check",
        allowed_verifier="git_status_short_contract_verifier",
    ),
    _registry_entry(
        command_id="git_diff_check",
        argv=("git", "diff", "--check"),
        command_semantics="read-only whitespace/error diff check",
        allowed_verifier="git_diff_check_contract_verifier",
    ),
)

INITIAL_COMMAND_REGISTRY = MappingProxyType(
    {entry.command_id: entry for entry in _INITIAL_REGISTRY_ENTRIES}
)

COMMAND_REGISTRY_HASH = command_registry_hash()
