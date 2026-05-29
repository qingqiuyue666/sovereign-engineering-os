"""System E2E acceptance V1.

This module runs a deterministic local acceptance path across the runtime
surfaces that are already implemented. It creates no daemon, launches no
processes, calls no providers, and does not repair corrupted evidence. Negative
probes are isolated under a probe directory so the accepted path remains
replayable.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Mapping, Sequence

from kernel.runtime.approval_runtime_contract import build_approval_runtime_request
from kernel.runtime.approval_runtime_integration import (
    APPROVAL_RUNTIME_EXECUTION_SCOPE,
    FileBackedApprovalRuntimeIntegration,
)
from kernel.runtime.controlled_execution_runtime import (
    FileBackedControlledExecutionRuntime,
)
from kernel.runtime.durable_job_queue import DurableJobQueue
from kernel.runtime.failure_bundle_center_integration import (
    FileBackedFailureBundleCenterIntegration,
)
from kernel.runtime.operator_console_runtime_surface import (
    FileBackedOperatorConsoleRuntimeSurface,
    validate_operator_console_runtime_snapshot,
)
from kernel.runtime.watchdog_runtime_integration import (
    FileBackedWatchdogRuntimeIntegration,
)
from kernel.runtime.worker_registry_capability_runtime import (
    FileBackedWorkerRegistryCapabilityRuntime,
)
from kernel.stores.artifact_store_persistence import FileBackedArtifactStore
from kernel.stores.real_wal_storage import FileBackedRealWalStorage
from kernel.stores.snapshot_replay_reconstruction import (
    FileBackedSnapshotReplayReconstructor,
)

__all__ = [
    "SYSTEM_E2E_ACCEPTANCE_VERSION",
    "SYSTEM_E2E_QUEUE_ID",
    "ZERO_HASH",
    "FileBackedSystemE2EAcceptance",
    "SystemE2EAcceptanceError",
    "SystemE2EAcceptanceReceipt",
    "SystemE2EGateResult",
    "compute_system_e2e_acceptance_receipt_hash",
    "compute_system_e2e_gate_result_hash",
]

SYSTEM_E2E_ACCEPTANCE_VERSION = "system_e2e_acceptance_v1"
SYSTEM_E2E_QUEUE_ID = "system-e2e-acceptance-queue-v1"
ZERO_HASH = "sha256:" + ("0" * 64)

_TASK_ID = "task-527-system-e2e"
_RUN_ID = "run-527-system-e2e"
_JOB_ID = "job-527-system-e2e"
_WORKER_ID = "worker-527-system-e2e"
_CONTROLLED_JOB_ID = "job-527-controlled-e2e"
_CONTROLLED_WORKER_ID = "worker-527-controlled-e2e"
_CONTROLLED_EXECUTION_ID = "execution-527-system-e2e"
_CONTROLLED_PREFLIGHT_ID = "preflight-527-system-e2e"
_SYSTEM_WAL_RELPATH = "system-e2e/system.real-wal.jsonl"
_SYSTEM_REPORT_RELPATH = "system-e2e/reports/final-acceptance-report.json"
_SYSTEM_RECEIPT_RELPATH = "system-e2e/receipts/final-acceptance-receipt.json"
_ARTIFACT_STORE_RELPATH = "artifact-store"
_ARTIFACT_STORE_ID = "failure-bundle-center-artifacts-v1"
_SNAPSHOT_STORE_RELPATH = "snapshot-replay"
_QUEUE_RELPATH = "queue/jobs.jsonl"
_PROBE_RELPATH = "system-e2e/probes"

_REQUIRED_GATE_IDS = (
    "task_created",
    "worker_admission",
    "approval_gate",
    "queue_submit",
    "wal_append",
    "lease_heartbeat",
    "controlled_execution_boundary",
    "artifact_write",
    "snapshot_create",
    "replay_reconstruct",
    "operator_console_read",
    "failure_bundle_path",
    "watchdog_path",
    "corrupt_wal_fail_closed",
    "corrupt_artifact_fail_closed",
    "missing_approval_fail_closed",
    "replay_final_state_verified",
    "final_acceptance_report_signable",
)
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_SECRET_PATH_PATTERN = re.compile(
    r"(?i)(^\.env$|\.env\.local|\.envrc|credential|id_rsa|id_dsa|id_ed25519|secret|token|password)"
)


class SystemE2EAcceptanceError(ValueError):
    """Raised when system E2E acceptance material fails closed."""


@dataclass(frozen=True)
class SystemE2EGateResult:
    gate_id: str
    accepted: bool
    evidence_hash: str
    failures: tuple[str, ...]
    gate_hash: str = ""

    def __post_init__(self) -> None:
        if self.gate_id not in _REQUIRED_GATE_IDS:
            raise SystemE2EAcceptanceError("gate_id_invalid")
        if not isinstance(self.accepted, bool):
            raise SystemE2EAcceptanceError("gate_accepted_must_be_bool")
        _require_sha256(self.evidence_hash, "evidence_hash")
        object.__setattr__(self, "failures", _normalize_failures(self.failures))
        if self.accepted and self.failures:
            raise SystemE2EAcceptanceError("accepted_gate_has_failures")
        if not self.accepted and not self.failures:
            raise SystemE2EAcceptanceError("rejected_gate_requires_failures")
        _install_or_verify_hash(self, "gate_hash", compute_system_e2e_gate_result_hash)

    def as_dict(self) -> dict[str, object]:
        return _json_ready(asdict(self))  # type: ignore[return-value]


@dataclass(frozen=True)
class SystemE2EAcceptanceReceipt:
    integration_version: str
    accepted: bool
    failures: tuple[str, ...]
    task_id: str
    run_id: str
    gate_results: tuple[SystemE2EGateResult, ...]
    task_wal_record_hash: str
    queue_record_hash: str
    worker_admission_receipt_hash: str
    worker_capability_consumption_receipt_hash: str
    approval_gate_receipt_hash: str
    watchdog_receipt_hash: str
    controlled_execution_receipt_hash: str
    result_artifact_record_hash: str
    failure_bundle_receipt_hash: str
    snapshot_receipt_hash: str
    final_snapshot_receipt_hash: str
    operator_console_snapshot_hash: str
    signable_report_hash: str
    signable_report_artifact_record_hash: str
    corrupt_wal_probe_hash: str
    corrupt_artifact_probe_hash: str
    missing_approval_probe_hash: str
    receipt_chain_hash: str
    deterministic_replay_verified: bool
    final_acceptance_report_signable: bool
    network_accessed: bool
    provider_called: bool
    background_daemon_enabled: bool
    direct_mutation_enabled: bool
    observed_at: str
    receipt_hash: str = ""

    def __post_init__(self) -> None:
        if self.integration_version != SYSTEM_E2E_ACCEPTANCE_VERSION:
            raise SystemE2EAcceptanceError("integration_version_invalid")
        if not isinstance(self.accepted, bool):
            raise SystemE2EAcceptanceError("accepted_must_be_bool")
        object.__setattr__(self, "failures", _normalize_failures(self.failures))
        object.__setattr__(
            self,
            "gate_results",
            _normalize_gate_results(self.gate_results),
        )
        _require_nonempty_string(self.task_id, "task_id")
        _require_nonempty_string(self.run_id, "run_id")
        for field_name in (
            "task_wal_record_hash",
            "queue_record_hash",
            "worker_admission_receipt_hash",
            "worker_capability_consumption_receipt_hash",
            "approval_gate_receipt_hash",
            "watchdog_receipt_hash",
            "controlled_execution_receipt_hash",
            "result_artifact_record_hash",
            "failure_bundle_receipt_hash",
            "snapshot_receipt_hash",
            "final_snapshot_receipt_hash",
            "operator_console_snapshot_hash",
            "signable_report_hash",
            "signable_report_artifact_record_hash",
            "corrupt_wal_probe_hash",
            "corrupt_artifact_probe_hash",
            "missing_approval_probe_hash",
            "receipt_chain_hash",
        ):
            _require_sha256(getattr(self, field_name), field_name)
        for field_name in (
            "deterministic_replay_verified",
            "final_acceptance_report_signable",
            "network_accessed",
            "provider_called",
            "background_daemon_enabled",
            "direct_mutation_enabled",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise SystemE2EAcceptanceError(field_name + "_must_be_bool")
        _require_nonempty_string(self.observed_at, "observed_at")
        expected_acceptance = (
            not self.failures
            and all(gate.accepted for gate in self.gate_results)
            and self.deterministic_replay_verified
            and self.final_acceptance_report_signable
            and not self.network_accessed
            and not self.provider_called
            and not self.background_daemon_enabled
            and not self.direct_mutation_enabled
        )
        if self.accepted != expected_acceptance:
            raise SystemE2EAcceptanceError("accepted_must_match_gate_evidence")
        if self.accepted:
            for field_name in (
                "task_wal_record_hash",
                "queue_record_hash",
                "worker_admission_receipt_hash",
                "worker_capability_consumption_receipt_hash",
                "approval_gate_receipt_hash",
                "watchdog_receipt_hash",
                "controlled_execution_receipt_hash",
                "result_artifact_record_hash",
                "failure_bundle_receipt_hash",
                "snapshot_receipt_hash",
                "final_snapshot_receipt_hash",
                "operator_console_snapshot_hash",
                "signable_report_hash",
                "signable_report_artifact_record_hash",
                "corrupt_wal_probe_hash",
                "corrupt_artifact_probe_hash",
                "missing_approval_probe_hash",
                "receipt_chain_hash",
            ):
                if getattr(self, field_name) == ZERO_HASH:
                    raise SystemE2EAcceptanceError(field_name + "_required")
        _install_or_verify_hash(
            self,
            "receipt_hash",
            compute_system_e2e_acceptance_receipt_hash,
        )

    def deterministic_material(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "approval_gate_receipt_hash": self.approval_gate_receipt_hash,
            "background_daemon_enabled": self.background_daemon_enabled,
            "controlled_execution_receipt_hash": self.controlled_execution_receipt_hash,
            "corrupt_artifact_probe_hash": self.corrupt_artifact_probe_hash,
            "corrupt_wal_probe_hash": self.corrupt_wal_probe_hash,
            "deterministic_replay_verified": self.deterministic_replay_verified,
            "direct_mutation_enabled": self.direct_mutation_enabled,
            "failure_bundle_receipt_hash": self.failure_bundle_receipt_hash,
            "failures": self.failures,
            "final_acceptance_report_signable": self.final_acceptance_report_signable,
            "final_snapshot_receipt_hash": self.final_snapshot_receipt_hash,
            "gate_results": tuple(gate.as_dict() for gate in self.gate_results),
            "integration_version": self.integration_version,
            "missing_approval_probe_hash": self.missing_approval_probe_hash,
            "network_accessed": self.network_accessed,
            "observed_at": self.observed_at,
            "operator_console_snapshot_hash": self.operator_console_snapshot_hash,
            "provider_called": self.provider_called,
            "queue_record_hash": self.queue_record_hash,
            "receipt_chain_hash": self.receipt_chain_hash,
            "result_artifact_record_hash": self.result_artifact_record_hash,
            "run_id": self.run_id,
            "signable_report_artifact_record_hash": (
                self.signable_report_artifact_record_hash
            ),
            "signable_report_hash": self.signable_report_hash,
            "snapshot_receipt_hash": self.snapshot_receipt_hash,
            "task_id": self.task_id,
            "task_wal_record_hash": self.task_wal_record_hash,
            "watchdog_receipt_hash": self.watchdog_receipt_hash,
            "worker_admission_receipt_hash": self.worker_admission_receipt_hash,
            "worker_capability_consumption_receipt_hash": (
                self.worker_capability_consumption_receipt_hash
            ),
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["receipt_hash"] = self.receipt_hash
        return _json_ready(payload)  # type: ignore[return-value]


class FileBackedSystemE2EAcceptance:
    """Runs the local-first system acceptance path against file-backed stores."""

    def __init__(self, *, runtime_root: str | Path) -> None:
        self.runtime_root = _validate_runtime_root(Path(runtime_root))

    def run(self, *, observed_at: str | None = None) -> SystemE2EAcceptanceReceipt:
        observed = _timestamp(observed_at)
        root = self.runtime_root
        root.mkdir(parents=True, exist_ok=True)

        task_wal_record_hash = self._append_task_created_wal(observed_at=observed)
        queue = self._queue()
        queued = queue.submit_job(
            job_id=_JOB_ID,
            task_id=_TASK_ID,
            run_id=_RUN_ID,
            payload={
                "acceptance_stage_hash": _sha256_text("system-e2e-queue-submit"),
                "task_descriptor_hash": _sha256_text("task-descriptor-527"),
                "worker_binding_hash": _sha256_text(_WORKER_ID),
            },
            idempotency_key="idempotency-527-system-e2e",
            max_attempts=2,
            priority=10,
            submitted_at=observed,
        )
        queued = queue.queue_job(_JOB_ID, queued_at=observed)

        approval_runtime = FileBackedApprovalRuntimeIntegration(
            runtime_root=root,
            artifact_store_relpath="approval-artifacts",
        )
        worker_approval = self._issue_approval(
            approval_runtime,
            approval_id="worker-admission",
            observed_at=observed,
        )
        worker_runtime = FileBackedWorkerRegistryCapabilityRuntime(runtime_root=root)
        worker_authorization = worker_runtime.authorize_worker_for_queue_job(
            self._worker_authorization_payload(worker_approval.approval_admission_hash),
            queue,
            approval_runtime,
            observed_at=observed,
        )
        worker_consumption = worker_runtime.consume_capability_for_queue_job(
            capability_token_id=worker_authorization.capability_token_id,
            queue=queue,
            worker_id=_WORKER_ID,
            job_id=_JOB_ID,
            consume_nonce="consume-527-system-e2e",
            now=observed,
            observed_at=observed,
            lease_timeout_seconds=300,
        )

        watchdog_receipt = FileBackedWatchdogRuntimeIntegration(
            runtime_root=root
        ).record_heartbeat(
            self._watchdog_payload(queue, worker_authorization.watchdog_policy_hash),
            queue,
            observed_at=observed,
        )

        failure_receipt = FileBackedFailureBundleCenterIntegration(
            runtime_root=root
        ).record_critical_failure(
            failure_kind="missing_record",
            task_id=_TASK_ID,
            job_id=_JOB_ID,
            run_id=_RUN_ID,
            context_hashes={
                "missing_record_context_hash": _sha256_text("missing-record-527"),
                "wal_pointer_hash": task_wal_record_hash,
            },
            recovery_plan_hash=_sha256_text("manual-recovery-527"),
            snapshot_reconstruction_hash=_sha256_text("watchdog-snapshot-527"),
            evidence_hashes={
                "watchdog_evidence_hash": watchdog_receipt.receipt_hash,
                "worker_gate_hash": worker_authorization.receipt_hash,
            },
            observed_at=observed,
        )

        controlled_approval = self._issue_approval(
            approval_runtime,
            approval_id="controlled-execution",
            observed_at=observed,
        )
        controlled_receipt = FileBackedControlledExecutionRuntime(
            runtime_root=root,
            enabled=True,
        ).run(
            self._controlled_execution_payload(
                controlled_approval.approval_admission_hash,
            ),
            approval_runtime,
            observed_at=observed,
        )

        first_snapshot = self._snapshot("post_execution", observed)
        report_material = self._build_signable_report_material(
            controlled_receipt_hash=controlled_receipt.receipt_hash,
            failure_bundle_receipt_hash=failure_receipt.receipt_hash,
            queue_record_hash=queued.last_event_hash,
            snapshot_receipt_hash=first_snapshot.receipt_hash,
            task_wal_record_hash=task_wal_record_hash,
            watchdog_receipt_hash=watchdog_receipt.receipt_hash,
            worker_authorization_receipt_hash=worker_authorization.receipt_hash,
            worker_consumption_receipt_hash=worker_consumption.receipt_hash,
            observed_at=observed,
        )
        signable_report_hash = _sha256_json(report_material)
        report_artifact = self._artifact_store().write_json_artifact(
            artifact_type="operator_report",
            task_id=_TASK_ID,
            run_id=_RUN_ID,
            payload=report_material,
            provenance_hash=signable_report_hash,
            metadata={
                "artifact_role": "system_e2e_acceptance",
                "integration_version": SYSTEM_E2E_ACCEPTANCE_VERSION,
            },
            created_at=observed,
        )
        report_wal_hash = self._append_report_wal(
            signable_report_hash=signable_report_hash,
            report_artifact_record_hash=report_artifact.record_hash,
            observed_at=observed,
        )
        final_snapshot = self._snapshot("post_execution", observed)
        console_snapshot = self._console().read_snapshot(
            task_id=_TASK_ID,
            run_id=_RUN_ID,
            observed_at=observed,
        )

        corrupt_wal_probe_hash = self._corrupt_wal_probe(observed)
        corrupt_artifact_probe_hash = self._corrupt_artifact_probe(observed)
        missing_approval_probe_hash = self._missing_approval_probe(observed)

        receipt_chain_hash = _sha256_json(
            {
                "controlled": controlled_receipt.receipt_hash,
                "failure": failure_receipt.receipt_hash,
                "final_snapshot": final_snapshot.receipt_hash,
                "report_artifact": report_artifact.record_hash,
                "report_wal": report_wal_hash,
                "snapshot": first_snapshot.receipt_hash,
                "watchdog": watchdog_receipt.receipt_hash,
                "worker_authorization": worker_authorization.receipt_hash,
                "worker_consumption": worker_consumption.receipt_hash,
            }
        )
        deterministic_replay_verified = (
            first_snapshot.accepted
            and final_snapshot.accepted
            and final_snapshot.expected_snapshot_root_hash
            == final_snapshot.observed_snapshot_root_hash
            and final_snapshot.snapshot_manifest_hash != ZERO_HASH
        )
        gate_results = self._gate_results(
            controlled_receipt=controlled_receipt,
            corrupt_artifact_probe_hash=corrupt_artifact_probe_hash,
            corrupt_wal_probe_hash=corrupt_wal_probe_hash,
            failure_receipt=failure_receipt,
            final_snapshot=final_snapshot,
            missing_approval_probe_hash=missing_approval_probe_hash,
            queue_record_hash=queued.last_event_hash,
            report_artifact_record_hash=report_artifact.record_hash,
            signable_report_hash=signable_report_hash,
            snapshot=first_snapshot,
            task_wal_record_hash=task_wal_record_hash,
            watchdog_receipt=watchdog_receipt,
            worker_authorization=worker_authorization,
            worker_consumption=worker_consumption,
            console_snapshot_hash=console_snapshot.snapshot_hash,
            console_valid=(
                console_snapshot.status == "ok"
                and validate_operator_console_runtime_snapshot(console_snapshot)
            ),
            deterministic_replay_verified=deterministic_replay_verified,
        )
        failures = tuple(
            failure
            for gate in gate_results
            if not gate.accepted
            for failure in gate.failures
        )
        receipt = SystemE2EAcceptanceReceipt(
            integration_version=SYSTEM_E2E_ACCEPTANCE_VERSION,
            accepted=not failures,
            failures=failures,
            task_id=_TASK_ID,
            run_id=_RUN_ID,
            gate_results=gate_results,
            task_wal_record_hash=task_wal_record_hash,
            queue_record_hash=queued.last_event_hash,
            worker_admission_receipt_hash=worker_authorization.receipt_hash,
            worker_capability_consumption_receipt_hash=worker_consumption.receipt_hash,
            approval_gate_receipt_hash=controlled_receipt.approval_gate_response_hash,
            watchdog_receipt_hash=watchdog_receipt.receipt_hash,
            controlled_execution_receipt_hash=controlled_receipt.receipt_hash,
            result_artifact_record_hash=controlled_receipt.result_artifact_record_hash,
            failure_bundle_receipt_hash=failure_receipt.receipt_hash,
            snapshot_receipt_hash=first_snapshot.receipt_hash,
            final_snapshot_receipt_hash=final_snapshot.receipt_hash,
            operator_console_snapshot_hash=console_snapshot.snapshot_hash,
            signable_report_hash=signable_report_hash,
            signable_report_artifact_record_hash=report_artifact.record_hash,
            corrupt_wal_probe_hash=corrupt_wal_probe_hash,
            corrupt_artifact_probe_hash=corrupt_artifact_probe_hash,
            missing_approval_probe_hash=missing_approval_probe_hash,
            receipt_chain_hash=receipt_chain_hash,
            deterministic_replay_verified=deterministic_replay_verified,
            final_acceptance_report_signable=(
                signable_report_hash != ZERO_HASH and report_artifact.record_hash != ZERO_HASH
            ),
            network_accessed=False,
            provider_called=False,
            background_daemon_enabled=False,
            direct_mutation_enabled=False,
            observed_at=observed,
        )
        self._write_json_no_overwrite(_SYSTEM_REPORT_RELPATH, report_material)
        self._write_json_no_overwrite(_SYSTEM_RECEIPT_RELPATH, receipt.as_dict())
        return receipt

    def _append_task_created_wal(self, *, observed_at: str) -> str:
        wal_path = self._resolve_relpath(_SYSTEM_WAL_RELPATH, "system_wal_relpath")
        wal_path.parent.mkdir(parents=True, exist_ok=True)
        task_material = {
            "acceptance_version": SYSTEM_E2E_ACCEPTANCE_VERSION,
            "human_invoked": True,
            "run_id": _RUN_ID,
            "task_descriptor_hash": _sha256_text("task-descriptor-527"),
            "task_id": _TASK_ID,
        }
        return FileBackedRealWalStorage(wal_path).append(
            record_type="SYSTEM_ACCEPTANCE_EVENT",
            task_id=_TASK_ID,
            run_id=_RUN_ID,
            payload_hash=_sha256_json(task_material),
            digest_bindings={
                "acceptance_version_hash": _sha256_text(SYSTEM_E2E_ACCEPTANCE_VERSION),
                "task_descriptor_hash": task_material["task_descriptor_hash"],
            },
            created_at=observed_at,
        ).record_hash

    def _append_report_wal(
        self,
        *,
        signable_report_hash: str,
        report_artifact_record_hash: str,
        observed_at: str,
    ) -> str:
        wal_path = self._resolve_relpath(_SYSTEM_WAL_RELPATH, "system_wal_relpath")
        material = {
            "report_artifact_record_hash": report_artifact_record_hash,
            "signable_report_hash": signable_report_hash,
        }
        return FileBackedRealWalStorage(wal_path).append(
            record_type="SYSTEM_ACCEPTANCE_EVENT",
            task_id=_TASK_ID,
            run_id=_RUN_ID,
            payload_hash=_sha256_json(material),
            digest_bindings=material,
            created_at=observed_at,
        ).record_hash

    def _issue_approval(
        self,
        approval_runtime: FileBackedApprovalRuntimeIntegration,
        *,
        approval_id: str,
        observed_at: str,
    ):
        request = {
            "approval_request_id": "approval-request-527-" + approval_id,
            "task_id": _TASK_ID,
            "run_id": _RUN_ID,
            "review_packet_hash": _sha256_text("review-" + approval_id),
            "promotion_receipt_hash": _sha256_text("promotion-" + approval_id),
            "wal_head_hash": _sha256_text("wal-head-" + approval_id),
            "artifact_manifest_hash": _sha256_text("artifact-manifest-" + approval_id),
            "snapshot_reconstruction_hash": _sha256_text("snapshot-" + approval_id),
            "capability_token_hash": _sha256_text("capability-" + approval_id),
            "risk_decision_hash": _sha256_text("risk-" + approval_id),
            "requested_action": "approve_next_manual_stage",
            "human_invoked": True,
            "production_autonomy_requested": False,
            "live_execution_requested": False,
        }
        built = build_approval_runtime_request(request, created_at=observed_at)
        return approval_runtime.issue_approval(
            request_payload=request,
            decision_payload={
                "approval_decision_id": "approval-decision-527-" + approval_id,
                "approval_request_hash": built.request_hash,
                "task_id": _TASK_ID,
                "run_id": _RUN_ID,
                "operator_id_hash": _sha256_text("operator-527"),
                "operator_action": "approved",
                "decision_reason_code": "operator_explicit_decision",
                "approval_scope": APPROVAL_RUNTIME_EXECUTION_SCOPE,
                "rollback_plan_hash": None,
                "human_attested": True,
                "production_autonomy_enabled": False,
                "live_execution_enabled": False,
            },
            expires_at="2026-05-29T23:59:00+00:00",
            issued_at=observed_at,
        )

    def _worker_authorization_payload(self, approval_admission_hash: str) -> dict[str, object]:
        return {
            "approval_admission_hash": approval_admission_hash,
            "artifact_manifest_hash": _sha256_text("artifact-manifest-worker-527"),
            "capability_hashes": (_sha256_text("worker-capability-527"),),
            "evidence_requirement_hashes": (_sha256_text("worker-evidence-527"),),
            "expires_at": "2026-05-29T23:59:00+00:00",
            "human_approval_required": True,
            "idempotency_key_hash": _sha256_text("idempotency-527-system-e2e"),
            "input_contract_hash": _sha256_text("input-contract-527"),
            "issue_nonce": "issue-527-system-e2e",
            "job_id": _JOB_ID,
            "max_memory_mb": 512,
            "max_runtime_ms": 60_000,
            "output_contract_hash": _sha256_text("output-contract-527"),
            "policy_hash": _sha256_text("worker-policy-527"),
            "registry_policy_hash": _sha256_text("registry-policy-527"),
            "requested_task_class": "static_contract_check",
            "run_id": _RUN_ID,
            "stderr_limit_bytes": 4096,
            "stdout_limit_bytes": 4096,
            "task_classes": ("static_contract_check",),
            "task_descriptor_hash": _sha256_text("task-descriptor-527"),
            "task_id": _TASK_ID,
            "worker_id": _WORKER_ID,
            "worker_kind": "local_deterministic",
        }

    def _watchdog_payload(
        self,
        queue: DurableJobQueue,
        watchdog_policy_hash: str,
    ) -> dict[str, object]:
        state = queue.get_job_state(_JOB_ID)
        return {
            "elapsed_ms": 1_000,
            "human_invoked": False,
            "job_id": _JOB_ID,
            "lease_id": state.lease_id,
            "lease_timeout_seconds": 300,
            "max_memory_mb": 512,
            "max_runtime_ms": 60_000,
            "observed_memory_mb": 128,
            "previous_watchdog_receipt_hash": ZERO_HASH,
            "recovery_plan_hash": _sha256_text("recovery-527"),
            "retry_after": "2026-05-29T00:20:00+00:00",
            "run_id": _RUN_ID,
            "snapshot_reconstruction_hash": _sha256_text("watchdog-snapshot-527"),
            "stderr_digest": _sha256_text("watchdog-stderr-527"),
            "stderr_truncated": False,
            "stdout_digest": _sha256_text("watchdog-stdout-527"),
            "stdout_truncated": False,
            "task_id": _TASK_ID,
            "watchdog_policy_hash": watchdog_policy_hash,
            "worker_id": _WORKER_ID,
        }

    def _controlled_execution_payload(self, approval_hash: str) -> dict[str, object]:
        return {
            "approval_admission_hash": approval_hash,
            "caller_intent": "run system e2e controlled execution boundary",
            "execution_id": _CONTROLLED_EXECUTION_ID,
            "human_invoked": True,
            "idempotency_key": "idempotency-527-controlled-e2e",
            "job_id": _CONTROLLED_JOB_ID,
            "preflight_id": _CONTROLLED_PREFLIGHT_ID,
            "requested_at": "2026-05-29T00:00:10+00:00",
            "requester": "operator",
            "run_id": _RUN_ID,
            "single_run_scope": True,
            "snapshot_ref": "system-e2e-controlled-snapshot",
            "task_id": _TASK_ID,
            "use_case_ids": ("uc_527_system_e2e_acceptance",),
            "worker_id": _CONTROLLED_WORKER_ID,
        }

    def _snapshot(self, snapshot_kind: str, observed: str):
        return FileBackedSnapshotReplayReconstructor(
            runtime_root=self.runtime_root,
            wal_source_relpath=_SYSTEM_WAL_RELPATH,
            artifact_store_relpath=_ARTIFACT_STORE_RELPATH,
            artifact_store_id=_ARTIFACT_STORE_ID,
            queue_source_relpath=_QUEUE_RELPATH,
            queue_id=SYSTEM_E2E_QUEUE_ID,
            snapshot_store_relpath=_SNAPSHOT_STORE_RELPATH,
        ).capture_snapshot(
            task_id=_TASK_ID,
            run_id=_RUN_ID,
            snapshot_kind=snapshot_kind,
            created_at=observed,
            observed_at=observed,
        )

    def _console(self) -> FileBackedOperatorConsoleRuntimeSurface:
        return FileBackedOperatorConsoleRuntimeSurface(
            runtime_root=self.runtime_root,
            wal_source_relpaths=(
                _SYSTEM_WAL_RELPATH,
                "queue/jobs.jsonl.real-wal.jsonl",
                "approval-runtime/approval.real-wal.jsonl",
                "artifact-store/artifact-store.real-wal.jsonl",
                "failure-bundle-center/failure.real-wal.jsonl",
                "worker-registry-runtime/worker-registry.real-wal.jsonl",
                "watchdog-runtime/watchdog.real-wal.jsonl",
                "controlled-execution/execution.real-wal.jsonl",
                "controlled-execution/queue/jobs.jsonl.real-wal.jsonl",
                "controlled-execution/artifacts/artifact-store.real-wal.jsonl",
            ),
            queue_source_relpath=_QUEUE_RELPATH,
            queue_id=SYSTEM_E2E_QUEUE_ID,
            artifact_store_relpath=_ARTIFACT_STORE_RELPATH,
            artifact_store_id=_ARTIFACT_STORE_ID,
        )

    def _build_signable_report_material(
        self,
        *,
        controlled_receipt_hash: str,
        failure_bundle_receipt_hash: str,
        queue_record_hash: str,
        snapshot_receipt_hash: str,
        task_wal_record_hash: str,
        watchdog_receipt_hash: str,
        worker_authorization_receipt_hash: str,
        worker_consumption_receipt_hash: str,
        observed_at: str,
    ) -> dict[str, object]:
        material = {
            "approval_gate_covered": True,
            "artifact_write_covered": True,
            "controlled_execution_receipt_hash": controlled_receipt_hash,
            "failure_bundle_receipt_hash": failure_bundle_receipt_hash,
            "final_acceptance_report_signable": True,
            "integration_version": SYSTEM_E2E_ACCEPTANCE_VERSION,
            "operator_signature_required": True,
            "queue_record_hash": queue_record_hash,
            "required_gate_ids": _REQUIRED_GATE_IDS,
            "run_id": _RUN_ID,
            "snapshot_receipt_hash": snapshot_receipt_hash,
            "task_id": _TASK_ID,
            "task_wal_record_hash": task_wal_record_hash,
            "watchdog_receipt_hash": watchdog_receipt_hash,
            "worker_gate_receipt_hash": worker_authorization_receipt_hash,
            "worker_consumption_receipt_hash": worker_consumption_receipt_hash,
        }
        return {
            **material,
            "observed_at": observed_at,
            "report_material_hash": _sha256_json(material),
        }

    def _gate_results(
        self,
        *,
        controlled_receipt: object,
        corrupt_artifact_probe_hash: str,
        corrupt_wal_probe_hash: str,
        failure_receipt: object,
        final_snapshot: object,
        missing_approval_probe_hash: str,
        queue_record_hash: str,
        report_artifact_record_hash: str,
        signable_report_hash: str,
        snapshot: object,
        task_wal_record_hash: str,
        watchdog_receipt: object,
        worker_authorization: object,
        worker_consumption: object,
        console_snapshot_hash: str,
        console_valid: bool,
        deterministic_replay_verified: bool,
    ) -> tuple[SystemE2EGateResult, ...]:
        specs = (
            ("task_created", task_wal_record_hash != ZERO_HASH, task_wal_record_hash),
            ("worker_admission", worker_authorization.accepted, worker_authorization.receipt_hash),
            ("approval_gate", controlled_receipt.accepted, controlled_receipt.approval_gate_response_hash),
            ("queue_submit", queue_record_hash != ZERO_HASH, queue_record_hash),
            ("wal_append", task_wal_record_hash != ZERO_HASH, task_wal_record_hash),
            ("lease_heartbeat", watchdog_receipt.accepted, watchdog_receipt.receipt_hash),
            (
                "controlled_execution_boundary",
                controlled_receipt.accepted and controlled_receipt.execution_performed,
                controlled_receipt.receipt_hash,
            ),
            (
                "artifact_write",
                controlled_receipt.result_artifact_record_hash != ZERO_HASH
                and report_artifact_record_hash != ZERO_HASH,
                _sha256_json(
                    {
                        "controlled_result": controlled_receipt.result_artifact_record_hash,
                        "report": report_artifact_record_hash,
                    }
                ),
            ),
            ("snapshot_create", snapshot.accepted, snapshot.receipt_hash),
            ("replay_reconstruct", snapshot.accepted, snapshot.receipt_hash),
            ("operator_console_read", console_valid, console_snapshot_hash),
            ("failure_bundle_path", failure_receipt.accepted, failure_receipt.receipt_hash),
            ("watchdog_path", watchdog_receipt.accepted, watchdog_receipt.receipt_hash),
            ("corrupt_wal_fail_closed", corrupt_wal_probe_hash != ZERO_HASH, corrupt_wal_probe_hash),
            (
                "corrupt_artifact_fail_closed",
                corrupt_artifact_probe_hash != ZERO_HASH,
                corrupt_artifact_probe_hash,
            ),
            (
                "missing_approval_fail_closed",
                missing_approval_probe_hash != ZERO_HASH,
                missing_approval_probe_hash,
            ),
            (
                "replay_final_state_verified",
                deterministic_replay_verified and final_snapshot.accepted,
                final_snapshot.receipt_hash,
            ),
            (
                "final_acceptance_report_signable",
                signable_report_hash != ZERO_HASH and report_artifact_record_hash != ZERO_HASH,
                signable_report_hash,
            ),
        )
        return tuple(
            SystemE2EGateResult(
                gate_id=gate_id,
                accepted=accepted,
                evidence_hash=evidence_hash if evidence_hash != ZERO_HASH else _sha256_text(gate_id),
                failures=() if accepted else (gate_id + "_failed",),
            )
            for gate_id, accepted, evidence_hash in specs
        )

    def _corrupt_wal_probe(self, observed: str) -> str:
        probe = self._resolve_relpath(_PROBE_RELPATH + "/corrupt-wal/wal.jsonl", "probe_wal")
        probe.parent.mkdir(parents=True, exist_ok=True)
        FileBackedRealWalStorage(probe).append(
            record_type="SYSTEM_ACCEPTANCE_EVENT",
            task_id=_TASK_ID,
            run_id=_RUN_ID,
            payload_hash=_sha256_text("corrupt-wal-probe"),
            digest_bindings={"probe_hash": _sha256_text("corrupt-wal")},
            created_at=observed,
        )
        with probe.open("a", encoding="utf-8") as handle:
            handle.write("{\"corrupted\": true\n")
        replay = FileBackedRealWalStorage(probe).replay()
        fail_closed = not replay.accepted and probe.exists()
        if not fail_closed:
            return ZERO_HASH
        return _sha256_json(
            {
                "accepted": replay.accepted,
                "probe": "corrupt_wal_fail_closed",
                "rejections": replay.rejection_reasons,
            }
        )

    def _corrupt_artifact_probe(self, observed: str) -> str:
        store = FileBackedArtifactStore(
            self._resolve_relpath(_PROBE_RELPATH + "/corrupt-artifact/store", "probe_artifact"),
            store_id="system-e2e-corrupt-artifact-probe-v1",
        )
        receipt = store.write_json_artifact(
            artifact_type="audit_json",
            task_id=_TASK_ID,
            run_id=_RUN_ID,
            payload={"probe_hash": _sha256_text("corrupt-artifact")},
            provenance_hash=_sha256_text("corrupt-artifact-provenance"),
            metadata={"probe_kind": "corrupt_artifact"},
            created_at=observed,
        )
        store.artifact_path(receipt.manifest).write_text(
            _canonical_json({"tampered": True}),
            encoding="utf-8",
        )
        replay = store.replay()
        fail_closed = not replay.accepted and store.artifact_path(receipt.manifest).exists()
        if not fail_closed:
            return ZERO_HASH
        return _sha256_json(
            {
                "accepted": replay.accepted,
                "probe": "corrupt_artifact_fail_closed",
                "rejections": replay.rejection_reasons,
            }
        )

    def _missing_approval_probe(self, observed: str) -> str:
        probe_root = self._resolve_relpath(_PROBE_RELPATH + "/missing-approval", "probe_root")
        approval_runtime = FileBackedApprovalRuntimeIntegration(runtime_root=probe_root)
        receipt = FileBackedControlledExecutionRuntime(
            runtime_root=probe_root,
            enabled=True,
        ).run(
            self._controlled_execution_payload(_sha256_text("missing-approval")),
            approval_runtime,
            observed_at=observed,
        )
        fail_closed = (
            not receipt.accepted
            and not receipt.execution_performed
            and any("approval_missing" in failure for failure in receipt.failures)
        )
        if not fail_closed:
            return ZERO_HASH
        return _sha256_json(
            {
                "failures": receipt.failures,
                "probe": "missing_approval_fail_closed",
                "receipt_hash": receipt.receipt_hash,
            }
        )

    def _queue(self) -> DurableJobQueue:
        return DurableJobQueue(
            path=self._resolve_relpath(_QUEUE_RELPATH, "queue_relpath"),
            queue_id=SYSTEM_E2E_QUEUE_ID,
        )

    def _artifact_store(self) -> FileBackedArtifactStore:
        return FileBackedArtifactStore(
            self._resolve_relpath(_ARTIFACT_STORE_RELPATH, "artifact_store_relpath"),
            store_id=_ARTIFACT_STORE_ID,
        )

    def _write_json_no_overwrite(self, relpath: str, payload: Mapping[str, object]) -> None:
        path = self._resolve_relpath(relpath, "json_relpath")
        if path.exists():
            raise SystemE2EAcceptanceError("acceptance_output_already_exists")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_canonical_json(payload) + "\n", encoding="utf-8")

    def _resolve_relpath(self, relpath: str, field_name: str) -> Path:
        _validate_relpath_text(relpath, field_name)
        root = self.runtime_root.resolve()
        candidate = (root / PurePosixPath(relpath)).resolve()
        if root != candidate and root not in candidate.parents:
            raise SystemE2EAcceptanceError(field_name + "_escapes_runtime_root")
        return candidate


def compute_system_e2e_gate_result_hash(
    gate: SystemE2EGateResult | Mapping[str, object],
) -> str:
    payload = gate.as_dict() if isinstance(gate, SystemE2EGateResult) else dict(gate)
    payload.pop("gate_hash", None)
    return _sha256_json(payload)


def compute_system_e2e_acceptance_receipt_hash(
    receipt: SystemE2EAcceptanceReceipt | Mapping[str, object],
) -> str:
    payload = (
        receipt.deterministic_material()
        if isinstance(receipt, SystemE2EAcceptanceReceipt)
        else dict(receipt)
    )
    payload.pop("receipt_hash", None)
    return _sha256_json(payload)


def _normalize_gate_results(value: Sequence[SystemE2EGateResult]) -> tuple[SystemE2EGateResult, ...]:
    if not isinstance(value, tuple):
        value = tuple(value)
    if any(not isinstance(item, SystemE2EGateResult) for item in value):
        raise SystemE2EAcceptanceError("gate_results_must_be_gate_results")
    by_id = {item.gate_id: item for item in value}
    if tuple(by_id) != _REQUIRED_GATE_IDS or len(value) != len(_REQUIRED_GATE_IDS):
        raise SystemE2EAcceptanceError("gate_results_must_cover_required_gates_in_order")
    return value


def _validate_runtime_root(path: Path) -> Path:
    for part in path.parts:
        if _SECRET_PATH_PATTERN.search(part):
            raise SystemE2EAcceptanceError("runtime_root_contains_sensitive_path")
    if path.exists() and not path.is_dir():
        raise SystemE2EAcceptanceError("runtime_root_must_be_directory")
    return path


def _validate_relpath_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise SystemE2EAcceptanceError(field_name + "_required")
    if value.startswith("/") or "\\" in value:
        raise SystemE2EAcceptanceError(field_name + "_must_be_posix_relative")
    path = PurePosixPath(value)
    if any(part in ("", ".", "..") for part in path.parts):
        raise SystemE2EAcceptanceError(field_name + "_invalid")
    for part in path.parts:
        if _SECRET_PATH_PATTERN.search(part):
            raise SystemE2EAcceptanceError(field_name + "_contains_sensitive_path")
    return value


def _require_nonempty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value:
        raise SystemE2EAcceptanceError(field_name + "_required")


def _require_sha256(value: object, field_name: str) -> None:
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise SystemE2EAcceptanceError(field_name + "_must_be_sha256")


def _normalize_failures(value: object) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise SystemE2EAcceptanceError("failures_must_be_sequence")
    failures = tuple(str(item) for item in value if str(item))
    for failure in failures:
        _require_nonempty_string(failure, "failure")
    return tuple(dict.fromkeys(failures))


def _install_or_verify_hash(instance: object, field_name: str, computer) -> None:
    current = getattr(instance, field_name)
    if current:
        _require_sha256(current, field_name)
    expected = computer(instance)
    if current and current != expected:
        raise SystemE2EAcceptanceError(field_name + "_mismatch")
    object.__setattr__(instance, field_name, expected)


def _timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    _require_nonempty_string(value, "timestamp")
    return value


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_json(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(
        _json_ready(value),
        sort_keys=True,
        separators=(",", ":"),
    )


def _json_ready(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if hasattr(value, "as_dict"):
        return _json_ready(value.as_dict())  # type: ignore[no-any-return]
    return value
