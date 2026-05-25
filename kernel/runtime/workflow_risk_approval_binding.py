"""Workflow risk approval binding v1.

Aggregates dry-run workflow tool risks into workflow-level approval
requirements. This module never issues accepted approval tokens and never
executes tools, calls providers, opens browsers, launches DCC applications, or
launches ComfyUI.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Mapping
import hashlib
import json
import re

from kernel.runtime.tool_approval_requirement_binding import ApprovalRequirement
from kernel.runtime.workflow_dry_run_plan import (
    PlanStep,
    WorkflowDryRunPlan,
    validate_workflow_dry_run_plan,
)
from kernel.runtime.workflow_tool_requirement_binding import (
    RequiredToolBinding,
    WorkflowToolRequirementBindingReport,
)

__all__ = [
    "RISK_RANK",
    "WorkflowRiskApprovalBindingReport",
    "bind_workflow_risk_approvals",
]

RISK_RANK = {
    "READ_ONLY": 0,
    "LOCAL_FILE_READ": 1,
    "LOCAL_FILE_WRITE": 2,
    "PROCESS_LAUNCH": 3,
    "NETWORK_ACCESS": 4,
    "BROWSER_CONTROL": 5,
    "PROVIDER_API": 6,
    "MCP_TOOL": 7,
    "DCC_CONTROL": 8,
    "COMFYUI_EXECUTION": 9,
    "RENDER_EXECUTION": 10,
    "MODEL_EXECUTION": 11,
    "PLUGIN_EXECUTION": 12,
    "CREDENTIAL_TOUCHING": 13,
    "HIGH_RISK": 14,
}

PRODUCTION_BLOCKING_RISKS = frozenset(
    (
        "HIGH_RISK",
        "DCC_CONTROL",
        "COMFYUI_EXECUTION",
        "BROWSER_CONTROL",
        "PROVIDER_API",
        "CREDENTIAL_TOUCHING",
    )
)

ALL_ADMISSION_BLOCKING_RISKS = frozenset(("CREDENTIAL_TOUCHING",))


@dataclass(frozen=True)
class WorkflowRiskApprovalBindingReport:
    report_id: str
    plan_id: str
    workflow_id: str
    highest_risk: str
    step_risk_summary: tuple[Mapping[str, object], ...]
    approval_requirements: tuple[Mapping[str, object], ...]
    missing_approvals: tuple[str, ...]
    blocked_steps: tuple[str, ...]
    production_admission_allowed: bool
    dry_run_admission_allowed: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    report_hash: str
    observed_at: str

    def as_dict(self) -> dict[str, object]:
        return {
            "report_id": self.report_id,
            "plan_id": self.plan_id,
            "workflow_id": self.workflow_id,
            "highest_risk": self.highest_risk,
            "step_risk_summary": [
                _json_ready(item) for item in self.step_risk_summary
            ],
            "approval_requirements": [
                _json_ready(item) for item in self.approval_requirements
            ],
            "missing_approvals": list(self.missing_approvals),
            "blocked_steps": list(self.blocked_steps),
            "production_admission_allowed": self.production_admission_allowed,
            "dry_run_admission_allowed": self.dry_run_admission_allowed,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "report_hash": self.report_hash,
            "observed_at": self.observed_at,
        }


def bind_workflow_risk_approvals(
    plan: WorkflowDryRunPlan | Mapping[str, object],
    tool_binding_report: WorkflowToolRequirementBindingReport | Mapping[str, object],
    tool_risk_assessment_summaries: tuple[object, ...] | list[object],
    approval_requirement_summaries: tuple[object, ...] | list[object] = (),
    *,
    observed_at: str | None = None,
) -> WorkflowRiskApprovalBindingReport:
    """Create workflow-level risk and approval requirement state."""

    dry_run_plan = _plan(plan)
    plan_failures = validate_workflow_dry_run_plan(dry_run_plan)
    if plan_failures:
        raise ValueError("workflow_dry_run_plan_invalid:" + ",".join(plan_failures))
    binding_report = _tool_binding_report(tool_binding_report)
    risks = _risk_map(tool_risk_assessment_summaries)
    approval_requirements = _approval_requirements(approval_requirement_summaries)
    approval_tools = {
        str(item["tool_id"]) for item in approval_requirements if item.get("tool_id")
    }
    blockers: set[str] = set(binding_report.blockers)
    warnings: set[str] = set(binding_report.warnings)
    blocked_steps: set[str] = set()
    missing_approvals: set[str] = set()
    step_summaries: list[Mapping[str, object]] = []
    all_risk_classes: set[str] = set()

    bindings_by_step = _bindings_by_step(binding_report.required_tool_bindings)
    for step in dry_run_plan.plan_steps:
        step_risks: set[str] = set()
        step_tool_ids: set[str] = set()
        step_approval_required = False
        for binding in bindings_by_step.get(step.step_id, ()):
            if binding.match_status in {"MISSING", "INCOMPATIBLE"}:
                blocked_steps.add(step.step_id)
                continue
            if not binding.matched_tool_id:
                blocked_steps.add(step.step_id)
                blockers.add(f"matched_tool_missing:{step.step_id}")
                continue
            step_tool_ids.add(binding.matched_tool_id)
            risk = risks.get(binding.matched_tool_id)
            if risk is None:
                blocked_steps.add(step.step_id)
                blockers.add(f"risk_assessment_missing:{binding.matched_tool_id}")
                continue
            risk_classes = _risk_classes(risk)
            step_risks.update(risk_classes)
            all_risk_classes.update(risk_classes)
            approval_required = bool(risk.get("approval_required")) or binding.match_status == "REQUIRES_APPROVAL"
            step_approval_required = step_approval_required or approval_required
            if approval_required and binding.matched_tool_id not in approval_tools:
                missing_approvals.add(binding.matched_tool_id)
                blocked_steps.add(step.step_id)
                blockers.add(f"approval_requirement_missing:{binding.matched_tool_id}")
        if ALL_ADMISSION_BLOCKING_RISKS.intersection(step_risks):
            blocked_steps.add(step.step_id)
            blockers.add(f"credential_touching_blocks_admission:{step.step_id}")
        if PRODUCTION_BLOCKING_RISKS.intersection(step_risks):
            warnings.add(f"production_blocked_by_risk:{step.step_id}")
        step_summaries.append(
            _stable_mapping(
                {
                    "step_id": step.step_id,
                    "required_tool_ids": step.required_tool_ids,
                    "matched_tool_ids": tuple(sorted(step_tool_ids)),
                    "risk_classes": tuple(sorted(step_risks, key=_risk_sort_key)),
                    "highest_risk": _highest_risk(step_risks),
                    "approval_required": step_approval_required,
                    "production_admission_allowed": False,
                }
            )
        )

    highest_risk = _highest_risk(all_risk_classes)
    dry_run_allowed = not blockers and not missing_approvals
    if ALL_ADMISSION_BLOCKING_RISKS.intersection(all_risk_classes):
        dry_run_allowed = False
    fields = {
        "plan_id": dry_run_plan.plan_id,
        "workflow_id": dry_run_plan.workflow_id,
        "highest_risk": highest_risk,
        "step_risk_summary": tuple(step_summaries),
        "approval_requirements": approval_requirements,
        "missing_approvals": tuple(sorted(missing_approvals)),
        "blocked_steps": tuple(sorted(blocked_steps)),
        "production_admission_allowed": False,
        "dry_run_admission_allowed": dry_run_allowed,
        "blockers": tuple(sorted(blockers)),
        "warnings": tuple(sorted(warnings)),
    }
    report_hash = _hash(fields)
    return WorkflowRiskApprovalBindingReport(
        report_id="workflow_risk_approval_" + report_hash.removeprefix("sha256:")[:32],
        **fields,
        report_hash=report_hash,
        observed_at=observed_at or _now(),
    )


def _bindings_by_step(
    bindings: tuple[RequiredToolBinding, ...],
) -> Mapping[str, tuple[RequiredToolBinding, ...]]:
    grouped: dict[str, list[RequiredToolBinding]] = {}
    for binding in bindings:
        grouped.setdefault(binding.step_id, []).append(binding)
    return {key: tuple(value) for key, value in grouped.items()}


def _approval_requirements(records: tuple[object, ...] | list[object]) -> tuple[Mapping[str, object], ...]:
    requirements = []
    for record in _records(records):
        requirements.append(
            _stable_mapping(
                {
                    "requirement_id": record.get("requirement_id"),
                    "tool_id": record.get("tool_id"),
                    "manifest_id": record.get("manifest_id"),
                    "required_action_type": record.get("required_action_type"),
                    "required_scope_id": record.get("required_scope_id"),
                    "risk_class": record.get("risk_class"),
                    "approval_required": bool(record.get("approval_required")),
                    "token_required": bool(record.get("token_required")),
                    "content_hash": record.get("content_hash"),
                }
            )
        )
    return tuple(sorted(requirements, key=lambda item: str(item.get("requirement_id"))))


def _risk_map(records: tuple[object, ...] | list[object]) -> Mapping[str, Mapping[str, object]]:
    risks: dict[str, Mapping[str, object]] = {}
    for record in _records(records):
        tool_id = record.get("tool_id")
        if not isinstance(tool_id, str) or not tool_id.strip():
            raise ValueError("risk_tool_id_required")
        risks[tool_id.strip()] = record
    return risks


def _risk_classes(record: Mapping[str, object]) -> tuple[str, ...]:
    value = record.get("risk_classes")
    if isinstance(value, (tuple, list)) and value:
        return tuple(str(item).strip() for item in value if str(item).strip())
    value = record.get("highest_risk") or record.get("risk_class")
    if isinstance(value, str) and value.strip():
        return (value.strip(),)
    return ("HIGH_RISK",)


def _highest_risk(risk_classes: set[str]) -> str:
    if not risk_classes:
        return "READ_ONLY"
    return max(risk_classes, key=_risk_sort_key)


def _risk_sort_key(risk_class: str) -> tuple[int, str]:
    return (RISK_RANK.get(risk_class, RISK_RANK["HIGH_RISK"]), risk_class)


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


def _records(records: tuple[object, ...] | list[object]) -> list[Mapping[str, object]]:
    if not isinstance(records, (tuple, list)):
        raise ValueError("summary_records_must_be_sequence")
    normalized = []
    for record in records:
        if isinstance(record, ApprovalRequirement):
            normalized.append(record.as_dict())
        elif hasattr(record, "as_dict"):
            normalized.append(record.as_dict())
        elif hasattr(record, "__dataclass_fields__"):
            normalized.append(asdict(record))
        elif isinstance(record, Mapping):
            normalized.append(dict(record))
        else:
            raise ValueError("summary_record_must_be_mapping_or_dataclass")
    return normalized


def _mapping_items(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, (tuple, list)):
        raise ValueError("value_must_be_sequence")
    return tuple(dict(item) for item in value if isinstance(item, Mapping))


def _sequence(payload: Mapping[str, object], field_name: str) -> tuple[object, ...]:
    value = payload.get(field_name)
    if not isinstance(value, (tuple, list)):
        raise ValueError(field_name + "_must_be_sequence")
    return tuple(value)


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


def _hash(payload: Mapping[str, object]) -> str:
    canonical = json.dumps(_json_ready(payload), sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value.strip()).strip("_").lower()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")
