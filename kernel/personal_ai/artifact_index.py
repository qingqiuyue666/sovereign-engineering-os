"""Metadata-only artifact index for Personal AI local job packages."""

from dataclasses import dataclass
from pathlib import Path
import re

from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "ArtifactIndexResult",
    "build_artifact_index",
]

_INDEX_TYPE = "personal_ai_local_v1_artifact_index"
_INDEX_MANIFEST_TYPE = "personal_ai_local_v1_artifact_index_manifest"

_SELF_ARTIFACT_FILES = {
    "artifact_index.json",
    "artifact_index_manifest.json",
    "job_package_validation.json",
}

_ARTIFACT_NAME_OVERRIDES = {
    "spreadsheet_structural_report.md": "spreadsheet_structural_report_markdown",
    "spreadsheet_structural_report.json": "spreadsheet_structural_report_json",
}

_BOUNDARIES = {
    "local_only": True,
    "no_runtime_authority": True,
    "no_execution_capability": True,
    "no_external_tool_control": True,
    "no_network": True,
    "no_api_calls": True,
    "no_subprocess": True,
    "no_adapter_implementation": True,
    "no_input_file_mutation": True,
    "no_input_content_copy": True,
    "no_raw_cell_value_copy": True,
    "no_spreadsheet_output_write": True,
    "no_destructive_actions": True,
}


@dataclass(frozen=True)
class ArtifactIndexResult:
    job_dir: Path
    artifact_index_path: Path
    artifact_index_manifest_path: Path
    indexed_artifacts: int
    artifact_hashes: dict[str, str]


def build_artifact_index(
    job_dir: Path,
    artifact_index_path: Path | None = None,
    artifact_index_manifest_path: Path | None = None,
) -> ArtifactIndexResult:
    job_path = Path(job_dir)
    index_path = (
        job_path / "artifact_index.json"
        if artifact_index_path is None
        else Path(artifact_index_path)
    )
    manifest_path = (
        job_path / "artifact_index_manifest.json"
        if artifact_index_manifest_path is None
        else Path(artifact_index_manifest_path)
    )
    _validate_inputs(job_path, index_path, manifest_path)

    entries = [_artifact_entry(job_path, path) for path in _indexed_paths(job_path)]
    artifact_hashes = {
        entry["artifact_name"]: entry["sha256"]
        for entry in entries
    }
    payload = {
        "index_type": _INDEX_TYPE,
        "authority": "non_authority",
        "execution_capability": "not_introduced",
        "job_dir": job_path.as_posix(),
        "indexed_artifacts": len(entries),
        "entries": entries,
        "content_indexed": False,
        "input_file_contents_copied": False,
        "raw_cell_values_copied": False,
        "input_mutation_performed": False,
        "spreadsheet_output_written": False,
        "boundaries": dict(_BOUNDARIES),
        "next_allowed_action": "human_review_only",
    }
    write_json_atomically(index_path, payload)

    manifest_payload = {
        "manifest_type": _INDEX_MANIFEST_TYPE,
        "authority": "non_authority",
        "execution_capability": "not_introduced",
        "job_dir": job_path.as_posix(),
        "artifact_index_path": index_path.as_posix(),
        "artifact_index_sha256": sha256_file(index_path),
        "indexed_artifacts": len(entries),
        "indexed_relative_paths": [
            entry["relative_path"]
            for entry in entries
        ],
        "artifact_hashes": artifact_hashes,
        "content_indexed": False,
        "input_file_contents_copied": False,
        "raw_cell_values_copied": False,
        "input_mutation_performed": False,
        "spreadsheet_output_written": False,
        "boundaries": dict(_BOUNDARIES),
        "next_allowed_action": "human_review_only",
    }
    write_json_atomically(manifest_path, manifest_payload)

    return ArtifactIndexResult(
        job_dir=job_path,
        artifact_index_path=index_path,
        artifact_index_manifest_path=manifest_path,
        indexed_artifacts=len(entries),
        artifact_hashes=artifact_hashes,
    )


def _validate_inputs(job_path, index_path, manifest_path):
    if not job_path.exists():
        raise ValueError("job_dir is missing")
    if not job_path.is_dir():
        raise ValueError("job_dir is not a directory")
    _require_existing_parent(index_path, "artifact_index_path parent is missing")
    _require_existing_parent(
        manifest_path,
        "artifact_index_manifest_path parent is missing",
    )


def _require_existing_parent(output_path, message):
    parent = Path(output_path).parent
    if not parent.exists() or not parent.is_dir():
        raise ValueError(message)


def _indexed_paths(job_path):
    return [
        path
        for path in sorted(job_path.iterdir(), key=lambda candidate: candidate.name)
        if path.is_file()
        and path.name not in _SELF_ARTIFACT_FILES
        and not path.name.startswith(".")
    ]


def _artifact_entry(job_path, path):
    relative_path = _relative_artifact_path(job_path, path)
    artifact_name = _artifact_name(path.name)
    search_terms = _search_terms(artifact_name, path.name, path.suffix)
    return {
        "artifact_name": artifact_name,
        "relative_path": relative_path,
        "extension": path.suffix,
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "search_terms": search_terms,
        "content_indexed": False,
    }


def _relative_artifact_path(job_path, path):
    try:
        return path.relative_to(job_path).as_posix()
    except ValueError as error:
        raise ValueError("artifact path escapes job_dir") from error


def _artifact_name(file_name):
    if file_name in _ARTIFACT_NAME_OVERRIDES:
        return _ARTIFACT_NAME_OVERRIDES[file_name]
    if file_name.endswith(".jsonl"):
        return file_name[:-6]
    if "." in file_name:
        return file_name.rsplit(".", 1)[0]
    return file_name


def _search_terms(artifact_name, file_name, suffix):
    raw_terms = [artifact_name, file_name, suffix.lstrip(".")]
    raw_terms.extend(re.split(r"[^A-Za-z0-9]+", artifact_name))
    raw_terms.extend(re.split(r"[^A-Za-z0-9]+", file_name))
    return sorted({
        term.lower()
        for term in raw_terms
        if term
    })
