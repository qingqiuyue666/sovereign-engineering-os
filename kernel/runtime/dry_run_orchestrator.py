"""Deterministic dry-run runtime orchestrator.

Wires existing foundation modules into a deterministic end-to-end dry-run
spine. The orchestrator is dry-run only — no provider calls, no network,
no autonomy, no real vault write, no SQLite, no file mutation.

Flow:
1. Validate RuntimeExecutionDescriptor
2. Validate state transition planned -> validated
3. Validate idempotency key
4. Produce dry-run runner receipt
5. Append event_journal event: descriptor_validated
6. Refuse provider execution via ProviderExecutionPlane boundary
7. Refuse evidence vault live write via EvidenceVaultBoundary / ProtectedStorageInterface
8. Append event_journal event: dry_run_completed
9. Produce final DryRunOrchestrationReceipt

Failure at any step produces a failure bundle and replay plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import hashlib
import json

from kernel.runtime.execution_descriptor import (
    ExecutionDescriptorReceipt,
    ExecutionDescriptorRejection,
    validate_execution_descriptor,
)
from kernel.runtime.runner import run_dry_run, RunnerReceipt
from kernel.runtime.state_machine import validate_state_transition, StateTransitionReceipt
from kernel.runtime.idempotency import IdempotencyGuard, IdempotencyReceipt
from kernel.runtime.event_journal import EventJournal, JournalAppendResult
from kernel.runtime.provider_execution_plane import (
    validate_provider_execution_plane,
    ProviderExecutionPlaneReceipt,
)
from kernel.evidence.evidence_vault_boundary import (
    validate_evidence_vault_boundary,
    EvidenceVaultBoundaryReceipt,
)
from kernel.evidence.protected_storage_interface import (
    validate_protected_storage_request,
    ProtectedStorageResult,
)

__all__ = [
    "DryRunOrchestrationReceipt",
    "DryRunOrchestratorRejection",
    "orchestrate_dry_run",
]

_FORBIDDEN_FIELDS: tuple[str, ...] = (
    "raw_prompt",
    "raw_provider_response",
    "secret_value",
    "env_value",
    "provider_api_key",
    "live_network_target",
    "autonomy_directive",
)

_POLICY_VERSION = "v1"
_CODE_VERSION = "0.1.0"


class DryRunOrchestratorRejection(ValueError):
    """Raised when orchestration input violates a policy boundary."""


@dataclass(frozen=True)
class DryRunOrchestrationReceipt:
    """Deterministic receipt from the dry-run runtime orchestrator.

    Contains digest refs to all sub-receipts produced during orchestration.
    """

    accepted: bool
    failures: tuple[str, ...]
    task_id: str
    run_id: str
    execution_id: str
    dry_run: bool
    state_transition_receipt_digest: str
    idempotency_receipt_digest: str
    runner_receipt_digest: str
    provider_boundary_receipt_digest: str
    evidence_boundary_receipt_digest: str
    event_journal_digest: str
    final_status: str
    policy_version: str
    code_version: str
    failure_bundle_digest: str
    replay_plan_digest: str

    def as_dict(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "failures": list(self.failures),
            "task_id": self.task_id,
            "run_id": self.run_id,
            "execution_id": self.execution_id,
            "dry_run": self.dry_run,
            "state_transition_receipt_digest": self.state_transition_receipt_digest,
            "idempotency_receipt_digest": self.idempotency_receipt_digest,
            "runner_receipt_digest": self.runner_receipt_digest,
            "provider_boundary_receipt_digest": self.provider_boundary_receipt_digest,
            "evidence_boundary_receipt_digest": self.evidence_boundary_receipt_digest,
            "event_journal_digest": self.event_journal_digest,
            "final_status": self.final_status,
            "policy_version": self.policy_version,
            "code_version": self.code_version,
            "failure_bundle_digest": self.failure_bundle_digest,
            "replay_plan_digest": self.replay_plan_digest,
        }


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest_payload(payload: Any) -> str:
    return "sha256:" + hashlib.sha256(
        _canonical_json(payload).encode("utf-8")
    ).hexdigest()


def _empty_digest() -> str:
    return "sha256:" + hashlib.sha256(b"").hexdigest()


def _rejection_digest(failures: tuple[str, ...]) -> str:
    return "sha256:" + hashlib.sha256(
        ("rejected:" + ":".join(sorted(failures))).encode("utf-8")
    ).hexdigest()


def _safe_str(value: object) -> str:
    if isinstance(value, str):
        return value
    return ""


def orchestrate_dry_run(
    descriptor: Mapping[str, object],
    *,
    guard: IdempotencyGuard | None = None,
    journal: EventJournal | None = None,
) -> DryRunOrchestrationReceipt:
    """Orchestrate a deterministic dry-run execution through all foundation modules.

    The orchestrator wires together:
    - execution_descriptor validation
    - state_machine transition (planned -> validated)
    - idempotency guard
    - runner dry-run
    - event_journal recording
    - provider_execution_plane boundary (refusal recorded)
    - evidence_vault_boundary + protected_storage_interface (refusal recorded)

    Args:
        descriptor: A RuntimeExecutionDescriptor payload.
        guard: Optional IdempotencyGuard for duplicate detection.
        journal: Optional EventJournal for event recording.

    Returns:
        DryRunOrchestrationReceipt with all digests and final status.
    """
    if not isinstance(descriptor, Mapping):
        raise DryRunOrchestratorRejection("orchestrator_input_must_be_a_mapping")

    failures: list[str] = []
    guard = guard if guard is not None else IdempotencyGuard()
    journal = journal if journal is not None else EventJournal()

    # Gate 1: forbidden fields in top-level descriptor
    for field in _FORBIDDEN_FIELDS:
        if field in descriptor:
            failures.append(f"{field}_forbidden")

    # Exit early if forbidden fields found
    if failures:
        task_id = _safe_str(descriptor.get("task_id", ""))
        run_id = _safe_str(descriptor.get("run_id", ""))
        execution_id = _safe_str(descriptor.get("execution_id", ""))
        return DryRunOrchestrationReceipt(
            accepted=False,
            failures=tuple(failures),
            task_id=task_id,
            run_id=run_id,
            execution_id=execution_id,
            dry_run=False,
            state_transition_receipt_digest=_empty_digest(),
            idempotency_receipt_digest=_empty_digest(),
            runner_receipt_digest=_empty_digest(),
            provider_boundary_receipt_digest=_empty_digest(),
            evidence_boundary_receipt_digest=_empty_digest(),
            event_journal_digest=_empty_digest(),
            final_status="rejected",
            policy_version=_POLICY_VERSION,
            code_version=_CODE_VERSION,
            failure_bundle_digest=_empty_digest(),
            replay_plan_digest=_empty_digest(),
        )

    # Step 1: Validate RuntimeExecutionDescriptor
    try:
        descriptor_receipt = validate_execution_descriptor(descriptor)
    except ExecutionDescriptorRejection as e:
        return DryRunOrchestrationReceipt(
            accepted=False,
            failures=(str(e),),
            task_id=_safe_str(descriptor.get("task_id", "")),
            run_id=_safe_str(descriptor.get("run_id", "")),
            execution_id=_safe_str(descriptor.get("execution_id", "")),
            dry_run=False,
            state_transition_receipt_digest=_empty_digest(),
            idempotency_receipt_digest=_empty_digest(),
            runner_receipt_digest=_empty_digest(),
            provider_boundary_receipt_digest=_empty_digest(),
            evidence_boundary_receipt_digest=_empty_digest(),
            event_journal_digest=_empty_digest(),
            final_status="rejected",
            policy_version=_POLICY_VERSION,
            code_version=_CODE_VERSION,
            failure_bundle_digest=_empty_digest(),
            replay_plan_digest=_empty_digest(),
        )

    if not descriptor_receipt.accepted:
        return _build_rejected(descriptor, descriptor_receipt.failures, guard, journal)

    descriptor_digest = descriptor_receipt.descriptor_digest

    task_id = descriptor_receipt.task_id
    run_id = descriptor_receipt.run_id
    execution_id = descriptor_receipt.execution_id

    # Step 2: Validate state transition planned -> validated
    state_payload = {
        "from_state": "planned",
        "to_state": "validated",
        "policy_version": _POLICY_VERSION,
        "code_version": _CODE_VERSION,
    }
    state_receipt: StateTransitionReceipt = validate_state_transition(state_payload)
    if not state_receipt.accepted:
        failures.extend(state_receipt.reasons)
        return _build_rejected_from_fields(
            task_id, run_id, execution_id, tuple(failures), guard, journal
        )
    state_digest = _digest_payload(state_receipt.as_dict())

    # Step 3: Validate idempotency
    idem_payload = {
        "idempotency_key": f"key:{execution_id}",
        "operation_digest": descriptor_digest,
        "policy_version": _POLICY_VERSION,
        "code_version": _CODE_VERSION,
    }
    idem_receipt: IdempotencyReceipt = guard.check(idem_payload)
    if not idem_receipt.accepted:
        failures.extend(idem_receipt.reasons)
        return _build_rejected_from_fields(
            task_id, run_id, execution_id, tuple(failures), guard, journal
        )
    idem_digest = _digest_payload(idem_receipt.as_dict())

    # Step 4: Produce dry-run runner receipt
    runner_payload: dict[str, object] = {
        "dry_run": True,
        "task_id": task_id,
        "run_id": run_id,
        "stage": "dry_run",
        "policy_version": _POLICY_VERSION,
        "code_version": _CODE_VERSION,
        "input_digest": descriptor_digest,
    }
    runner_receipt: RunnerReceipt = run_dry_run(runner_payload)
    if not runner_receipt.accepted():
        failures.extend(runner_receipt.failures)
        return _build_rejected_from_fields(
            task_id, run_id, execution_id, tuple(failures), guard, journal
        )
    runner_digest = _digest_payload(runner_receipt.as_dict())

    # Step 5: Append event_journal event: descriptor_validated
    event1_result: JournalAppendResult = journal.append({
        "event_id": f"evt:descriptor_validated:{execution_id}",
        "run_id": run_id,
        "task_id": task_id,
        "stage": "dry_run",
        "event_type": "descriptor_validated",
        "logical_sequence": 1,
        "payload_digest": descriptor_digest,
    })
    if not event1_result.accepted:
        failures.extend(event1_result.failures)
        return _build_rejected_from_fields(
            task_id, run_id, execution_id, tuple(failures), guard, journal
        )

    # Step 6: Refuse provider execution (record refusal, do not execute)
    provider_payload = {
        "provider_id": "none",
        "policy_version": _POLICY_VERSION,
        "code_version": _CODE_VERSION,
        "request_digest": _empty_digest(),
        "authorization_digest": _empty_digest(),
        "provider_enabled": False,
        "network_access": False,
        "tool_calls_enabled": False,
        "file_edits_enabled": False,
        "production_autonomy": False,
    }
    provider_receipt: ProviderExecutionPlaneReceipt = validate_provider_execution_plane(provider_payload)
    provider_digest = _digest_payload(provider_receipt.as_dict())

    # Verify provider_enabled rejection is recorded, not live-executed
    if "provider_enabled" in descriptor and descriptor.get("provider_enabled") is True:
        failures.append("provider_execution_rejected_dry_run_only")
        return _build_rejected_from_fields(
            task_id, run_id, execution_id, tuple(failures), guard, journal
        )

    # Step 7: Refuse evidence vault live write (record refusal, do not execute)
    vault_payload = {
        "policy_version": _POLICY_VERSION,
        "code_version": _CODE_VERSION,
        "artifact_digest": descriptor_digest,
        "vault_enabled": False,
    }
    vault_receipt: EvidenceVaultBoundaryReceipt = validate_evidence_vault_boundary(vault_payload)
    vault_digest = _digest_payload(vault_receipt.as_dict())

    storage_payload = {
        "storage_request_id": f"stor:{execution_id}",
        "policy_version": _POLICY_VERSION,
        "code_version": _CODE_VERSION,
        "human_approval_token": "none",
        "artifact_digest": descriptor_digest,
        "live_write": False,
    }
    storage_receipt: ProtectedStorageResult = validate_protected_storage_request(storage_payload)
    storage_digest = _digest_payload(storage_receipt.as_dict())

    # Combined evidence boundary digest
    evidence_boundary_digest = _digest_payload({
        "vault_boundary": vault_digest,
        "storage_interface": storage_digest,
    })

    # Step 8: Append event_journal event: dry_run_completed
    event2_result: JournalAppendResult = journal.append({
        "event_id": f"evt:dry_run_completed:{execution_id}",
        "run_id": run_id,
        "task_id": task_id,
        "stage": "dry_run",
        "event_type": "dry_run_completed",
        "logical_sequence": 2,
        "payload_digest": runner_digest,
    })
    if not event2_result.accepted:
        failures.extend(event2_result.failures)
        return _build_rejected_from_fields(
            task_id, run_id, execution_id, tuple(failures), guard, journal
        )

    # Compute event journal digest from all events
    journal_events = [e.as_dict() for e in journal.events if e.run_id == run_id]
    journal_digest = _digest_payload(journal_events)

    # Step 9: Produce final DryRunOrchestrationReceipt
    return DryRunOrchestrationReceipt(
        accepted=True,
        failures=(),
        task_id=task_id,
        run_id=run_id,
        execution_id=execution_id,
        dry_run=True,
        state_transition_receipt_digest=state_digest,
        idempotency_receipt_digest=idem_digest,
        runner_receipt_digest=runner_digest,
        provider_boundary_receipt_digest=provider_digest,
        evidence_boundary_receipt_digest=evidence_boundary_digest,
        event_journal_digest=journal_digest,
        final_status="dry_run_completed",
        policy_version=_POLICY_VERSION,
        code_version=_CODE_VERSION,
        failure_bundle_digest=_empty_digest(),
        replay_plan_digest=_empty_digest(),
    )


def _build_rejected(
    descriptor: Mapping[str, object],
    failures: tuple[str, ...],
    guard: IdempotencyGuard,
    journal: EventJournal,
) -> DryRunOrchestrationReceipt:
    """Build a rejection receipt with failure bundle and replay plan digests."""
    task_id = _safe_str(descriptor.get("task_id", ""))
    run_id = _safe_str(descriptor.get("run_id", ""))
    execution_id = _safe_str(descriptor.get("execution_id", ""))

    # Build failure bundle digest
    failure_bundle = {
        "failure_id": f"fail:{execution_id}",
        "task_id": task_id,
        "run_id": run_id,
        "stage": "dry_run",
        "error_class": "DescriptorValidationError",
        "sanitized_message": ":".join(sorted(failures)),
        "policy_version": _POLICY_VERSION,
        "code_version": _CODE_VERSION,
        "retry_decision": "manual_recovery_required",
        "quarantine_ref": f"quarantine:{execution_id}",
        "rollback_ref": f"rollback:{execution_id}",
        "state_snapshot_digest": _rejection_digest(failures),
        "input_snapshot_digest": _rejection_digest(failures),
    }
    failure_bundle_digest = _digest_payload(failure_bundle)

    # Build replay plan digest
    replay_plan = {
        "task_id": task_id,
        "run_id": run_id,
        "replay_id": f"replay:{execution_id}",
        "policy_version": _POLICY_VERSION,
        "code_version": _CODE_VERSION,
        "input_snapshot_digest": _rejection_digest(failures),
        "state_snapshot_digest": _rejection_digest(failures),
        "environment_descriptor_digest": _empty_digest(),
        "expected_output_digest": _empty_digest(),
    }
    replay_plan_digest = _digest_payload(replay_plan)

    return DryRunOrchestrationReceipt(
        accepted=False,
        failures=failures,
        task_id=task_id,
        run_id=run_id,
        execution_id=execution_id,
        dry_run=False,
        state_transition_receipt_digest=_empty_digest(),
        idempotency_receipt_digest=_empty_digest(),
        runner_receipt_digest=_empty_digest(),
        provider_boundary_receipt_digest=_empty_digest(),
        evidence_boundary_receipt_digest=_empty_digest(),
        event_journal_digest=_empty_digest(),
        final_status="rejected",
        policy_version=_POLICY_VERSION,
        code_version=_CODE_VERSION,
        failure_bundle_digest=failure_bundle_digest,
        replay_plan_digest=replay_plan_digest,
    )


def _build_rejected_from_fields(
    task_id: str,
    run_id: str,
    execution_id: str,
    failures: tuple[str, ...],
    guard: IdempotencyGuard,
    journal: EventJournal,
) -> DryRunOrchestrationReceipt:
    """Build a rejection receipt when we have fields but no descriptor."""
    failure_bundle = {
        "failure_id": f"fail:{execution_id}",
        "task_id": task_id,
        "run_id": run_id,
        "stage": "dry_run",
        "error_class": "OrchestrationError",
        "sanitized_message": ":".join(sorted(failures)),
        "policy_version": _POLICY_VERSION,
        "code_version": _CODE_VERSION,
        "retry_decision": "manual_recovery_required",
        "quarantine_ref": f"quarantine:{execution_id}",
        "rollback_ref": f"rollback:{execution_id}",
        "state_snapshot_digest": _rejection_digest(failures),
        "input_snapshot_digest": _rejection_digest(failures),
    }
    failure_bundle_digest = _digest_payload(failure_bundle)

    replay_plan = {
        "task_id": task_id,
        "run_id": run_id,
        "replay_id": f"replay:{execution_id}",
        "policy_version": _POLICY_VERSION,
        "code_version": _CODE_VERSION,
        "input_snapshot_digest": _rejection_digest(failures),
        "state_snapshot_digest": _rejection_digest(failures),
        "environment_descriptor_digest": _empty_digest(),
        "expected_output_digest": _empty_digest(),
    }
    replay_plan_digest = _digest_payload(replay_plan)

    return DryRunOrchestrationReceipt(
        accepted=False,
        failures=failures,
        task_id=task_id,
        run_id=run_id,
        execution_id=execution_id,
        dry_run=False,
        state_transition_receipt_digest=_empty_digest(),
        idempotency_receipt_digest=_empty_digest(),
        runner_receipt_digest=_empty_digest(),
        provider_boundary_receipt_digest=_empty_digest(),
        evidence_boundary_receipt_digest=_empty_digest(),
        event_journal_digest=_empty_digest(),
        final_status="rejected",
        policy_version=_POLICY_VERSION,
        code_version=_CODE_VERSION,
        failure_bundle_digest=failure_bundle_digest,
        replay_plan_digest=replay_plan_digest,
    )
