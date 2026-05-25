"""Workflow tool requirement binding v1.

Binds dry-run plan steps to normalized tool manifest metadata. This module is
advisory only: it never executes tools, calls MCP, runs CLI commands, installs
dependencies, launches DCC applications, launches ComfyUI, or performs network
lookups.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Mapping
import hashlib
import json
import re

from kernel.runtime.tool_manifest_normalizer import NormalizedToolManifest
from kernel.runtime.tool_manifest_risk_binding import bind_tool_manifest_risk
from kernel.runtime.workflow_dry_run_plan import (
    PlanStep,
    WorkflowDryRunPlan,
    validate_workflow_dry_run_plan,
)

__all__ = [
    "MATCH_STATUSES",
    "RequiredToolBinding",
    "WorkflowToolRequirementBindingReport",
    "bind_workflow_tool_requirements",
]

MATCH_STATUSES = (
    "MATCHED",
    "MISSING",
    "INCOMPATIBLE",
    "REQUIRES_APPROVAL",
)

METADATA_ONLY_SOURCE_TYPES = frozenset(
    (
        "MCP_SERVER",
        "MCP_TOOL",
        "DCC_APP",
        "DCC_PLUGIN",
        "COMFYUI_WORKFLOW",
        "GITHUB_REPO",
    )
)

APPROVAL_RISK_CLASSES = frozenset(
    (
        "LOCAL_FILE_WRITE",
        "PROCESS_LAUNCH",
        "NETWORK_ACCESS",
        "BROWSER_CONTROL",
        "PROVIDER_API",
        "CREDENTIAL_TOUCHING",
        "DCC_CONTROL",
        "COMFYUI_EXECUTION",
        "RENDER_EXECUTION",
        "MODEL_EXECUTION",
        "PLUGIN_EXECUTION",
    )
)


@dataclass(frozen=True)
class RequiredToolBinding:
    step_id: str
    required_capability: str
    matched_tool_id: str | None
    manifest_id: str | None
    source_type: str | None
    match_status: str
    reason: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class WorkflowToolRequirementBindingReport:
    binding_id: str
    plan_id: str
    workflow_id: str
    required_tool_bindings: tuple[RequiredToolBinding, ...]
    missing_tool_requirements: tuple[str, ...]
    candidate_tool_matches: tuple[Mapping[str, object], ...]
    incompatible_tools: tuple[Mapping[str, object], ...]
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    binding_hash: str
    observed_at: str

    def as_dict(self) -> dict[str, object]:
        return {
            "binding_id": self.binding_id,
            "plan_id": self.plan_id,
            "workflow_id": self.workflow_id,
            "required_tool_bindings": [
                binding.as_dict() for binding in self.required_tool_bindings
            ],
            "missing_tool_requirements": list(self.missing_tool_requirements),
            "candidate_tool_matches": [
                _json_ready(match) for match in self.candidate_tool_matches
            ],
            "incompatible_tools": [
                _json_ready(tool) for tool in self.incompatible_tools
            ],
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "binding_hash": self.binding_hash,
            "observed_at": self.observed_at,
        }


def bind_workflow_tool_requirements(
    plan: WorkflowDryRunPlan | Mapping[str, object],
    available_tool_manifests: tuple[object, ...] | list[object],
    *,
    capability_mapping: Mapping[str, object] | None = None,
    observed_at: str | None = None,
) -> WorkflowToolRequirementBindingReport:
    """Bind required plan capabilities to normalized manifests as metadata."""

    dry_run_plan = _plan(plan)
    plan_failures = validate_workflow_dry_run_plan(dry_run_plan)
    if plan_failures:
        raise ValueError("workflow_dry_run_plan_invalid:" + ",".join(plan_failures))
    manifests = tuple(_manifest(manifest) for manifest in available_tool_manifests)
    mapping = _capability_mapping(capability_mapping or {})
    required_bindings: list[RequiredToolBinding] = []
    candidate_matches: list[Mapping[str, object]] = []
    incompatible_tools: list[Mapping[str, object]] = []
    blockers: set[str] = set()
    warnings: set[str] = set()

    for step in dry_run_plan.plan_steps:
        for required in step.required_tool_ids:
            requirement = _requirement(required, mapping)
            match = _match_requirement(requirement, manifests)
            if match is None:
                required_bindings.append(
                    RequiredToolBinding(
                        step_id=step.step_id,
                        required_capability=requirement["capability"],
                        matched_tool_id=None,
                        manifest_id=None,
                        source_type=None,
                        match_status="MISSING",
                        reason="required_tool_manifest_missing",
                    )
                )
                blockers.add(f"missing_tool_requirement:{requirement['capability']}")
                continue

            manifest, compatible, reason = match
            candidate_matches.append(_candidate_match(step, requirement, manifest))
            if manifest.source_type in METADATA_ONLY_SOURCE_TYPES:
                warnings.add(f"metadata_only_candidate:{manifest.source_type}:{manifest.tool_id}")
            if not compatible:
                required_bindings.append(
                    RequiredToolBinding(
                        step_id=step.step_id,
                        required_capability=requirement["capability"],
                        matched_tool_id=manifest.tool_id,
                        manifest_id=manifest.manifest_id,
                        source_type=manifest.source_type,
                        match_status="INCOMPATIBLE",
                        reason=reason,
                    )
                )
                incompatible = {
                    "step_id": step.step_id,
                    "required_capability": requirement["capability"],
                    "tool_id": manifest.tool_id,
                    "manifest_id": manifest.manifest_id,
                    "source_type": manifest.source_type,
                    "reason": reason,
                }
                incompatible_tools.append(incompatible)
                blockers.add(f"incompatible_tool:{manifest.tool_id}")
                continue

            risk_report = bind_tool_manifest_risk(manifest)
            requires_approval = _requires_approval(manifest, risk_report.as_dict())
            status = "REQUIRES_APPROVAL" if requires_approval else "MATCHED"
            if requires_approval:
                warnings.add(f"tool_requires_approval:{manifest.tool_id}")
            required_bindings.append(
                RequiredToolBinding(
                    step_id=step.step_id,
                    required_capability=requirement["capability"],
                    matched_tool_id=manifest.tool_id,
                    manifest_id=manifest.manifest_id,
                    source_type=manifest.source_type,
                    match_status=status,
                    reason=(
                        "matched_tool_requires_approval"
                        if requires_approval
                        else "matched_normalized_manifest"
                    ),
                )
            )

    missing = tuple(
        sorted(
            {
                binding.required_capability
                for binding in required_bindings
                if binding.match_status == "MISSING"
            }
        )
    )
    hash_fields = {
        "plan_id": dry_run_plan.plan_id,
        "workflow_id": dry_run_plan.workflow_id,
        "required_tool_bindings": [
            binding.as_dict() for binding in required_bindings
        ],
        "missing_tool_requirements": missing,
        "candidate_tool_matches": tuple(candidate_matches),
        "incompatible_tools": tuple(incompatible_tools),
        "blockers": tuple(sorted(blockers)),
        "warnings": tuple(sorted(warnings)),
    }
    binding_hash = _hash(hash_fields)
    return WorkflowToolRequirementBindingReport(
        binding_id="workflow_tool_binding_" + binding_hash.removeprefix("sha256:")[:32],
        plan_id=dry_run_plan.plan_id,
        workflow_id=dry_run_plan.workflow_id,
        required_tool_bindings=tuple(required_bindings),
        missing_tool_requirements=missing,
        candidate_tool_matches=tuple(candidate_matches),
        incompatible_tools=tuple(incompatible_tools),
        blockers=tuple(sorted(blockers)),
        warnings=tuple(sorted(warnings)),
        binding_hash=binding_hash,
        observed_at=observed_at or _now(),
    )


def _match_requirement(
    requirement: Mapping[str, object],
    manifests: tuple[NormalizedToolManifest, ...],
) -> tuple[NormalizedToolManifest, bool, str] | None:
    candidates = tuple(
        manifest
        for manifest in manifests
        if _manifest_satisfies_requirement(manifest, str(requirement["capability"]))
    )
    if not candidates:
        return None
    manifest = sorted(candidates, key=lambda item: (item.tool_id, item.manifest_id))[0]
    allowed_source_types = requirement.get("allowed_source_types")
    if isinstance(allowed_source_types, tuple) and allowed_source_types:
        if manifest.source_type not in allowed_source_types:
            return (
                manifest,
                False,
                "source_type_not_allowed_for_required_capability",
            )
    return manifest, True, "normalized_manifest_capability_match"


def _requires_approval(
    manifest: NormalizedToolManifest,
    risk_report: Mapping[str, object],
) -> bool:
    risk_classes = {
        str(item)
        for item in risk_report.get("risk_classes", ())
        if str(item).strip()
    }
    if APPROVAL_RISK_CLASSES.intersection(risk_classes):
        return True
    if risk_report.get("highest_risk") == "HIGH_RISK" and manifest.source_type == "UNKNOWN":
        return True
    return False


def _manifest_satisfies_requirement(
    manifest: NormalizedToolManifest,
    required_capability: str,
) -> bool:
    required = _normalize_token(required_capability)
    if required in {_normalize_token(manifest.tool_id), _normalize_token(manifest.manifest_id)}:
        return True
    if required == _normalize_token(manifest.display_name):
        return True
    return required in {_normalize_token(item) for item in manifest.declared_capabilities}


def _candidate_match(
    step: PlanStep,
    requirement: Mapping[str, object],
    manifest: NormalizedToolManifest,
) -> Mapping[str, object]:
    return _stable_mapping(
        {
            "step_id": step.step_id,
            "required_capability": requirement["capability"],
            "tool_id": manifest.tool_id,
            "manifest_id": manifest.manifest_id,
            "source_type": manifest.source_type,
            "metadata_only": manifest.source_type in METADATA_ONLY_SOURCE_TYPES,
            "direct_execution_allowed": False,
            "runtime_integration_allowed": False,
        }
    )


def _requirement(required: str, mapping: Mapping[str, Mapping[str, object]]) -> Mapping[str, object]:
    normalized = _normalize_token(required)
    mapped = mapping.get(required) or mapping.get(normalized)
    if mapped:
        capability = str(mapped.get("capability") or normalized)
        allowed_source_types = mapped.get("allowed_source_types", ())
        if isinstance(allowed_source_types, (tuple, list)):
            source_types = tuple(str(item).strip().upper() for item in allowed_source_types if str(item).strip())
        else:
            source_types = ()
        return {
            "capability": _normalize_token(capability),
            "allowed_source_types": source_types,
        }
    return {"capability": normalized, "allowed_source_types": ()}


def _capability_mapping(payload: Mapping[str, object]) -> Mapping[str, Mapping[str, object]]:
    if not isinstance(payload, Mapping):
        raise ValueError("capability_mapping_must_be_mapping")
    normalized: dict[str, Mapping[str, object]] = {}
    for key, value in payload.items():
        if isinstance(value, Mapping):
            normalized[str(key)] = dict(value)
            normalized[_normalize_token(str(key))] = dict(value)
        else:
            normalized[str(key)] = {"capability": str(value)}
            normalized[_normalize_token(str(key))] = {"capability": str(value)}
    return normalized


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


def _manifest(value: object) -> NormalizedToolManifest:
    if isinstance(value, NormalizedToolManifest):
        return value
    if hasattr(value, "as_dict"):
        value = value.as_dict()
    if not isinstance(value, Mapping):
        raise ValueError("tool_manifest_must_be_normalized_manifest_or_mapping")
    return NormalizedToolManifest(
        manifest_id=_required_string(value, "manifest_id"),
        source_type=_required_string(value, "source_type"),
        tool_id=_required_string(value, "tool_id"),
        display_name=_required_string(value, "display_name"),
        declared_capabilities=_string_tuple(value.get("declared_capabilities", ())),
        input_contract=_required_mapping(value, "input_contract"),
        output_contract=_required_mapping(value, "output_contract"),
        filesystem_scope=_required_string(value, "filesystem_scope"),
        network_scope=_required_string(value, "network_scope"),
        process_scope=_required_string(value, "process_scope"),
        credential_scope=_required_string(value, "credential_scope"),
        provider_scope=_required_string(value, "provider_scope"),
        dcc_scope=_required_string(value, "dcc_scope"),
        model_scope=_required_string(value, "model_scope"),
        browser_scope=_required_string(value, "browser_scope"),
        plugin_scope=_required_string(value, "plugin_scope"),
        normalized_at=_required_string(value, "normalized_at"),
        content_hash=_required_string(value, "content_hash"),
        direct_execution_allowed=bool(value.get("direct_execution_allowed")),
        runtime_integration_allowed=bool(value.get("runtime_integration_allowed")),
    )


def _sequence(payload: Mapping[str, object], field_name: str) -> tuple[object, ...]:
    value = payload.get(field_name)
    if not isinstance(value, (tuple, list)):
        raise ValueError(field_name + "_must_be_sequence")
    return tuple(value)


def _required_mapping(payload: Mapping[str, object], field_name: str) -> Mapping[str, object]:
    value = payload.get(field_name)
    if not isinstance(value, Mapping):
        raise ValueError(field_name + "_must_be_mapping")
    return dict(value)


def _required_string(payload: Mapping[str, object], field_name: str) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field_name + "_required")
    return value.strip()


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise ValueError("value_must_be_sequence")
    return tuple(str(item) for item in value if str(item).strip())


def _normalize_token(value: object) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", str(value).strip()).strip("_").lower()
    return normalized or "unknown"


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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")
