"""Runtime delivery package builder for Personal AI Execution OS v2."""

from dataclasses import dataclass
from pathlib import Path
import json
import shutil

from kernel.personal_ai.hash_utils import sha256_file
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
)


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
    provenance_chain_references = _provenance_references(source_dir)
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
    artifacts = manifest.get("artifacts", [])
    verified_artifacts = []
    missing_artifacts = []
    hash_mismatches = []
    if not isinstance(artifacts, list):
        raise ValueError("runtime delivery manifest artifacts malformed")
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

    raw_value_leakage_detected = _raw_value_leakage_detected(package_path)
    complete = (
        not missing_artifacts
        and not hash_mismatches
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
    return {
        "artifact_name": artifact_name,
        "file_name": package_path.name,
        "source_path": source_path.as_posix(),
        "package_path": package_path.as_posix(),
        "sha256": sha256_file(package_path),
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


def _raw_value_leakage_detected(package_dir):
    for path in sorted(Path(package_dir).iterdir()):
        if path.suffix.lower() not in (".json", ".md"):
            continue
        text = path.read_text(encoding="utf-8")
        if "RAW_HEADER_SECRET" in text or "RAW_CELL_SECRET" in text:
            return True
    return False
