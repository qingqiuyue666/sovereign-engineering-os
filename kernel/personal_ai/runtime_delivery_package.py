"""Runtime delivery package builder for Personal AI Execution OS v2."""

from dataclasses import dataclass
from pathlib import Path
import json
import shutil

from kernel.personal_ai.adapters.xlsx_readonly_runtime import (
    xlsx_artifact_contains_sentinel,
)
from kernel.personal_ai.hash_utils import sha256_canonical_json, sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.job_package import validate_job_id

__all__ = [
    "RuntimeDeliveryPackageResult",
    "build_runtime_delivery_package",
    "validate_runtime_delivery_package",
]

_MANIFEST_FILE = "runtime_delivery_manifest.json"
_VALIDATION_FILE = "runtime_delivery_validation.json"

_KNOWN_RUNTIME_ARTIFACTS = (
    ("xlsx_inspection_json", "xlsx_inspection.json"),
    ("xlsx_inspection_summary", "xlsx_inspection_summary.md"),
    ("xlsx_output_plan", "xlsx_output_plan.json"),
    ("xlsx_output_manifest", "xlsx_output_manifest.json"),
    ("xlsx_output_delivery_summary", "xlsx_output_delivery_summary.md"),
    ("xlsx_output_validation", "xlsx_output_validation.json"),
    ("model_inference_artifact", "model_inference_artifact.json"),
    ("model_failure_bundle", "model_failure_bundle.json"),
    ("browser_action_log", "browser_action_log.json"),
    ("browser_evidence_manifest", "browser_evidence_manifest.json"),
    ("comfyui_output_manifest", "comfyui_output_manifest.json"),
    ("comfyui_preview_evidence", "comfyui_preview_evidence.json"),
    ("comfyui_failure_bundle", "comfyui_failure_bundle.json"),
    ("blender_output_manifest", "blender_output_manifest.json"),
    ("blender_preview_evidence", "blender_preview_evidence.json"),
    ("blender_failure_bundle", "blender_failure_bundle.json"),
    ("task_graph_execution_manifest", "task_graph_execution_manifest.json"),
    ("task_graph_replay_manifest", "task_graph_replay_manifest.json"),
    ("task_graph_failure_bundle", "task_graph_failure_bundle.json"),
)

_ARTIFACT_POLICIES = {
    "xlsx_inspection_json": ("metadata_only", "low"),
    "xlsx_inspection_summary": ("metadata_only", "low"),
    "xlsx_output_plan": ("metadata_only", "low"),
    "xlsx_output_manifest": ("metadata_only", "low"),
    "xlsx_output_delivery_summary": ("metadata_only", "low"),
    "xlsx_output_validation": ("metadata_only", "low"),
    "model_inference_artifact": ("metadata_only", "medium"),
    "model_failure_bundle": ("metadata_only", "medium"),
    "browser_action_log": ("metadata_only", "medium"),
    "browser_evidence_manifest": ("metadata_only", "medium"),
    "comfyui_output_manifest": ("metadata_only", "medium"),
    "comfyui_preview_evidence": ("metadata_only", "medium"),
    "comfyui_failure_bundle": ("metadata_only", "medium"),
    "blender_output_manifest": ("metadata_only", "medium"),
    "blender_preview_evidence": ("metadata_only", "medium"),
    "blender_failure_bundle": ("metadata_only", "medium"),
    "task_graph_execution_manifest": ("metadata_only", "medium"),
    "task_graph_replay_manifest": ("metadata_only", "medium"),
    "task_graph_failure_bundle": ("metadata_only", "medium"),
    "generated_output_xlsx": ("derived_data", "medium"),
}

_DELIVERY_POLICY = {
    "allowed_output_categories": ["derived_data", "metadata_only"],
    "raw_derived_allowed": False,
    "raw_derived_requires_explicit_policy_gate": True,
    "requires_hash_bound_manifest": True,
    "requires_replay_verification": True,
    "requires_generic_leakage_scan": True,
    "network_runtime_allowed": False,
    "subprocess_runtime_allowed": False,
    "browser_runtime_allowed": False,
    "model_api_runtime_allowed": False,
    "creative_runtime_allowed": False,
}

_DEFAULT_FORBIDDEN_LEAKAGE_TOKENS = (
    "RAW_HEADER_SECRET",
    "RAW_CELL_SECRET",
)
_TEXT_LEAKAGE_SUFFIXES = (".csv", ".html", ".json", ".md", ".tsv", ".txt")
_XLSX_LEAKAGE_MAX_ROWS = 200
_XLSX_LEAKAGE_MAX_COLUMNS = 50


@dataclass(frozen=True)
class RuntimeDeliveryPackageResult:
    package_id: str
    package_dir: Path
    runtime_delivery_manifest_path: Path
    runtime_delivery_validation_path: Path
    packaged_artifacts: tuple[str, ...]
    complete: bool
    raw_value_leakage_detected: bool
    required_human_approval: bool


def build_runtime_delivery_package(
    runtime_artifact_dir: Path,
    output_root_dir: Path,
    *,
    package_id: str,
    input_dir: Path | None = None,
) -> RuntimeDeliveryPackageResult:
    source_dir = Path(runtime_artifact_dir)
    output_root = Path(output_root_dir)
    _validate_inputs(source_dir, output_root, package_id, input_dir)
    package_dir = output_root / package_id
    if package_dir.exists():
        raise ValueError("runtime delivery package_dir already exists")
    package_dir.mkdir()

    artifact_records = []
    for artifact_name, file_name in _KNOWN_RUNTIME_ARTIFACTS:
        source_path = source_dir / file_name
        if source_path.exists() and source_path.is_file():
            target_path = package_dir / file_name
            _copy_without_overwrite(source_path, target_path)
            artifact_records.append(
                _artifact_record(artifact_name, source_path, target_path)
            )

    output_artifact = _copy_generated_xlsx_output(source_dir, package_dir)
    if output_artifact is not None:
        artifact_records.append(output_artifact)

    artifact_records = sorted(
        artifact_records,
        key=lambda record: record["artifact_name"],
    )
    _enforce_delivery_policy(artifact_records)
    provenance_chain_references = _provenance_references(source_dir)
    artifact_hashes = _artifact_hashes_from_records(artifact_records)
    manifest_path = package_dir / _MANIFEST_FILE
    validation_path = package_dir / _VALIDATION_FILE
    _require_no_overwrite(manifest_path)
    _require_no_overwrite(validation_path)
    manifest = {
        "manifest_type": "personal_ai_execution_os_v2_runtime_delivery_manifest",
        "manifest_version": 1,
        "authority": "non_authority",
        "execution_capability": "bounded_local_runtime_delivery",
        "source_runtime_artifact_dir": source_dir.as_posix(),
        "package_id": package_id,
        "package_dir": package_dir.as_posix(),
        "delivery_policy": dict(_DELIVERY_POLICY),
        "artifact_count": len(artifact_records),
        "artifact_hashes": artifact_hashes,
        "artifact_order": [
            artifact["artifact_name"] for artifact in artifact_records
        ],
        "package_replay": {
            "artifact_set_sha256": sha256_canonical_json(artifact_hashes),
            "artifact_hash_algorithm": "sha256",
            "manifest_ordering": "artifact_name_sorted",
        },
        "artifacts": artifact_records,
        "generated_output_xlsx_hash": _generated_output_xlsx_hash(
            artifact_records
        ),
        "provenance_chain_references": provenance_chain_references,
        "input_mutation_performed": False,
        "overwrite_performed": False,
        "raw_value_copy_performed": False,
        "required_human_approval": True,
        "next_allowed_action": "human_review_only",
    }
    write_json_atomically(manifest_path, manifest)
    validation = validate_runtime_delivery_package(package_dir, validation_path)
    return RuntimeDeliveryPackageResult(
        package_id=package_id,
        package_dir=package_dir,
        runtime_delivery_manifest_path=manifest_path,
        runtime_delivery_validation_path=validation.runtime_delivery_validation_path,
        packaged_artifacts=tuple(
            artifact["artifact_name"] for artifact in artifact_records
        ),
        complete=validation.complete,
        raw_value_leakage_detected=validation.raw_value_leakage_detected,
        required_human_approval=True,
    )


def validate_runtime_delivery_package(
    package_dir: Path,
    output_validation_path: Path | None = None,
    *,
    raw_sentinel_values: list[str] | None = None,
) -> RuntimeDeliveryPackageResult:
    package_path = Path(package_dir)
    if not package_path.exists() or not package_path.is_dir():
        raise ValueError("runtime delivery package_dir is missing")
    manifest_path = package_path / _MANIFEST_FILE
    if not manifest_path.exists() or not manifest_path.is_file():
        raise ValueError("runtime delivery manifest is missing")
    validation_path = (
        Path(output_validation_path)
        if output_validation_path is not None
        else package_path / _VALIDATION_FILE
    )
    if not validation_path.parent.exists() or not validation_path.parent.is_dir():
        raise ValueError("runtime delivery validation parent is missing")
    _require_no_overwrite(validation_path)
    manifest = _read_json(manifest_path)
    _validate_manifest_shape(manifest)
    artifacts = manifest.get("artifacts", [])
    verified_artifacts = []
    missing_artifacts = []
    hash_mismatches = []
    verified_artifact_hashes = {}
    for artifact in artifacts:
        package_path_value = Path(str(artifact.get("package_path", "")))
        artifact_name = str(artifact.get("artifact_name", ""))
        if not package_path_value.exists() or not package_path_value.is_file():
            missing_artifacts.append(artifact_name)
            continue
        if sha256_file(package_path_value) != artifact.get("sha256"):
            hash_mismatches.append(artifact_name)
        else:
            verified_artifacts.append(artifact_name)
            verified_artifact_hashes[artifact_name] = artifact["sha256"]

    policy_failures = _policy_failures(manifest)
    package_replay_verified = _package_replay_verified(
        manifest,
        verified_artifact_hashes,
    )
    raw_value_leakage_detected = _raw_value_leakage_detected(
        package_path,
        raw_sentinel_values or [],
    )
    complete = (
        not missing_artifacts
        and not hash_mismatches
        and not policy_failures
        and package_replay_verified
        and not raw_value_leakage_detected
        and bool(verified_artifacts)
    )
    validation = {
        "validation_type": "personal_ai_execution_os_v2_runtime_delivery_validation",
        "authority": "non_authority",
        "execution_capability": "bounded_local_runtime_delivery",
        "package_dir": package_path.as_posix(),
        "manifest_path": manifest_path.as_posix(),
        "verified_artifacts": sorted(verified_artifacts),
        "missing_artifacts": sorted(missing_artifacts),
        "hash_mismatches": sorted(hash_mismatches),
        "artifact_hashes_verified": not missing_artifacts and not hash_mismatches,
        "package_replay_verified": package_replay_verified,
        "policy_verified": not policy_failures,
        "policy_failures": sorted(policy_failures),
        "raw_value_leakage_detected": raw_value_leakage_detected,
        "complete": complete,
        "required_human_approval": True,
    }
    write_json_atomically(validation_path, validation)
    return RuntimeDeliveryPackageResult(
        package_id=str(manifest.get("package_id", package_path.name)),
        package_dir=package_path,
        runtime_delivery_manifest_path=manifest_path,
        runtime_delivery_validation_path=validation_path,
        packaged_artifacts=tuple(sorted(verified_artifacts)),
        complete=complete,
        raw_value_leakage_detected=raw_value_leakage_detected,
        required_human_approval=True,
    )


def _validate_inputs(source_dir, output_root, package_id, input_dir):
    if not source_dir.exists() or not source_dir.is_dir():
        raise ValueError("runtime_artifact_dir is missing")
    if not output_root.exists() or not output_root.is_dir():
        raise ValueError("output_root_dir is missing")
    validate_job_id(package_id)
    if input_dir is not None and _path_is_inside(output_root, Path(input_dir)):
        raise ValueError("output_root_dir must be outside input_dir")
    if _path_is_inside(output_root, source_dir):
        raise ValueError("output_root_dir must be outside runtime_artifact_dir")


def _path_is_inside(candidate_path, root_path):
    resolved_candidate = Path(candidate_path).resolve(strict=True)
    resolved_root = Path(root_path).resolve(strict=True)
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError:
        return False
    return True


def _copy_without_overwrite(source_path, target_path):
    _require_no_overwrite(target_path)
    shutil.copy2(source_path, target_path)


def _require_no_overwrite(path):
    if Path(path).exists():
        raise ValueError("runtime delivery target already exists")


def _artifact_record(artifact_name, source_path, package_path):
    output_category, sensitivity = _ARTIFACT_POLICIES[artifact_name]
    return {
        "artifact_name": artifact_name,
        "file_name": package_path.name,
        "source_path": source_path.as_posix(),
        "package_path": package_path.as_posix(),
        "sha256": sha256_file(package_path),
        "output_category": output_category,
        "sensitivity_classification": sensitivity,
        "delivery_policy_allowed": output_category in _DELIVERY_POLICY[
            "allowed_output_categories"
        ],
    }


def _copy_generated_xlsx_output(source_dir, package_dir):
    manifest_path = source_dir / "xlsx_output_manifest.json"
    if not manifest_path.exists():
        return None
    manifest = _read_json(manifest_path)
    output_workbook_path = Path(str(manifest.get("output_workbook_path", "")))
    if not output_workbook_path.exists() or not output_workbook_path.is_file():
        return None
    target_path = package_dir / output_workbook_path.name
    _copy_without_overwrite(output_workbook_path, target_path)
    return _artifact_record(
        "generated_output_xlsx",
        output_workbook_path,
        target_path,
    )


def _generated_output_xlsx_hash(artifact_records):
    for artifact in artifact_records:
        if artifact["artifact_name"] == "generated_output_xlsx":
            return artifact["sha256"]
    return None


def _provenance_references(source_dir):
    manifest_path = source_dir / "xlsx_output_manifest.json"
    if not manifest_path.exists():
        return {}
    manifest = _read_json(manifest_path)
    references = {}
    for field_name in (
        "input_sha256",
        "plan_sha256",
        "approval_sha256",
        "xlsx_inspection_sha256",
        "output_workbook_sha256",
    ):
        if field_name in manifest:
            references[field_name] = manifest[field_name]
    return references


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _artifact_hashes_from_records(artifact_records):
    return {
        artifact["artifact_name"]: artifact["sha256"]
        for artifact in artifact_records
    }


def _enforce_delivery_policy(artifact_records):
    failures = []
    for artifact in artifact_records:
        output_category = artifact.get("output_category")
        if (
            output_category == "raw_derived"
            and not _DELIVERY_POLICY["raw_derived_allowed"]
        ):
            failures.append(artifact["artifact_name"] + ":raw_derived")
        if output_category not in _DELIVERY_POLICY["allowed_output_categories"]:
            failures.append(artifact["artifact_name"] + ":output_category")
        if artifact.get("delivery_policy_allowed") is not True:
            failures.append(artifact["artifact_name"] + ":delivery_policy_allowed")
    if failures:
        raise ValueError(
            "runtime delivery policy rejected artifacts: " + ",".join(failures)
        )


def _validate_manifest_shape(manifest):
    if not isinstance(manifest, dict):
        raise ValueError("runtime delivery manifest is malformed")
    if manifest.get("manifest_type") != (
        "personal_ai_execution_os_v2_runtime_delivery_manifest"
    ):
        raise ValueError("runtime delivery manifest type mismatch")
    if manifest.get("authority") != "non_authority":
        raise ValueError("runtime delivery manifest authority mismatch")
    if manifest.get("required_human_approval") is not True:
        raise ValueError("runtime delivery manifest must require human approval")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list):
        raise ValueError("runtime delivery manifest artifacts malformed")
    artifact_hashes = manifest.get("artifact_hashes")
    if not isinstance(artifact_hashes, dict):
        raise ValueError("runtime delivery manifest artifact_hashes malformed")
    artifact_order = manifest.get("artifact_order")
    if not isinstance(artifact_order, list):
        raise ValueError("runtime delivery manifest artifact_order malformed")
    if artifact_order != sorted(artifact_order):
        raise ValueError(
            "runtime delivery manifest artifact_order is not deterministic"
        )
    if artifact_order != [artifact.get("artifact_name") for artifact in artifacts]:
        raise ValueError("runtime delivery manifest artifact_order mismatch")
    delivery_policy = manifest.get("delivery_policy")
    if not isinstance(delivery_policy, dict):
        raise ValueError("runtime delivery manifest delivery_policy malformed")
    package_replay = manifest.get("package_replay")
    if not isinstance(package_replay, dict):
        raise ValueError("runtime delivery manifest package_replay malformed")
    if not isinstance(package_replay.get("artifact_set_sha256"), str):
        raise ValueError("runtime delivery manifest package_replay malformed")
    for artifact in artifacts:
        _validate_artifact_record_shape(artifact, artifact_hashes, delivery_policy)


def _validate_artifact_record_shape(artifact, artifact_hashes, delivery_policy):
    if not isinstance(artifact, dict):
        raise ValueError("runtime delivery manifest artifact record malformed")
    for field_name in (
        "artifact_name",
        "file_name",
        "source_path",
        "package_path",
        "sha256",
        "output_category",
        "sensitivity_classification",
    ):
        if not isinstance(artifact.get(field_name), str) or not artifact[field_name]:
            raise ValueError("runtime delivery manifest artifact record malformed")
    if artifact.get("delivery_policy_allowed") is not True:
        raise ValueError("runtime delivery manifest artifact policy flag mismatch")
    if artifact_hashes.get(artifact["artifact_name"]) != artifact["sha256"]:
        raise ValueError("runtime delivery manifest artifact hash index mismatch")
    allowed_categories = delivery_policy.get("allowed_output_categories")
    if not isinstance(allowed_categories, list):
        raise ValueError("runtime delivery manifest delivery_policy malformed")
    if artifact["output_category"] not in (
        "metadata_only",
        "derived_data",
        "raw_derived",
    ):
        raise ValueError("runtime delivery manifest artifact category malformed")


def _policy_failures(manifest):
    failures = []
    policy = manifest.get("delivery_policy", {})
    allowed_categories = policy.get("allowed_output_categories", [])
    raw_derived_allowed = policy.get("raw_derived_allowed") is True
    for artifact in manifest.get("artifacts", []):
        output_category = artifact["output_category"]
        if output_category == "raw_derived" and not raw_derived_allowed:
            failures.append(artifact["artifact_name"] + ":raw_derived")
        if output_category not in allowed_categories:
            failures.append(artifact["artifact_name"] + ":output_category")
        if artifact.get("delivery_policy_allowed") is not True:
            failures.append(artifact["artifact_name"] + ":delivery_policy_allowed")
    return failures


def _package_replay_verified(manifest, verified_artifact_hashes):
    expected_hashes = manifest.get("artifact_hashes", {})
    if expected_hashes != verified_artifact_hashes:
        return False
    package_replay = manifest.get("package_replay", {})
    return package_replay.get("artifact_set_sha256") == sha256_canonical_json(
        expected_hashes
    )


def _raw_value_leakage_detected(package_dir, raw_sentinel_values):
    sentinels = [
        value
        for value in (*_DEFAULT_FORBIDDEN_LEAKAGE_TOKENS, *raw_sentinel_values)
        if isinstance(value, str) and value
    ]
    if not sentinels:
        return False
    for path in sorted(Path(package_dir).iterdir()):
        suffix = path.suffix.lower()
        if suffix in _TEXT_LEAKAGE_SUFFIXES and _text_artifact_leaks(path, sentinels):
            return True
        if suffix == ".xlsx" and _xlsx_artifact_leaks(path, sentinels):
            return True
    return False


def _text_artifact_leaks(path, sentinels):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return True
    return any(sentinel in text for sentinel in sentinels)


def _xlsx_artifact_leaks(path, sentinels):
    return xlsx_artifact_contains_sentinel(
        path,
        sentinels,
        max_rows=_XLSX_LEAKAGE_MAX_ROWS,
        max_columns=_XLSX_LEAKAGE_MAX_COLUMNS,
    )
