"""Operator console runtime surface V1.

Builds a read-only operator projection from persisted local evidence. The
surface reads existing WAL, queue, artifact, approval, failure-bundle,
snapshot/replay, worker, and watchdog stores; it never creates missing stores,
repairs corruption, writes console state, dispatches work, or executes tools.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path, PurePosixPath
import re
from typing import Iterable, Mapping, Sequence

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_bool, strict_digest, strict_nonempty_string
from kernel.runtime.approval_runtime_integration import (
    ApprovalRuntimeConsumptionReceipt,
    ApprovalRuntimeIntegratedReceipt,
)
from kernel.runtime.durable_job_queue import DurableJobQueue
from kernel.runtime.failure_bundle_center_integration import (
    FailureBundleCenterIntegratedReceipt,
)
from kernel.runtime.operator_console_readonly_contract import (
    build_console_readonly_data_source,
    build_operator_console_readonly_snapshot,
)
from kernel.runtime.watchdog_runtime_integration import (
    WatchdogOperatorState,
    WatchdogRuntimeReceipt,
)
from kernel.runtime.worker_registry_capability_runtime import (
    WorkerCapabilityToken,
    WorkerRegistryCapabilityRuntimeReceipt,
)
from kernel.stores.artifact_store_persistence import FileBackedArtifactStore
from kernel.stores.real_wal_storage import FileBackedRealWalStorage
from kernel.stores.snapshot_replay_reconstruction import SnapshotReplayOutputReceipt

__all__ = [
    "OPERATOR_CONSOLE_RUNTIME_SURFACE_VERSION",
    "ZERO_HASH",
    "FileBackedOperatorConsoleRuntimeSurface",
    "OperatorConsoleMutationRouteReceipt",
    "OperatorConsoleRuntimePanel",
    "OperatorConsoleRuntimeSnapshot",
    "OperatorConsoleRuntimeSurfaceError",
    "admit_operator_console_mutation_route",
    "compute_operator_console_mutation_route_receipt_hash",
    "compute_operator_console_runtime_panel_hash",
    "compute_operator_console_runtime_snapshot_hash",
    "validate_operator_console_runtime_snapshot",
]

OPERATOR_CONSOLE_RUNTIME_SURFACE_VERSION = "operator_console_runtime_surface_v1"
ZERO_HASH = "sha256:" + ("0" * 64)

_READ_ONLY_REDACTION_POLICY_HASH = digest_payload(
    {"policy": "operator_console_runtime_surface_digest_only_redaction_v1"}
)
_CONTROLLED_EXECUTION_ROUTE = "approval_controlled_execution_runtime"
_DEFAULT_PANEL_IDS = (
    "summary",
    "wal",
    "queue",
    "artifacts",
    "approvals",
    "failures",
    "replay",
    "workers",
    "watchdog",
    "system_health",
)
_STATUS_VALUES = frozenset({"ok", "stale", "failure"})
_SEVERITY_VALUES = frozenset({"green", "yellow", "red"})
_SOURCE_TYPE_BY_PANEL = {
    "wal": "wal",
    "queue": "job_queue",
    "artifacts": "artifact_store",
    "approvals": "approval_runtime",
    "failures": "failure_bundle_center",
    "replay": "replay_report",
    "workers": "worker_registry",
    "watchdog": "watchdog_receipts",
}
_FORBIDDEN_MUTATION_FIELDS = frozenset(
    {
        "args",
        "argv",
        "body",
        "command",
        "command_id",
        "command_line",
        "content",
        "cwd",
        "env",
        "environment",
        "executable",
        "executable_path",
        "filesystem_path",
        "network",
        "output",
        "path",
        "payload",
        "prompt",
        "raw_command",
        "raw_output",
        "raw_stderr",
        "raw_stdout",
        "shell",
        "stderr",
        "stdout",
        "subprocess",
        "text",
        "timeout",
        "url",
        "value",
        "workdir",
    }
)
_SECRET_KEY_PATTERN = re.compile(
    r"(?i)(api[_-]?key|auth|authorization|credential|password|private[_-]?key|secret|token)"
)
_SECRET_VALUE_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{16,}"),
    re.compile(r"(?i)\bsk-[a-z0-9]{20,}"),
    re.compile(
        r"(?s)-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----"
    ),
)
_SECRET_PATH_PATTERN = re.compile(
    r"(?i)(^\.env$|\.env\.local|\.envrc|credential|id_rsa|id_dsa|id_ed25519|secret|token|password)"
)


class OperatorConsoleRuntimeSurfaceError(ValueError):
    """Raised when the console runtime surface request is invalid."""


@dataclass(frozen=True)
class OperatorConsoleRuntimePanel:
    integration_version: str
    panel_id: str
    source_type: str
    status: str
    severity: str
    read_only: bool
    mutation_enabled: bool
    command_enabled: bool
    dispatch_enabled: bool
    live_fetch_enabled: bool
    external_tool_enabled: bool
    stale: bool
    record_count: int
    evidence_hash: str
    wal_record_hash: str
    latest_record_hash: str
    failures: tuple[str, ...]
    panel_hash: str = ""

    def __post_init__(self) -> None:
        if self.integration_version != OPERATOR_CONSOLE_RUNTIME_SURFACE_VERSION:
            raise OperatorConsoleRuntimeSurfaceError("panel_version_invalid")
        if self.panel_id not in _DEFAULT_PANEL_IDS:
            raise OperatorConsoleRuntimeSurfaceError("panel_id_invalid")
        if self.source_type and self.source_type not in set(_SOURCE_TYPE_BY_PANEL.values()) | {"summary", "system_health"}:
            raise OperatorConsoleRuntimeSurfaceError("source_type_invalid")
        if self.status not in _STATUS_VALUES:
            raise OperatorConsoleRuntimeSurfaceError("panel_status_invalid")
        if self.severity not in _SEVERITY_VALUES:
            raise OperatorConsoleRuntimeSurfaceError("panel_severity_invalid")
        for field_name in (
            "read_only",
            "mutation_enabled",
            "command_enabled",
            "dispatch_enabled",
            "live_fetch_enabled",
            "external_tool_enabled",
            "stale",
        ):
            if not strict_bool(getattr(self, field_name)):
                raise OperatorConsoleRuntimeSurfaceError(field_name + "_must_be_bool")
        if not _read_only_flags_valid(self):
            raise OperatorConsoleRuntimeSurfaceError("panel_must_be_read_only")
        if not isinstance(self.record_count, int) or isinstance(self.record_count, bool):
            raise OperatorConsoleRuntimeSurfaceError("record_count_must_be_int")
        if self.record_count < 0:
            raise OperatorConsoleRuntimeSurfaceError("record_count_must_be_nonnegative")
        for field_name in ("evidence_hash", "wal_record_hash", "latest_record_hash"):
            if not strict_digest(getattr(self, field_name)):
                raise OperatorConsoleRuntimeSurfaceError(field_name + "_must_be_digest")
        object.__setattr__(
            self,
            "failures",
            _normalize_failures(self.failures, allow_empty=True),
        )
        if self.status == "ok" and self.failures:
            raise OperatorConsoleRuntimeSurfaceError("ok_panel_cannot_have_failures")
        if self.status == "failure" and not self.failures:
            raise OperatorConsoleRuntimeSurfaceError("failure_panel_requires_failures")
        if self.status == "stale" and not self.stale:
            raise OperatorConsoleRuntimeSurfaceError("stale_panel_requires_stale_flag")
        _install_or_verify_hash(self, "panel_hash", compute_operator_console_runtime_panel_hash)

    def deterministic_material(self) -> dict[str, object]:
        return {
            "command_enabled": self.command_enabled,
            "dispatch_enabled": self.dispatch_enabled,
            "evidence_hash": self.evidence_hash,
            "external_tool_enabled": self.external_tool_enabled,
            "failures": self.failures,
            "integration_version": self.integration_version,
            "latest_record_hash": self.latest_record_hash,
            "live_fetch_enabled": self.live_fetch_enabled,
            "mutation_enabled": self.mutation_enabled,
            "panel_id": self.panel_id,
            "read_only": self.read_only,
            "record_count": self.record_count,
            "severity": self.severity,
            "source_type": self.source_type,
            "stale": self.stale,
            "status": self.status,
            "wal_record_hash": self.wal_record_hash,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["panel_hash"] = self.panel_hash
        return _json_ready(payload)  # type: ignore[return-value]


@dataclass(frozen=True)
class OperatorConsoleRuntimeSnapshot:
    integration_version: str
    task_id: str
    run_id: str
    status: str
    severity: str
    panels: tuple[OperatorConsoleRuntimePanel, ...]
    red_panel_ids: tuple[str, ...]
    stale_panel_ids: tuple[str, ...]
    wal_head_hash: str
    artifact_store_root_hash: str
    approval_runtime_hash: str
    failure_center_manifest_hash: str
    worker_registry_manifest_hash: str
    watchdog_chain_head_hash: str
    replay_report_hash: str
    snapshot_reconstruction_hash: str
    readonly_contract_snapshot_hash: str
    mutation_route_required: str
    read_only: bool
    direct_console_edits_enabled: bool
    mutation_enabled: bool
    command_enabled: bool
    dispatch_enabled: bool
    live_fetch_enabled: bool
    external_tool_enabled: bool
    observed_at: str
    snapshot_hash: str = ""

    def __post_init__(self) -> None:
        if self.integration_version != OPERATOR_CONSOLE_RUNTIME_SURFACE_VERSION:
            raise OperatorConsoleRuntimeSurfaceError("snapshot_version_invalid")
        for field_name in ("task_id", "run_id", "observed_at", "mutation_route_required"):
            if not strict_nonempty_string(getattr(self, field_name)):
                raise OperatorConsoleRuntimeSurfaceError(field_name + "_required")
        if self.status not in _STATUS_VALUES:
            raise OperatorConsoleRuntimeSurfaceError("snapshot_status_invalid")
        if self.severity not in _SEVERITY_VALUES:
            raise OperatorConsoleRuntimeSurfaceError("snapshot_severity_invalid")
        if self.mutation_route_required != _CONTROLLED_EXECUTION_ROUTE:
            raise OperatorConsoleRuntimeSurfaceError("mutation_route_required_invalid")
        for field_name in (
            "read_only",
            "direct_console_edits_enabled",
            "mutation_enabled",
            "command_enabled",
            "dispatch_enabled",
            "live_fetch_enabled",
            "external_tool_enabled",
        ):
            if not strict_bool(getattr(self, field_name)):
                raise OperatorConsoleRuntimeSurfaceError(field_name + "_must_be_bool")
        if (
            self.read_only is not True
            or self.direct_console_edits_enabled is not False
            or self.mutation_enabled is not False
            or self.command_enabled is not False
            or self.dispatch_enabled is not False
            or self.live_fetch_enabled is not False
            or self.external_tool_enabled is not False
        ):
            raise OperatorConsoleRuntimeSurfaceError("snapshot_must_be_read_only")
        object.__setattr__(self, "panels", tuple(self.panels))
        if len({panel.panel_id for panel in self.panels}) != len(self.panels):
            raise OperatorConsoleRuntimeSurfaceError("duplicate_console_panels")
        if set(_DEFAULT_PANEL_IDS) - {panel.panel_id for panel in self.panels}:
            raise OperatorConsoleRuntimeSurfaceError("required_console_panels_missing")
        for panel in self.panels:
            if not isinstance(panel, OperatorConsoleRuntimePanel):
                raise OperatorConsoleRuntimeSurfaceError("panel_must_be_runtime_panel")
        object.__setattr__(
            self,
            "red_panel_ids",
            _normalize_string_tuple(self.red_panel_ids, "red_panel_ids"),
        )
        object.__setattr__(
            self,
            "stale_panel_ids",
            _normalize_string_tuple(self.stale_panel_ids, "stale_panel_ids"),
        )
        expected_red = tuple(
            panel.panel_id for panel in self.panels if panel.severity == "red"
        )
        expected_stale = tuple(panel.panel_id for panel in self.panels if panel.stale)
        if self.red_panel_ids != expected_red:
            raise OperatorConsoleRuntimeSurfaceError("red_panel_ids_mismatch")
        if self.stale_panel_ids != expected_stale:
            raise OperatorConsoleRuntimeSurfaceError("stale_panel_ids_mismatch")
        for field_name in (
            "approval_runtime_hash",
            "artifact_store_root_hash",
            "failure_center_manifest_hash",
            "readonly_contract_snapshot_hash",
            "replay_report_hash",
            "snapshot_reconstruction_hash",
            "wal_head_hash",
            "watchdog_chain_head_hash",
            "worker_registry_manifest_hash",
        ):
            if not strict_digest(getattr(self, field_name)):
                raise OperatorConsoleRuntimeSurfaceError(field_name + "_must_be_digest")
        _install_or_verify_hash(self, "snapshot_hash", compute_operator_console_runtime_snapshot_hash)

    def deterministic_material(self) -> dict[str, object]:
        return {
            "approval_runtime_hash": self.approval_runtime_hash,
            "artifact_store_root_hash": self.artifact_store_root_hash,
            "command_enabled": self.command_enabled,
            "direct_console_edits_enabled": self.direct_console_edits_enabled,
            "dispatch_enabled": self.dispatch_enabled,
            "external_tool_enabled": self.external_tool_enabled,
            "failure_center_manifest_hash": self.failure_center_manifest_hash,
            "integration_version": self.integration_version,
            "live_fetch_enabled": self.live_fetch_enabled,
            "mutation_enabled": self.mutation_enabled,
            "mutation_route_required": self.mutation_route_required,
            "panels": tuple(panel.panel_hash for panel in self.panels),
            "read_only": self.read_only,
            "readonly_contract_snapshot_hash": self.readonly_contract_snapshot_hash,
            "red_panel_ids": self.red_panel_ids,
            "replay_report_hash": self.replay_report_hash,
            "run_id": self.run_id,
            "severity": self.severity,
            "snapshot_reconstruction_hash": self.snapshot_reconstruction_hash,
            "stale_panel_ids": self.stale_panel_ids,
            "status": self.status,
            "task_id": self.task_id,
            "wal_head_hash": self.wal_head_hash,
            "watchdog_chain_head_hash": self.watchdog_chain_head_hash,
            "worker_registry_manifest_hash": self.worker_registry_manifest_hash,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["observed_at"] = self.observed_at
        payload["panels"] = tuple(panel.as_dict() for panel in self.panels)
        payload["snapshot_hash"] = self.snapshot_hash
        return _json_ready(payload)  # type: ignore[return-value]


@dataclass(frozen=True)
class OperatorConsoleMutationRouteReceipt:
    integration_version: str
    accepted: bool
    failures: tuple[str, ...]
    requested_route: str
    required_route: str
    routed_to_controlled_execution: bool
    console_mutation_performed: bool
    direct_console_edits_enabled: bool
    approval_receipt_hash: str
    controlled_execution_receipt_hash: str
    receipt_hash: str = ""

    def __post_init__(self) -> None:
        if self.integration_version != OPERATOR_CONSOLE_RUNTIME_SURFACE_VERSION:
            raise OperatorConsoleRuntimeSurfaceError("mutation_route_version_invalid")
        if not strict_bool(self.accepted):
            raise OperatorConsoleRuntimeSurfaceError("accepted_must_be_bool")
        for field_name in (
            "routed_to_controlled_execution",
            "console_mutation_performed",
            "direct_console_edits_enabled",
        ):
            if not strict_bool(getattr(self, field_name)):
                raise OperatorConsoleRuntimeSurfaceError(field_name + "_must_be_bool")
        if self.required_route != _CONTROLLED_EXECUTION_ROUTE:
            raise OperatorConsoleRuntimeSurfaceError("required_route_invalid")
        if self.console_mutation_performed is not False or self.direct_console_edits_enabled is not False:
            raise OperatorConsoleRuntimeSurfaceError("console_mutation_must_not_be_performed")
        object.__setattr__(
            self,
            "failures",
            _normalize_failures(self.failures, allow_empty=True),
        )
        if self.accepted and self.failures:
            raise OperatorConsoleRuntimeSurfaceError("accepted_route_has_failures")
        if not self.accepted and not self.failures:
            raise OperatorConsoleRuntimeSurfaceError("rejected_route_requires_failures")
        for field_name in ("approval_receipt_hash", "controlled_execution_receipt_hash"):
            if not strict_digest(getattr(self, field_name)):
                raise OperatorConsoleRuntimeSurfaceError(field_name + "_must_be_digest")
        if self.accepted:
            if self.requested_route != self.required_route:
                raise OperatorConsoleRuntimeSurfaceError("accepted_route_mismatch")
            if self.routed_to_controlled_execution is not True:
                raise OperatorConsoleRuntimeSurfaceError("accepted_route_not_controlled")
            if self.approval_receipt_hash == ZERO_HASH:
                raise OperatorConsoleRuntimeSurfaceError("accepted_route_requires_approval_hash")
            if self.controlled_execution_receipt_hash == ZERO_HASH:
                raise OperatorConsoleRuntimeSurfaceError("accepted_route_requires_execution_hash")
        _install_or_verify_hash(
            self,
            "receipt_hash",
            compute_operator_console_mutation_route_receipt_hash,
        )

    def as_dict(self) -> dict[str, object]:
        return _json_ready(asdict(self))  # type: ignore[return-value]


class FileBackedOperatorConsoleRuntimeSurface:
    """Read-only projection over persisted local runtime evidence."""

    read_only = True
    mutation_enabled = False
    command_enabled = False
    dispatch_enabled = False
    live_fetch_enabled = False
    external_tool_enabled = False

    def __init__(
        self,
        *,
        runtime_root: str | Path,
        wal_source_relpaths: Sequence[str],
        queue_source_relpath: str,
        queue_id: str,
        artifact_store_relpath: str,
        artifact_store_id: str = "artifact-store-persistence-v1",
        approval_store_relpath: str = "approval-runtime",
        failure_store_relpath: str = "failure-bundle-center",
        snapshot_store_relpath: str = "snapshot-replay",
        worker_state_relpath: str = "worker-registry-runtime/state",
        worker_receipt_relpath: str = "worker-registry-runtime/receipts",
        watchdog_operator_state_relpath: str = "watchdog-runtime/operator-state",
        watchdog_receipt_relpath: str = "watchdog-runtime/receipts",
    ) -> None:
        self.runtime_root = _validate_runtime_root(Path(runtime_root))
        self.wal_source_relpaths = _validate_relpath_tuple(
            wal_source_relpaths,
            "wal_source_relpaths",
            require_nonempty=True,
        )
        self.queue_source_relpath = _validate_relpath_text(
            queue_source_relpath,
            "queue_source_relpath",
            allow_empty=False,
        )
        self.queue_id = _validated_identifier(queue_id, "queue_id")
        self.artifact_store_relpath = _validate_relpath_text(
            artifact_store_relpath,
            "artifact_store_relpath",
            allow_empty=False,
        )
        self.artifact_store_id = _validated_identifier(
            artifact_store_id,
            "artifact_store_id",
        )
        self.approval_store_relpath = _validate_relpath_text(
            approval_store_relpath,
            "approval_store_relpath",
            allow_empty=False,
        )
        self.failure_store_relpath = _validate_relpath_text(
            failure_store_relpath,
            "failure_store_relpath",
            allow_empty=False,
        )
        self.snapshot_store_relpath = _validate_relpath_text(
            snapshot_store_relpath,
            "snapshot_store_relpath",
            allow_empty=False,
        )
        self.worker_state_relpath = _validate_relpath_text(
            worker_state_relpath,
            "worker_state_relpath",
            allow_empty=False,
        )
        self.worker_receipt_relpath = _validate_relpath_text(
            worker_receipt_relpath,
            "worker_receipt_relpath",
            allow_empty=False,
        )
        self.watchdog_operator_state_relpath = _validate_relpath_text(
            watchdog_operator_state_relpath,
            "watchdog_operator_state_relpath",
            allow_empty=False,
        )
        self.watchdog_receipt_relpath = _validate_relpath_text(
            watchdog_receipt_relpath,
            "watchdog_receipt_relpath",
            allow_empty=False,
        )

    def read_snapshot(
        self,
        *,
        task_id: str,
        run_id: str,
        observed_at: str | None = None,
    ) -> OperatorConsoleRuntimeSnapshot:
        _require_nonempty_string(task_id, "task_id")
        _require_nonempty_string(run_id, "run_id")
        observed = _timestamp(observed_at)
        panels = (
            self._summary_panel_placeholder(),
            self._read_wal_panel(),
            self._read_queue_panel(observed_at=observed),
            self._read_artifact_panel(),
            self._read_approval_panel(),
            self._read_failure_panel(),
            self._read_snapshot_replay_panel(),
            self._read_worker_panel(),
            self._read_watchdog_panel(),
        )
        system_panel = _system_health_panel(panels)
        panels = (panels[0], *panels[1:], system_panel)
        summary_panel = _summary_panel(panels[1:])
        panels = (summary_panel, *panels[1:])
        data_sources = [
            build_console_readonly_data_source(
                {
                    "command_enabled": False,
                    "dispatch_enabled": False,
                    "external_tool_enabled": False,
                    "live_fetch_enabled": False,
                    "mutation_enabled": False,
                    "read_only": True,
                    "redaction_policy_hash": _READ_ONLY_REDACTION_POLICY_HASH,
                    "source_hash": panel.panel_hash,
                    "source_id": "operator-console-" + panel.panel_id,
                    "source_type": panel.source_type,
                    "wal_record_hash": panel.wal_record_hash,
                },
                observed_at=observed,
            )
            for panel in panels
            if panel.source_type in _SOURCE_TYPE_BY_PANEL.values()
        ]
        by_id = {panel.panel_id: panel for panel in panels}
        readonly_snapshot = build_operator_console_readonly_snapshot(
            console_snapshot_id="operator-console-runtime-" + _sha256_json(
                {
                    "panel_hashes": tuple(panel.panel_hash for panel in panels),
                    "run_id": run_id,
                    "task_id": task_id,
                }
            ).removeprefix("sha256:")[:32],
            task_id=task_id,
            run_id=run_id,
            data_sources=data_sources,
            wal_head_hash=by_id["wal"].latest_record_hash,
            artifact_store_root_hash=by_id["artifacts"].evidence_hash,
            approval_runtime_hash=by_id["approvals"].evidence_hash,
            failure_center_manifest_hash=by_id["failures"].evidence_hash,
            worker_registry_manifest_hash=by_id["workers"].evidence_hash,
            watchdog_chain_head_hash=by_id["watchdog"].evidence_hash,
            replay_report_hash=by_id["replay"].evidence_hash,
            snapshot_reconstruction_hash=by_id["replay"].latest_record_hash,
            observed_at=observed,
        )
        red_ids = tuple(panel.panel_id for panel in panels if panel.severity == "red")
        stale_ids = tuple(panel.panel_id for panel in panels if panel.stale)
        status = "failure" if red_ids else ("stale" if stale_ids else "ok")
        severity = "red" if red_ids else ("yellow" if stale_ids else "green")
        return OperatorConsoleRuntimeSnapshot(
            integration_version=OPERATOR_CONSOLE_RUNTIME_SURFACE_VERSION,
            task_id=task_id,
            run_id=run_id,
            status=status,
            severity=severity,
            panels=panels,
            red_panel_ids=red_ids,
            stale_panel_ids=stale_ids,
            wal_head_hash=by_id["wal"].latest_record_hash,
            artifact_store_root_hash=by_id["artifacts"].evidence_hash,
            approval_runtime_hash=by_id["approvals"].evidence_hash,
            failure_center_manifest_hash=by_id["failures"].evidence_hash,
            worker_registry_manifest_hash=by_id["workers"].evidence_hash,
            watchdog_chain_head_hash=by_id["watchdog"].evidence_hash,
            replay_report_hash=by_id["replay"].evidence_hash,
            snapshot_reconstruction_hash=by_id["replay"].latest_record_hash,
            readonly_contract_snapshot_hash=readonly_snapshot.snapshot_hash,
            mutation_route_required=_CONTROLLED_EXECUTION_ROUTE,
            read_only=True,
            direct_console_edits_enabled=False,
            mutation_enabled=False,
            command_enabled=False,
            dispatch_enabled=False,
            live_fetch_enabled=False,
            external_tool_enabled=False,
            observed_at=observed,
        )

    def _summary_panel_placeholder(self) -> OperatorConsoleRuntimePanel:
        return _panel(
            panel_id="summary",
            source_type="summary",
            record_count=0,
            evidence_hash=_sha256_json({"summary": "placeholder"}),
            latest_record_hash=ZERO_HASH,
            wal_record_hash=ZERO_HASH,
        )

    def _read_wal_panel(self) -> OperatorConsoleRuntimePanel:
        failures: list[str] = []
        record_hashes: list[str] = []
        replay_hashes: list[str] = []
        latest_hash = ZERO_HASH
        for relpath in self.wal_source_relpaths:
            path = self._resolve_relpath(relpath, "wal_source_relpath")
            if not path.exists():
                failures.append("wal_missing")
                continue
            if path.is_symlink() or not path.is_file():
                failures.append("wal_source_not_regular_file")
                continue
            try:
                store = FileBackedRealWalStorage(path)
                records = store.read_records()
                replay = store.replay()
                replay_hashes.append(replay.replay_result_hash)
                if not records:
                    failures.append("wal_empty")
                    continue
                record_hashes.extend(record.record_hash for record in records)
                latest_hash = records[-1].record_hash
            except Exception as exc:
                failures.append("wal_replay_failed:" + _safe_error_text(exc))
        return _panel(
            panel_id="wal",
            source_type="wal",
            record_count=len(record_hashes),
            evidence_hash=_sha256_json(
                {"record_hashes": tuple(record_hashes), "replay_hashes": tuple(replay_hashes)}
            ),
            latest_record_hash=latest_hash,
            wal_record_hash=latest_hash,
            failures=failures,
        )

    def _read_queue_panel(self, *, observed_at: str) -> OperatorConsoleRuntimePanel:
        path = self._resolve_relpath(self.queue_source_relpath, "queue_source_relpath")
        if not path.exists():
            return _panel(
                panel_id="queue",
                source_type="job_queue",
                record_count=0,
                evidence_hash=_sha256_json({"queue": "missing"}),
                latest_record_hash=ZERO_HASH,
                wal_record_hash=ZERO_HASH,
                failures=("queue_missing",),
            )
        failures: list[str] = []
        stale = False
        stale_hashes: list[str] = []
        record_hashes: list[str] = []
        latest_hash = ZERO_HASH
        latest_wal = ZERO_HASH
        try:
            queue = DurableJobQueue(path=path, queue_id=self.queue_id)
            records = queue.records
            if not records:
                failures.append("queue_empty")
            record_hashes = [record.record_hash for record in records]
            if records:
                latest_hash = records[-1].record_hash
                latest_wal = records[-1].event.wal_record_hash
            for state in queue.list_job_states():
                if state.state != "leased":
                    continue
                lease_event = _latest_lease_event(records, state.job_id, state.lease_id)
                if lease_event is not None and lease_event.lease_expires_at:
                    if _parse_timestamp(lease_event.lease_expires_at) <= _parse_timestamp(observed_at):
                        stale = True
                        stale_hashes.append(state.last_event_hash)
            if stale:
                failures.append("stale_lease_detected")
        except Exception as exc:
            failures.append("queue_replay_failed:" + _safe_error_text(exc))
        return _panel(
            panel_id="queue",
            source_type="job_queue",
            record_count=len(record_hashes),
            evidence_hash=_sha256_json(
                {"record_hashes": tuple(record_hashes), "stale_hashes": tuple(stale_hashes)}
            ),
            latest_record_hash=latest_hash,
            wal_record_hash=latest_wal,
            failures=failures if not stale else tuple(failure for failure in failures if failure != "stale_lease_detected"),
            stale=stale,
        )

    def _read_artifact_panel(self) -> OperatorConsoleRuntimePanel:
        root = self._resolve_relpath(self.artifact_store_relpath, "artifact_store_relpath")
        manifest_log = root / "artifact-manifests.jsonl"
        if not manifest_log.exists():
            return _panel(
                panel_id="artifacts",
                source_type="artifact_store",
                record_count=0,
                evidence_hash=_sha256_json({"artifact_store": "missing"}),
                latest_record_hash=ZERO_HASH,
                wal_record_hash=ZERO_HASH,
                failures=("artifact_manifest_missing",),
            )
        failures: list[str] = []
        record_hashes: list[str] = []
        manifest_hashes: list[str] = []
        latest_hash = ZERO_HASH
        latest_wal = ZERO_HASH
        replay_hash = ZERO_HASH
        try:
            store = FileBackedArtifactStore(root, store_id=self.artifact_store_id)
            replay = store.replay()
            replay_hash = replay.replay_result_hash
            if not replay.accepted:
                failures.extend("artifact_replay_rejected:" + failure for failure in replay.rejection_reasons)
            else:
                records = store.read_records()
                if not records:
                    failures.append("artifact_manifest_empty")
                record_hashes = [record.record_hash for record in records]
                manifest_hashes = [record.manifest.manifest_hash for record in records]
                if records:
                    latest_hash = records[-1].record_hash
                    latest_wal = records[-1].manifest.wal_record_hash
        except Exception as exc:
            failures.append("artifact_replay_failed:" + _safe_error_text(exc))
        return _panel(
            panel_id="artifacts",
            source_type="artifact_store",
            record_count=len(record_hashes),
            evidence_hash=_sha256_json(
                {
                    "manifest_hashes": tuple(manifest_hashes),
                    "record_hashes": tuple(record_hashes),
                    "replay_hash": replay_hash,
                }
            ),
            latest_record_hash=latest_hash,
            wal_record_hash=latest_wal,
            failures=failures,
        )

    def _read_approval_panel(self) -> OperatorConsoleRuntimePanel:
        root = self._resolve_relpath(self.approval_store_relpath, "approval_store_relpath")
        files, failures = _collect_json_files(root, "approval_state")
        receipt_hashes: list[str] = []
        wal_hashes: list[str] = []
        for payload in files:
            try:
                receipt_hashes.extend(_approval_receipt_hashes(payload))
                wal_hashes.extend(_digest_values_for_keys(payload, {"approval_wal_record_hash", "consumption_wal_record_hash"}))
            except Exception as exc:
                failures.append("approval_state_invalid:" + _safe_error_text(exc))
        if not files and not failures:
            failures.append("approval_state_empty")
        latest = receipt_hashes[-1] if receipt_hashes else ZERO_HASH
        latest_wal = wal_hashes[-1] if wal_hashes else ZERO_HASH
        return _panel(
            panel_id="approvals",
            source_type="approval_runtime",
            record_count=len(files),
            evidence_hash=_sha256_json({"receipt_hashes": tuple(receipt_hashes)}),
            latest_record_hash=latest,
            wal_record_hash=latest_wal,
            failures=failures,
        )

    def _read_failure_panel(self) -> OperatorConsoleRuntimePanel:
        root = self._resolve_relpath(self.failure_store_relpath, "failure_store_relpath")
        files, failures = _collect_json_files(root, "failure_bundle_state")
        receipt_hashes: list[str] = []
        wal_hashes: list[str] = []
        for payload in files:
            try:
                receipt_hashes.extend(_failure_receipt_hashes(payload))
                wal_hashes.extend(_digest_values_for_keys(payload, {"failure_wal_record_hash", "wal_head_hash"}))
            except Exception as exc:
                failures.append("failure_bundle_state_invalid:" + _safe_error_text(exc))
        if not files and not failures:
            failures.append("failure_bundle_state_empty")
        latest = receipt_hashes[-1] if receipt_hashes else ZERO_HASH
        latest_wal = wal_hashes[-1] if wal_hashes else ZERO_HASH
        return _panel(
            panel_id="failures",
            source_type="failure_bundle_center",
            record_count=len(files),
            evidence_hash=_sha256_json({"receipt_hashes": tuple(receipt_hashes)}),
            latest_record_hash=latest,
            wal_record_hash=latest_wal,
            failures=failures,
        )

    def _read_snapshot_replay_panel(self) -> OperatorConsoleRuntimePanel:
        root = self._resolve_relpath(self.snapshot_store_relpath, "snapshot_store_relpath")
        files, failures = _collect_json_files(root, "snapshot_replay_state")
        receipt_hashes: list[str] = []
        accepted_hashes: list[str] = []
        for payload in files:
            if "output_receipt_version" not in payload:
                continue
            try:
                receipt = SnapshotReplayOutputReceipt(**dict(payload))  # type: ignore[arg-type]
                receipt_hashes.append(receipt.receipt_hash)
                if receipt.accepted:
                    accepted_hashes.append(receipt.snapshot_manifest_hash)
                else:
                    failures.append("snapshot_replay_receipt_rejected")
            except Exception as exc:
                failures.append("snapshot_replay_receipt_invalid:" + _safe_error_text(exc))
        if not receipt_hashes and not failures:
            failures.append("snapshot_replay_receipt_missing")
        latest = receipt_hashes[-1] if receipt_hashes else ZERO_HASH
        latest_snapshot = accepted_hashes[-1] if accepted_hashes else latest
        return _panel(
            panel_id="replay",
            source_type="replay_report",
            record_count=len(receipt_hashes),
            evidence_hash=_sha256_json(
                {
                    "accepted_snapshot_hashes": tuple(accepted_hashes),
                    "receipt_hashes": tuple(receipt_hashes),
                }
            ),
            latest_record_hash=latest_snapshot if latest_snapshot else ZERO_HASH,
            wal_record_hash=ZERO_HASH,
            failures=failures,
        )

    def _read_worker_panel(self) -> OperatorConsoleRuntimePanel:
        roots = (
            self._resolve_relpath(self.worker_state_relpath, "worker_state_relpath"),
            self._resolve_relpath(self.worker_receipt_relpath, "worker_receipt_relpath"),
        )
        files: list[Mapping[str, object]] = []
        failures: list[str] = []
        for root in roots:
            collected, root_failures = _collect_json_files(root, "worker_state")
            files.extend(collected)
            failures.extend(root_failures)
        receipt_hashes: list[str] = []
        wal_hashes: list[str] = []
        for payload in files:
            try:
                receipt_hashes.extend(_worker_receipt_hashes(payload))
                wal_hashes.extend(_digest_values_for_keys(payload, {"worker_state_wal_record_hash"}))
            except Exception as exc:
                failures.append("worker_state_invalid:" + _safe_error_text(exc))
        if not files and not failures:
            failures.append("worker_state_empty")
        latest = receipt_hashes[-1] if receipt_hashes else ZERO_HASH
        latest_wal = wal_hashes[-1] if wal_hashes else ZERO_HASH
        return _panel(
            panel_id="workers",
            source_type="worker_registry",
            record_count=len(files),
            evidence_hash=_sha256_json({"receipt_hashes": tuple(receipt_hashes)}),
            latest_record_hash=latest,
            wal_record_hash=latest_wal,
            failures=failures,
        )

    def _read_watchdog_panel(self) -> OperatorConsoleRuntimePanel:
        roots = (
            self._resolve_relpath(
                self.watchdog_operator_state_relpath,
                "watchdog_operator_state_relpath",
            ),
            self._resolve_relpath(self.watchdog_receipt_relpath, "watchdog_receipt_relpath"),
        )
        files: list[Mapping[str, object]] = []
        failures: list[str] = []
        for root in roots:
            collected, root_failures = _collect_json_files(root, "watchdog_state")
            files.extend(collected)
            failures.extend(root_failures)
        receipt_hashes: list[str] = []
        wal_hashes: list[str] = []
        stale = False
        resource_breach = False
        for payload in files:
            try:
                hashes, wals, saw_stale, saw_breach = _watchdog_hashes(payload)
                receipt_hashes.extend(hashes)
                wal_hashes.extend(wals)
                stale = stale or saw_stale
                resource_breach = resource_breach or saw_breach
            except Exception as exc:
                failures.append("watchdog_state_invalid:" + _safe_error_text(exc))
        if resource_breach:
            failures.append("watchdog_resource_breach_detected")
        if not files and not failures:
            failures.append("watchdog_state_empty")
        latest = receipt_hashes[-1] if receipt_hashes else ZERO_HASH
        latest_wal = wal_hashes[-1] if wal_hashes else ZERO_HASH
        return _panel(
            panel_id="watchdog",
            source_type="watchdog_receipts",
            record_count=len(files),
            evidence_hash=_sha256_json({"receipt_hashes": tuple(receipt_hashes)}),
            latest_record_hash=latest,
            wal_record_hash=latest_wal,
            failures=failures,
            stale=stale,
        )

    def _resolve_relpath(self, relpath: str, field_name: str) -> Path:
        clean = _validate_relpath_text(relpath, field_name, allow_empty=False)
        candidate = self.runtime_root / clean
        current = self.runtime_root
        for part in PurePosixPath(clean).parts:
            current = current / part
            if current.exists() and current.is_symlink():
                raise OperatorConsoleRuntimeSurfaceError(field_name + "_is_symlink")
        resolved = candidate.resolve(strict=False)
        if not resolved.is_relative_to(self.runtime_root):
            raise OperatorConsoleRuntimeSurfaceError(field_name + "_escapes_runtime_root")
        return resolved


def admit_operator_console_mutation_route(
    payload: Mapping[str, object],
) -> OperatorConsoleMutationRouteReceipt:
    failures: list[str] = []
    requested_route = ""
    approval_hash = ZERO_HASH
    execution_hash = ZERO_HASH
    if not isinstance(payload, Mapping):
        failures.append("mutation_route_payload_must_be_mapping")
    else:
        try:
            _scan_mutation_payload(payload)
        except OperatorConsoleRuntimeSurfaceError as exc:
            failures.append(str(exc))
        route = payload.get("mutation_route")
        if isinstance(route, str):
            requested_route = route
        if requested_route != _CONTROLLED_EXECUTION_ROUTE:
            failures.append("controlled_execution_route_required")
        approval_value = payload.get("approval_receipt_hash")
        if strict_digest(approval_value):
            approval_hash = str(approval_value)
        else:
            failures.append("approval_receipt_hash_required")
        execution_value = payload.get("controlled_execution_receipt_hash")
        if strict_digest(execution_value):
            execution_hash = str(execution_value)
        else:
            failures.append("controlled_execution_receipt_hash_required")
        if approval_hash == ZERO_HASH:
            failures.append("approval_receipt_hash_must_not_be_zero")
        if execution_hash == ZERO_HASH:
            failures.append("controlled_execution_receipt_hash_must_not_be_zero")

    accepted = not failures
    return OperatorConsoleMutationRouteReceipt(
        integration_version=OPERATOR_CONSOLE_RUNTIME_SURFACE_VERSION,
        accepted=accepted,
        failures=tuple(_dedupe(failures)),
        requested_route=requested_route or "not_provided",
        required_route=_CONTROLLED_EXECUTION_ROUTE,
        routed_to_controlled_execution=accepted,
        console_mutation_performed=False,
        direct_console_edits_enabled=False,
        approval_receipt_hash=approval_hash,
        controlled_execution_receipt_hash=execution_hash,
    )


def validate_operator_console_runtime_snapshot(
    snapshot: OperatorConsoleRuntimeSnapshot,
) -> bool:
    if not isinstance(snapshot, OperatorConsoleRuntimeSnapshot):
        return False
    try:
        recomputed = compute_operator_console_runtime_snapshot_hash(snapshot)
    except Exception:
        return False
    return snapshot.snapshot_hash == recomputed


def compute_operator_console_runtime_panel_hash(
    panel: OperatorConsoleRuntimePanel | Mapping[str, object],
) -> str:
    data = panel.deterministic_material() if isinstance(panel, OperatorConsoleRuntimePanel) else dict(panel)
    data.pop("panel_hash", None)
    return _sha256_json(data)


def compute_operator_console_runtime_snapshot_hash(
    snapshot: OperatorConsoleRuntimeSnapshot | Mapping[str, object],
) -> str:
    data = snapshot.deterministic_material() if isinstance(snapshot, OperatorConsoleRuntimeSnapshot) else dict(snapshot)
    data.pop("snapshot_hash", None)
    data.pop("observed_at", None)
    return _sha256_json(data)


def compute_operator_console_mutation_route_receipt_hash(
    receipt: OperatorConsoleMutationRouteReceipt | Mapping[str, object],
) -> str:
    data = receipt.as_dict() if isinstance(receipt, OperatorConsoleMutationRouteReceipt) else dict(receipt)
    data.pop("receipt_hash", None)
    return _sha256_json(data)


def _panel(
    *,
    panel_id: str,
    source_type: str,
    record_count: int,
    evidence_hash: str,
    latest_record_hash: str,
    wal_record_hash: str,
    failures: Sequence[str] = (),
    stale: bool = False,
) -> OperatorConsoleRuntimePanel:
    normalized_failures = tuple(_dedupe(str(failure) for failure in failures if str(failure)))
    failure_only = bool(normalized_failures)
    status = "failure" if failure_only else ("stale" if stale else "ok")
    severity = "red" if failure_only else ("yellow" if stale else "green")
    return OperatorConsoleRuntimePanel(
        integration_version=OPERATOR_CONSOLE_RUNTIME_SURFACE_VERSION,
        panel_id=panel_id,
        source_type=source_type,
        status=status,
        severity=severity,
        read_only=True,
        mutation_enabled=False,
        command_enabled=False,
        dispatch_enabled=False,
        live_fetch_enabled=False,
        external_tool_enabled=False,
        stale=stale,
        record_count=record_count,
        evidence_hash=evidence_hash,
        wal_record_hash=wal_record_hash,
        latest_record_hash=latest_record_hash,
        failures=normalized_failures,
    )


def _summary_panel(panels: Sequence[OperatorConsoleRuntimePanel]) -> OperatorConsoleRuntimePanel:
    failures: list[str] = []
    if any(panel.severity == "red" for panel in panels):
        failures.append("console_evidence_failure_detected")
    stale = any(panel.stale for panel in panels)
    return _panel(
        panel_id="summary",
        source_type="summary",
        record_count=sum(panel.record_count for panel in panels),
        evidence_hash=_sha256_json(
            {
                "panel_hashes": tuple(panel.panel_hash for panel in panels),
                "red_panels": tuple(panel.panel_id for panel in panels if panel.severity == "red"),
                "stale_panels": tuple(panel.panel_id for panel in panels if panel.stale),
            }
        ),
        latest_record_hash=panels[-1].panel_hash if panels else ZERO_HASH,
        wal_record_hash=ZERO_HASH,
        failures=failures,
        stale=stale,
    )


def _system_health_panel(panels: Sequence[OperatorConsoleRuntimePanel]) -> OperatorConsoleRuntimePanel:
    failures: list[str] = []
    if any(panel.severity == "red" for panel in panels):
        failures.append("system_health_red_due_to_evidence_failure")
    stale = any(panel.stale for panel in panels)
    return _panel(
        panel_id="system_health",
        source_type="system_health",
        record_count=len(panels),
        evidence_hash=_sha256_json(
            {
                "panel_hashes": tuple(panel.panel_hash for panel in panels),
                "surface": OPERATOR_CONSOLE_RUNTIME_SURFACE_VERSION,
            }
        ),
        latest_record_hash=panels[-1].panel_hash if panels else ZERO_HASH,
        wal_record_hash=ZERO_HASH,
        failures=failures,
        stale=stale,
    )


def _approval_receipt_hashes(payload: Mapping[str, object]) -> tuple[str, ...]:
    hashes: list[str] = []
    if "integrated_receipt" in payload:
        integrated = payload.get("integrated_receipt")
        if not isinstance(integrated, Mapping):
            raise OperatorConsoleRuntimeSurfaceError("approval_integrated_receipt_invalid")
        hashes.append(ApprovalRuntimeIntegratedReceipt(**dict(integrated)).receipt_hash)  # type: ignore[arg-type]
    if _looks_like_consumption_receipt(payload):
        hashes.append(ApprovalRuntimeConsumptionReceipt(**dict(payload)).receipt_hash)  # type: ignore[arg-type]
    if "revocation_receipt" in payload:
        revoked = payload.get("revocation_receipt")
        if not isinstance(revoked, Mapping):
            raise OperatorConsoleRuntimeSurfaceError("approval_revocation_receipt_invalid")
        hashes.append(ApprovalRuntimeConsumptionReceipt(**dict(revoked)).receipt_hash)  # type: ignore[arg-type]
    return tuple(hashes or _digest_values_for_keys(payload, {"receipt_hash"}))


def _failure_receipt_hashes(payload: Mapping[str, object]) -> tuple[str, ...]:
    hashes: list[str] = []
    if "integration_receipt" in payload:
        receipt = payload.get("integration_receipt")
        if not isinstance(receipt, Mapping):
            raise OperatorConsoleRuntimeSurfaceError("failure_integration_receipt_invalid")
        hashes.append(FailureBundleCenterIntegratedReceipt(**dict(receipt)).receipt_hash)  # type: ignore[arg-type]
    if _looks_like_failure_receipt(payload):
        hashes.append(FailureBundleCenterIntegratedReceipt(**dict(payload)).receipt_hash)  # type: ignore[arg-type]
    return tuple(hashes or _digest_values_for_keys(payload, {"receipt_hash", "manifest_hash"}))


def _worker_receipt_hashes(payload: Mapping[str, object]) -> tuple[str, ...]:
    hashes: list[str] = []
    if "capability" in payload:
        capability = payload.get("capability")
        if not isinstance(capability, Mapping):
            raise OperatorConsoleRuntimeSurfaceError("worker_capability_invalid")
        hashes.append(WorkerCapabilityToken(**dict(capability)).capability_token_hash)  # type: ignore[arg-type]
    if "quarantine_receipt" in payload:
        quarantine = payload.get("quarantine_receipt")
        if not isinstance(quarantine, Mapping):
            raise OperatorConsoleRuntimeSurfaceError("worker_quarantine_receipt_invalid")
        hashes.append(WorkerRegistryCapabilityRuntimeReceipt(**dict(quarantine)).receipt_hash)  # type: ignore[arg-type]
    if _looks_like_worker_receipt(payload):
        hashes.append(WorkerRegistryCapabilityRuntimeReceipt(**dict(payload)).receipt_hash)  # type: ignore[arg-type]
    return tuple(hashes or _digest_values_for_keys(payload, {"receipt_hash", "capability_token_hash"}))


def _watchdog_hashes(payload: Mapping[str, object]) -> tuple[tuple[str, ...], tuple[str, ...], bool, bool]:
    hashes: list[str] = []
    wals: list[str] = []
    stale = False
    resource_breach = False
    if "operator_state_hash" in payload and "latest_watchdog_receipt_hash" in payload:
        state = WatchdogOperatorState(**dict(payload))  # type: ignore[arg-type]
        hashes.append(state.operator_state_hash)
        hashes.append(state.latest_watchdog_receipt_hash)
        stale = stale or state.stale_lease_detected
        resource_breach = resource_breach or state.resource_breach_detected
    if "receipt_hash" in payload and "watchdog_wal_record_hash" in payload:
        receipt = WatchdogRuntimeReceipt(**dict(payload))  # type: ignore[arg-type]
        hashes.append(receipt.receipt_hash)
        wals.append(receipt.watchdog_wal_record_hash)
        stale = stale or receipt.stale_lease_detected
        resource_breach = resource_breach or receipt.resource_breach_detected
    if not hashes:
        hashes.extend(_digest_values_for_keys(payload, {"receipt_hash", "operator_state_hash"}))
    if not wals:
        wals.extend(_digest_values_for_keys(payload, {"watchdog_wal_record_hash"}))
    return tuple(hashes), tuple(wals), stale, resource_breach


def _looks_like_consumption_receipt(payload: Mapping[str, object]) -> bool:
    return {"approval_id", "approval_admission_hash", "consumption_wal_record_hash", "receipt_hash"}.issubset(payload)


def _looks_like_failure_receipt(payload: Mapping[str, object]) -> bool:
    return {"failure_bundle_id", "failure_wal_record_hash", "center_manifest_hash", "receipt_hash"}.issubset(payload)


def _looks_like_worker_receipt(payload: Mapping[str, object]) -> bool:
    return {"event_type", "worker_state_wal_record_hash", "queue_record_hash", "receipt_hash"}.issubset(payload)


def _digest_values_for_keys(
    payload: Mapping[str, object] | Sequence[object],
    keys: set[str],
) -> tuple[str, ...]:
    found: list[str] = []
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if str(key) in keys and strict_digest(value):
                found.append(str(value))
            if isinstance(value, Mapping) or (
                isinstance(value, Sequence) and not isinstance(value, (str, bytes))
            ):
                found.extend(_digest_values_for_keys(value, keys))
    elif isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
        for value in payload:
            if isinstance(value, Mapping) or (
                isinstance(value, Sequence) and not isinstance(value, (str, bytes))
            ):
                found.extend(_digest_values_for_keys(value, keys))
    return tuple(found)


def _collect_json_files(root: Path, label: str) -> tuple[list[Mapping[str, object]], list[str]]:
    failures: list[str] = []
    payloads: list[Mapping[str, object]] = []
    if not root.exists():
        return payloads, [label + "_missing"]
    if root.is_symlink():
        return payloads, [label + "_root_is_symlink"]
    if root.is_file():
        candidates = [root]
    elif root.is_dir():
        candidates = list(_iter_json_files(root, failures, label))
    else:
        return payloads, [label + "_root_not_regular"]
    for path in candidates:
        try:
            payload = _read_json_object(path, label)
            payloads.append(payload)
        except OperatorConsoleRuntimeSurfaceError as exc:
            failures.append(label + "_invalid:" + str(exc))
    return payloads, list(_dedupe(failures))


def _iter_json_files(root: Path, failures: list[str], label: str) -> Iterable[Path]:
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            children = sorted(current.iterdir(), key=lambda item: item.name)
        except OSError as exc:
            failures.append(label + "_read_failed:" + _safe_error_text(exc))
            continue
        for child in children:
            if child.is_symlink():
                failures.append(label + "_symlink_detected")
                continue
            if child.is_dir():
                stack.append(child)
                continue
            if child.is_file() and child.suffix == ".json":
                yield child


def _read_json_object(path: Path, label: str) -> Mapping[str, object]:
    if path.is_symlink():
        raise OperatorConsoleRuntimeSurfaceError(label + "_file_is_symlink")
    if not path.is_file():
        raise OperatorConsoleRuntimeSurfaceError(label + "_file_not_regular")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise OperatorConsoleRuntimeSurfaceError(label + "_invalid_json") from exc
    except OSError as exc:
        raise OperatorConsoleRuntimeSurfaceError(label + "_read_failed") from exc
    if not isinstance(payload, Mapping):
        raise OperatorConsoleRuntimeSurfaceError(label + "_must_be_json_object")
    _scan_public_payload_safety(payload)
    return payload


def _latest_lease_event(records: Sequence[object], job_id: str, lease_id: str):
    for record in reversed(records):
        event = getattr(record, "event", None)
        if (
            getattr(event, "job_id", None) == job_id
            and getattr(event, "lease_id", None) == lease_id
            and getattr(event, "event_type", None) in {"JOB_LEASED", "JOB_HEARTBEAT"}
        ):
            return event
    return None


def _scan_public_payload_safety(value: object, *, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            if (
                _SECRET_KEY_PATTERN.search(key_text)
                and not key_text.endswith("_hash")
                and not key_text.endswith("_id")
            ):
                raise OperatorConsoleRuntimeSurfaceError(
                    "unsafe_console_evidence_key:" + ".".join(path + (key_text,))
                )
            _scan_public_payload_safety(item, path=path + (key_text,))
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, item in enumerate(value):
            _scan_public_payload_safety(item, path=path + (str(index),))
        return
    if isinstance(value, str) and any(pattern.search(value) for pattern in _SECRET_VALUE_PATTERNS):
        raise OperatorConsoleRuntimeSurfaceError(
            "unsafe_console_evidence_value:" + ".".join(path)
        )


def _scan_mutation_payload(value: object, *, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_text = str(key)
            lowered = key_text.lower()
            if lowered in _FORBIDDEN_MUTATION_FIELDS:
                raise OperatorConsoleRuntimeSurfaceError(
                    "direct_console_mutation_field_forbidden:" + ".".join(path + (key_text,))
                )
            if _SECRET_KEY_PATTERN.search(lowered) and not lowered.endswith("_hash"):
                raise OperatorConsoleRuntimeSurfaceError(
                    "mutation_route_secret_like_key:" + ".".join(path + (key_text,))
                )
            _scan_mutation_payload(item, path=path + (key_text,))
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, item in enumerate(value):
            _scan_mutation_payload(item, path=path + (str(index),))
        return
    if isinstance(value, str) and any(pattern.search(value) for pattern in _SECRET_VALUE_PATTERNS):
        raise OperatorConsoleRuntimeSurfaceError(
            "mutation_route_secret_like_value:" + ".".join(path)
        )


def _read_only_flags_valid(panel: OperatorConsoleRuntimePanel) -> bool:
    return (
        panel.read_only is True
        and panel.mutation_enabled is False
        and panel.command_enabled is False
        and panel.dispatch_enabled is False
        and panel.live_fetch_enabled is False
        and panel.external_tool_enabled is False
    )


def _normalize_failures(value: object, *, allow_empty: bool) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise OperatorConsoleRuntimeSurfaceError("failures_must_be_sequence")
    failures = tuple(str(item) for item in value if str(item))
    if not allow_empty and not failures:
        raise OperatorConsoleRuntimeSurfaceError("failures_required")
    for failure in failures:
        _require_nonempty_string(failure, "failure")
    return tuple(_dedupe(failures))


def _normalize_string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise OperatorConsoleRuntimeSurfaceError(field_name + "_must_be_sequence")
    normalized = tuple(str(item) for item in value)
    if not all(strict_nonempty_string(item) for item in normalized):
        raise OperatorConsoleRuntimeSurfaceError(field_name + "_must_be_nonempty_strings")
    return normalized


def _install_or_verify_hash(target: object, field_name: str, hash_fn: object) -> None:
    expected = hash_fn(target)  # type: ignore[operator]
    current = getattr(target, field_name)
    if current:
        if not strict_digest(current):
            raise OperatorConsoleRuntimeSurfaceError(field_name + "_must_be_digest")
        if current != expected:
            raise OperatorConsoleRuntimeSurfaceError(field_name + "_mismatch")
        return
    object.__setattr__(target, field_name, expected)


def _validate_runtime_root(root: Path) -> Path:
    raw = root.expanduser()
    if not str(raw):
        raise OperatorConsoleRuntimeSurfaceError("runtime_root_required")
    if raw.exists() and raw.is_symlink():
        raise OperatorConsoleRuntimeSurfaceError("runtime_root_is_symlink")
    if raw.exists() and not raw.is_dir():
        raise OperatorConsoleRuntimeSurfaceError("runtime_root_must_be_directory")
    resolved = raw.resolve(strict=False)
    _reject_secret_or_git_path(resolved, "runtime_root")
    return resolved


def _validate_relpath_tuple(
    values: Sequence[str],
    field_name: str,
    *,
    require_nonempty: bool,
) -> tuple[str, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise OperatorConsoleRuntimeSurfaceError(field_name + "_must_be_sequence")
    normalized = tuple(
        _validate_relpath_text(value, field_name, allow_empty=False)
        for value in values
    )
    if require_nonempty and not normalized:
        raise OperatorConsoleRuntimeSurfaceError(field_name + "_required")
    if len(set(normalized)) != len(normalized):
        raise OperatorConsoleRuntimeSurfaceError(field_name + "_duplicates_forbidden")
    return normalized


def _validate_relpath_text(value: object, field_name: str, *, allow_empty: bool) -> str:
    if not isinstance(value, str):
        raise OperatorConsoleRuntimeSurfaceError(field_name + "_must_be_string")
    if not value:
        if allow_empty:
            return ""
        raise OperatorConsoleRuntimeSurfaceError(field_name + "_required")
    if "\\" in value:
        raise OperatorConsoleRuntimeSurfaceError(field_name + "_must_use_posix_separators")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise OperatorConsoleRuntimeSurfaceError(field_name + "_must_be_relative")
    _reject_secret_or_git_path(Path(*path.parts), field_name)
    return str(path)


def _validated_identifier(value: object, field_name: str) -> str:
    if not strict_nonempty_string(value):
        raise OperatorConsoleRuntimeSurfaceError(field_name + "_required")
    text = str(value)
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.:-]{0,159}", text):
        raise OperatorConsoleRuntimeSurfaceError(field_name + "_invalid")
    return text


def _reject_secret_or_git_path(path: Path, field_name: str) -> None:
    if ".git" in path.parts:
        raise OperatorConsoleRuntimeSurfaceError(field_name + "_cannot_enter_git")
    if any(_SECRET_PATH_PATTERN.fullmatch(part) for part in path.parts):
        raise OperatorConsoleRuntimeSurfaceError(field_name + "_secret_like")


def _require_nonempty_string(value: object, field_name: str) -> None:
    if not strict_nonempty_string(value):
        raise OperatorConsoleRuntimeSurfaceError(field_name + "_required")


def _parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OperatorConsoleRuntimeSurfaceError("timestamp_invalid") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat(timespec="microseconds")
    if not strict_nonempty_string(value):
        raise OperatorConsoleRuntimeSurfaceError("timestamp_required")
    _parse_timestamp(value)
    return value


def _safe_error_text(exc: BaseException) -> str:
    text = str(exc.__class__.__name__)
    message = str(exc)
    if message:
        safe = re.sub(r"[^A-Za-z0-9_.,:-]", "_", message)
        text += ":" + safe[:160]
    return text


def _sha256_json(value: object) -> str:
    return digest_payload(_json_ready(value))


def _json_ready(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise OperatorConsoleRuntimeSurfaceError(
        "json_value_type_forbidden:" + type(value).__name__
    )


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return tuple(deduped)
