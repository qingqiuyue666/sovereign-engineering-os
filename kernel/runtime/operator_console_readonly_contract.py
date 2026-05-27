"""Read-only operator console contract v1.

This module defines digest-only read models for an operator console snapshot.
It does not render a UI, mutate state, dispatch work, call providers, open
external tools, or read environment state. Observation timestamps are metadata
and excluded from deterministic hashes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_bool, strict_digest, strict_nonempty_string

__all__ = [
    "ConsoleReadOnlyDataSource",
    "OperatorConsoleReadOnlySnapshot",
    "build_console_readonly_data_source",
    "build_operator_console_readonly_snapshot",
    "validate_console_readonly_data_source",
    "validate_operator_console_readonly_snapshot",
]

_CONTRACT_VERSION = "operator-console-readonly-contract-v1"
_CODE_VERSION = "0.1.0"

_REQUIRED_PANELS = (
    "summary",
    "queue",
    "artifacts",
    "receipts",
    "failures",
    "approvals",
    "replay",
    "workers",
    "watchdog",
    "system_health",
)
_ALLOWED_SOURCE_TYPES = frozenset(
    {
        "approval_runtime",
        "artifact_store",
        "failure_bundle_center",
        "job_queue",
        "pr_readiness",
        "replay_report",
        "snapshot_store",
        "system_health",
        "wal",
        "watchdog_receipts",
        "worker_registry",
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
        "value",
    }
)
_FORBIDDEN_KEY_FRAGMENTS = (
    "api_key",
    "credential",
    "private_key",
    "raw",
    "secret",
)


@dataclass(frozen=True)
class ConsoleReadOnlyDataSource:
    """Digest-only data source visible in the read-only console."""

    source_id: str
    source_type: str
    source_hash: str
    wal_record_hash: str
    redaction_policy_hash: str
    read_only: bool
    mutation_enabled: bool
    command_enabled: bool
    dispatch_enabled: bool
    live_fetch_enabled: bool
    external_tool_enabled: bool
    contract_version: str = _CONTRACT_VERSION
    code_version: str = _CODE_VERSION
    data_source_hash: str = ""
    observed_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "code_version": self.code_version,
            "command_enabled": self.command_enabled,
            "contract_version": self.contract_version,
            "dispatch_enabled": self.dispatch_enabled,
            "external_tool_enabled": self.external_tool_enabled,
            "live_fetch_enabled": self.live_fetch_enabled,
            "mutation_enabled": self.mutation_enabled,
            "read_only": self.read_only,
            "redaction_policy_hash": self.redaction_policy_hash,
            "source_hash": self.source_hash,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "wal_record_hash": self.wal_record_hash,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["data_source_hash"] = self.data_source_hash
        payload["observed_at"] = self.observed_at
        return payload


@dataclass(frozen=True)
class OperatorConsoleReadOnlySnapshot:
    """Deterministic read-only console snapshot."""

    console_snapshot_id: str
    task_id: str
    run_id: str
    panel_ids: tuple[str, ...]
    data_source_hashes: tuple[str, ...]
    wal_head_hash: str
    artifact_store_root_hash: str
    approval_runtime_hash: str
    failure_center_manifest_hash: str
    worker_registry_manifest_hash: str
    watchdog_chain_head_hash: str
    replay_report_hash: str
    snapshot_reconstruction_hash: str
    read_only: bool
    mutation_enabled: bool
    command_enabled: bool
    dispatch_enabled: bool
    live_fetch_enabled: bool
    external_tool_enabled: bool
    contract_version: str = _CONTRACT_VERSION
    code_version: str = _CODE_VERSION
    snapshot_hash: str = ""
    observed_at: str = ""

    def deterministic_material(self) -> dict[str, object]:
        return {
            "approval_runtime_hash": self.approval_runtime_hash,
            "artifact_store_root_hash": self.artifact_store_root_hash,
            "code_version": self.code_version,
            "command_enabled": self.command_enabled,
            "console_snapshot_id": self.console_snapshot_id,
            "contract_version": self.contract_version,
            "data_source_hashes": self.data_source_hashes,
            "dispatch_enabled": self.dispatch_enabled,
            "external_tool_enabled": self.external_tool_enabled,
            "failure_center_manifest_hash": self.failure_center_manifest_hash,
            "live_fetch_enabled": self.live_fetch_enabled,
            "mutation_enabled": self.mutation_enabled,
            "panel_ids": self.panel_ids,
            "read_only": self.read_only,
            "replay_report_hash": self.replay_report_hash,
            "run_id": self.run_id,
            "snapshot_reconstruction_hash": self.snapshot_reconstruction_hash,
            "task_id": self.task_id,
            "wal_head_hash": self.wal_head_hash,
            "watchdog_chain_head_hash": self.watchdog_chain_head_hash,
            "worker_registry_manifest_hash": self.worker_registry_manifest_hash,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["observed_at"] = self.observed_at
        payload["snapshot_hash"] = self.snapshot_hash
        return payload


def build_console_readonly_data_source(
    payload: Mapping[str, Any],
    *,
    observed_at: str | None = None,
) -> ConsoleReadOnlyDataSource:
    """Build a validated read-only console data source."""

    _require_mapping(payload)
    _reject_forbidden_material(payload)

    source_id = _string_field(payload, "source_id")
    source_type = _string_field(payload, "source_type")
    read_only = _bool_field(payload, "read_only")
    mutation_enabled = _bool_field(payload, "mutation_enabled")
    command_enabled = _bool_field(payload, "command_enabled")
    dispatch_enabled = _bool_field(payload, "dispatch_enabled")
    live_fetch_enabled = _bool_field(payload, "live_fetch_enabled")
    external_tool_enabled = _bool_field(payload, "external_tool_enabled")

    if source_type not in _ALLOWED_SOURCE_TYPES:
        raise ValueError("console_data_source_type_not_allowed")
    _require_read_only_flags(
        read_only=read_only,
        mutation_enabled=mutation_enabled,
        command_enabled=command_enabled,
        dispatch_enabled=dispatch_enabled,
        live_fetch_enabled=live_fetch_enabled,
        external_tool_enabled=external_tool_enabled,
    )

    material = {
        "code_version": _CODE_VERSION,
        "command_enabled": command_enabled,
        "contract_version": _CONTRACT_VERSION,
        "dispatch_enabled": dispatch_enabled,
        "external_tool_enabled": external_tool_enabled,
        "live_fetch_enabled": live_fetch_enabled,
        "mutation_enabled": mutation_enabled,
        "read_only": read_only,
        "redaction_policy_hash": _digest_field(payload, "redaction_policy_hash"),
        "source_hash": _digest_field(payload, "source_hash"),
        "source_id": source_id,
        "source_type": source_type,
        "wal_record_hash": _digest_field(payload, "wal_record_hash"),
    }
    observed = _observed_at(observed_at)
    return ConsoleReadOnlyDataSource(
        source_id=source_id,
        source_type=source_type,
        source_hash=str(material["source_hash"]),
        wal_record_hash=str(material["wal_record_hash"]),
        redaction_policy_hash=str(material["redaction_policy_hash"]),
        read_only=read_only,
        mutation_enabled=mutation_enabled,
        command_enabled=command_enabled,
        dispatch_enabled=dispatch_enabled,
        live_fetch_enabled=live_fetch_enabled,
        external_tool_enabled=external_tool_enabled,
        data_source_hash=digest_payload(material),
        observed_at=observed,
    )


def build_operator_console_readonly_snapshot(
    *,
    console_snapshot_id: str,
    task_id: str,
    run_id: str,
    data_sources: Sequence[ConsoleReadOnlyDataSource],
    wal_head_hash: str,
    artifact_store_root_hash: str,
    approval_runtime_hash: str,
    failure_center_manifest_hash: str,
    worker_registry_manifest_hash: str,
    watchdog_chain_head_hash: str,
    replay_report_hash: str,
    snapshot_reconstruction_hash: str,
    panel_ids: Sequence[str] = _REQUIRED_PANELS,
    observed_at: str | None = None,
) -> OperatorConsoleReadOnlySnapshot:
    """Build a deterministic read-only operator console snapshot."""

    for field, value in (
        ("console_snapshot_id", console_snapshot_id),
        ("task_id", task_id),
        ("run_id", run_id),
    ):
        if not strict_nonempty_string(value):
            raise ValueError(f"{field}_must_be_nonempty_string")

    panel_tuple = _panel_tuple(panel_ids)
    data_source_hashes: list[str] = []
    source_ids: set[str] = set()
    for source in data_sources:
        if not validate_console_readonly_data_source(source):
            raise ValueError("console_data_source_invalid")
        if source.source_id in source_ids:
            raise ValueError("duplicate_console_data_source_id")
        if source.data_source_hash in data_source_hashes:
            raise ValueError("duplicate_console_data_source_hash")
        source_ids.add(source.source_id)
        data_source_hashes.append(source.data_source_hash)
    if not data_source_hashes:
        raise ValueError("console_data_sources_required")

    material = {
        "approval_runtime_hash": _checked_digest(approval_runtime_hash, "approval_runtime_hash"),
        "artifact_store_root_hash": _checked_digest(artifact_store_root_hash, "artifact_store_root_hash"),
        "code_version": _CODE_VERSION,
        "command_enabled": False,
        "console_snapshot_id": console_snapshot_id,
        "contract_version": _CONTRACT_VERSION,
        "data_source_hashes": tuple(data_source_hashes),
        "dispatch_enabled": False,
        "external_tool_enabled": False,
        "failure_center_manifest_hash": _checked_digest(
            failure_center_manifest_hash,
            "failure_center_manifest_hash",
        ),
        "live_fetch_enabled": False,
        "mutation_enabled": False,
        "panel_ids": panel_tuple,
        "read_only": True,
        "replay_report_hash": _checked_digest(replay_report_hash, "replay_report_hash"),
        "run_id": run_id,
        "snapshot_reconstruction_hash": _checked_digest(
            snapshot_reconstruction_hash,
            "snapshot_reconstruction_hash",
        ),
        "task_id": task_id,
        "wal_head_hash": _checked_digest(wal_head_hash, "wal_head_hash"),
        "watchdog_chain_head_hash": _checked_digest(
            watchdog_chain_head_hash,
            "watchdog_chain_head_hash",
        ),
        "worker_registry_manifest_hash": _checked_digest(
            worker_registry_manifest_hash,
            "worker_registry_manifest_hash",
        ),
    }
    observed = _observed_at(observed_at)
    return OperatorConsoleReadOnlySnapshot(
        console_snapshot_id=console_snapshot_id,
        task_id=task_id,
        run_id=run_id,
        panel_ids=panel_tuple,
        data_source_hashes=tuple(data_source_hashes),
        wal_head_hash=str(material["wal_head_hash"]),
        artifact_store_root_hash=str(material["artifact_store_root_hash"]),
        approval_runtime_hash=str(material["approval_runtime_hash"]),
        failure_center_manifest_hash=str(material["failure_center_manifest_hash"]),
        worker_registry_manifest_hash=str(material["worker_registry_manifest_hash"]),
        watchdog_chain_head_hash=str(material["watchdog_chain_head_hash"]),
        replay_report_hash=str(material["replay_report_hash"]),
        snapshot_reconstruction_hash=str(material["snapshot_reconstruction_hash"]),
        read_only=True,
        mutation_enabled=False,
        command_enabled=False,
        dispatch_enabled=False,
        live_fetch_enabled=False,
        external_tool_enabled=False,
        snapshot_hash=digest_payload(material),
        observed_at=observed,
    )


def validate_console_readonly_data_source(source: ConsoleReadOnlyDataSource) -> bool:
    if not isinstance(source, ConsoleReadOnlyDataSource):
        return False
    if not strict_nonempty_string(source.source_id):
        return False
    if source.source_type not in _ALLOWED_SOURCE_TYPES:
        return False
    for value in (source.source_hash, source.wal_record_hash, source.redaction_policy_hash):
        if not strict_digest(value):
            return False
    if not _read_only_flags_valid(
        read_only=source.read_only,
        mutation_enabled=source.mutation_enabled,
        command_enabled=source.command_enabled,
        dispatch_enabled=source.dispatch_enabled,
        live_fetch_enabled=source.live_fetch_enabled,
        external_tool_enabled=source.external_tool_enabled,
    ):
        return False
    if not strict_nonempty_string(source.contract_version):
        return False
    if not strict_nonempty_string(source.code_version):
        return False
    return source.data_source_hash == digest_payload(source.deterministic_material())


def validate_operator_console_readonly_snapshot(
    snapshot: OperatorConsoleReadOnlySnapshot,
) -> bool:
    if not isinstance(snapshot, OperatorConsoleReadOnlySnapshot):
        return False
    for value in (
        snapshot.console_snapshot_id,
        snapshot.task_id,
        snapshot.run_id,
        snapshot.contract_version,
        snapshot.code_version,
    ):
        if not strict_nonempty_string(value):
            return False
    if not _panel_tuple_valid(snapshot.panel_ids):
        return False
    if not snapshot.data_source_hashes:
        return False
    if len(set(snapshot.data_source_hashes)) != len(snapshot.data_source_hashes):
        return False
    if not all(strict_digest(value) for value in snapshot.data_source_hashes):
        return False
    for value in (
        snapshot.wal_head_hash,
        snapshot.artifact_store_root_hash,
        snapshot.approval_runtime_hash,
        snapshot.failure_center_manifest_hash,
        snapshot.worker_registry_manifest_hash,
        snapshot.watchdog_chain_head_hash,
        snapshot.replay_report_hash,
        snapshot.snapshot_reconstruction_hash,
    ):
        if not strict_digest(value):
            return False
    if not _read_only_flags_valid(
        read_only=snapshot.read_only,
        mutation_enabled=snapshot.mutation_enabled,
        command_enabled=snapshot.command_enabled,
        dispatch_enabled=snapshot.dispatch_enabled,
        live_fetch_enabled=snapshot.live_fetch_enabled,
        external_tool_enabled=snapshot.external_tool_enabled,
    ):
        return False
    return snapshot.snapshot_hash == digest_payload(snapshot.deterministic_material())


def _require_mapping(payload: Mapping[str, Any]) -> None:
    if not isinstance(payload, Mapping):
        raise ValueError("console_readonly_payload_must_be_mapping")


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


def _bool_field(payload: Mapping[str, Any], field: str) -> bool:
    value = payload.get(field)
    if not strict_bool(value):
        raise ValueError(f"{field}_must_be_bool")
    return bool(value)


def _checked_digest(value: Any, field: str) -> str:
    if not strict_digest(value):
        raise ValueError(f"{field}_must_be_valid_digest")
    return str(value)


def _panel_tuple(panel_ids: Sequence[str]) -> tuple[str, ...]:
    if not isinstance(panel_ids, Sequence) or isinstance(panel_ids, (str, bytes)):
        raise ValueError("panel_ids_must_be_sequence")
    panel_tuple = tuple(str(panel_id) for panel_id in panel_ids if strict_nonempty_string(panel_id))
    if len(panel_tuple) != len(panel_ids):
        raise ValueError("panel_ids_must_contain_nonempty_strings")
    if not _panel_tuple_valid(panel_tuple):
        raise ValueError("panel_ids_must_include_required_panels_once")
    return panel_tuple


def _panel_tuple_valid(panel_ids: tuple[str, ...]) -> bool:
    return (
        bool(panel_ids)
        and len(set(panel_ids)) == len(panel_ids)
        and set(_REQUIRED_PANELS).issubset(set(panel_ids))
    )


def _require_read_only_flags(**flags: bool) -> None:
    if not _read_only_flags_valid(**flags):
        raise ValueError("console_source_must_be_read_only")


def _read_only_flags_valid(
    *,
    read_only: bool,
    mutation_enabled: bool,
    command_enabled: bool,
    dispatch_enabled: bool,
    live_fetch_enabled: bool,
    external_tool_enabled: bool,
) -> bool:
    return (
        read_only is True
        and mutation_enabled is False
        and command_enabled is False
        and dispatch_enabled is False
        and live_fetch_enabled is False
        and external_tool_enabled is False
    )


def _reject_forbidden_material(value: Any, *, path: str = "") -> None:
    if isinstance(value, Mapping):
        for raw_key, nested in value.items():
            if not isinstance(raw_key, str):
                raise ValueError("console_readonly_keys_must_be_strings")
            key = raw_key.lower()
            key_path = f"{path}.{raw_key}" if path else raw_key
            if key in _FORBIDDEN_EXACT_KEYS:
                raise ValueError(f"forbidden_console_material_field_{key_path}")
            if any(fragment in key for fragment in _FORBIDDEN_KEY_FRAGMENTS):
                raise ValueError(f"forbidden_console_material_field_{key_path}")
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
