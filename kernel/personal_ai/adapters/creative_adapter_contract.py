"""Deferred creative adapter policy contracts for Personal AI v2."""

from dataclasses import dataclass

__all__ = [
    "CreativeAdapterFamily",
    "CreativeAdapterPolicy",
    "build_creative_adapter_policies",
    "policy_for_family",
    "validate_creative_adapter_policy",
]


class CreativeAdapterFamily:
    COMFYUI = "comfyui_workflow_api"
    BLENDER = "blender_python_mcp"
    UNREAL = "unreal_python_editor_utility_commandlet"
    HOUDINI = "houdini_hom_hython_hda"
    AFTER_EFFECTS = "after_effects_extendscript_uxp_aerender"
    ZBRUSH = "zbrush_support_handoff"

    @classmethod
    def all(cls) -> tuple[str, ...]:
        return (
            cls.COMFYUI,
            cls.BLENDER,
            cls.UNREAL,
            cls.HOUDINI,
            cls.AFTER_EFFECTS,
            cls.ZBRUSH,
        )


@dataclass(frozen=True)
class CreativeAdapterPolicy:
    family: str
    proposed_adapter: str
    runtime_admitted: bool = False
    external_tool_control_admitted: bool = False
    explicit_future_admission_required: bool = True
    explicit_adapter_admission_required: bool = True
    source_asset_overwrite_allowed: bool = False
    output_manifest_required: bool = True
    preview_render_evidence_required: bool = True
    operation_allowlist_required: bool = True
    operation_allowlist: tuple[str, ...] = ()
    logs_required: bool = True
    human_approval_required: bool = True
    capability_token_required: bool = True
    quarantine_required: bool = True
    output_hashing_required: bool = True
    real_runtime_deferred_reason: str = (
        "real creative software runtime requires future explicit adapter admission"
    )

    def to_dict(self) -> dict[str, object]:
        return {
            "family": self.family,
            "proposed_adapter": self.proposed_adapter,
            "runtime_admitted": self.runtime_admitted,
            "external_tool_control_admitted": self.external_tool_control_admitted,
            "explicit_future_admission_required": (
                self.explicit_future_admission_required
            ),
            "explicit_adapter_admission_required": (
                self.explicit_adapter_admission_required
            ),
            "source_asset_overwrite_allowed": self.source_asset_overwrite_allowed,
            "output_manifest_required": self.output_manifest_required,
            "preview_render_evidence_required": (
                self.preview_render_evidence_required
            ),
            "operation_allowlist_required": self.operation_allowlist_required,
            "operation_allowlist": sorted(self.operation_allowlist),
            "logs_required": self.logs_required,
            "human_approval_required": self.human_approval_required,
            "capability_token_required": self.capability_token_required,
            "quarantine_required": self.quarantine_required,
            "output_hashing_required": self.output_hashing_required,
            "real_runtime_deferred_reason": self.real_runtime_deferred_reason,
        }


def build_creative_adapter_policies() -> tuple[CreativeAdapterPolicy, ...]:
    return (
        CreativeAdapterPolicy(
            family=CreativeAdapterFamily.COMFYUI,
            proposed_adapter="future_comfyui_controlled_runtime",
            operation_allowlist=(
                "CheckpointLoaderSimple",
                "CLIPTextEncode",
                "EmptyLatentImage",
                "KSampler",
                "LoadImage",
                "PreviewImage",
                "SaveImage",
                "VAEDecode",
            ),
        ),
        CreativeAdapterPolicy(
            family=CreativeAdapterFamily.BLENDER,
            proposed_adapter="future_blender_controlled_runtime",
            operation_allowlist=(
                "add_camera",
                "add_light",
                "add_mesh_primitive",
                "assign_material",
                "create_collection",
                "export_glb_preview",
                "render_preview",
                "set_camera",
                "set_object_transform",
            ),
        ),
        CreativeAdapterPolicy(
            family=CreativeAdapterFamily.UNREAL,
            proposed_adapter="future_unreal_controlled_runtime",
            operation_allowlist=(
                "open_project_fixture_metadata",
                "render_preview_queue_manifest",
                "validate_asset_references",
            ),
        ),
        CreativeAdapterPolicy(
            family=CreativeAdapterFamily.HOUDINI,
            proposed_adapter="future_houdini_controlled_runtime",
            operation_allowlist=(
                "inspect_hda_manifest",
                "render_preview_manifest",
                "validate_node_allowlist",
            ),
        ),
        CreativeAdapterPolicy(
            family=CreativeAdapterFamily.AFTER_EFFECTS,
            proposed_adapter="future_after_effects_controlled_runtime",
            operation_allowlist=(
                "inspect_project_manifest",
                "render_preview_manifest",
                "validate_composition_references",
            ),
        ),
        CreativeAdapterPolicy(
            family=CreativeAdapterFamily.ZBRUSH,
            proposed_adapter="future_zbrush_handoff_policy",
            operation_allowlist=(
                "inspect_tool_manifest",
                "record_preview_evidence",
                "validate_source_asset_hashes",
            ),
        ),
    )


def policy_for_family(family: str) -> CreativeAdapterPolicy:
    for policy in build_creative_adapter_policies():
        if policy.family == family:
            return policy
    raise ValueError("creative adapter family is not registered")


def validate_creative_adapter_policy(
    policy: CreativeAdapterPolicy,
) -> tuple[str, ...]:
    failures = []
    if policy.family not in CreativeAdapterFamily.all():
        failures.append("family_unknown")
    if not policy.proposed_adapter:
        failures.append("proposed_adapter_missing")
    if policy.runtime_admitted:
        failures.append("runtime_must_not_be_admitted")
    if policy.external_tool_control_admitted:
        failures.append("external_tool_control_must_not_be_admitted")
    if not policy.explicit_future_admission_required:
        failures.append("future_admission_required")
    if not policy.explicit_adapter_admission_required:
        failures.append("explicit_adapter_admission_required")
    if policy.source_asset_overwrite_allowed:
        failures.append("source_asset_overwrite_forbidden")
    if not policy.operation_allowlist_required:
        failures.append("operation_allowlist_required_missing")
    if not policy.operation_allowlist:
        failures.append("operation_allowlist_missing")
    for field_name in (
        "output_manifest_required",
        "preview_render_evidence_required",
        "logs_required",
        "human_approval_required",
        "capability_token_required",
        "quarantine_required",
        "output_hashing_required",
    ):
        if getattr(policy, field_name) is not True:
            failures.append(field_name + "_missing")
    return tuple(sorted(failures))
