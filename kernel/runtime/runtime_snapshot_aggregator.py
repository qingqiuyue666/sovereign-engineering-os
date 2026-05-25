"""Runtime snapshot aggregator v1.

Aggregates dry-run runtime summaries into a deterministic snapshot for future
Operator Console consumption. This module is read-only and does not execute
tools, mutate journals, persist raw payloads, or create UI runtime surfaces.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Mapping
import hashlib
import json
import re

__all__ = [
    "ALLOWED_NEXT_ACTIONS",
    "FORBIDDEN_NEXT_ACTIONS",
    "RuntimeSnapshot",
    "aggregate_runtime_snapshot",
]

ALLOWED_NEXT_ACTIONS = frozenset(
    (
        "review_risk_assessment",
        "issue_scoped_approval",
        "run_dry_run_plan",
        "inspect_asset_inventory",
        "inspect_quarantine",
        "fix_manifest",
        "reject_tool_candidate",
    )
)

FORBIDDEN_NEXT_ACTIONS = frozenset(
    (
        "execute_raw_command",
        "launch_dcc",
        "run_comfyui",
        "call_provider",
        "open_browser",
        "access_network",
        "delete_files",
        "mutate_assets",
    )
)

_FORBIDDEN_SUMMARY_FIELDS = frozenset(
    (
        "raw_payload",
        "payload",
        "raw_prompt",
        "raw_provider_response",
        "secret_value",
        "env_value",
        "credential",
        "credentials",
        "secret",
        "api_key",
        "provider_key",
        "token_value",
        "password",
        "private_key",
        "raw_command",
        "command",
        "command_line",
        "argv",
        "args",
        "executable",
        "executable_path",
        "cwd",
        "workdir",
        "env",
        "environment",
        "path",
        "path_override",
        "timeout",
    )
)


@dataclass(frozen=True)
class RuntimeSnapshot:
    snapshot_id: str
    generated_at: str
    system_state: Mapping[str, object]
    journal_summary: Mapping[str, object]
    asset_summary: Mapping[str, object]
    workflow_summary: Mapping[str, object]
    tool_summary: Mapping[str, object]
    risk_summary: Mapping[str, object]
    approval_summary: Mapping[str, object]
    queue_summary: Mapping[str, object] | None
    next_actions: tuple[str, ...]
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    snapshot_hash: str

    def as_dict(self) -> dict[str, object]:
        return {
            "snapshot_id": self.snapshot_id,
            "generated_at": self.generated_at,
            "system_state": _json_ready(self.system_state),
            "journal_summary": _json_ready(self.journal_summary),
            "asset_summary": _json_ready(self.asset_summary),
            "workflow_summary": _json_ready(self.workflow_summary),
            "tool_summary": _json_ready(self.tool_summary),
            "risk_summary": _json_ready(self.risk_summary),
            "approval_summary": _json_ready(self.approval_summary),
            "queue_summary": _json_ready(self.queue_summary),
            "next_actions": list(self.next_actions),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "snapshot_hash": self.snapshot_hash,
        }


def aggregate_runtime_snapshot(
    *,
    system_state: Mapping[str, object],
    journal_event_summaries: tuple[object, ...] | list[object] = (),
    asset_inventory_summaries: tuple[object, ...] | list[object] = (),
    workflow_graph_descriptors: tuple[object, ...] | list[object] = (),
    tool_manifest_summaries: tuple[object, ...] | list[object] = (),
    risk_assessments: tuple[object, ...] | list[object] = (),
    approval_requirements: tuple[object, ...] | list[object] = (),
    approval_token_summaries: tuple[object, ...] | list[object] = (),
    operator_console_state_model_ref: object | None = None,
    queue_summary: Mapping[str, object] | None = None,
    next_actions: tuple[str, ...] | list[str] = (),
    blockers: tuple[str, ...] | list[str] = (),
    warnings: tuple[str, ...] | list[str] = (),
    generated_at: str | None = None,
) -> RuntimeSnapshot:
    """Aggregate read-only summaries into one Operator Console snapshot."""

    system_summary = _system_state(system_state, operator_console_state_model_ref)
    journal_summary = _journal_summary(journal_event_summaries)
    asset_summary = _asset_summary(asset_inventory_summaries)
    workflow_summary = _workflow_summary(workflow_graph_descriptors)
    tool_summary = _tool_summary(tool_manifest_summaries)
    risk_summary = _risk_summary(risk_assessments)
    approval_summary = _approval_summary(
        approval_requirements=approval_requirements,
        approval_token_summaries=approval_token_summaries,
    )
    sanitized_queue_summary = (
        None if queue_summary is None else _sanitize_mapping(queue_summary)
    )
    resolved_blockers = tuple(sorted(str(item) for item in blockers if str(item)))
    resolved_warnings = tuple(sorted(str(item) for item in warnings if str(item)))
    resolved_next_actions = _next_actions(
        explicit_actions=tuple(next_actions),
        asset_summary=asset_summary,
        risk_summary=risk_summary,
        approval_summary=approval_summary,
        blockers=resolved_blockers,
    )
    fields = {
        "system_state": system_summary,
        "journal_summary": journal_summary,
        "asset_summary": asset_summary,
        "workflow_summary": workflow_summary,
        "tool_summary": tool_summary,
        "risk_summary": risk_summary,
        "approval_summary": approval_summary,
        "queue_summary": sanitized_queue_summary,
        "next_actions": resolved_next_actions,
        "blockers": resolved_blockers,
        "warnings": resolved_warnings,
    }
    snapshot_hash = _hash(fields)
    return RuntimeSnapshot(
        snapshot_id="runtime_snapshot_" + snapshot_hash.removeprefix("sha256:")[:32],
        generated_at=generated_at or _now(),
        **fields,
        snapshot_hash=snapshot_hash,
    )


def _system_state(
    system_state: Mapping[str, object],
    operator_console_state_model_ref: object | None,
) -> Mapping[str, object]:
    if not isinstance(system_state, Mapping):
        raise ValueError("system_state_must_be_mapping")
    summary = dict(_sanitize_mapping(system_state))
    if operator_console_state_model_ref is not None:
        console_state = _record(operator_console_state_model_ref)
        summary["operator_console_state_model_ref"] = {
            "model_version": console_state.get("model_version", "unknown"),
            "ui_runtime_present": bool(console_state.get("ui_runtime_present")),
            "production_autonomy_allowed": bool(
                console_state.get("production_autonomy_allowed")
            ),
            "panel_count": len(console_state.get("panels", ()))
            if isinstance(console_state.get("panels"), (list, tuple))
            else 0,
        }
    return _stable_mapping(summary)


def _journal_summary(records: tuple[object, ...] | list[object]) -> Mapping[str, object]:
    items = _records(records)
    return _stable_mapping(
        {
            "event_count": len(items),
            "event_ids": _field_values(items, "event_id"),
            "run_ids": _field_values(items, "run_id"),
            "task_ids": _field_values(items, "task_id"),
            "stages": _field_values(items, "stage"),
            "event_types": _field_values(items, "event_type"),
            "payload_digests": _field_values(items, "payload_digest"),
            "content_hashes": _hash_values(items),
        }
    )


def _asset_summary(records: tuple[object, ...] | list[object]) -> Mapping[str, object]:
    items = _records(records)
    return _stable_mapping(
        {
            "asset_count": len(items),
            "asset_ids": _field_values(items, "asset_id"),
            "root_ids": _field_values(items, "root_id"),
            "media_classes": _field_values(items, "media_class"),
            "sha256_values": _field_values(items, "sha256"),
            "content_hashes": _hash_values(items),
        }
    )


def _workflow_summary(records: tuple[object, ...] | list[object]) -> Mapping[str, object]:
    items = _records(records)
    return _stable_mapping(
        {
            "workflow_count": len(items),
            "workflow_ids": _field_values(items, "workflow_id"),
            "graph_hashes": _field_values(items, "graph_hash"),
            "required_tools": _flatten_field_values(items, "required_tools"),
            "required_assets": _flatten_field_values(items, "required_assets"),
            "approval_requirements": _flatten_field_values(
                items, "approval_requirements"
            ),
        }
    )


def _tool_summary(records: tuple[object, ...] | list[object]) -> Mapping[str, object]:
    items = _records(records)
    return _stable_mapping(
        {
            "tool_count": len(items),
            "tool_ids": _field_values(items, "tool_id"),
            "manifest_ids": _field_values(items, "manifest_id"),
            "source_types": _field_values(items, "source_type"),
            "content_hashes": _hash_values(items),
        }
    )


def _risk_summary(records: tuple[object, ...] | list[object]) -> Mapping[str, object]:
    items = _records(records)
    approval_required_count = sum(1 for item in items if bool(item.get("approval_required")))
    production_blocked_count = sum(
        1 for item in items if not bool(item.get("production_admission_allowed"))
    )
    high_risk_count = sum(1 for item in items if item.get("highest_risk") == "HIGH_RISK")
    return _stable_mapping(
        {
            "risk_count": len(items),
            "tool_ids": _field_values(items, "tool_id"),
            "highest_risks": _field_values(items, "highest_risk"),
            "risk_classes": _flatten_field_values(items, "risk_classes"),
            "approval_required_count": approval_required_count,
            "production_blocked_count": production_blocked_count,
            "high_risk_count": high_risk_count,
            "content_hashes": _hash_values(items),
        }
    )


def _approval_summary(
    *,
    approval_requirements: tuple[object, ...] | list[object],
    approval_token_summaries: tuple[object, ...] | list[object],
) -> Mapping[str, object]:
    requirements = _records(approval_requirements)
    tokens = _records(approval_token_summaries)
    return _stable_mapping(
        {
            "requirement_count": len(requirements),
            "approval_required_count": sum(
                1 for item in requirements if bool(item.get("approval_required"))
            ),
            "token_required_count": sum(
                1 for item in requirements if bool(item.get("token_required"))
            ),
            "requirement_ids": _field_values(requirements, "requirement_id"),
            "required_action_types": _field_values(requirements, "required_action_type"),
            "token_count": len(tokens),
            "token_ids": _field_values(tokens, "approval_id"),
            "revoked_token_count": sum(1 for item in tokens if bool(item.get("revoked"))),
            "content_hashes": _hash_values(requirements + tokens),
        }
    )


def _next_actions(
    *,
    explicit_actions: tuple[str, ...],
    asset_summary: Mapping[str, object],
    risk_summary: Mapping[str, object],
    approval_summary: Mapping[str, object],
    blockers: tuple[str, ...],
) -> tuple[str, ...]:
    actions = set(str(action) for action in explicit_actions if str(action))
    forbidden = sorted(actions.intersection(FORBIDDEN_NEXT_ACTIONS))
    if forbidden:
        raise ValueError("forbidden_next_actions:" + ",".join(forbidden))
    unknown = sorted(actions.difference(ALLOWED_NEXT_ACTIONS))
    if unknown:
        raise ValueError("unknown_next_actions:" + ",".join(unknown))
    if not actions:
        if int(risk_summary["risk_count"]) > 0:
            actions.add("review_risk_assessment")
        if int(approval_summary["approval_required_count"]) > 0:
            actions.add("issue_scoped_approval")
        if int(asset_summary["asset_count"]) > 0:
            actions.add("inspect_asset_inventory")
        if blockers:
            actions.add("fix_manifest")
    return tuple(sorted(actions))


def _records(records: tuple[object, ...] | list[object]) -> list[Mapping[str, object]]:
    if not isinstance(records, (tuple, list)):
        raise ValueError("summary_records_must_be_sequence")
    return [_record(record) for record in records]


def _record(record: object) -> Mapping[str, object]:
    if hasattr(record, "as_dict"):
        value = record.as_dict()
    elif dataclass_is_instance(record):
        value = asdict(record)
    elif isinstance(record, Mapping):
        value = dict(record)
    else:
        raise ValueError("summary_record_must_be_mapping_or_dataclass")
    return _sanitize_mapping(value)


def dataclass_is_instance(value: object) -> bool:
    return hasattr(value, "__dataclass_fields__")


def _sanitize_mapping(payload: Mapping[str, object]) -> Mapping[str, object]:
    forbidden = _forbidden_fields(payload)
    if forbidden:
        raise ValueError("forbidden_summary_fields:" + ",".join(forbidden))
    return _stable_mapping(payload)


def _forbidden_fields(payload: Mapping[str, object]) -> tuple[str, ...]:
    found: set[str] = set()
    for key, value in payload.items():
        normalized = _normalize_key(str(key))
        if normalized in _FORBIDDEN_SUMMARY_FIELDS:
            found.add(normalized)
        if isinstance(value, Mapping):
            found.update(_forbidden_fields(value))
        elif isinstance(value, (tuple, list)):
            for item in value:
                if isinstance(item, Mapping):
                    found.update(_forbidden_fields(item))
    return tuple(sorted(found))


def _field_values(records: list[Mapping[str, object]], field_name: str) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                str(record[field_name])
                for record in records
                if field_name in record and record[field_name] not in (None, "")
            }
        )
    )


def _flatten_field_values(
    records: list[Mapping[str, object]],
    field_name: str,
) -> tuple[str, ...]:
    values: set[str] = set()
    for record in records:
        value = record.get(field_name)
        if isinstance(value, (tuple, list)):
            values.update(str(item) for item in value if str(item))
        elif value not in (None, ""):
            values.add(str(value))
    return tuple(sorted(values))


def _hash_values(records: list[Mapping[str, object]]) -> tuple[str, ...]:
    values: set[str] = set()
    for record in records:
        for field_name in ("content_hash", "binding_hash", "graph_hash", "snapshot_hash"):
            value = record.get(field_name)
            if isinstance(value, str) and value.startswith("sha256:"):
                values.add(value)
    return tuple(sorted(values))


def _stable_mapping(payload: Mapping[str, object]) -> Mapping[str, object]:
    return {str(key): _json_ready(payload[key]) for key in sorted(payload, key=str)}


def _json_ready(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _json_ready(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value.strip()).strip("_").lower()


def _hash(payload: Mapping[str, object]) -> str:
    canonical = json.dumps(_json_ready(payload), sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")
