"""Workflow dry-run plan v1.

Converts task intent and workflow graph descriptors into deterministic planning
records. The plan is descriptor-only: it never executes nodes, starts tools,
calls providers, opens browsers, launches DCC applications, or mutates assets.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Mapping
import hashlib
import json
import re

from kernel.runtime.task_to_workflow_router_skeleton import (
    HIGH_RISK_DOMAINS,
    TaskIntent,
    WorkflowGraphDescriptor,
    route_task_intent,
    validate_task_intent,
    validate_workflow_graph_descriptor,
)

__all__ = [
    "FORBIDDEN_PLAN_FIELDS",
    "PlanStep",
    "WorkflowDryRunPlan",
    "create_workflow_dry_run_plan",
    "validate_workflow_dry_run_plan",
]

FORBIDDEN_PLAN_FIELDS = frozenset(
    (
        "raw_command",
        "command",
        "command_line",
        "argv",
        "args",
        "shell",
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

HIGH_RISK_MARKERS = frozenset(
    (
        "HIGH_RISK",
        "DCC_CONTROL",
        "COMFYUI_EXECUTION",
        "BROWSER_CONTROL",
        "PROVIDER_API",
        "CREDENTIAL_TOUCHING",
    )
)


@dataclass(frozen=True)
class PlanStep:
    step_id: str
    node_id: str
    step_type: str
    description: str
    required_tool_ids: tuple[str, ...]
    required_asset_ids: tuple[str, ...]
    risk_refs: tuple[str, ...]
    approval_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    status: str = "PLANNED"
    executable: bool = False

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["required_tool_ids"] = list(self.required_tool_ids)
        data["required_asset_ids"] = list(self.required_asset_ids)
        data["risk_refs"] = list(self.risk_refs)
        data["approval_refs"] = list(self.approval_refs)
        data["evidence_refs"] = list(self.evidence_refs)
        return data


@dataclass(frozen=True)
class WorkflowDryRunPlan:
    plan_id: str
    task_id: str
    workflow_id: str
    workflow_graph_hash: str
    plan_steps: tuple[PlanStep, ...]
    required_tools: tuple[str, ...]
    required_assets: tuple[str, ...]
    approval_requirements: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    rollback_plan: tuple[str, ...]
    evaluation_plan: tuple[str, ...]
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    dry_run_only: bool
    executable: bool
    content_hash: str
    generated_at: str

    def as_dict(self) -> dict[str, object]:
        return {
            "plan_id": self.plan_id,
            "task_id": self.task_id,
            "workflow_id": self.workflow_id,
            "workflow_graph_hash": self.workflow_graph_hash,
            "plan_steps": [step.as_dict() for step in self.plan_steps],
            "required_tools": list(self.required_tools),
            "required_assets": list(self.required_assets),
            "approval_requirements": list(self.approval_requirements),
            "evidence_requirements": list(self.evidence_requirements),
            "rollback_plan": list(self.rollback_plan),
            "evaluation_plan": list(self.evaluation_plan),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "dry_run_only": self.dry_run_only,
            "executable": self.executable,
            "content_hash": self.content_hash,
            "generated_at": self.generated_at,
        }


def create_workflow_dry_run_plan(
    task_intent: TaskIntent | Mapping[str, object],
    workflow_graph: WorkflowGraphDescriptor | Mapping[str, object] | None = None,
    *,
    asset_summary_refs: tuple[object, ...] | list[object] = (),
    tool_manifest_refs: tuple[object, ...] | list[object] = (),
    generated_at: str | None = None,
) -> WorkflowDryRunPlan:
    """Build a deterministic plan from already-structured descriptors."""

    intent = _task_intent(task_intent)
    intent_failures = validate_task_intent(intent)
    if intent_failures:
        raise ValueError("task_intent_invalid:" + ",".join(intent_failures))

    descriptor = (
        route_task_intent(intent) if workflow_graph is None else _workflow_graph(workflow_graph)
    )
    descriptor_failures = validate_workflow_graph_descriptor(descriptor)
    if descriptor_failures:
        raise ValueError(
            "workflow_graph_descriptor_invalid:" + ",".join(descriptor_failures)
        )
    if not descriptor.rollback_plan:
        raise ValueError("rollback_plan_required")
    if not descriptor.evaluation_plan:
        raise ValueError("evaluation_plan_required")

    _reject_forbidden_payload(intent.as_dict())
    _reject_forbidden_payload(descriptor.as_dict())
    _reject_forbidden_records(asset_summary_refs)
    _reject_forbidden_records(tool_manifest_refs)

    plan_steps = _plan_steps(intent=intent, descriptor=descriptor)
    approval_requirements = _approval_requirements(
        descriptor.approval_requirements,
        plan_steps,
    )
    required_assets = _required_assets(descriptor.required_assets, asset_summary_refs)
    required_tools = _required_tools(descriptor.required_tools, tool_manifest_refs)
    warnings = _warnings(intent, descriptor, asset_summary_refs, tool_manifest_refs)
    hash_fields = {
        "task_id": intent.task_id,
        "workflow_id": descriptor.workflow_id,
        "workflow_graph_hash": descriptor.graph_hash,
        "plan_steps": [step.as_dict() for step in plan_steps],
        "required_tools": required_tools,
        "required_assets": required_assets,
        "approval_requirements": approval_requirements,
        "evidence_requirements": tuple(sorted(descriptor.evidence_requirements)),
        "rollback_plan": tuple(descriptor.rollback_plan),
        "evaluation_plan": tuple(descriptor.evaluation_plan),
        "blockers": (),
        "warnings": warnings,
        "dry_run_only": True,
        "executable": False,
    }
    content_hash = _hash(hash_fields)
    plan = WorkflowDryRunPlan(
        plan_id="workflow_dry_run_plan_" + content_hash.removeprefix("sha256:")[:32],
        task_id=intent.task_id,
        workflow_id=descriptor.workflow_id,
        workflow_graph_hash=descriptor.graph_hash,
        plan_steps=plan_steps,
        required_tools=required_tools,
        required_assets=required_assets,
        approval_requirements=approval_requirements,
        evidence_requirements=tuple(sorted(descriptor.evidence_requirements)),
        rollback_plan=tuple(descriptor.rollback_plan),
        evaluation_plan=tuple(descriptor.evaluation_plan),
        blockers=(),
        warnings=warnings,
        dry_run_only=True,
        executable=False,
        content_hash=content_hash,
        generated_at=generated_at or _now(),
    )
    failures = validate_workflow_dry_run_plan(plan)
    if failures:
        raise ValueError("workflow_dry_run_plan_invalid:" + ",".join(failures))
    return plan


def validate_workflow_dry_run_plan(plan: WorkflowDryRunPlan) -> tuple[str, ...]:
    failures: list[str] = []
    if plan.dry_run_only is not True:
        failures.append("dry_run_only_must_be_true")
    if plan.executable is not False:
        failures.append("plan_executable_must_be_false")
    if not plan.plan_steps:
        failures.append("plan_steps_required")
    if not plan.rollback_plan:
        failures.append("rollback_plan_required")
    if not plan.evaluation_plan:
        failures.append("evaluation_plan_required")
    for step in plan.plan_steps:
        if step.status != "PLANNED":
            failures.append(f"step_status_invalid:{step.step_id}")
        if step.executable is not False:
            failures.append(f"step_executable_must_be_false:{step.step_id}")
    forbidden = _forbidden_fields(plan.as_dict())
    failures.extend(f"forbidden_plan_field:{field}" for field in forbidden)
    expected_hash = _hash(
        {
            key: value
            for key, value in plan.as_dict().items()
            if key not in {"plan_id", "content_hash", "generated_at"}
        }
    )
    if plan.content_hash != expected_hash:
        failures.append("content_hash_mismatch")
    expected_plan_id = "workflow_dry_run_plan_" + plan.content_hash.removeprefix(
        "sha256:"
    )[:32]
    if plan.plan_id != expected_plan_id:
        failures.append("plan_id_mismatch")
    return tuple(failures)


def _plan_steps(
    *,
    intent: TaskIntent,
    descriptor: WorkflowGraphDescriptor,
) -> tuple[PlanStep, ...]:
    steps: list[PlanStep] = []
    for index, node in enumerate(descriptor.nodes):
        node_id = _node_id(node, index)
        risk_refs = _step_refs(node, "risk_refs", "risk")
        if _is_high_risk_node(intent, node):
            risk_refs = tuple(sorted(set(risk_refs) | {"risk:high"}))
        approval_refs = _step_refs(node, "approval_refs", "approval")
        if _is_high_risk_node(intent, node):
            approval_refs = tuple(
                sorted(
                    set(approval_refs)
                    | {f"approval_requirement_placeholder:{node_id}"}
                )
            )
        evidence_refs = _step_refs(node, "evidence_refs", "evidence")
        if not evidence_refs:
            evidence_refs = tuple(sorted(descriptor.evidence_requirements))
        steps.append(
            PlanStep(
                step_id=f"plan_step_{index:03d}_{_slug(node_id)}",
                node_id=node_id,
                step_type=_step_type(node),
                description=_description(node, index),
                required_tool_ids=_node_or_graph_refs(
                    node,
                    descriptor.required_tools,
                    ("required_tool_ids", "required_tools", "tool_ids"),
                ),
                required_asset_ids=_node_or_graph_refs(
                    node,
                    descriptor.required_assets,
                    ("required_asset_ids", "required_assets", "asset_ids"),
                ),
                risk_refs=risk_refs,
                approval_refs=approval_refs,
                evidence_refs=evidence_refs,
            )
        )
    return tuple(steps)


def _approval_requirements(
    descriptor_requirements: tuple[str, ...],
    steps: tuple[PlanStep, ...],
) -> tuple[str, ...]:
    requirements = set(descriptor_requirements)
    for step in steps:
        requirements.update(step.approval_refs)
    return tuple(sorted(requirements))


def _required_assets(
    descriptor_assets: tuple[str, ...],
    asset_summary_refs: tuple[object, ...] | list[object],
) -> tuple[str, ...]:
    values = set(descriptor_assets)
    for record in _records(asset_summary_refs):
        for field_name in ("asset_id", "asset_ref", "content_hash"):
            value = record.get(field_name)
            if isinstance(value, str) and value.strip():
                values.add(value.strip())
                break
    return tuple(sorted(values))


def _required_tools(
    descriptor_tools: tuple[str, ...],
    tool_manifest_refs: tuple[object, ...] | list[object],
) -> tuple[str, ...]:
    values = set(descriptor_tools)
    for record in _records(tool_manifest_refs):
        for field_name in ("tool_id", "manifest_id", "capability"):
            value = record.get(field_name)
            if isinstance(value, str) and value.strip():
                values.add(value.strip())
                break
    return tuple(sorted(values))


def _warnings(
    intent: TaskIntent,
    descriptor: WorkflowGraphDescriptor,
    asset_summary_refs: tuple[object, ...] | list[object],
    tool_manifest_refs: tuple[object, ...] | list[object],
) -> tuple[str, ...]:
    warnings: set[str] = set()
    if intent.domain in HIGH_RISK_DOMAINS:
        warnings.add("high_risk_domain_requires_operator_review")
    if descriptor.required_assets and not asset_summary_refs:
        warnings.add("asset_summary_refs_not_supplied")
    if descriptor.required_tools and not tool_manifest_refs:
        warnings.add("tool_manifest_refs_not_supplied")
    return tuple(sorted(warnings))


def _task_intent(value: TaskIntent | Mapping[str, object]) -> TaskIntent:
    if isinstance(value, TaskIntent):
        return value
    if not isinstance(value, Mapping):
        raise ValueError("task_intent_must_be_task_intent_or_mapping")
    return TaskIntent.from_mapping(value)


def _workflow_graph(
    value: WorkflowGraphDescriptor | Mapping[str, object],
) -> WorkflowGraphDescriptor:
    if isinstance(value, WorkflowGraphDescriptor):
        return value
    if not isinstance(value, Mapping):
        raise ValueError("workflow_graph_must_be_descriptor_or_mapping")
    return WorkflowGraphDescriptor(
        workflow_id=_required_string(value, "workflow_id"),
        workflow_version=_required_string(value, "workflow_version"),
        nodes=tuple(_mapping_items(value, "nodes")),
        edges=tuple(_mapping_items(value, "edges")),
        required_tools=_string_tuple(value.get("required_tools", ())),
        required_assets=_string_tuple(value.get("required_assets", ())),
        approval_requirements=_string_tuple(value.get("approval_requirements", ())),
        evidence_requirements=_string_tuple(value.get("evidence_requirements", ())),
        rollback_plan=_string_tuple(value.get("rollback_plan", ())),
        evaluation_plan=_string_tuple(value.get("evaluation_plan", ())),
        graph_hash=_required_string(value, "graph_hash"),
    )


def _node_id(node: Mapping[str, object], index: int) -> str:
    value = node.get("node_id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return f"node_{index:03d}"


def _step_type(node: Mapping[str, object]) -> str:
    for field_name in ("step_type", "stage", "node_type"):
        value = node.get(field_name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "descriptor_stage"


def _description(node: Mapping[str, object], index: int) -> str:
    value = node.get("description") or node.get("objective_ref")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return f"Dry-run descriptor step {index:03d}"


def _node_or_graph_refs(
    node: Mapping[str, object],
    fallback: tuple[str, ...],
    field_names: tuple[str, ...],
) -> tuple[str, ...]:
    values: set[str] = set()
    for field_name in field_names:
        value = node.get(field_name)
        if isinstance(value, (tuple, list)):
            values.update(str(item).strip() for item in value if str(item).strip())
        elif isinstance(value, str) and value.strip():
            values.add(value.strip())
    if not values:
        values.update(fallback)
    return tuple(sorted(values))


def _step_refs(
    node: Mapping[str, object],
    field_name: str,
    singular_field_name: str,
) -> tuple[str, ...]:
    value = node.get(field_name)
    if isinstance(value, (tuple, list)):
        return tuple(sorted(str(item).strip() for item in value if str(item).strip()))
    if isinstance(value, str) and value.strip():
        return (value.strip(),)
    value = node.get(singular_field_name)
    if isinstance(value, str) and value.strip():
        return (value.strip(),)
    return ()


def _is_high_risk_node(intent: TaskIntent, node: Mapping[str, object]) -> bool:
    if intent.domain in HIGH_RISK_DOMAINS:
        return True
    for field_name in ("risk_level", "highest_risk", "risk_class"):
        value = node.get(field_name)
        if isinstance(value, str) and value.strip().upper() in HIGH_RISK_MARKERS:
            return True
    value = node.get("risk_classes")
    return isinstance(value, (tuple, list)) and any(
        str(item).strip().upper() in HIGH_RISK_MARKERS for item in value
    )


def _reject_forbidden_records(records: tuple[object, ...] | list[object]) -> None:
    for record in _records(records):
        _reject_forbidden_payload(record)


def _reject_forbidden_payload(payload: Mapping[str, object]) -> None:
    forbidden = _forbidden_fields(payload)
    if forbidden:
        raise ValueError("forbidden_plan_fields:" + ",".join(forbidden))


def _forbidden_fields(payload: Mapping[str, object]) -> tuple[str, ...]:
    found: set[str] = set()
    for key, value in payload.items():
        normalized = _normalize_key(str(key))
        if normalized in FORBIDDEN_PLAN_FIELDS:
            found.add(normalized)
        if isinstance(value, Mapping):
            found.update(_forbidden_fields(value))
        elif isinstance(value, (tuple, list)):
            for item in value:
                if isinstance(item, Mapping):
                    found.update(_forbidden_fields(item))
    return tuple(sorted(found))


def _records(records: tuple[object, ...] | list[object]) -> list[Mapping[str, object]]:
    if not isinstance(records, (tuple, list)):
        raise ValueError("summary_refs_must_be_sequence")
    normalized: list[Mapping[str, object]] = []
    for record in records:
        if hasattr(record, "as_dict"):
            normalized.append(record.as_dict())
        elif hasattr(record, "__dataclass_fields__"):
            normalized.append(asdict(record))
        elif isinstance(record, Mapping):
            normalized.append(dict(record))
        else:
            raise ValueError("summary_ref_must_be_mapping_or_dataclass")
    return normalized


def _mapping_items(payload: Mapping[str, object], field_name: str) -> tuple[Mapping[str, object], ...]:
    value = payload.get(field_name)
    if not isinstance(value, (tuple, list)):
        raise ValueError(field_name + "_must_be_sequence")
    return tuple(dict(item) for item in value if isinstance(item, Mapping))


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise ValueError("value_must_be_sequence")
    return tuple(str(item) for item in value if str(item).strip())


def _required_string(payload: Mapping[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field_name + "_required")
    return value.strip()


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip()).strip("_").lower()
    return normalized or "node"


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value.strip()).strip("_").lower()


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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")
