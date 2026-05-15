"""Controlled local ComfyUI workflow fixture runtime."""

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.hash_utils import sha256_canonical_json, sha256_file
from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "ComfyUIControlledResult",
    "run_comfyui_controlled_fixture",
]

_MANIFEST_FILE = "comfyui_output_manifest.json"
_EVIDENCE_FILE = "comfyui_preview_evidence.json"
_FAILURE_FILE = "comfyui_failure_bundle.json"
_ALLOWED_NODE_TYPES = {
    "CheckpointLoaderSimple",
    "CLIPTextEncode",
    "EmptyLatentImage",
    "KSampler",
    "LoadImage",
    "PreviewImage",
    "SaveImage",
    "VAEDecode",
}
_FORBIDDEN_NODE_TOKENS = (
    "download",
    "exec",
    "http",
    "network",
    "python",
    "script",
    "subprocess",
    "url",
)


@dataclass(frozen=True)
class ComfyUIControlledResult:
    workflow_path: Path
    output_dir: Path
    output_manifest_path: Path | None
    preview_evidence_path: Path | None
    failure_bundle_path: Path | None
    success: bool
    required_human_approval: bool


def run_comfyui_controlled_fixture(
    workflow_path: Path,
    output_dir: Path,
    *,
    input_asset_paths: tuple[Path, ...] = (),
    endpoint_config_path: Path | None = None,
) -> ComfyUIControlledResult:
    workflow_file = Path(workflow_path)
    output_path = Path(output_dir)
    _validate_output_dir(output_path)
    manifest_path = output_path / _MANIFEST_FILE
    evidence_path = output_path / _EVIDENCE_FILE
    failure_path = output_path / _FAILURE_FILE
    _require_no_overwrite(manifest_path)
    _require_no_overwrite(evidence_path)
    _require_no_overwrite(failure_path)

    try:
        workflow = _read_json_object(workflow_file, "workflow_path")
        _validate_endpoint_policy(endpoint_config_path)
        node_records = _validate_workflow(workflow)
        asset_records = _asset_records(input_asset_paths)
    except ValueError as error:
        _write_failure_bundle(workflow_file, failure_path, error)
        return ComfyUIControlledResult(
            workflow_path=workflow_file,
            output_dir=output_path,
            output_manifest_path=None,
            preview_evidence_path=None,
            failure_bundle_path=failure_path,
            success=False,
            required_human_approval=True,
        )

    workflow_hash = sha256_file(workflow_file)
    evidence = {
        "evidence_type": "personal_ai_comfyui_preview_evidence_v1",
        "authority": "non_authority",
        "execution_capability": "local_fixture_contract_only",
        "workflow_sha256": workflow_hash,
        "preview_render_evidence_required": True,
        "preview_evidence_mode": "mock_manifest_only",
        "real_comfyui_endpoint_called": False,
        "external_downloads_performed": False,
        "arbitrary_node_execution_performed": False,
        "input_asset_hashes": {
            asset["path"]: asset["sha256"] for asset in asset_records
        },
        "deterministic_preview_sha256": sha256_canonical_json(
            {
                "assets": asset_records,
                "nodes": node_records,
                "workflow_sha256": workflow_hash,
            }
        ),
        "required_human_approval": True,
    }
    manifest = {
        "manifest_type": "personal_ai_comfyui_output_manifest_v1",
        "authority": "non_authority",
        "execution_capability": "local_fixture_contract_only",
        "adapter_id": "comfyui_controlled_fixture_runtime",
        "runtime_admitted": False,
        "real_comfyui_endpoint_called": False,
        "local_endpoint_policy": {
            "real_endpoint_disabled_by_default": True,
            "only_loopback_endpoint_may_be_considered_after_future_admission": True,
            "network_runtime_allowed": False,
        },
        "workflow_path": workflow_file.as_posix(),
        "workflow_sha256": workflow_hash,
        "workflow_node_count": len(node_records),
        "allowed_node_types": sorted(_ALLOWED_NODE_TYPES),
        "validated_nodes": node_records,
        "input_assets": asset_records,
        "output_artifacts": [
            {
                "artifact_name": "comfyui_preview_evidence",
                "path": evidence_path.as_posix(),
            }
        ],
        "source_asset_overwrite_performed": False,
        "output_manifest_required": True,
        "preview_render_evidence_required": True,
        "failure_quarantine_required": True,
        "external_downloads_allowed": False,
        "arbitrary_node_execution_allowed": False,
        "required_human_approval": True,
        "next_allowed_action": "human_review_only",
    }
    write_json_atomically(evidence_path, evidence)
    write_json_atomically(manifest_path, manifest)
    return ComfyUIControlledResult(
        workflow_path=workflow_file,
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
        raise ValueError("comfyui runtime output already exists")


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


def _validate_endpoint_policy(endpoint_config_path):
    if endpoint_config_path is None:
        return
    config = _read_json_object(Path(endpoint_config_path), "endpoint_config_path")
    endpoint = str(config.get("endpoint", ""))
    if not endpoint.startswith(("http://127.0.0.1", "http://localhost")):
        raise ValueError("comfyui endpoint must be loopback")
    if config.get("enable_real_endpoint") is True:
        raise ValueError("real ComfyUI endpoint calls are not admitted")


def _validate_workflow(workflow):
    nodes = workflow.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("comfyui workflow nodes are malformed")
    records = []
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise ValueError("comfyui workflow node is malformed")
        node_id = str(node.get("id", ""))
        node_type = str(node.get("type", ""))
        inputs = node.get("inputs", {})
        if not node_id:
            raise ValueError("comfyui workflow node id is missing")
        if node_type not in _ALLOWED_NODE_TYPES:
            raise ValueError("comfyui workflow node type is not allowed")
        lowered_type = node_type.lower()
        if any(token in lowered_type for token in _FORBIDDEN_NODE_TOKENS):
            raise ValueError("comfyui workflow node type is forbidden")
        if not isinstance(inputs, dict):
            raise ValueError("comfyui workflow node inputs are malformed")
        _validate_node_inputs(inputs)
        records.append(
            {
                "index": index,
                "id": node_id,
                "type": node_type,
                "input_keys": sorted(str(key) for key in inputs),
            }
        )
    return records


def _validate_node_inputs(inputs):
    for key, value in inputs.items():
        lowered_key = str(key).lower()
        if any(token in lowered_key for token in _FORBIDDEN_NODE_TOKENS):
            raise ValueError("comfyui workflow input key is forbidden")
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            raise ValueError("comfyui workflow external downloads are not allowed")


def _asset_records(input_asset_paths):
    records = []
    for asset_path in input_asset_paths:
        path = Path(asset_path)
        if not path.exists() or not path.is_file():
            raise ValueError("input asset path is missing")
        if path.is_symlink():
            raise ValueError("input asset path must not be a symlink")
        records.append(
            {
                "path": path.as_posix(),
                "file_name": path.name,
                "sha256": sha256_file(path),
                "source_asset_overwrite_performed": False,
            }
        )
    return records


def _write_failure_bundle(workflow_file, failure_path, error):
    payload = {
        "failure_type": "personal_ai_comfyui_failure_bundle_v1",
        "authority": "non_authority",
        "execution_capability": "local_fixture_contract_only",
        "workflow_path": workflow_file.as_posix(),
        "workflow_sha256": sha256_file(workflow_file)
        if workflow_file.exists() and workflow_file.is_file()
        else None,
        "error_type": error.__class__.__name__,
        "error_message": str(error),
        "real_comfyui_endpoint_called": False,
        "external_downloads_performed": False,
        "arbitrary_node_execution_performed": False,
        "source_asset_overwrite_performed": False,
        "required_human_approval": True,
        "next_allowed_action": "human_review_only",
    }
    write_json_atomically(failure_path, payload)
