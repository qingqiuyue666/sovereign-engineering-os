"""Controlled local Blender operation-plan fixture runtime."""

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.hash_utils import sha256_canonical_json, sha256_file
from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "BlenderControlledResult",
    "run_blender_controlled_fixture",
]

_MANIFEST_FILE = "blender_output_manifest.json"
_EVIDENCE_FILE = "blender_preview_evidence.json"
_FAILURE_FILE = "blender_failure_bundle.json"
_ALLOWED_OPERATIONS = {
    "add_camera",
    "add_light",
    "add_mesh_primitive",
    "assign_material",
    "create_collection",
    "export_glb_preview",
    "render_preview",
    "set_camera",
    "set_object_transform",
}
_FORBIDDEN_PLAN_TOKENS = (
    "__import__",
    "bpy.app.handlers",
    "download",
    "eval",
    "exec",
    "http",
    "network",
    "open(",
    "os.",
    "python",
    "script",
    "subprocess",
    "sys.",
    "url",
)


@dataclass(frozen=True)
class BlenderControlledResult:
    scene_path: Path
    operation_plan_path: Path
    output_dir: Path
    output_manifest_path: Path | None
    preview_evidence_path: Path | None
    failure_bundle_path: Path | None
    success: bool
    required_human_approval: bool


def run_blender_controlled_fixture(
    scene_path: Path,
    operation_plan_path: Path,
    output_dir: Path,
) -> BlenderControlledResult:
    scene_file = Path(scene_path)
    plan_file = Path(operation_plan_path)
    output_path = Path(output_dir)
    _validate_output_dir(output_path)
    manifest_path = output_path / _MANIFEST_FILE
    evidence_path = output_path / _EVIDENCE_FILE
    failure_path = output_path / _FAILURE_FILE
    _require_no_overwrite(manifest_path)
    _require_no_overwrite(evidence_path)
    _require_no_overwrite(failure_path)

    try:
        _validate_scene_file(scene_file)
        plan = _read_json_object(plan_file, "operation_plan_path")
        operation_records = _validate_operation_plan(plan, scene_file)
    except ValueError as error:
        _write_failure_bundle(scene_file, plan_file, failure_path, error)
        return BlenderControlledResult(
            scene_path=scene_file,
            operation_plan_path=plan_file,
            output_dir=output_path,
            output_manifest_path=None,
            preview_evidence_path=None,
            failure_bundle_path=failure_path,
            success=False,
            required_human_approval=True,
        )

    scene_hash = sha256_file(scene_file)
    plan_hash = sha256_file(plan_file)
    evidence = {
        "evidence_type": "personal_ai_blender_preview_evidence_v1",
        "authority": "non_authority",
        "execution_capability": "local_fixture_contract_only",
        "scene_sha256": scene_hash,
        "operation_plan_sha256": plan_hash,
        "preview_render_evidence_required": True,
        "preview_evidence_mode": "mock_manifest_only",
        "real_blender_runtime_called": False,
        "arbitrary_python_execution_performed": False,
        "subprocess_execution_performed": False,
        "source_asset_overwrite_performed": False,
        "deterministic_preview_sha256": sha256_canonical_json(
            {
                "operations": operation_records,
                "operation_plan_sha256": plan_hash,
                "scene_sha256": scene_hash,
            }
        ),
        "required_human_approval": True,
    }
    manifest = {
        "manifest_type": "personal_ai_blender_output_manifest_v1",
        "authority": "non_authority",
        "execution_capability": "local_fixture_contract_only",
        "adapter_id": "blender_controlled_fixture_runtime",
        "runtime_admitted": False,
        "real_blender_runtime_called": False,
        "blender_runtime_policy": {
            "real_runtime_disabled_by_default": True,
            "subprocess_runtime_allowed": False,
            "external_tool_control_allowed": False,
            "arbitrary_python_execution_allowed": False,
            "future_adapter_admission_required_for_real_runtime": True,
        },
        "scene_path": scene_file.as_posix(),
        "scene_sha256": scene_hash,
        "operation_plan_path": plan_file.as_posix(),
        "operation_plan_sha256": plan_hash,
        "allowed_operations": sorted(_ALLOWED_OPERATIONS),
        "validated_operations": operation_records,
        "output_artifacts": [
            {
                "artifact_name": "blender_preview_evidence",
                "path": evidence_path.as_posix(),
            }
        ],
        "source_asset_overwrite_performed": False,
        "output_manifest_required": True,
        "preview_render_evidence_required": True,
        "failure_quarantine_required": True,
        "operation_allowlist_required": True,
        "required_human_approval": True,
        "next_allowed_action": "human_review_only",
    }
    write_json_atomically(evidence_path, evidence)
    write_json_atomically(manifest_path, manifest)
    return BlenderControlledResult(
        scene_path=scene_file,
        operation_plan_path=plan_file,
        output_dir=output_path,
        output_manifest_path=manifest_path,
        preview_evidence_path=evidence_path,
        failure_bundle_path=None,
        success=True,
        required_human_approval=True,
    )


def _validate_output_dir(output_path):
    if not output_path.exists() or not output_path.is_dir():
        raise ValueError("output_dir is missing")


def _require_no_overwrite(path):
    if Path(path).exists():
        raise ValueError("blender runtime output already exists")


def _validate_scene_file(scene_file):
    if not scene_file.exists() or not scene_file.is_file():
        raise ValueError("scene_path is missing")
    if scene_file.is_symlink():
        raise ValueError("scene_path must not be a symlink")
    if scene_file.suffix.lower() not in (".blend", ".glb", ".gltf"):
        raise ValueError("scene_path extension is not allowed")


def _read_json_object(path, label):
    artifact_path = Path(path)
    if not artifact_path.exists() or not artifact_path.is_file():
        raise ValueError(label + " is missing")
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(label + " is malformed") from error
    if not isinstance(payload, dict):
        raise ValueError(label + " must be an object")
    return payload


def _validate_operation_plan(plan, scene_file):
    operations = plan.get("operations")
    if not isinstance(operations, list) or not operations:
        raise ValueError("blender operation plan operations are malformed")
    records = []
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            raise ValueError("blender operation is malformed")
        operation_type = str(operation.get("operation", ""))
        if operation_type not in _ALLOWED_OPERATIONS:
            raise ValueError("blender operation is not allowed")
        _validate_no_forbidden_tokens(operation)
        _validate_no_source_overwrite(operation, scene_file)
        parameters = operation.get("parameters", {})
        if not isinstance(parameters, dict):
            raise ValueError("blender operation parameters are malformed")
        records.append(
            {
                "index": index,
                "operation": operation_type,
                "parameter_keys": sorted(str(key) for key in parameters),
            }
        )
    return records


def _validate_no_forbidden_tokens(value):
    if isinstance(value, dict):
        for key, item in value.items():
            _validate_no_forbidden_tokens(str(key))
            _validate_no_forbidden_tokens(item)
        return
    if isinstance(value, list):
        for item in value:
            _validate_no_forbidden_tokens(item)
        return
    if isinstance(value, str):
        lowered = value.lower()
        if any(token in lowered for token in _FORBIDDEN_PLAN_TOKENS):
            raise ValueError("blender operation contains forbidden runtime token")


def _validate_no_source_overwrite(operation, scene_file):
    scene_resolved = scene_file.resolve(strict=True)
    _validate_no_source_overwrite_value(operation, scene_resolved)


def _validate_no_source_overwrite_value(value, scene_resolved):
    if isinstance(value, dict):
        for key, item in value.items():
            lowered_key = str(key).lower()
            if lowered_key in ("output_path", "target_path", "write_path"):
                _validate_path_is_not_source(item, scene_resolved)
            _validate_no_source_overwrite_value(item, scene_resolved)
    elif isinstance(value, list):
        for item in value:
            _validate_no_source_overwrite_value(item, scene_resolved)


def _validate_path_is_not_source(candidate, scene_resolved):
    if not isinstance(candidate, str) or not candidate:
        return
    try:
        candidate_resolved = Path(candidate).resolve(strict=False)
    except OSError as error:
        raise ValueError("blender operation path is invalid") from error
    if candidate_resolved == scene_resolved:
        raise ValueError("blender operation must not overwrite source scene")


def _write_failure_bundle(scene_file, plan_file, failure_path, error):
    payload = {
        "failure_type": "personal_ai_blender_failure_bundle_v1",
        "authority": "non_authority",
        "execution_capability": "local_fixture_contract_only",
        "scene_path": scene_file.as_posix(),
        "scene_sha256": sha256_file(scene_file)
        if scene_file.exists() and scene_file.is_file() and not scene_file.is_symlink()
        else None,
        "operation_plan_path": plan_file.as_posix(),
        "operation_plan_sha256": sha256_file(plan_file)
        if plan_file.exists() and plan_file.is_file()
        else None,
        "error_type": error.__class__.__name__,
        "error_message": str(error),
        "real_blender_runtime_called": False,
        "arbitrary_python_execution_performed": False,
        "subprocess_execution_performed": False,
        "source_asset_overwrite_performed": False,
        "required_human_approval": True,
        "next_allowed_action": "human_review_only",
    }
    write_json_atomically(failure_path, payload)
