"""Deterministic ComfyUI workflow specification for the private creative sample."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from kernel.runtime._production_workbench_validation import (
    OBSERVED_AT_NOT_PROVIDED,
    compute_content_hash,
    contains_required_terms,
    prepare_material,
    render_markdown,
    require_dict_fields,
    require_list_fields,
    require_required_members,
    require_string_fields,
)

__all__ = [
    "COMFYUI_REQUIRED_INPUT_PASSES",
    "ComfyUIWorkflowSpec",
    "build_comfyui_workflow_spec",
    "render_comfyui_workflow_spec_markdown",
]

_POLICY_VERSION = "comfyui-workflow-spec-v1"
_CODE_VERSION = "0.1.0"

COMFYUI_REQUIRED_INPUT_PASSES = ("depth", "normal", "emission_or_mask", "reference_frame")
_REQUIRED_CONSTRAINT_TERMS = (
    "prompt-only",
    "model download",
    "network",
    "execution",
    "raw prompt",
    "raw output",
)

_STRING_FIELDS = ("spec_id", "project_name", "policy_version", "code_version")
_LIST_FIELDS = (
    "input_passes",
    "control_maps",
    "style_reference_policy",
    "model_category_policy",
    "denoise_policy",
    "node_group_requirements",
    "failure_cases",
    "review_criteria",
    "blocked_execution",
    "rollback_plan",
)
_DICT_FIELDS = ("output_contract",)


@dataclass(frozen=True)
class ComfyUIWorkflowSpec:
    """Repository-ready controlled ComfyUI workflow specification."""

    spec_id: str
    project_name: str
    input_passes: tuple[object, ...]
    control_maps: tuple[object, ...]
    style_reference_policy: tuple[object, ...]
    model_category_policy: tuple[object, ...]
    denoise_policy: tuple[object, ...]
    node_group_requirements: tuple[object, ...]
    output_contract: dict[str, object]
    failure_cases: tuple[object, ...]
    review_criteria: tuple[object, ...]
    blocked_execution: tuple[object, ...]
    rollback_plan: tuple[object, ...]
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    content_hash: str = ""
    observed_at: str = OBSERVED_AT_NOT_PROVIDED

    def deterministic_material(self) -> dict[str, object]:
        return {
            "blocked_execution": list(self.blocked_execution),
            "code_version": self.code_version,
            "control_maps": list(self.control_maps),
            "denoise_policy": list(self.denoise_policy),
            "failure_cases": list(self.failure_cases),
            "input_passes": list(self.input_passes),
            "model_category_policy": list(self.model_category_policy),
            "node_group_requirements": list(self.node_group_requirements),
            "output_contract": self.output_contract,
            "policy_version": self.policy_version,
            "project_name": self.project_name,
            "review_criteria": list(self.review_criteria),
            "rollback_plan": list(self.rollback_plan),
            "spec_id": self.spec_id,
            "style_reference_policy": list(self.style_reference_policy),
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


def build_comfyui_workflow_spec(
    material: Mapping[str, object],
    *,
    observed_at: str | None = None,
) -> ComfyUIWorkflowSpec:
    """Build a deterministic ComfyUI spec without loading models or running workflows."""

    normalized, observed = prepare_material(
        material,
        observed_at=observed_at,
        material_name="comfyui_workflow_spec_material",
    )
    require_string_fields(normalized, _STRING_FIELDS)
    require_list_fields(normalized, _LIST_FIELDS)
    require_dict_fields(normalized, _DICT_FIELDS)
    require_required_members(normalized["input_passes"], COMFYUI_REQUIRED_INPUT_PASSES, field="input_passes")
    if not contains_required_terms(normalized["blocked_execution"], ("comfyui", "execution")):
        raise ValueError("blocked_execution_must_block_comfyui_execution")
    if not contains_required_terms(normalized, _REQUIRED_CONSTRAINT_TERMS):
        raise ValueError("required_comfyui_constraints_missing")

    spec = ComfyUIWorkflowSpec(
        spec_id=normalized["spec_id"],
        project_name=normalized["project_name"],
        input_passes=tuple(normalized["input_passes"]),
        control_maps=tuple(normalized["control_maps"]),
        style_reference_policy=tuple(normalized["style_reference_policy"]),
        model_category_policy=tuple(normalized["model_category_policy"]),
        denoise_policy=tuple(normalized["denoise_policy"]),
        node_group_requirements=tuple(normalized["node_group_requirements"]),
        output_contract=normalized["output_contract"],
        failure_cases=tuple(normalized["failure_cases"]),
        review_criteria=tuple(normalized["review_criteria"]),
        blocked_execution=tuple(normalized["blocked_execution"]),
        rollback_plan=tuple(normalized["rollback_plan"]),
        policy_version=normalized["policy_version"],
        code_version=normalized["code_version"],
        content_hash="",
        observed_at=observed,
    )
    return _with_hash(spec)


def render_comfyui_workflow_spec_markdown(spec: ComfyUIWorkflowSpec) -> str:
    """Render ComfyUI workflow spec Markdown deterministically."""

    if not isinstance(spec, ComfyUIWorkflowSpec):
        raise ValueError("spec_must_be_comfyui_workflow_spec")
    material = spec.deterministic_material()
    return render_markdown(
        "ComfyUI Workflow Specification v1",
        metadata_rows=(
            ("spec_id", spec.spec_id),
            ("project_name", spec.project_name),
            ("policy_version", spec.policy_version),
            ("code_version", spec.code_version),
            ("content_hash", spec.content_hash),
            ("observed_at", spec.observed_at),
        ),
        sections=(
            ("Input Passes", material["input_passes"]),
            ("Control Maps", material["control_maps"]),
            ("Style Reference Policy", material["style_reference_policy"]),
            ("Model Category Policy", material["model_category_policy"]),
            ("Denoise Policy", material["denoise_policy"]),
            ("Node Group Requirements", material["node_group_requirements"]),
            ("Output Contract", material["output_contract"]),
            ("Failure Cases", material["failure_cases"]),
            ("Review Criteria", material["review_criteria"]),
            ("Blocked Execution", material["blocked_execution"]),
            ("Rollback Plan", material["rollback_plan"]),
        ),
    )


def _with_hash(spec: ComfyUIWorkflowSpec) -> ComfyUIWorkflowSpec:
    return ComfyUIWorkflowSpec(
        spec_id=spec.spec_id,
        project_name=spec.project_name,
        input_passes=spec.input_passes,
        control_maps=spec.control_maps,
        style_reference_policy=spec.style_reference_policy,
        model_category_policy=spec.model_category_policy,
        denoise_policy=spec.denoise_policy,
        node_group_requirements=spec.node_group_requirements,
        output_contract=spec.output_contract,
        failure_cases=spec.failure_cases,
        review_criteria=spec.review_criteria,
        blocked_execution=spec.blocked_execution,
        rollback_plan=spec.rollback_plan,
        policy_version=spec.policy_version,
        code_version=spec.code_version,
        content_hash=compute_content_hash(spec.deterministic_material()),
        observed_at=spec.observed_at,
    )
