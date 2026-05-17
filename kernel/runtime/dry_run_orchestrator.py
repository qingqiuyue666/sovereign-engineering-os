"""Deterministic dry-run runtime orchestrator.

Wires the V12 runtime spine into a dry-run-only orchestrator. It proves
provider and evidence live-surface refusal paths without executing live
provider calls, network access, vault writes, production autonomy, SQLite,
or secret access. Rejection paths are bound through the existing
failure_bundle and replay_plan modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import hashlib
import json

from kernel.evidence.evidence_vault_boundary import validate_evidence_vault_boundary
from kernel.evidence.protected_storage_interface import validate_protected_storage_request
from kernel.runtime.event_journal import EventJournal
from kernel.runtime.execution_descriptor import ExecutionDescriptorRejection, validate_execution_descriptor
from kernel.runtime.failure_bundle import build_failure_bundle, validate_failure_bundle
from kernel.runtime.idempotency import IdempotencyGuard
from kernel.runtime.provider_execution_plane import validate_provider_execution_plane
from kernel.runtime.replay_plan import validate_replay_plan
from kernel.runtime.runner import run_dry_run
from kernel.runtime.state_machine import validate_state_transition

__all__ = ["DryRunOrchestrationReceipt", "DryRunOrchestratorRejection", "orchestrate_dry_run"]

_POLICY_VERSION = "v1"
_CODE_VERSION = "0.1.0"
_FORBIDDEN_FIELDS = (
    "raw_prompt", "raw_provider_response", "secret_value", "env_value",
    "provider_api_key", "live_network_target", "autonomy_directive",
)
_EMPTY_DIGEST = "sha256:" + hashlib.sha256(b"").hexdigest()


class DryRunOrchestratorRejection(ValueError):
    """Raised when orchestration input violates a policy boundary."""


@dataclass(frozen=True)
class DryRunOrchestrationReceipt:
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
    provider_boundary_refused: bool
    provider_boundary_failures: tuple[str, ...]
    evidence_boundary_refused: bool
    evidence_boundary_failures: tuple[str, ...]

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
            "provider_boundary_refused": self.provider_boundary_refused,
            "provider_boundary_failures": list(self.provider_boundary_failures),
            "evidence_boundary_refused": self.evidence_boundary_refused,
            "evidence_boundary_failures": list(self.evidence_boundary_failures),
        }


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(payload: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _failure_digest(failures: tuple[str, ...]) -> str:
    return "sha256:" + hashlib.sha256(("rejected:" + ":".join(sorted(failures))).encode("utf-8")).hexdigest()


def _safe_str(payload: Mapping[str, object], field: str) -> str:
    value = payload.get(field, "")
    return value if isinstance(value, str) else ""


def orchestrate_dry_run(
    descriptor: Mapping[str, object],
    *,
    guard: IdempotencyGuard | None = None,
    journal: EventJournal | None = None,
) -> DryRunOrchestrationReceipt:
    if not isinstance(descriptor, Mapping):
        raise DryRunOrchestratorRejection("orchestrator_input_must_be_a_mapping")

    forbidden = tuple(f"{field}_forbidden" for field in _FORBIDDEN_FIELDS if field in descriptor)
    if forbidden:
        return _reject(descriptor, forbidden)

    try:
        descriptor_receipt = validate_execution_descriptor(descriptor)
    except ExecutionDescriptorRejection as exc:
        return _reject(descriptor, (str(exc),))
    if not descriptor_receipt.accepted:
        return _reject(descriptor, descriptor_receipt.failures)

    guard = guard if guard is not None else IdempotencyGuard()
    journal = journal if journal is not None else EventJournal()
    task_id = descriptor_receipt.task_id
    run_id = descriptor_receipt.run_id
    execution_id = descriptor_receipt.execution_id
    descriptor_digest = descriptor_receipt.descriptor_digest

    state_receipt = validate_state_transition({
        "from_state": "planned", "to_state": "validated",
        "policy_version": _POLICY_VERSION, "code_version": _CODE_VERSION,
    })
    if not state_receipt.accepted:
        return _reject_fields(task_id, run_id, execution_id, tuple(state_receipt.reasons))
    state_digest = _digest(state_receipt.as_dict())

    idem_receipt = guard.check({
        "idempotency_key": f"key:{execution_id}",
        "operation_digest": descriptor_digest,
        "policy_version": _POLICY_VERSION,
        "code_version": _CODE_VERSION,
    })
    if not idem_receipt.accepted:
        return _reject_fields(task_id, run_id, execution_id, tuple(idem_receipt.reasons))
    idem_digest = _digest(idem_receipt.as_dict())

    runner_receipt = run_dry_run({
        "dry_run": True, "task_id": task_id, "run_id": run_id,
        "stage": "dry_run", "policy_version": _POLICY_VERSION,
        "code_version": _CODE_VERSION, "input_digest": descriptor_digest,
    })
    if not runner_receipt.accepted():
        return _reject_fields(task_id, run_id, execution_id, tuple(runner_receipt.failures))
    runner_digest = _digest(runner_receipt.as_dict())

    event_1 = journal.append({
        "event_id": f"evt:descriptor_validated:{execution_id}",
        "run_id": run_id, "task_id": task_id, "stage": "dry_run",
        "event_type": "descriptor_validated", "logical_sequence": 1,
        "payload_digest": descriptor_digest,
    })
    if not event_1.accepted:
        return _reject_fields(task_id, run_id, execution_id, tuple(event_1.failures))

    provider_receipt = validate_provider_execution_plane({
        "provider_id": "simulated-live-provider",
        "policy_version": _POLICY_VERSION,
        "code_version": _CODE_VERSION,
        "request_digest": descriptor_digest,
        "authorization_digest": _failure_digest(("simulated_provider_authorization",)),
        "provider_enabled": True,
        "network_access": True,
        "tool_calls_enabled": True,
        "file_edits_enabled": True,
        "production_autonomy": True,
    })
    provider_refused = not provider_receipt.accepted
    if not provider_refused:
        return _reject_fields(task_id, run_id, execution_id, ("provider_boundary_failed_to_refuse_live_execution",))
    provider_digest = _digest(provider_receipt.as_dict())

    vault_receipt = validate_evidence_vault_boundary({
        "policy_version": _POLICY_VERSION,
        "code_version": _CODE_VERSION,
        "artifact_digest": descriptor_digest,
        "vault_enabled": True,
    })
    storage_receipt = validate_protected_storage_request({
        "storage_request_id": f"stor:{execution_id}",
        "policy_version": _POLICY_VERSION,
        "code_version": _CODE_VERSION,
        "human_approval_token": "simulated-human-approval-token",
        "artifact_digest": descriptor_digest,
        "live_write": True,
    })
    evidence_failures = tuple(vault_receipt.failures) + tuple(storage_receipt.failures)
    evidence_refused = (not vault_receipt.accepted) and (not storage_receipt.accepted)
    if not evidence_refused:
        return _reject_fields(task_id, run_id, execution_id, ("evidence_boundary_failed_to_refuse_live_write",))
    evidence_digest = _digest({"vault_boundary": vault_receipt.as_dict(), "storage_interface": storage_receipt.as_dict()})

    event_2 = journal.append({
        "event_id": f"evt:dry_run_completed:{execution_id}",
        "run_id": run_id, "task_id": task_id, "stage": "dry_run",
        "event_type": "dry_run_completed", "logical_sequence": 2,
        "payload_digest": runner_digest,
    })
    if not event_2.accepted:
        return _reject_fields(task_id, run_id, execution_id, tuple(event_2.failures))

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
        evidence_boundary_receipt_digest=evidence_digest,
        event_journal_digest=_digest([event.as_dict() for event in journal.events if event.run_id == run_id]),
        final_status="dry_run_completed",
        policy_version=_POLICY_VERSION,
        code_version=_CODE_VERSION,
        failure_bundle_digest=_EMPTY_DIGEST,
        replay_plan_digest=_EMPTY_DIGEST,
        provider_boundary_refused=True,
        provider_boundary_failures=tuple(provider_receipt.failures),
        evidence_boundary_refused=True,
        evidence_boundary_failures=evidence_failures,
    )


def _validated_failure_and_replay_digests(
    task_id: str,
    run_id: str,
    execution_id: str,
    failures: tuple[str, ...],
) -> tuple[str, str, tuple[str, ...]]:
    validation_failures: list[str] = []
    failure_bundle = build_failure_bundle(
        task_id=task_id,
        run_id=run_id,
        stage="dry_run",
        error_class="OrchestrationRejected",
        message=":".join(sorted(failures)),
        state_snapshot={"status": "rejected", "failures_digest": _failure_digest(failures)},
        input_snapshot={"execution_id": execution_id, "failures_digest": _failure_digest(failures)},
        policy_version=_POLICY_VERSION,
        code_version=_CODE_VERSION,
        retry_decision="manual_recovery_required",
        quarantine_ref=f"quarantine:{execution_id}",
        rollback_ref=f"rollback:{execution_id}",
    )
    failure_validation = validate_failure_bundle(failure_bundle)
    if not failure_validation.accepted:
        validation_failures.extend(f"failure_bundle:{item}" for item in failure_validation.failures)

    replay_plan = {
        "task_id": task_id,
        "run_id": run_id,
        "replay_id": f"replay:{execution_id}",
        "policy_version": _POLICY_VERSION,
        "code_version": _CODE_VERSION,
        "input_snapshot_digest": failure_bundle["input_snapshot_digest"],
        "state_snapshot_digest": failure_bundle["state_snapshot_digest"],
        "environment_descriptor_digest": _EMPTY_DIGEST,
        "expected_output_digest": _EMPTY_DIGEST,
        "provider_live_requery": False,
    }
    replay_validation = validate_replay_plan(replay_plan)
    if not replay_validation.accepted:
        validation_failures.extend(f"replay_plan:{item}" for item in replay_validation.failures)

    return (
        _digest({"bundle": failure_bundle, "validation": {"accepted": failure_validation.accepted, "failures": list(failure_validation.failures), "bundle_digest": failure_validation.bundle_digest}}),
        _digest({"plan": replay_plan, "validation": replay_validation.as_dict()}),
        tuple(validation_failures),
    )


def _reject(descriptor: Mapping[str, object], failures: tuple[str, ...]) -> DryRunOrchestrationReceipt:
    return _reject_fields(_safe_str(descriptor, "task_id"), _safe_str(descriptor, "run_id"), _safe_str(descriptor, "execution_id"), failures)


def _reject_fields(task_id: str, run_id: str, execution_id: str, failures: tuple[str, ...]) -> DryRunOrchestrationReceipt:
    failure_digest, replay_digest, validation_failures = _validated_failure_and_replay_digests(task_id, run_id, execution_id, failures)
    return DryRunOrchestrationReceipt(
        accepted=False,
        failures=tuple(failures) + validation_failures,
        task_id=task_id,
        run_id=run_id,
        execution_id=execution_id,
        dry_run=False,
        state_transition_receipt_digest=_EMPTY_DIGEST,
        idempotency_receipt_digest=_EMPTY_DIGEST,
        runner_receipt_digest=_EMPTY_DIGEST,
        provider_boundary_receipt_digest=_EMPTY_DIGEST,
        evidence_boundary_receipt_digest=_EMPTY_DIGEST,
        event_journal_digest=_EMPTY_DIGEST,
        final_status="rejected",
        policy_version=_POLICY_VERSION,
        code_version=_CODE_VERSION,
        failure_bundle_digest=failure_digest,
        replay_plan_digest=replay_digest,
        provider_boundary_refused=False,
        provider_boundary_failures=(),
        evidence_boundary_refused=False,
        evidence_boundary_failures=(),
    )
