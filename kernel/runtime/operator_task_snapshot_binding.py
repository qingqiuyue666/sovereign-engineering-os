"""Operator task snapshot binding v1.

Builds a task-level read model for future Operator Console consumption from a
dry-run plan, tool binding report, risk approval report, asset summaries, and
journal summaries. The snapshot is advisory and does not authorize execution.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Mapping
import hashlib
import json
import re

from kernel.runtime.operator_console_state_model import build_operator_console_state
from kernel.runtime.workflow_dry_run_plan import (
    PlanStep,
    WorkflowDryRunPlan,
    validate_workflow_dry_run_plan,
)
from kernel.runtime.workflow_risk_approval_binding import (
    WorkflowRiskApprovalBindingReport,
)
from kernel.runtime.workflow_tool_requirement_binding import (
    RequiredToolBinding,
    WorkflowToolRequirementBindingReport,
)

__all__ = [
    "ALLOWED_NEXT_ACTIONS",
    "FORBIDDEN_NEXT_ACTIONS",
    "OperatorTaskSnapshot",
    "build_operator_task_snapshot",
]

ALLOWED_NEXT_ACTIONS = frozenset(
    (
        "review_dry_run_plan",
        "inspect_missing_tool",
        "review_risk_assessment",
        "issue_scoped_approval",
        "inspect_asset_inventory",
        "inspect_quarantine",
        "fix_tool_manifest",
        "reject_tool_candidate",
        "rerun_dry_run_planning",
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
        "install_dependency",
        "run_mcp_tool",
        "run_cli_tool",
        "run_plugin",
    )
)

FORBIDDEN_SUMMARY_FIELDS = frozenset(
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
        "executable_path",
        "cwd",
        "workdir",
        "env",
        "environment",
        "path_override",
        "timeout",
    )
)


@dataclass(frozen=True)
class OperatorTaskSnapshot:
    snapshot_id: str
    task_id: str
    workflow_id: str
    generated_at: str
    dry_run_plan_summary: Mapping[str, object]
    tool_binding_summary: Mapping[str, object]
    risk_approval_summary: Mapping[str, object]
    asset_summary: Mapping[str, object]
    journal_summary: Mapping[str, object]
    approval_summary: Mapping[str, object]
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    next_actions: tuple[str, ...]
    operator_state: Mapping[str, object]
    snapshot_hash: str

    def as_dict(self) -> dict[str, object]:
        return {
            "snapshot_id": self.snapshot_id,
            "task_id": self.task_id,
            "workflow_id": self.workflow_id,
            "generated_at": self.generated_at,
            "dry_run_plan_summary": _json_ready(self.dry_run_plan_summary),
            "tool_binding_summary": _json_ready(self.tool_binding_summary),
            "risk_approval_summary": _json_ready(self.risk_approval_summary),
            "asset_summary": _json_ready(self.asset_summary),
            "journal_summary": _json_ready(self.journal_summary),
            "approval_summary": _json_ready(self.approval_summary),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "next_actions": list(self.next_actions),
            "operator_state": _json_ready(self.operator_state),
            "snapshot_hash": self.snapshot_hash,
        }


def build_operator_task_snapshot(
    *,
    dry_run_plan: WorkflowDryRunPlan | Mapping[str, object],
    tool_binding_report: WorkflowToolRequirementBindingReport | Mapping[str, object],
    risk_approval_report: WorkflowRiskApprovalBindingReport | Mapping[str, object],
    asset_inventory_summaries: tuple[object, ...] | list[object] = (),
    journal_summaries: tuple[object, ...] | list[object] = (),
    approval_requirement_summaries: tuple[object, ...] | list[object] = (),
    operator_state_ref: object | None = None,
    next_actions: tuple[str, ...] | list[str] = (),
    generated_at: str | None = None,
) -> OperatorTaskSnapshot:
    """Aggregate task-level planning state without runtime authority."""

    plan = _plan(dry_run_plan)
    plan_failures = validate_workflow_dry_run_plan(plan)
    if plan_failures:
        raise ValueError("workflow_dry_run_plan_invalid:" + ",".join(plan_failures))
    tool_report = _tool_binding_report(tool_binding_report)
    risk_report = _risk_approval_report(risk_approval_report)
    assets = _records(asset_inventory_summaries)
    journals = _records(journal_summaries)
    approvals = _records(approval_requirement_summaries)
    operator_state = _operator_state(operator_state_ref)

    dry_run_plan_summary = _plan_summary(plan)
    tool_binding_summary = _tool_summary(tool_report)
    risk_approval_summary = _risk_summary(risk_report)
    asset_summary = _asset_summary(assets)
    journal_summary = _journal_summary(journals)
    approval_summary = _approval_summary(approvals, risk_report)
    blockers = _blockers(plan, tool_report, risk_report)
    warnings = _warnings(plan, tool_report, risk_report)
    resolved_next_actions = _next_actions(
        explicit_actions=tuple(next_actions),
        tool_binding_summary=tool_binding_summary,
        risk_approval_summary=risk_approval_summary,
        asset_summary=asset_summary,
        blockers=blockers,
    )
    fields = {
        "task_id": plan.task_id,
        "workflow_id": plan.workflow_id,
        "dry_run_plan_summary": dry_run_plan_summary,
        "tool_binding_summary": tool_binding_summary,
        "risk_approval_summary": risk_approval_summary,
        "asset_summary": asset_summary,
        "journal_summary": journal_summary,
        "approval_summary": approval_summary,
        "blockers": blockers,
        "warnings": warnings,
        "next_actions": resolved_next_actions,
        "operator_state": operator_state,
    }
    snapshot_hash = _hash(fields)
    return OperatorTaskSnapshot(
        snapshot_id="operator_task_snapshot_" + snapshot_hash.removeprefix("sha256:")[:32],
        task_id=plan.task_id,
        workflow_id=plan.workflow_id,
        generated_at=generated_at or _now(),
        dry_run_plan_summary=dry_run_plan_summary,
        tool_binding_summary=tool_binding_summary,
        risk_approval_summary=risk_approval_summary,
        asset_summary=asset_summary,
        journal_summary=journal_summary,
        approval_summary=approval_summary,
        blockers=blockers,
        warnings=warnings,
        next_actions=resolved_next_actions,
        operator_state=operator_state,
        snapshot_hash=snapshot_hash,
    )


def _plan_summary(plan: WorkflowDryRunPlan) -> Mapping[str, object]:
    return _stable_mapping(
        {
            "plan_id": plan.plan_id,
            "task_id": plan.task_id,
            "workflow_id": plan.workflow_id,
            "workflow_graph_hash": plan.workflow_graph_hash,
            "step_count": len(plan.plan_steps),
            "required_tools": plan.required_tools,
            "required_assets": plan.required_assets,
            "approval_requirements": plan.approval_requirements,
            "evidence_requirements": plan.evidence_requirements,
            "dry_run_only": plan.dry_run_only,
            "executable": plan.executable,
            "content_hash": plan.content_hash,
        }
    )


def _tool_summary(report: WorkflowToolRequirementBindingReport) -> Mapping[str, object]:
    statuses = [binding.match_status for binding in report.required_tool_bindings]
    return _stable_mapping(
        {
            "binding_id": report.binding_id,
            "plan_id": report.plan_id,
            "workflow_id": report.workflow_id,
            "binding_count": len(report.required_tool_bindings),
            "matched_count": statuses.count("MATCHED"),
            "missing_count": statuses.count("MISSING"),
            "incompatible_count": statuses.count("INCOMPATIBLE"),
            "requires_approval_count": statuses.count("REQUIRES_APPROVAL"),
            "missing_tool_requirements": report.missing_tool_requirements,
            "incompatible_tools": report.incompatible_tools,
            "blockers": report.blockers,
            "warnings": report.warnings,
            "binding_hash": report.binding_hash,
        }
    )


def _risk_summary(report: WorkflowRiskApprovalBindingReport) -> Mapping[str, object]:
    return _stable_mapping(
        {
            "report_id": report.report_id,
            "plan_id": report.plan_id,
            "workflow_id": report.workflow_id,
            "highest_risk": report.highest_risk,
            "blocked_steps": report.blocked_steps,
            "missing_approvals": report.missing_approvals,
            "production_admission_allowed": report.production_admission_allowed,
            "dry_run_admission_allowed": report.dry_run_admission_allowed,
            "blockers": report.blockers,
            "warnings": report.warnings,
            "report_hash": report.report_hash,
        }
    )


def _asset_summary(records: list[Mapping[str, object]]) -> Mapping[str, object]:
    return _stable_mapping(
        {
            "asset_count": len(records),
            "asset_ids": _field_values(records, "asset_id"),
            "media_classes": _field_values(records, "media_class"),
            "content_hashes": _hash_values(records),
        }
    )


def _journal_summary(records: list[Mapping[str, object]]) -> Mapping[str, object]:
    return _stable_mapping(
        {
            "event_count": len(records),
            "event_ids": _field_values(records, "event_id"),
            "run_ids": _field_values(records, "run_id"),
            "task_ids": _field_values(records, "task_id"),
            "stages": _field_values(records, "stage"),
            "content_hashes": _hash_values(records),
        }
    )


def _approval_summary(
    records: list[Mapping[str, object]],
    risk_report: WorkflowRiskApprovalBindingReport,
) -> Mapping[str, object]:
    return _stable_mapping(
        {
            "requirement_count": len(records),
            "requirement_ids": _field_values(records, "requirement_id"),
            "required_action_types": _field_values(records, "required_action_type"),
            "missing_approvals": risk_report.missing_approvals,
            "content_hashes": _hash_values(records),
        }
    )


def _blockers(
    plan: WorkflowDryRunPlan,
    tool_report: WorkflowToolRequirementBindingReport,
    risk_report: WorkflowRiskApprovalBindingReport,
) -> tuple[str, ...]:
    values = set(plan.blockers)
    values.update(tool_report.blockers)
    values.update(risk_report.blockers)
    if not risk_report.dry_run_admission_allowed:
        values.add("workflow_dry_run_admission_blocked")
    return tuple(sorted(values))


def _warnings(
    plan: WorkflowDryRunPlan,
    tool_report: WorkflowToolRequirementBindingReport,
    risk_report: WorkflowRiskApprovalBindingReport,
) -> tuple[str, ...]:
    values = set(plan.warnings)
    values.update(tool_report.warnings)
    values.update(risk_report.warnings)
    if risk_report.production_admission_allowed:
        values.add("unexpected_production_admission_true")
    return tuple(sorted(values))


def _next_actions(
    *,
    explicit_actions: tuple[str, ...],
    tool_binding_summary: Mapping[str, object],
    risk_approval_summary: Mapping[str, object],
    asset_summary: Mapping[str, object],
    blockers: tuple[str, ...],
) -> tuple[str, ...]:
    actions = {str(action) for action in explicit_actions if str(action)}
    forbidden = sorted(actions.intersection(FORBIDDEN_NEXT_ACTIONS))
    if forbidden:
        raise ValueError("forbidden_next_actions:" + ",".join(forbidden))
    unknown = sorted(actions.difference(ALLOWED_NEXT_ACTIONS))
    if unknown:
        raise ValueError("unknown_next_actions:" + ",".join(unknown))
    if not actions:
        actions.add("review_dry_run_plan")
        if int(tool_binding_summary["missing_count"]) > 0:
            actions.add("inspect_missing_tool")
        if int(tool_binding_summary["incompatible_count"]) > 0:
            actions.add("fix_tool_manifest")
            actions.add("reject_tool_candidate")
        if risk_approval_summary["missing_approvals"]:
            actions.add("issue_scoped_approval")
        if (
            int(tool_binding_summary["requires_approval_count"]) > 0
            or risk_approval_summary["highest_risk"] == "HIGH_RISK"
        ):
            actions.add("review_risk_assessment")
        if int(asset_summary["asset_count"]) > 0:
            actions.add("inspect_asset_inventory")
        if blockers:
            actions.add("rerun_dry_run_planning")
    return tuple(sorted(actions))


def _operator_state(operator_state_ref: object | None) -> Mapping[str, object]:
    state = operator_state_ref or build_operator_console_state()
    record = _record(state)
    return _stable_mapping(
        {
            "model_version": record.get("model_version", "unknown"),
            "ui_runtime_present": bool(record.get("ui_runtime_present")),
            "production_autonomy_allowed": bool(record.get("production_autonomy_allowed")),
            "panel_count": len(record.get("panels", ()))
            if isinstance(record.get("panels"), (tuple, list))
            else 0,
            "read_only_snapshot": True,
            "advisory_only": True,
            "execution_authorized": False,
        }
    )


def _records(records: tuple[object, ...] | list[object]) -> list[Mapping[str, object]]:
    if not isinstance(records, (tuple, list)):
        raise ValueError("summary_records_must_be_sequence")
    return [_record(record) for record in records]


def _record(record: object) -> Mapping[str, object]:
    if hasattr(record, "as_dict"):
        value = record.as_dict()
    elif hasattr(record, "__dataclass_fields__"):
        value = asdict(record)
    elif isinstance(record, Mapping):
        value = dict(record)
    else:
        raise ValueError("summary_record_must_be_mapping_or_dataclass")
    forbidden = _forbidden_fields(value)
    if forbidden:
        raise ValueError("forbidden_summary_fields:" + ",".join(forbidden))
    return _stable_mapping(value)


def _forbidden_fields(payload: Mapping[str, object]) -> tuple[str, ...]:
    found: set[str] = set()
    for key, value in payload.items():
        normalized = _normalize_key(str(key))
        if normalized in FORBIDDEN_SUMMARY_FIELDS:
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


def _hash_values(records: list[Mapping[str, object]]) -> tuple[str, ...]:
    values: set[str] = set()
    for record in records:
        for field_name in ("content_hash", "binding_hash", "report_hash", "snapshot_hash"):
            value = record.get(field_name)
            if isinstance(value, str) and value.startswith("sha256:"):
                values.add(value)
    return tuple(sorted(values))


def _risk_approval_report(
    value: WorkflowRiskApprovalBindingReport | Mapping[str, object],
) -> WorkflowRiskApprovalBindingReport:
    if isinstance(value, WorkflowRiskApprovalBindingReport):
        return value
    if not isinstance(value, Mapping):
        raise ValueError("risk_approval_report_must_be_report_or_mapping")
    return WorkflowRiskApprovalBindingReport(
        report_id=_required_string(value, "report_id"),
        plan_id=_required_string(value, "plan_id"),
        workflow_id=_required_string(value, "workflow_id"),
        highest_risk=_required_string(value, "highest_risk"),
        step_risk_summary=tuple(_mapping_items(value.get("step_risk_summary", ()))),
        approval_requirements=tuple(_mapping_items(value.get("approval_requirements", ()))),
        missing_approvals=_string_tuple(value.get("missing_approvals", ())),
        blocked_steps=_string_tuple(value.get("blocked_steps", ())),
        production_admission_allowed=bool(value.get("production_admission_allowed")),
        dry_run_admission_allowed=bool(value.get("dry_run_admission_allowed")),
        blockers=_string_tuple(value.get("blockers", ())),
        warnings=_string_tuple(value.get("warnings", ())),
        report_hash=_required_string(value, "report_hash"),
        observed_at=_required_string(value, "observed_at"),
    )


def _tool_binding_report(
    value: WorkflowToolRequirementBindingReport | Mapping[str, object],
) -> WorkflowToolRequirementBindingReport:
    if isinstance(value, WorkflowToolRequirementBindingReport):
        return value
    if not isinstance(value, Mapping):
        raise ValueError("tool_binding_report_must_be_report_or_mapping")
    return WorkflowToolRequirementBindingReport(
        binding_id=_required_string(value, "binding_id"),
        plan_id=_required_string(value, "plan_id"),
        workflow_id=_required_string(value, "workflow_id"),
        required_tool_bindings=tuple(
            _required_tool_binding(item)
            for item in _sequence(value, "required_tool_bindings")
        ),
        missing_tool_requirements=_string_tuple(value.get("missing_tool_requirements", ())),
        candidate_tool_matches=tuple(_mapping_items(value.get("candidate_tool_matches", ()))),
        incompatible_tools=tuple(_mapping_items(value.get("incompatible_tools", ()))),
        blockers=_string_tuple(value.get("blockers", ())),
        warnings=_string_tuple(value.get("warnings", ())),
        binding_hash=_required_string(value, "binding_hash"),
        observed_at=_required_string(value, "observed_at"),
    )


def _required_tool_binding(value: object) -> RequiredToolBinding:
    if isinstance(value, RequiredToolBinding):
        return value
    if not isinstance(value, Mapping):
        raise ValueError("required_tool_binding_must_be_mapping")
    return RequiredToolBinding(
        step_id=_required_string(value, "step_id"),
        required_capability=_required_string(value, "required_capability"),
        matched_tool_id=_optional_string(value.get("matched_tool_id")),
        manifest_id=_optional_string(value.get("manifest_id")),
        source_type=_optional_string(value.get("source_type")),
        match_status=_required_string(value, "match_status"),
        reason=_required_string(value, "reason"),
    )


def _plan(value: WorkflowDryRunPlan | Mapping[str, object]) -> WorkflowDryRunPlan:
    if isinstance(value, WorkflowDryRunPlan):
        return value
    if not isinstance(value, Mapping):
        raise ValueError("plan_must_be_workflow_dry_run_plan_or_mapping")
    return WorkflowDryRunPlan(
        plan_id=_required_string(value, "plan_id"),
        task_id=_required_string(value, "task_id"),
        workflow_id=_required_string(value, "workflow_id"),
        workflow_graph_hash=_required_string(value, "workflow_graph_hash"),
        plan_steps=tuple(_plan_step(item) for item in _sequence(value, "plan_steps")),
        required_tools=_string_tuple(value.get("required_tools", ())),
        required_assets=_string_tuple(value.get("required_assets", ())),
        approval_requirements=_string_tuple(value.get("approval_requirements", ())),
        evidence_requirements=_string_tuple(value.get("evidence_requirements", ())),
        rollback_plan=_string_tuple(value.get("rollback_plan", ())),
        evaluation_plan=_string_tuple(value.get("evaluation_plan", ())),
        blockers=_string_tuple(value.get("blockers", ())),
        warnings=_string_tuple(value.get("warnings", ())),
        dry_run_only=bool(value.get("dry_run_only")),
        executable=bool(value.get("executable")),
        content_hash=_required_string(value, "content_hash"),
        generated_at=_required_string(value, "generated_at"),
    )


def _plan_step(value: object) -> PlanStep:
    if isinstance(value, PlanStep):
        return value
    if not isinstance(value, Mapping):
        raise ValueError("plan_step_must_be_mapping")
    return PlanStep(
        step_id=_required_string(value, "step_id"),
        node_id=_required_string(value, "node_id"),
        step_type=_required_string(value, "step_type"),
        description=_required_string(value, "description"),
        required_tool_ids=_string_tuple(value.get("required_tool_ids", ())),
        required_asset_ids=_string_tuple(value.get("required_asset_ids", ())),
        risk_refs=_string_tuple(value.get("risk_refs", ())),
        approval_refs=_string_tuple(value.get("approval_refs", ())),
        evidence_refs=_string_tuple(value.get("evidence_refs", ())),
        status=_required_string(value, "status"),
        executable=bool(value.get("executable")),
    )


def _sequence(payload: Mapping[str, object], field_name: str) -> tuple[object, ...]:
    value = payload.get(field_name)
    if not isinstance(value, (tuple, list)):
        raise ValueError(field_name + "_must_be_sequence")
    return tuple(value)


def _mapping_items(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, (tuple, list)):
        raise ValueError("value_must_be_sequence")
    return tuple(dict(item) for item in value if isinstance(item, Mapping))


def _required_string(payload: Mapping[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field_name + "_required")
    return value.strip()


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise ValueError("value_must_be_sequence")
    return tuple(str(item) for item in value if str(item).strip())


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
