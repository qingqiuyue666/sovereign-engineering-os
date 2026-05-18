"""Bounded local runtime orchestration slice.

This orchestrator wires local support modules into one dry-run-only runtime
path. It produces deterministic receipts and sanitized failure bundles without
network access, live provider calls, process execution, environment reads,
SQLite mutation, raw prompt persistence, or production autonomy.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Mapping

from kernel.audit.hashchain import digest_payload
from kernel.audit.trail import AuditTrail
from kernel.daemon.watchdog import Watchdog
from kernel.deadlock.breaker import CircuitBreaker, CircuitBreakerConfig
from kernel.errors.hierarchy import SovereignError
from kernel.retry.backoff import RetryConfig, RetryResult, retry_call
from kernel.runtime.local_runtime_failure_bundle import (
    LocalRuntimeFailureBundle,
    build_local_runtime_failure_bundle,
)
from kernel.runtime.local_runtime_guards import LocalRuntimeGuardResult, validate_local_runtime_guards
from kernel.runtime.local_runtime_receipt import LocalRuntimeReceipt, build_local_runtime_receipt
from kernel.state.transitions import TaskLifecycle, build_task_lifecycle
from tools.provider_transport.provider_adapter_registry import ProviderAdapterDescriptor, register_provider_adapter
from tools.provider_transport.provider_dry_run_receipt import ProviderDryRunReceipt
from tools.provider_transport.provider_transport_runtime import TransportExecutionResult, execute_provider_transport

__all__ = [
    "LocalRuntimeOrchestrationResult",
    "orchestrate_local_runtime",
]

_POLICY_VERSION = "local-runtime-orchestrator-v1"
_CODE_VERSION = "0.1.0"
_DEFAULT_STAGE = "local_runtime_dry_run"
_DEFAULT_DIGEST = "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
_DEFAULT_PROVIDER_CAPABILITIES = ("fetch_price", "validate_asset", "mock_execute")
_DIGEST_VALUE_KEYS = frozenset(
    {
        "capabilities",
        "dry_run",
        "evidence_binding",
        "policy_version",
        "provider_id",
        "request_id",
        "run_id",
        "runtime_stage",
        "task_id",
    }
)


@dataclass(frozen=True)
class LocalRuntimeOrchestrationResult:
    """Structured output from a local runtime orchestration attempt."""

    accepted: bool
    receipt: LocalRuntimeReceipt
    guard_result: LocalRuntimeGuardResult
    failure_bundle: LocalRuntimeFailureBundle | None
    provider_dry_run_receipt: ProviderDryRunReceipt | None
    state_transition_hashes: tuple[str, ...]
    audit_entry_hashes: tuple[str, ...]
    audit_chain_head: str
    retry_attempts: int
    retry_total_delay_seconds: float
    circuit_breaker_snapshot: Mapping[str, object]
    watchdog_snapshot: Mapping[str, object]
    boundary_flags: Mapping[str, bool]

    def as_dict(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "audit_chain_head": self.audit_chain_head,
            "audit_entry_hashes": list(self.audit_entry_hashes),
            "boundary_flags": dict(self.boundary_flags),
            "circuit_breaker_snapshot": dict(self.circuit_breaker_snapshot),
            "failure_bundle": self.failure_bundle.as_dict() if self.failure_bundle else None,
            "guard_result": self.guard_result.as_dict(),
            "provider_dry_run_receipt": (
                self.provider_dry_run_receipt.as_dict() if self.provider_dry_run_receipt else None
            ),
            "receipt": self.receipt.as_dict(),
            "retry_attempts": self.retry_attempts,
            "retry_total_delay_seconds": self.retry_total_delay_seconds,
            "state_transition_hashes": list(self.state_transition_hashes),
            "watchdog_snapshot": dict(self.watchdog_snapshot),
        }


def orchestrate_local_runtime(
    payload: Mapping[str, object] | object,
    *,
    audit_trail: AuditTrail | None = None,
    circuit_breaker: CircuitBreaker | None = None,
    watchdog: Watchdog | None = None,
    retry_config: RetryConfig | None = None,
    provider_operation: Callable[[], TransportExecutionResult] | None = None,
    observed_at: str | None = None,
) -> LocalRuntimeOrchestrationResult:
    """Run the bounded local runtime orchestration path."""

    trail = audit_trail if audit_trail is not None else AuditTrail(name="local_runtime_orchestrator")
    input_digest = _input_digest(payload)
    task_id = _payload_string(payload, "task_id", default="unknown_task")
    run_id = _payload_string(payload, "run_id", default="unknown_run")
    runtime_stage = _payload_string(payload, "runtime_stage", default=_DEFAULT_STAGE)
    guard_result = validate_local_runtime_guards(payload)

    if not guard_result.accepted:
        return _reject(
            trail=trail,
            guard_result=guard_result,
            input_digest=input_digest,
            task_id=task_id,
            run_id=run_id,
            runtime_stage=runtime_stage,
            failure_code="runtime_guard_rejected",
            failure_stage="guard",
            failure_reasons=guard_result.failures,
            observed_at=observed_at,
        )

    start_entry = trail.record(
        "local_runtime.guard_accepted",
        {
            "input_digest": input_digest,
            "run_id": run_id,
            "runtime_stage": runtime_stage,
            "task_id": task_id,
        },
        observed_at=observed_at,
    )

    active_watchdog = watchdog if watchdog is not None else Watchdog(deadline_seconds=30.0, name=f"local_runtime:{run_id}")
    active_watchdog.feed(observed_at=observed_at)
    first_watchdog = active_watchdog.check(observed_at=observed_at)

    transitions: list[str] = []
    try:
        lifecycle = build_task_lifecycle(task_id)
        transitions.append(lifecycle.fire(TaskLifecycle.VALIDATED.value, observed_at=observed_at).content_hash)
        transitions.append(lifecycle.fire(TaskLifecycle.PLANNED.value, observed_at=observed_at).content_hash)
        transitions.append(
            lifecycle.fire(
                TaskLifecycle.DRY_RUN_COMPLETE.value,
                context={"dry_run_only": True},
                observed_at=observed_at,
            ).content_hash
        )
    except Exception as exc:
        return _reject(
            trail=trail,
            guard_result=guard_result,
            input_digest=input_digest,
            task_id=task_id,
            run_id=run_id,
            runtime_stage=runtime_stage,
            failure_code="state_transition_failed",
            failure_stage="state_machine",
            failure_reasons=(f"state_transition_failed:{exc.__class__.__name__}",),
            exception=exc,
            observed_at=observed_at,
        )

    for index, transition_hash in enumerate(transitions, start=1):
        trail.record(
            "local_runtime.state_transition",
            {
                "input_digest": input_digest,
                "run_id": run_id,
                "sequence": index,
                "task_id": task_id,
                "transition_hash": transition_hash,
            },
            observed_at=observed_at,
        )

    breaker = circuit_breaker if circuit_breaker is not None else CircuitBreaker(
        "local_runtime_provider_transport",
        CircuitBreakerConfig(failure_threshold=2, recovery_timeout_seconds=60.0),
    )
    retry_policy = retry_config if retry_config is not None else RetryConfig(
        max_attempts=2,
        base_delay_seconds=0.0,
        max_delay_seconds=0.0,
    )
    operation = provider_operation if provider_operation is not None else lambda: _execute_default_provider_transport(payload)

    retry_result: RetryResult | None = None
    try:
        retry_result = retry_call(
            lambda: breaker.call(operation),
            config=retry_policy,
            operation_name="local_runtime_provider_transport",
            sleeper=lambda _delay: None,
        )
    except Exception as exc:
        return _reject(
            trail=trail,
            guard_result=guard_result,
            input_digest=input_digest,
            task_id=task_id,
            run_id=run_id,
            runtime_stage=runtime_stage,
            failure_code="provider_transport_failed",
            failure_stage="provider_transport",
            failure_reasons=(f"provider_transport_failed:{exc.__class__.__name__}",),
            exception=exc,
            circuit_breaker=breaker,
            watchdog=active_watchdog,
            state_transition_hashes=tuple(transitions),
            observed_at=observed_at,
        )

    provider_result = retry_result.result
    if not isinstance(provider_result, TransportExecutionResult):
        return _reject(
            trail=trail,
            guard_result=guard_result,
            input_digest=input_digest,
            task_id=task_id,
            run_id=run_id,
            runtime_stage=runtime_stage,
            failure_code="provider_transport_invalid_result",
            failure_stage="provider_transport",
            failure_reasons=("provider_transport_invalid_result",),
            circuit_breaker=breaker,
            watchdog=active_watchdog,
            state_transition_hashes=tuple(transitions),
            observed_at=observed_at,
        )

    provider_receipt = provider_result.dry_run_receipt
    if not provider_result.accepted or provider_receipt is None:
        return _reject(
            trail=trail,
            guard_result=guard_result,
            input_digest=input_digest,
            task_id=task_id,
            run_id=run_id,
            runtime_stage=runtime_stage,
            failure_code="provider_dry_run_rejected",
            failure_stage="provider_transport",
            failure_reasons=("provider_transport_rejected",),
            circuit_breaker=breaker,
            watchdog=active_watchdog,
            state_transition_hashes=tuple(transitions),
            observed_at=observed_at,
        )

    if not (provider_receipt.dry_run and provider_receipt.no_network and provider_receipt.no_provider_call):
        return _reject(
            trail=trail,
            guard_result=guard_result,
            input_digest=input_digest,
            task_id=task_id,
            run_id=run_id,
            runtime_stage=runtime_stage,
            failure_code="provider_dry_run_boundary_failed",
            failure_stage="provider_transport",
            failure_reasons=("provider_dry_run_boundary_failed",),
            circuit_breaker=breaker,
            watchdog=active_watchdog,
            state_transition_hashes=tuple(transitions),
            observed_at=observed_at,
        )

    final_watchdog = active_watchdog.check(observed_at=observed_at)
    provider_entry = trail.record(
        "local_runtime.provider_dry_run_receipt",
        {
            "input_digest": input_digest,
            "provider_receipt_hash": provider_receipt.canonical_hash,
            "provider_receipt_id": provider_receipt.receipt_id,
            "run_id": run_id,
            "task_id": task_id,
        },
        observed_at=observed_at,
    )
    receipt = build_local_runtime_receipt(
        run_id=run_id,
        task_id=task_id,
        runtime_stage=runtime_stage,
        input_digest=input_digest,
        accepted=True,
        provider_dry_run_receipt_ref=provider_receipt.receipt_id,
        observed_at=observed_at,
    )
    receipt_entry = trail.record(
        "local_runtime.receipt_created",
        {
            "input_digest": input_digest,
            "receipt_hash": receipt.content_hash,
            "run_id": run_id,
            "task_id": task_id,
        },
        observed_at=observed_at,
    )

    audit_entries = trail.entries
    return LocalRuntimeOrchestrationResult(
        accepted=True,
        receipt=receipt,
        guard_result=guard_result,
        failure_bundle=None,
        provider_dry_run_receipt=provider_receipt,
        state_transition_hashes=tuple(transitions),
        audit_entry_hashes=tuple(entry.content_hash for entry in audit_entries),
        audit_chain_head=audit_entries[-1].hash_chain_entry.current_hash,
        retry_attempts=retry_result.attempts,
        retry_total_delay_seconds=retry_result.total_delay_seconds,
        circuit_breaker_snapshot=breaker.snapshot(),
        watchdog_snapshot=_watchdog_snapshot_dict(final_watchdog),
        boundary_flags=_boundary_flags(),
    )


def _reject(
    *,
    trail: AuditTrail,
    guard_result: LocalRuntimeGuardResult,
    input_digest: str,
    task_id: str,
    run_id: str,
    runtime_stage: str,
    failure_code: str,
    failure_stage: str,
    failure_reasons: tuple[str, ...],
    exception: BaseException | None = None,
    circuit_breaker: CircuitBreaker | None = None,
    watchdog: Watchdog | None = None,
    state_transition_hashes: tuple[str, ...] = (),
    observed_at: str | None = None,
) -> LocalRuntimeOrchestrationResult:
    bundle = build_local_runtime_failure_bundle(
        failure_code=failure_code,
        failure_stage=failure_stage,
        input_digest=input_digest,
        run_id=run_id,
        task_id=task_id,
        exception=exception,
    )
    trail.record(
        "local_runtime.rejected",
        {
            "failure_bundle_hash": bundle.content_hash,
            "failure_code": failure_code,
            "failure_reasons": list(failure_reasons),
            "input_digest": input_digest,
            "run_id": run_id,
            "runtime_stage": runtime_stage,
            "task_id": task_id,
        },
        observed_at=observed_at,
    )
    receipt = build_local_runtime_receipt(
        run_id=run_id,
        task_id=task_id,
        runtime_stage=runtime_stage,
        input_digest=input_digest,
        accepted=False,
        rejection_reason=",".join(failure_reasons),
        failure_bundle_ref=bundle.content_hash,
        observed_at=observed_at,
    )
    trail.record(
        "local_runtime.receipt_created",
        {
            "failure_bundle_hash": bundle.content_hash,
            "input_digest": input_digest,
            "receipt_hash": receipt.content_hash,
            "run_id": run_id,
            "task_id": task_id,
        },
        observed_at=observed_at,
    )
    audit_entries = trail.entries
    active_watchdog_snapshot = (
        _watchdog_snapshot_dict(watchdog.snapshot(observed_at=observed_at)) if watchdog is not None else {}
    )
    active_breaker_snapshot = circuit_breaker.snapshot() if circuit_breaker is not None else {}
    return LocalRuntimeOrchestrationResult(
        accepted=False,
        receipt=receipt,
        guard_result=guard_result,
        failure_bundle=bundle,
        provider_dry_run_receipt=None,
        state_transition_hashes=state_transition_hashes,
        audit_entry_hashes=tuple(entry.content_hash for entry in audit_entries),
        audit_chain_head=audit_entries[-1].hash_chain_entry.current_hash,
        retry_attempts=0,
        retry_total_delay_seconds=0.0,
        circuit_breaker_snapshot=active_breaker_snapshot,
        watchdog_snapshot=active_watchdog_snapshot,
        boundary_flags=_boundary_flags(),
    )


def _execute_default_provider_transport(payload: Mapping[str, object] | object) -> TransportExecutionResult:
    provider_request = _provider_request(payload)
    provider_id = str(provider_request.get("provider_id", "mock-finance"))
    capabilities = _capabilities(provider_request.get("capabilities", _DEFAULT_PROVIDER_CAPABILITIES))
    register_provider_adapter(
        ProviderAdapterDescriptor(
            provider_id=provider_id,
            capabilities=frozenset(capabilities),
            boundary_ref="local-runtime-dry-run-provider-boundary-v1",
            enabled=False,
            dry_run_only=True,
            no_network=True,
        )
    )
    transport_payload = {
        "provider_id": provider_id,
        "request_id": str(provider_request.get("request_id", "local-runtime-provider-request")),
        "capability_token": ",".join(capabilities),
        "evidence_binding": str(provider_request.get("evidence_binding", "local-runtime-evidence-binding")),
        "dry_run": True,
        "live_mode": False,
        "network_mode": False,
    }
    return execute_provider_transport(transport_payload)


def _provider_request(payload: Mapping[str, object] | object) -> Mapping[str, object]:
    if isinstance(payload, Mapping):
        value = payload.get("provider_request", {})
        if isinstance(value, Mapping):
            return value
    return {}


def _capabilities(value: object) -> tuple[str, ...]:
    if isinstance(value, (list, tuple, set, frozenset)):
        capabilities = tuple(str(item) for item in value if isinstance(item, str) and item.strip())
        if capabilities:
            return tuple(sorted(set(capabilities)))
    return _DEFAULT_PROVIDER_CAPABILITIES


def _input_digest(payload: Mapping[str, object] | object) -> str:
    return digest_payload(_safe_digest_material(payload, key="root"))


def _safe_digest_material(value: object, *, key: str) -> object:
    if isinstance(value, Mapping):
        return {
            str(item_key): _safe_digest_material(item_value, key=str(item_key))
            for item_key, item_value in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_safe_digest_material(item, key=key) for item in value]
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    if isinstance(value, str):
        if key in _DIGEST_VALUE_KEYS or value.startswith("sha256:"):
            return value
        return {"redacted": True, "type": "str"}
    return {"type": value.__class__.__name__}


def _payload_string(payload: Mapping[str, object] | object, field: str, *, default: str) -> str:
    if isinstance(payload, Mapping):
        value = payload.get(field)
        if isinstance(value, str) and value.strip():
            return value
    return default


def _watchdog_snapshot_dict(snapshot: object) -> dict[str, object]:
    if hasattr(snapshot, "deterministic_material"):
        material = snapshot.deterministic_material()  # type: ignore[attr-defined]
        observed_at = getattr(snapshot, "observed_at", None)
        seconds_since_feed = getattr(snapshot, "seconds_since_feed", None)
        return {
            **material,
            "observed_at": observed_at,
            "seconds_since_feed": seconds_since_feed,
            "control_only": True,
        }
    return {}


def _boundary_flags() -> dict[str, bool]:
    return {
        "dry_run_only": True,
        "live_provider_calls_allowed": False,
        "network_execution_allowed": False,
        "production_autonomy_allowed": False,
        "secret_or_env_reads_allowed": False,
        "sqlite_mutation_allowed": False,
        "subprocess_execution_allowed": False,
        "watchdog_control_only": True,
    }
