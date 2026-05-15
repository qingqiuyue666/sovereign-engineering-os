"""Product-grade Blender runtime boundary helpers."""

from dataclasses import dataclass
from pathlib import Path

from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.runtime_admission_gate import runtime_policy_for_class

__all__ = [
    "BlenderRuntimeAdmissionArtifacts",
    "BlenderRuntimeBoundary",
    "boundary_for_blender_runtime",
    "build_blender_runtime_boundaries",
    "validate_blender_runtime_boundary",
    "write_blender_runtime_admission_artifacts",
]

_CONFIG_TYPE = "personal_ai_runtime_config_v1"
_APPROVAL_TYPE = "personal_ai_runtime_human_approval_v1"
_MANIFEST_TYPE = "personal_ai_runtime_manifest_v1"
_APPROVED_ACTION = "admit_runtime_execution"
_ALLOWED_OPERATIONS = (
    "add_camera",
    "add_light",
    "add_mesh_primitive",
    "assign_material",
    "create_collection",
    "export_glb_preview",
    "render_preview",
    "set_camera",
    "set_object_transform",
)


@dataclass(frozen=True)
class BlenderRuntimeBoundary:
    runtime_id: str
    adapter_id: str
    capability: str
    runtime_class: str
    local_fixture_default: bool
    real_blender_runtime: bool
    enabled_by_default: bool
    admitted_by_default: bool
    allowed_operations: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "runtime_id": self.runtime_id,
            "adapter_id": self.adapter_id,
            "capability": self.capability,
            "runtime_class": self.runtime_class,
            "local_fixture_default": self.local_fixture_default,
            "real_blender_runtime": self.real_blender_runtime,
            "enabled_by_default": self.enabled_by_default,
            "admitted_by_default": self.admitted_by_default,
            "allowed_operations": list(self.allowed_operations),
            "arbitrary_python_allowed": False,
            "subprocess_launch_allowed": False,
            "uncontrolled_subprocess_allowed": False,
            "source_asset_overwrite_allowed": False,
            "scene_hash_binding_required": True,
            "output_manifest_required": True,
            "preview_evidence_required": True,
            "failure_quarantine_required": True,
            "runtime_admission_required_for_blender": self.real_blender_runtime,
        }


@dataclass(frozen=True)
class BlenderRuntimeAdmissionArtifacts:
    config_path: Path
    human_approval_path: Path
    manifest_path: Path
    config_sha256: str
    human_approval_sha256: str
    manifest_sha256: str


def build_blender_runtime_boundaries() -> tuple[BlenderRuntimeBoundary, ...]:
    return (
        BlenderRuntimeBoundary(
            runtime_id="blender_operation_fixture",
            adapter_id="blender_controlled_fixture_runtime",
            capability="validate_blender_operation_plan_fixture",
            runtime_class="local_fixture",
            local_fixture_default=True,
            real_blender_runtime=False,
            enabled_by_default=True,
            admitted_by_default=True,
            allowed_operations=_ALLOWED_OPERATIONS,
        ),
        BlenderRuntimeBoundary(
            runtime_id="blender_real_runtime_boundary",
            adapter_id="blender_real_runtime_boundary",
            capability="execute_blender_operation_plan",
            runtime_class="blender_runtime",
            local_fixture_default=False,
            real_blender_runtime=True,
            enabled_by_default=False,
            admitted_by_default=False,
            allowed_operations=_ALLOWED_OPERATIONS,
        ),
    )


def boundary_for_blender_runtime(runtime_id: str) -> BlenderRuntimeBoundary:
    for boundary in build_blender_runtime_boundaries():
        if boundary.runtime_id == runtime_id:
            return boundary
    raise ValueError("blender runtime is not registered")


def validate_blender_runtime_boundary(
    boundary: BlenderRuntimeBoundary,
) -> tuple[str, ...]:
    failures = []
    if not boundary.runtime_id:
        failures.append("runtime_id_missing")
    if not boundary.adapter_id:
        failures.append("adapter_id_missing")
    if not boundary.capability:
        failures.append("capability_missing")
    if boundary.runtime_class not in ("local_fixture", "blender_runtime"):
        failures.append("runtime_class_invalid")
    if not boundary.allowed_operations:
        failures.append("allowed_operations_missing")
    if boundary.real_blender_runtime:
        if boundary.enabled_by_default:
            failures.append("real_blender_enabled_by_default")
        if boundary.admitted_by_default:
            failures.append("real_blender_admitted_by_default")
    else:
        if not boundary.local_fixture_default:
            failures.append("fixture_default_missing")
        if not boundary.enabled_by_default:
            failures.append("fixture_disabled")
        if not boundary.admitted_by_default:
            failures.append("fixture_not_admitted")
    return tuple(sorted(failures))


def write_blender_runtime_admission_artifacts(
    output_dir: Path,
    *,
    runtime_id: str = "blender_real_runtime_boundary",
    dry_run: bool = True,
    reviewer_id: str = "human-reviewer",
) -> BlenderRuntimeAdmissionArtifacts:
    output_path = Path(output_dir)
    if not output_path.exists() or not output_path.is_dir():
        raise ValueError("output_dir is missing")
    boundary = boundary_for_blender_runtime(runtime_id)
    failures = validate_blender_runtime_boundary(boundary)
    if failures:
        raise ValueError("blender runtime boundary is invalid: " + ",".join(failures))
    if not reviewer_id.strip():
        raise ValueError("reviewer_id is required")

    config_path = output_path / "blender_runtime_config.json"
    manifest_path = output_path / "blender_runtime_manifest.json"
    approval_path = output_path / "blender_runtime_approval.json"
    _require_no_overwrite(config_path)
    _require_no_overwrite(manifest_path)
    _require_no_overwrite(approval_path)

    policy = runtime_policy_for_class(boundary.runtime_class).to_dict()
    config = {
        "config_type": _CONFIG_TYPE,
        "adapter_id": boundary.adapter_id,
        "capability": boundary.capability,
        "runtime_class": boundary.runtime_class,
        "runtime_id": boundary.runtime_id,
        "dry_run": dry_run,
        "real_runtime_enabled": False,
        "runtime_class_policy": policy,
        "allowed_operations": list(boundary.allowed_operations),
        "arbitrary_python_allowed": False,
        "subprocess_launch_allowed": False,
        "uncontrolled_subprocess_allowed": False,
        "source_asset_overwrite_allowed": False,
        "scene_hash_binding_required": True,
        "output_manifest_required": True,
        "preview_evidence_required": True,
        "failure_quarantine_required": True,
        "required_human_approval": True,
    }
    write_json_atomically(config_path, config)
    config_sha256 = sha256_file(config_path)

    manifest = {
        "manifest_type": _MANIFEST_TYPE,
        "adapter_id": boundary.adapter_id,
        "capability": boundary.capability,
        "runtime_class": boundary.runtime_class,
        "runtime_id": boundary.runtime_id,
        "dry_run": dry_run,
        "config_sha256": config_sha256,
        "operation_plan_validation_required": True,
        "scene_hash_binding_required": True,
        "output_manifest_required": True,
        "preview_evidence_required": True,
        "real_blender_runtime_called": False,
        "subprocess_execution_performed": False,
        "arbitrary_python_execution_performed": False,
        "required_human_approval": True,
    }
    write_json_atomically(manifest_path, manifest)
    manifest_sha256 = sha256_file(manifest_path)

    approval = {
        "approval_type": _APPROVAL_TYPE,
        "adapter_id": boundary.adapter_id,
        "capability": boundary.capability,
        "runtime_class": boundary.runtime_class,
        "runtime_id": boundary.runtime_id,
        "approved_action": _APPROVED_ACTION,
        "approved": True,
        "human_reviewed": True,
        "reviewer_id": reviewer_id.strip(),
        "config_sha256": config_sha256,
        "manifest_sha256": manifest_sha256,
        "required_human_approval": True,
    }
    write_json_atomically(approval_path, approval)
    return BlenderRuntimeAdmissionArtifacts(
        config_path=config_path,
        human_approval_path=approval_path,
        manifest_path=manifest_path,
        config_sha256=config_sha256,
        human_approval_sha256=sha256_file(approval_path),
        manifest_sha256=manifest_sha256,
    )


def _require_no_overwrite(path: Path) -> None:
    if path.exists():
        raise ValueError("blender runtime admission artifact already exists")
