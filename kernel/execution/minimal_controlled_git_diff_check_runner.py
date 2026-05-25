"""Minimal controlled runner for the git_diff_check execution slice."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from types import MappingProxyType
from typing import Callable, Mapping

from kernel.execution.minimal_controlled_execution_admission_wal_verifier import (
    ExecutionAdmissionRecord,
    ExecutionWalRecord,
    build_execution_admission_record,
    build_execution_wal_record,
)
from kernel.execution.minimal_controlled_execution_contract import (
    EXECUTION_FAILURE_TYPES,
    EXECUTION_REQUEST_FORBIDDEN_FIELDS,
    INITIAL_COMMAND_REGISTRY,
    POLICY_VERSION,
    ExecutionPolicyDecision,
    ExecutionRequest,
    ExecutionSnapshotRef,
    build_execution_request,
    command_registry_hash,
    decide_execution_request,
    decision_hash,
    failure_bundle_hash,
    receipt_hash,
    request_hash,
    snapshot_hash,
    verifier_input_hash,
)

__all__ = [
    "EXECUTABLE_COMMAND_IDS",
    "REPOSITORY_ROOT",
    "RUNNER_FAILURE_TYPES",
    "ExecutionAttempt",
    "MinimalControlledExecutionFailureBundle",
    "MinimalControlledExecutionReceipt",
    "MinimalControlledExecutionRunResult",
    "MinimalControlledExecutionVerification",
    "MinimalControlledExecutionVerifierBinding",
    "MinimalControlledExecutionVerifierInput",
    "run_minimal_controlled_git_diff_check",
    "verify_minimal_controlled_git_diff_check_result",
]

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EXECUTABLE_COMMAND_IDS = ("git_diff_check",)
RUNNER_FAILURE_TYPES = frozenset(
    set(EXECUTION_FAILURE_TYPES) | {"COMMAND_NOT_EXECUTABLE_IN_THIS_SLICE"}
)
_COMMAND_ID = "git_diff_check"
_MINIMAL_ENV = MappingProxyType(
    {
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_TERMINAL_PROMPT": "0",
        "HOME": str(REPOSITORY_ROOT),
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "TZ": "UTC",
    }
)


class _DictMixin:
    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class MinimalControlledExecutionReceipt(_DictMixin):
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
        _install_hash(self, "receipt_hash", receipt_hash)


@dataclass(frozen=True)
class MinimalControlledExecutionFailureBundle(_DictMixin):
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
        if self.failure_type not in RUNNER_FAILURE_TYPES:
            raise ValueError("failure_type_invalid")
        object.__setattr__(self, "failure_reasons", tuple(self.failure_reasons))
        _install_hash(self, "failure_bundle_hash", failure_bundle_hash)


@dataclass(frozen=True)
class MinimalControlledExecutionVerifierInput(_DictMixin):
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
        _install_hash(self, "verifier_input_hash", verifier_input_hash)


@dataclass(frozen=True)
class MinimalControlledExecutionVerifierBinding(_DictMixin):
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
        _install_hash(self, "verifier_binding_hash", _verifier_binding_hash)


@dataclass(frozen=True)
class ExecutionAttempt(_DictMixin):
    command_id: str
    argv: tuple[str, ...]
    cwd: str
    shell: bool
    timeout_ms: int
    env_keys: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "argv", tuple(self.argv))
        object.__setattr__(self, "env_keys", tuple(self.env_keys))


@dataclass(frozen=True)
class MinimalControlledExecutionRunResult(_DictMixin):
    request: ExecutionRequest
    policy_decision: ExecutionPolicyDecision
    admission_record: ExecutionAdmissionRecord
    wal_records: tuple[ExecutionWalRecord, ...]
    pre_snapshot: ExecutionSnapshotRef
    post_snapshot: ExecutionSnapshotRef
    receipt: MinimalControlledExecutionReceipt | None
    failure_bundle: MinimalControlledExecutionFailureBundle | None
    verifier_input: MinimalControlledExecutionVerifierInput | None
    verifier_binding: MinimalControlledExecutionVerifierBinding | None
    attempt: ExecutionAttempt | None
    execution_performed: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "wal_records", tuple(self.wal_records))


@dataclass(frozen=True)
class MinimalControlledExecutionVerification:
    accepted: bool
    rejection_reasons: tuple[str, ...]
    verifier_input: MinimalControlledExecutionVerifierInput | None
    verifier_binding: MinimalControlledExecutionVerifierBinding | None


def run_minimal_controlled_git_diff_check(
    request: ExecutionRequest | Mapping[str, object],
    *,
    wal_append: Callable[[ExecutionWalRecord], None] | None = None,
) -> MinimalControlledExecutionRunResult:
    normalized = request if isinstance(request, ExecutionRequest) else build_execution_request(request)
    decision = decide_execution_request(
        normalized,
        decision_id="decision-" + normalized.request_id,
        decided_at=_utc_now(),
    )
    admission = build_execution_admission_record(
        normalized,
        admission_record_id="admission-" + normalized.request_id,
        decision_id=decision.decision_id,
        decided_at=decision.decided_at,
        created_at=_utc_now(),
    )
    pre_snapshot = _snapshot(normalized, "PRE")
    wal_records: list[ExecutionWalRecord] = []
    try:
        _append_admission_wal(normalized, decision, admission, wal_records, wal_append)
    except Exception as exc:
        post_snapshot = _snapshot(normalized, "POST")
        return _result(
            normalized,
            decision,
            admission,
            wal_records,
            pre_snapshot,
            post_snapshot,
            None,
            _failure(
                normalized,
                decision,
                pre_snapshot,
                post_snapshot,
                "WAL_APPEND_FAILED",
                ("WAL_APPEND_FAILED", "EXECUTION_NOT_ATTEMPTED", type(exc).__name__),
                False,
            ),
            None,
            False,
        )

    if not decision.accepted:
        post_snapshot = _snapshot(normalized, "POST")
        failure_type = _rejection_failure_type(decision)
        return _result(
            normalized,
            decision,
            admission,
            wal_records,
            pre_snapshot,
            post_snapshot,
            None,
            _failure(
                normalized,
                decision,
                pre_snapshot,
                post_snapshot,
                failure_type,
                decision.rejection_reasons,
                False,
            ),
            None,
            False,
        )

    if normalized.command_id not in EXECUTABLE_COMMAND_IDS:
        post_snapshot = _snapshot(normalized, "POST")
        return _result(
            normalized,
            decision,
            admission,
            wal_records,
            pre_snapshot,
            post_snapshot,
            None,
            _failure(
                normalized,
                decision,
                pre_snapshot,
                post_snapshot,
                "COMMAND_NOT_EXECUTABLE_IN_THIS_SLICE",
                ("COMMAND_NOT_EXECUTABLE_IN_THIS_SLICE", normalized.command_id),
                False,
            ),
            None,
            False,
        )

    entry = INITIAL_COMMAND_REGISTRY[_COMMAND_ID]
    attempt = ExecutionAttempt(
        command_id=normalized.command_id,
        argv=entry.argv,
        cwd=str(REPOSITORY_ROOT),
        shell=False,
        timeout_ms=entry.timeout_ms,
        env_keys=tuple(sorted(_MINIMAL_ENV)),
    )
    started_at = _utc_now()
    try:
        completed = subprocess.run(
            list(entry.argv),
            capture_output=True,
            cwd=str(REPOSITORY_ROOT),
            env=dict(_MINIMAL_ENV),
            shell=False,
            text=True,
            timeout=entry.timeout_ms / 1000,
        )
    except subprocess.TimeoutExpired:
        post_snapshot = _snapshot(normalized, "POST")
        return _result(
            normalized,
            decision,
            admission,
            wal_records,
            pre_snapshot,
            post_snapshot,
            None,
            _failure(
                normalized,
                decision,
                pre_snapshot,
                post_snapshot,
                "EXECUTION_TIMEOUT",
                ("EXECUTION_TIMEOUT",),
                False,
            ),
            attempt,
            False,
        )

    post_snapshot = _snapshot(normalized, "POST")
    stdout_meta = _output_meta(completed.stdout, entry.output_limit_bytes)
    stderr_meta = _output_meta(completed.stderr, entry.output_limit_bytes)
    receipt = MinimalControlledExecutionReceipt(
        receipt_id="receipt-" + normalized.request_id,
        request_id=normalized.request_id,
        command_id=normalized.command_id,
        receipt_status="EXECUTION_COMPLETED",
        started_at=started_at,
        finished_at=_utc_now(),
        exit_code=completed.returncode,
        stdout_digest=stdout_meta["digest"],
        stderr_digest=stderr_meta["digest"],
        stdout_truncated=stdout_meta["truncated"],
        stderr_truncated=stderr_meta["truncated"],
        output_limit_bytes=entry.output_limit_bytes,
        pre_snapshot_hash=pre_snapshot.snapshot_hash,
        post_snapshot_hash=post_snapshot.snapshot_hash,
        registry_entry_hash=entry.registry_entry_hash,
        policy_decision_hash=decision.decision_hash,
        execution_performed=True,
    )
    failure = _completed_failure(
        normalized,
        decision,
        pre_snapshot,
        post_snapshot,
        completed.returncode,
        stdout_meta["truncated"] or stderr_meta["truncated"],
    )
    return _result(
        normalized,
        decision,
        admission,
        wal_records,
        pre_snapshot,
        post_snapshot,
        receipt,
        failure,
        attempt,
        True,
    )


def verify_minimal_controlled_git_diff_check_result(
    result: MinimalControlledExecutionRunResult,
) -> MinimalControlledExecutionVerification:
    failures: list[str] = []
    request = result.request
    decision = result.policy_decision
    receipt = result.receipt
    entry = INITIAL_COMMAND_REGISTRY[_COMMAND_ID]

    _check(request.request_hash == request_hash(request), failures, "request_hash_mismatch")
    _check(decision.decision_hash == decision_hash(decision), failures, "decision_hash_mismatch")
    _check(decision.request_id == request.request_id, failures, "decision_request_id_mismatch")
    _check(decision.command_id == request.command_id, failures, "decision_command_id_mismatch")
    _check(decision.registry_hash == command_registry_hash(), failures, "registry_hash_mismatch")
    _check(
        not set(request.as_dict()).intersection(EXECUTION_REQUEST_FORBIDDEN_FIELDS),
        failures,
        "forbidden_request_field_accepted",
    )
    _check(
        tuple(INITIAL_COMMAND_REGISTRY) == ("git_status_short", "git_diff_check"),
        failures,
        "registry_command_ids_mismatch",
    )
    _check(
        EXECUTABLE_COMMAND_IDS == ("git_diff_check",),
        failures,
        "executable_command_ids_mismatch",
    )
    _check(
        result.pre_snapshot.snapshot_hash == snapshot_hash(result.pre_snapshot),
        failures,
        "pre_snapshot_hash_mismatch",
    )
    _check(
        result.post_snapshot.snapshot_hash == snapshot_hash(result.post_snapshot),
        failures,
        "post_snapshot_hash_mismatch",
    )

    if receipt is not None:
        receipt_payload = receipt.as_dict()
        _check(receipt.receipt_hash == receipt_hash(receipt), failures, "receipt_hash_mismatch")
        _check(receipt.request_id == request.request_id, failures, "receipt_request_id_mismatch")
        _check(receipt.command_id == _COMMAND_ID, failures, "receipt_command_id_mismatch")
        _check(request.command_id == _COMMAND_ID, failures, "request_command_id_mismatch")
        _check(decision.command_id == _COMMAND_ID, failures, "decision_command_id_mismatch")
        _check(
            receipt.policy_decision_hash == decision.decision_hash,
            failures,
            "policy_decision_hash_mismatch",
        )
        _check(
            receipt.registry_entry_hash == entry.registry_entry_hash,
            failures,
            "registry_entry_hash_mismatch",
        )
        _check(
            receipt.pre_snapshot_hash == result.pre_snapshot.snapshot_hash,
            failures,
            "pre_snapshot_hash_mismatch",
        )
        _check(
            receipt.post_snapshot_hash == result.post_snapshot.snapshot_hash,
            failures,
            "post_snapshot_hash_mismatch",
        )
        _check(
            receipt.output_limit_bytes == entry.output_limit_bytes,
            failures,
            "output_limit_bytes_mismatch",
        )
        for raw_field in ("stdout", "stderr", "stdout_text", "stderr_text", "raw_stdout", "raw_stderr"):
            _check(raw_field not in receipt_payload, failures, "raw_output_persisted")
        if result.attempt is None:
            failures.append("execution_attempt_missing")
        else:
            _check(result.attempt.command_id == _COMMAND_ID, failures, "attempt_command_id_mismatch")
            _check(result.attempt.argv == entry.argv, failures, "attempt_argv_mismatch")
            _check(result.attempt.cwd == str(REPOSITORY_ROOT), failures, "attempt_cwd_mismatch")
            _check(result.attempt.shell is False, failures, "attempt_shell_not_false")
            _check(result.attempt.timeout_ms == entry.timeout_ms, failures, "attempt_timeout_mismatch")
            _check(
                result.attempt.env_keys == tuple(sorted(_MINIMAL_ENV)),
                failures,
                "attempt_env_mismatch",
            )

    if result.failure_bundle is not None:
        _check(
            result.failure_bundle.failure_bundle_hash
            == failure_bundle_hash(result.failure_bundle),
            failures,
            "failure_bundle_hash_mismatch",
        )

    verifier_input = _verifier_input(result) if receipt is not None else None
    verifier_binding = _verifier_binding(result)
    return MinimalControlledExecutionVerification(
        accepted=not failures,
        rejection_reasons=tuple(failures),
        verifier_input=verifier_input,
        verifier_binding=verifier_binding,
    )


def _result(
    request: ExecutionRequest,
    decision: ExecutionPolicyDecision,
    admission: ExecutionAdmissionRecord,
    wal_records: list[ExecutionWalRecord],
    pre_snapshot: ExecutionSnapshotRef,
    post_snapshot: ExecutionSnapshotRef,
    receipt: MinimalControlledExecutionReceipt | None,
    failure: MinimalControlledExecutionFailureBundle | None,
    attempt: ExecutionAttempt | None,
    execution_performed: bool,
) -> MinimalControlledExecutionRunResult:
    result = MinimalControlledExecutionRunResult(
        request=request,
        policy_decision=decision,
        admission_record=admission,
        wal_records=tuple(wal_records),
        pre_snapshot=pre_snapshot,
        post_snapshot=post_snapshot,
        receipt=receipt,
        failure_bundle=failure,
        verifier_input=None,
        verifier_binding=None,
        attempt=attempt,
        execution_performed=execution_performed,
    )
    verification = verify_minimal_controlled_git_diff_check_result(result)
    if verification.accepted:
        return replace(
            result,
            verifier_input=verification.verifier_input,
            verifier_binding=verification.verifier_binding,
        )
    return replace(
        result,
        receipt=None,
        failure_bundle=_failure(
            request,
            decision,
            pre_snapshot,
            post_snapshot,
            "RECEIPT_VERIFICATION_FAILED",
            verification.rejection_reasons,
            False,
        ),
        execution_performed=False,
    )


def _append_admission_wal(
    request: ExecutionRequest,
    decision: ExecutionPolicyDecision,
    admission: ExecutionAdmissionRecord,
    wal_records: list[ExecutionWalRecord],
    wal_append: Callable[[ExecutionWalRecord], None] | None,
) -> None:
    wal = build_execution_wal_record(
        {
            "admission_record_hash": admission.admission_record_hash,
            "command_id": request.command_id,
            "created_at": _utc_now(),
            "decision_hash": decision.decision_hash,
            "execution_performed": False,
            "failure_bundle_hash": "",
            "registry_entry_hash": admission.registry_entry_hash,
            "registry_hash": admission.registry_hash,
            "request_hash": request.request_hash,
            "run_id": request.run_id,
            "sequence": 1,
            "task_id": request.task_id,
            "verifier_input_hash": "",
            "wal_record_id": "wal-" + request.request_id + "-1",
            "wal_record_type": "EXECUTION_ADMISSION_ACCEPTED"
            if decision.accepted
            else "EXECUTION_ADMISSION_REJECTED",
        }
    )
    if wal_append is not None:
        wal_append(wal)
    wal_records.append(wal)


def _failure(
    request: ExecutionRequest,
    decision: ExecutionPolicyDecision,
    pre_snapshot: ExecutionSnapshotRef,
    post_snapshot: ExecutionSnapshotRef,
    failure_type: str,
    reasons: tuple[str, ...],
    execution_performed: bool,
) -> MinimalControlledExecutionFailureBundle:
    return MinimalControlledExecutionFailureBundle(
        failure_bundle_id="failure-" + request.request_id + "-" + failure_type.lower(),
        request_id=request.request_id,
        command_id=request.command_id,
        failure_type=failure_type,
        failure_reasons=reasons,
        policy_decision_hash=decision.decision_hash,
        registry_entry_hash=decision.registry_entry_hash,
        pre_snapshot_hash=pre_snapshot.snapshot_hash,
        post_snapshot_hash=post_snapshot.snapshot_hash,
        execution_performed=execution_performed,
    )


def _completed_failure(
    request: ExecutionRequest,
    decision: ExecutionPolicyDecision,
    pre_snapshot: ExecutionSnapshotRef,
    post_snapshot: ExecutionSnapshotRef,
    exit_code: int,
    output_limit_exceeded: bool,
) -> MinimalControlledExecutionFailureBundle | None:
    if output_limit_exceeded:
        return _failure(
            request,
            decision,
            pre_snapshot,
            post_snapshot,
            "OUTPUT_LIMIT_EXCEEDED",
            ("OUTPUT_LIMIT_EXCEEDED",),
            True,
        )
    if exit_code not in INITIAL_COMMAND_REGISTRY[_COMMAND_ID].allowed_exit_codes:
        return _failure(
            request,
            decision,
            pre_snapshot,
            post_snapshot,
            "NONZERO_EXIT",
            ("NONZERO_EXIT", "exit_code:" + str(exit_code)),
            True,
        )
    return None


def _rejection_failure_type(decision: ExecutionPolicyDecision) -> str:
    if "UNKNOWN_COMMAND_ID" in decision.rejection_reasons:
        return "UNKNOWN_COMMAND_ID"
    if "DEFERRED_COMMAND_ID" in decision.rejection_reasons:
        return "DEFERRED_COMMAND_ID"
    return "POLICY_REJECTED"


def _verifier_input(
    result: MinimalControlledExecutionRunResult,
) -> MinimalControlledExecutionVerifierInput:
    receipt = result.receipt
    if receipt is None:
        raise ValueError("receipt_required")
    return MinimalControlledExecutionVerifierInput(
        verifier_input_id="verifier-input-" + result.request.request_id,
        request_hash=result.request.request_hash,
        decision_hash=result.policy_decision.decision_hash,
        registry_entry_hash=receipt.registry_entry_hash,
        receipt_hash=receipt.receipt_hash,
        pre_snapshot_hash=result.pre_snapshot.snapshot_hash,
        post_snapshot_hash=result.post_snapshot.snapshot_hash,
        verifier_policy_version=POLICY_VERSION,
        execution_performed=receipt.execution_performed,
    )


def _verifier_binding(
    result: MinimalControlledExecutionRunResult,
) -> MinimalControlledExecutionVerifierBinding | None:
    receipt_hash_value = result.receipt.receipt_hash if result.receipt is not None else ""
    failure_hash_value = (
        result.failure_bundle.failure_bundle_hash
        if result.failure_bundle is not None
        else ""
    )
    if not receipt_hash_value and not failure_hash_value:
        return None
    return MinimalControlledExecutionVerifierBinding(
        verifier_binding_id="verifier-binding-" + result.request.request_id,
        request_hash=result.request.request_hash,
        decision_hash=result.policy_decision.decision_hash,
        admission_record_hash=result.admission_record.admission_record_hash,
        receipt_hash=receipt_hash_value,
        failure_bundle_hash=failure_hash_value,
        pre_snapshot_hash=result.pre_snapshot.snapshot_hash,
        post_snapshot_hash=result.post_snapshot.snapshot_hash,
        registry_entry_hash=result.receipt.registry_entry_hash
        if result.receipt is not None
        else result.admission_record.registry_entry_hash,
        registry_hash=result.admission_record.registry_hash,
        execution_performed=bool(result.receipt and result.receipt.execution_performed),
        verifier_policy_version=POLICY_VERSION,
    )


def _snapshot(request: ExecutionRequest, snapshot_type: str) -> ExecutionSnapshotRef:
    root_hash = "sha256:" + _sha256_text(
        _canonical_json(
            {
                "git_head": _git_head_ref(),
                "registry_hash": command_registry_hash(),
                "repository_root": str(REPOSITORY_ROOT),
            }
        )
    )
    return ExecutionSnapshotRef(
        snapshot_id="snapshot-" + request.request_id + "-" + snapshot_type.lower(),
        task_id=request.task_id,
        run_id=request.run_id,
        command_id=request.command_id,
        snapshot_type=snapshot_type,
        root_hash=root_hash,
        captured_at=_utc_now(),
        execution_performed=False,
    )


def _git_head_ref() -> str:
    git_dir = REPOSITORY_ROOT / ".git"
    try:
        head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return "HEAD:unavailable"
    if not head.startswith("ref: "):
        return "HEAD:" + head
    ref_name = head[5:]
    try:
        ref_value = (git_dir / ref_name).read_text(encoding="utf-8").strip()
    except OSError:
        ref_value = "unavailable"
    return "HEAD:" + ref_name + ":" + ref_value


def _output_meta(value: object, limit: int) -> dict[str, object]:
    if value is None:
        raw = b""
    elif isinstance(value, bytes):
        raw = value
    else:
        raw = str(value).encode("utf-8", errors="replace")
    bounded = raw[:limit]
    return {
        "digest": "sha256:" + hashlib.sha256(bounded).hexdigest(),
        "truncated": len(raw) > limit,
    }


def _install_hash(target: object, field_name: str, hash_fn: object) -> None:
    expected = hash_fn(target)  # type: ignore[operator]
    current = getattr(target, field_name)
    if current and current != expected:
        raise ValueError(field_name + "_mismatch")
    object.__setattr__(target, field_name, expected)


def _verifier_binding_hash(
    binding: MinimalControlledExecutionVerifierBinding | Mapping[str, object],
) -> str:
    data = binding.as_dict() if isinstance(binding, MinimalControlledExecutionVerifierBinding) else dict(binding)
    data.pop("verifier_binding_hash", None)
    return "sha256:" + _sha256_text(_canonical_json(data))


def _check(condition: bool, failures: list[str], reason: str) -> None:
    if not condition:
        failures.append(reason)


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
