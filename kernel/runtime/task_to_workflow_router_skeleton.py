"""Task-to-workflow router skeleton v1.

Converts structured task intent into deterministic workflow graph descriptors.
This module does not execute workflows, spawn subprocesses, call providers,
perform network activity, or launch tools.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping
import hashlib
import json

__all__ = [
    "SUPPORTED_DOMAINS",
    "TaskIntent",
    "WorkflowGraphDescriptor",
    "route_task_intent",
    "validate_task_intent",
    "validate_workflow_graph_descriptor",
]

SUPPORTED_DOMAINS = (
    "VIDEO",
    "VFX",
    "AI_IMAGE",
    "COMFYUI_WORKFLOW",
    "DCC_SCENE",
    "GIT_CODE_AUDIT",
    "ASSET_INGESTION",
    "RELEASE_VALIDATION",
)

HIGH_RISK_DOMAINS = frozenset(("VFX", "COMFYUI_WORKFLOW", "DCC_SCENE"))


@dataclass(frozen=True)
class TaskIntent:
    task_id: str
    domain: str
    objective: str
    inputs: Mapping[str, object]
    constraints: Mapping[str, object]
    risk_tolerance: str
    desired_outputs: tuple[str, ...]

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> "TaskIntent":
        return cls(
            task_id=_required_string(payload, "task_id"),
            domain=_required_string(payload, "domain"),
            objective=_required_string(payload, "objective"),
            inputs=_required_mapping(payload, "inputs"),
            constraints=_required_mapping(payload, "constraints"),
            risk_tolerance=_required_string(payload, "risk_tolerance"),
            desired_outputs=tuple(_required_sequence(payload, "desired_outputs")),
        )

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["inputs"] = dict(self.inputs)
        data["constraints"] = dict(self.constraints)
        data["desired_outputs"] = list(self.desired_outputs)
        return data


@dataclass(frozen=True)
class WorkflowGraphDescriptor:
    workflow_id: str
    workflow_version: str
    nodes: tuple[Mapping[str, object], ...]
    edges: tuple[Mapping[str, object], ...]
    required_tools: tuple[str, ...]
    required_assets: tuple[str, ...]
    approval_requirements: tuple[str, ...]
    evidence_requirements: tuple[str, ...]
    rollback_plan: tuple[str, ...]
    evaluation_plan: tuple[str, ...]
    graph_hash: str

    def as_dict(self) -> dict[str, object]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_version": self.workflow_version,
            "nodes": [dict(node) for node in self.nodes],
            "edges": [dict(edge) for edge in self.edges],
            "required_tools": list(self.required_tools),
            "required_assets": list(self.required_assets),
            "approval_requirements": list(self.approval_requirements),
            "evidence_requirements": list(self.evidence_requirements),
            "rollback_plan": list(self.rollback_plan),
            "evaluation_plan": list(self.evaluation_plan),
            "graph_hash": self.graph_hash,
        }


def route_task_intent(intent: TaskIntent | Mapping[str, object]) -> WorkflowGraphDescriptor:
    if isinstance(intent, Mapping):
        task_intent = TaskIntent.from_mapping(intent)
    else:
        task_intent = intent
    failures = validate_task_intent(task_intent)
    if failures:
        raise ValueError("task_intent_invalid:" + ",".join(failures))

    template = _route_template(task_intent.domain)
    nodes = _nodes_for(task_intent, template)
    edges = _edges_for(nodes)
    approval_requirements = _approval_requirements(task_intent)
    required_assets = tuple(sorted(str(value) for value in task_intent.inputs.get("assets", ())))
    descriptor_payload = {
        "workflow_id": f"workflow_{task_intent.task_id}_{task_intent.domain.lower()}",
        "workflow_version": "v1",
        "nodes": nodes,
        "edges": edges,
        "required_tools": tuple(template["required_tools"]),
        "required_assets": required_assets,
        "approval_requirements": approval_requirements,
        "evidence_requirements": tuple(template["evidence_requirements"]),
        "rollback_plan": tuple(template["rollback_plan"]),
        "evaluation_plan": tuple(template["evaluation_plan"]),
    }
    graph_hash = _hash(_json_ready(descriptor_payload))
    descriptor = WorkflowGraphDescriptor(**descriptor_payload, graph_hash=graph_hash)
    descriptor_failures = validate_workflow_graph_descriptor(descriptor)
    if descriptor_failures:
        raise ValueError("workflow_graph_descriptor_invalid:" + ",".join(descriptor_failures))
    return descriptor


def validate_task_intent(intent: TaskIntent) -> tuple[str, ...]:
    failures: list[str] = []
    if not isinstance(intent.task_id, str) or not intent.task_id.strip():
        failures.append("task_id_required")
    if intent.domain not in SUPPORTED_DOMAINS:
        failures.append("domain_not_supported")
    if not isinstance(intent.objective, str) or not intent.objective.strip():
        failures.append("objective_required")
    if not isinstance(intent.inputs, Mapping):
        failures.append("inputs_must_be_mapping")
    if not isinstance(intent.constraints, Mapping):
        failures.append("constraints_must_be_mapping")
    if not isinstance(intent.risk_tolerance, str) or not intent.risk_tolerance.strip():
        failures.append("risk_tolerance_required")
    if not intent.desired_outputs:
        failures.append("desired_outputs_required")
    return tuple(failures)


def validate_workflow_graph_descriptor(
    descriptor: WorkflowGraphDescriptor,
) -> tuple[str, ...]:
    failures: list[str] = []
    if not descriptor.nodes:
        failures.append("nodes_required")
    if not descriptor.evaluation_plan:
        failures.append("evaluation_plan_required")
    if not descriptor.rollback_plan:
        failures.append("rollback_plan_required")
    if not descriptor.evidence_requirements:
        failures.append("evidence_requirements_required")
    encoded = _canonical_json(descriptor.as_dict()).lower()
    for forbidden in (
        "command_line",
        "raw_command",
        "argv",
        "subprocess",
        "shell=true",
        "execute_workflow",
        "direct_launch",
    ):
        if forbidden in encoded:
            failures.append(f"forbidden_encoded_surface:{forbidden}")
    expected_hash = _hash(
        {
            key: value
            for key, value in descriptor.as_dict().items()
            if key != "graph_hash"
        }
    )
    if descriptor.graph_hash != expected_hash:
        failures.append("graph_hash_mismatch")
    return tuple(failures)


def _route_template(domain: str) -> Mapping[str, object]:
    templates = {
        "VIDEO": {
            "stages": ("intake", "timeline_plan", "evidence_review"),
            "required_tools": ("timeline_descriptor", "evidence_ledger"),
            "evidence_requirements": ("source_asset_inventory", "timeline_plan_hash"),
            "rollback_plan": ("discard_descriptor", "preserve_inputs"),
            "evaluation_plan": ("check_required_outputs", "review_timing_constraints"),
        },
        "VFX": {
            "stages": ("intake", "shot_breakdown", "cache_plan", "evidence_review"),
            "required_tools": ("asset_inventory", "shot_descriptor"),
            "evidence_requirements": ("source_asset_inventory", "risk_review"),
            "rollback_plan": ("discard_generated_descriptors", "preserve_source_assets"),
            "evaluation_plan": ("review_shot_requirements", "verify_no_tool_launch"),
        },
        "AI_IMAGE": {
            "stages": ("intake", "prompt_boundary_plan", "asset_reference_plan", "review"),
            "required_tools": ("prompt_policy_descriptor", "asset_inventory"),
            "evidence_requirements": ("input_digest_refs", "style_constraint_summary"),
            "rollback_plan": ("discard_prompt_descriptor", "preserve_references"),
            "evaluation_plan": ("review_prompt_safety", "verify_desired_outputs"),
        },
        "COMFYUI_WORKFLOW": {
            "stages": ("intake", "workflow_spec_plan", "node_risk_review", "review"),
            "required_tools": ("workflow_descriptor", "risk_panel"),
            "evidence_requirements": ("workflow_spec_hash", "node_risk_summary"),
            "rollback_plan": ("discard_workflow_descriptor", "preserve_inputs"),
            "evaluation_plan": ("validate_workflow_shape", "verify_no_runtime_launch"),
        },
        "DCC_SCENE": {
            "stages": ("intake", "scene_inventory", "dependency_plan", "review"),
            "required_tools": ("scene_descriptor", "asset_inventory"),
            "evidence_requirements": ("scene_asset_inventory", "dependency_summary"),
            "rollback_plan": ("discard_scene_descriptor", "preserve_scene_files"),
            "evaluation_plan": ("validate_scene_requirements", "verify_no_dcc_launch"),
        },
        "GIT_CODE_AUDIT": {
            "stages": ("intake", "diff_scope_plan", "risk_review", "report"),
            "required_tools": ("repository_descriptor", "risk_classifier"),
            "evidence_requirements": ("changed_file_list", "test_plan_summary"),
            "rollback_plan": ("discard_report", "preserve_repository"),
            "evaluation_plan": ("verify_findings_have_file_refs", "check_test_plan"),
        },
        "ASSET_INGESTION": {
            "stages": ("intake", "root_validation", "inventory_plan", "review"),
            "required_tools": ("asset_inventory", "evidence_ledger"),
            "evidence_requirements": ("root_policy_result", "inventory_hashes"),
            "rollback_plan": ("discard_inventory_records", "preserve_files"),
            "evaluation_plan": ("verify_root_bounds", "verify_media_class_coverage"),
        },
        "RELEASE_VALIDATION": {
            "stages": ("intake", "test_matrix_plan", "evidence_review", "release_report"),
            "required_tools": ("test_matrix_descriptor", "evidence_ledger"),
            "evidence_requirements": ("test_command_results", "diff_check_result"),
            "rollback_plan": ("discard_release_report", "preserve_branch"),
            "evaluation_plan": ("verify_required_checks", "verify_blockers_listed"),
        },
    }
    return templates[domain]


def _nodes_for(
    task_intent: TaskIntent,
    template: Mapping[str, object],
) -> tuple[Mapping[str, object], ...]:
    nodes = []
    for index, stage in enumerate(template["stages"]):
        nodes.append(
            {
                "node_id": f"{task_intent.domain.lower()}_{index:02d}_{stage}",
                "node_type": "descriptor_stage",
                "stage": stage,
                "objective_ref": task_intent.objective,
                "produces_descriptor_only": True,
            }
        )
    return tuple(nodes)


def _edges_for(nodes: tuple[Mapping[str, object], ...]) -> tuple[Mapping[str, object], ...]:
    edges = []
    for index in range(1, len(nodes)):
        edges.append(
            {
                "from": nodes[index - 1]["node_id"],
                "to": nodes[index]["node_id"],
                "edge_type": "descriptor_dependency",
            }
        )
    return tuple(edges)


def _approval_requirements(task_intent: TaskIntent) -> tuple[str, ...]:
    requirements = []
    if task_intent.domain in HIGH_RISK_DOMAINS:
        requirements.append("operator_approval_required_for_high_risk_domain")
    if task_intent.risk_tolerance.upper() in {"LOW", "NONE"}:
        requirements.append("operator_review_before_runtime_promotion")
    return tuple(requirements)


def _required_string(payload: Mapping[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field_name + "_required")
    return value.strip()


def _required_mapping(payload: Mapping[str, object], field_name: str) -> Mapping[str, object]:
    value = payload.get(field_name)
    if not isinstance(value, Mapping):
        raise ValueError(field_name + "_must_be_mapping")
    return dict(value)


def _required_sequence(payload: Mapping[str, object], field_name: str) -> tuple[str, ...]:
    value = payload.get(field_name)
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError(field_name + "_must_be_nonempty_sequence")
    return tuple(str(entry) for entry in value)


def _json_ready(payload: Mapping[str, object]) -> dict[str, object]:
    ready: dict[str, object] = {}
    for key, value in payload.items():
        if isinstance(value, tuple):
            ready[key] = [
                dict(item) if isinstance(item, Mapping) else item for item in value
            ]
        else:
            ready[key] = value
    return ready


def _canonical_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _hash(payload: Mapping[str, object]) -> str:
    return "sha256:" + hashlib.sha256(
        _canonical_json(payload).encode("utf-8")
    ).hexdigest()
