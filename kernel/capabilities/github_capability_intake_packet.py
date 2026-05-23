"""Local-first GitHub capability intake packet builder.

This module intentionally performs metadata intake only. It never searches
GitHub, clones repositories, runs git, installs dependencies, imports
candidate code, or executes third-party code.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import os
import re

from kernel.personal_ai.hash_utils import sha256_file

__all__ = [
    "GITHUB_CAPABILITY_INTAKE_PACKET_FILE",
    "GITHUB_CAPABILITY_INTAKE_PACKET_MANIFEST_FILE",
    "GITHUB_CAPABILITY_INTAKE_PACKET_SUMMARY_FILE",
    "GITHUB_CAPABILITY_INTAKE_PACKET_CHECKLIST_FILE",
    "GITHUB_CAPABILITY_INTAKE_ARTIFACT_INDEX_FILE",
    "GITHUB_CAPABILITY_INTAKE_ARTIFACT_INDEX_MANIFEST_FILE",
    "NO_SCOPE_FALSE_FIELDS",
    "GitHubCapabilityIntakePacketResult",
    "build_github_capability_intake_packet",
]


GITHUB_CAPABILITY_INTAKE_PACKET_FILE = "github_capability_intake_packet.json"
GITHUB_CAPABILITY_INTAKE_PACKET_MANIFEST_FILE = (
    "github_capability_intake_packet_manifest.json"
)
GITHUB_CAPABILITY_INTAKE_PACKET_SUMMARY_FILE = (
    "github_capability_intake_packet_summary.md"
)
GITHUB_CAPABILITY_INTAKE_PACKET_CHECKLIST_FILE = (
    "github_capability_intake_packet_checklist.md"
)
GITHUB_CAPABILITY_INTAKE_ARTIFACT_INDEX_FILE = "artifact_index.json"
GITHUB_CAPABILITY_INTAKE_ARTIFACT_INDEX_MANIFEST_FILE = (
    "artifact_index_manifest.json"
)

_INTAKE_TYPE = "github_capability_intake_packet_lite_v1"
_MANIFEST_TYPE = "github_capability_intake_packet_lite_manifest_v1"
_ARTIFACT_INDEX_TYPE = "github_capability_intake_packet_lite_artifact_index_v1"
_ARTIFACT_INDEX_MANIFEST_TYPE = (
    "github_capability_intake_packet_lite_artifact_index_manifest_v1"
)
_AUTHORITY = "non_authority_external_capability_intake_record"
_EXECUTION_CAPABILITY = "github_capability_intake_packet_only"
_READY_STATUS = "github_capability_intake_packet_ready"
_BLOCKED_STATUS = "github_capability_intake_packet_blocked"
_INTAKE_DECISION = "submit_github_capability_for_human_review"
_NEXT_ALLOWED_ACTION = "select_candidate_for_bounded_sandbox_smoke"

_OUTPUT_FILES = (
    GITHUB_CAPABILITY_INTAKE_PACKET_FILE,
    GITHUB_CAPABILITY_INTAKE_PACKET_MANIFEST_FILE,
    GITHUB_CAPABILITY_INTAKE_PACKET_SUMMARY_FILE,
    GITHUB_CAPABILITY_INTAKE_PACKET_CHECKLIST_FILE,
    GITHUB_CAPABILITY_INTAKE_ARTIFACT_INDEX_FILE,
    GITHUB_CAPABILITY_INTAKE_ARTIFACT_INDEX_MANIFEST_FILE,
)

_INTAKE_ARTIFACTS = (
    ("github_capability_intake_packet", GITHUB_CAPABILITY_INTAKE_PACKET_FILE),
    (
        "github_capability_intake_packet_manifest",
        GITHUB_CAPABILITY_INTAKE_PACKET_MANIFEST_FILE,
    ),
    (
        "github_capability_intake_packet_summary",
        GITHUB_CAPABILITY_INTAKE_PACKET_SUMMARY_FILE,
    ),
    (
        "github_capability_intake_packet_checklist",
        GITHUB_CAPABILITY_INTAKE_PACKET_CHECKLIST_FILE,
    ),
)

_SOURCE_ORIGINS = {
    "manual",
    "user_supplied",
    "web_research",
    "file_library",
    "prior_chat",
}

_INTENDED_USES = {
    "worker_adapter",
    "reference_pattern",
    "source_library",
    "local_tool",
    "mcp_connector",
    "browser_automation",
    "desktop_control",
    "asset_pipeline",
    "evaluation_target",
}

_CAPABILITY_DOMAINS = {
    "ai_agent_orchestration",
    "desktop_control",
    "browser_automation",
    "file_system_indexing",
    "code_audit",
    "local_job_queue",
    "artifact_store",
    "model_router",
    "mcp_adapter",
    "github_automation",
    "terminal_automation",
    "vfx_pipeline",
    "comfyui_workflow",
    "houdini_pipeline",
    "blender_pipeline",
    "unreal_pipeline",
    "data_pipeline",
    "observability",
    "security_sandboxing",
    "accessibility_console",
}

_REQUIRED_STRING_FIELDS = (
    "candidate_id",
    "candidate_name",
    "repo_url",
    "repo_full_name",
    "user_value_hypothesis",
    "integration_hypothesis",
)

_DECLARED_LIST_FIELDS = (
    "declared_runtime_languages",
    "declared_external_services",
    "declared_install_commands",
    "declared_run_commands",
    "declared_network_requirements",
    "declared_secret_requirements",
    "declared_file_system_permissions",
    "declared_risks",
)

_ROOT_ALLOWLIST = (
    "README",
    "README.md",
    "README.rst",
    "LICENSE",
    "LICENSE.md",
    "COPYING",
    "SECURITY.md",
    "pyproject.toml",
    "package.json",
    "requirements.txt",
    "Cargo.toml",
    "go.mod",
    "Dockerfile",
    "docker-compose.yml",
)

_MAX_EVIDENCE_FILES = 20
_MAX_BYTES_PER_EVIDENCE_FILE = 262144
_MAX_TOTAL_EVIDENCE_BYTES = 1048576
_MAX_STRING_LENGTH = 10000
_MAX_LIST_ITEMS = 100
_REPO_FULL_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

NO_SCOPE_FALSE_FIELDS: dict[str, bool] = {
    "network_access_performed": False,
    "github_network_search_performed": False,
    "git_clone_performed": False,
    "git_command_performed": False,
    "dependency_installation_performed": False,
    "third_party_code_execution_performed": False,
    "candidate_code_imported": False,
    "candidate_repo_mutation_performed": False,
    "candidate_repo_write_performed": False,
    "candidate_repo_delete_performed": False,
    "candidate_repo_move_performed": False,
    "candidate_repo_rename_performed": False,
    "candidate_repo_recursive_scan_performed": False,
    "candidate_repo_unbounded_read_performed": False,
    "candidate_repo_symlink_followed": False,
    "model_api_called": False,
    "external_runtime_invoked": False,
    "secret_access_performed": False,
    "adapter_generated": False,
    "adapter_registered": False,
    "auto_adoption_performed": False,
    "production_promotion_granted": False,
    "automatic_approval_performed": False,
    "autonomous_execution_performed": False,
}

_DISALLOWED_ACTIONS = (
    "search_github",
    "network_fetch",
    "git_clone",
    "git_command",
    "dependency_installation",
    "third_party_code_execution",
    "candidate_code_import",
    "adapter_generation",
    "adapter_registration",
    "candidate_repo_mutation",
    "candidate_repo_write",
    "candidate_repo_delete",
    "candidate_repo_move",
    "candidate_repo_rename",
    "candidate_repo_recursive_scan",
    "candidate_repo_unbounded_read",
    "candidate_repo_symlink_follow",
    "model_api_call",
    "secret_access",
    "auto_adoption",
    "production_promotion",
    "automatic_approval",
    "autonomous_execution",
)


@dataclass(frozen=True)
class GitHubCapabilityIntakePacketResult:
    candidate_manifest_path: Path
    output_dir: Path
    packet_path: Path | None
    packet_manifest_path: Path | None
    summary_path: Path | None
    checklist_path: Path | None
    artifact_index_path: Path | None
    artifact_index_manifest_path: Path | None
    complete: bool
    intake_status: str
    payload: dict[str, object]


def build_github_capability_intake_packet(
    candidate_manifest: Path,
    output_dir: Path,
    intake_id: str,
    *,
    candidate_repo_dir: Path | None = None,
    project_id: str | None = None,
    reviewer_id: str | None = None,
    operator_notes: str | None = None,
) -> GitHubCapabilityIntakePacketResult:
    """Build a non-networked GitHub capability intake packet."""

    manifest_path = Path(candidate_manifest)
    output_path = Path(output_dir)
    repo_path = None if candidate_repo_dir is None else Path(candidate_repo_dir)
    paths = _output_paths(output_path)

    preflight_error = _preflight_output_error(output_path, paths)
    if preflight_error is not None:
        return _structured_failure_result(
            manifest_path,
            output_path,
            "preflight_output_dir",
            preflight_error,
            intake_id=intake_id,
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
            candidate_repo_dir=repo_path,
        )

    if not _non_empty_text(intake_id):
        return _structured_failure_result(
            manifest_path,
            output_path,
            "preflight_intake_id",
            "intake_id is missing",
            intake_id=intake_id,
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
            candidate_repo_dir=repo_path,
        )

    manifest_payload, manifest_error = _read_candidate_manifest(manifest_path)
    if manifest_error is not None:
        return _structured_failure_result(
            manifest_path,
            output_path,
            "preflight_candidate_manifest",
            manifest_error,
            intake_id=intake_id,
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
            candidate_repo_dir=repo_path,
        )

    normalized_manifest, validation_error = _validate_candidate_manifest(
        manifest_payload
    )
    if validation_error is not None:
        return _structured_failure_result(
            manifest_path,
            output_path,
            "preflight_candidate_manifest_schema",
            validation_error,
            intake_id=intake_id,
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
            candidate_repo_dir=repo_path,
        )

    repo_error = _candidate_repo_dir_error(repo_path, output_path)
    if repo_error is not None:
        return _structured_failure_result(
            manifest_path,
            output_path,
            "preflight_candidate_repo_dir",
            repo_error,
            intake_id=intake_id,
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
            candidate_repo_dir=repo_path,
        )

    evidence = _collect_local_repo_evidence(repo_path)
    if evidence["unsafe_symlink_detected"]:
        return _structured_failure_result(
            manifest_path,
            output_path,
            "preflight_candidate_repo_evidence_symlink",
            "local repo evidence file must not be a symlink: "
            + str(evidence["unsafe_symlink_path"]),
            intake_id=intake_id,
            project_id=project_id,
            reviewer_id=reviewer_id,
            operator_notes=operator_notes,
            candidate_repo_dir=repo_path,
        )

    candidate_manifest_sha256 = sha256_file(manifest_path)
    packet = _packet_payload(
        normalized_manifest,
        intake_id=intake_id,
        project_id=project_id,
        reviewer_id=reviewer_id,
        operator_notes=operator_notes,
        candidate_manifest_path=manifest_path,
        candidate_manifest_sha256=candidate_manifest_sha256,
        candidate_repo_dir=repo_path,
        evidence=evidence,
    )
    summary = _summary_markdown(packet)
    checklist = _checklist_markdown(packet)

    _write_json_exclusive(paths[GITHUB_CAPABILITY_INTAKE_PACKET_FILE], packet)
    _write_text_exclusive(
        paths[GITHUB_CAPABILITY_INTAKE_PACKET_SUMMARY_FILE],
        summary,
    )
    _write_text_exclusive(
        paths[GITHUB_CAPABILITY_INTAKE_PACKET_CHECKLIST_FILE],
        checklist,
    )
    packet_manifest = _packet_manifest_payload(
        paths=paths,
        packet=packet,
        candidate_manifest_path=manifest_path,
        candidate_manifest_sha256=candidate_manifest_sha256,
    )
    _write_json_exclusive(
        paths[GITHUB_CAPABILITY_INTAKE_PACKET_MANIFEST_FILE],
        packet_manifest,
    )
    artifact_index = _artifact_index_payload(output_path, paths)
    _write_json_exclusive(
        paths[GITHUB_CAPABILITY_INTAKE_ARTIFACT_INDEX_FILE],
        artifact_index,
    )
    artifact_index_manifest = _artifact_index_manifest_payload(
        output_path,
        paths,
        artifact_index,
    )
    _write_json_exclusive(
        paths[GITHUB_CAPABILITY_INTAKE_ARTIFACT_INDEX_MANIFEST_FILE],
        artifact_index_manifest,
    )

    return GitHubCapabilityIntakePacketResult(
        candidate_manifest_path=manifest_path,
        output_dir=output_path,
        packet_path=paths[GITHUB_CAPABILITY_INTAKE_PACKET_FILE],
        packet_manifest_path=paths[GITHUB_CAPABILITY_INTAKE_PACKET_MANIFEST_FILE],
        summary_path=paths[GITHUB_CAPABILITY_INTAKE_PACKET_SUMMARY_FILE],
        checklist_path=paths[GITHUB_CAPABILITY_INTAKE_PACKET_CHECKLIST_FILE],
        artifact_index_path=paths[GITHUB_CAPABILITY_INTAKE_ARTIFACT_INDEX_FILE],
        artifact_index_manifest_path=paths[
            GITHUB_CAPABILITY_INTAKE_ARTIFACT_INDEX_MANIFEST_FILE
        ],
        complete=True,
        intake_status=_READY_STATUS,
        payload=_launcher_payload_from_packet(packet, paths),
    )


def _output_paths(output_path: Path) -> dict[str, Path]:
    return {file_name: output_path / file_name for file_name in _OUTPUT_FILES}


def _preflight_output_error(output_path: Path, paths: dict[str, Path]) -> str | None:
    if output_path.is_symlink():
        return "output_dir must not be a symlink"
    if not output_path.exists():
        return "output_dir is missing"
    if not output_path.is_dir():
        return "output_dir is not a directory"
    for file_name in sorted(paths):
        if os.path.lexists(paths[file_name]):
            return "github capability intake output already exists: " + file_name
    return None


def _read_candidate_manifest(manifest_path: Path) -> tuple[dict[str, object], str | None]:
    if not os.path.lexists(manifest_path):
        return {}, "candidate_manifest is missing"
    if manifest_path.is_symlink():
        return {}, "candidate_manifest must not be a symlink"
    if not manifest_path.is_file():
        return {}, "candidate_manifest must be a regular file"
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        return {}, "candidate_manifest must be a valid JSON object: " + _safe_text(error)
    if not isinstance(payload, dict):
        return {}, "candidate_manifest must be a valid JSON object"
    return payload, None


def _validate_candidate_manifest(
    manifest: dict[str, object],
) -> tuple[dict[str, object], str | None]:
    if manifest.get("candidate_type") != "github_capability_candidate_v1":
        return {}, "candidate_type must be github_capability_candidate_v1"
    normalized: dict[str, object] = {
        "candidate_type": "github_capability_candidate_v1"
    }
    for field_name in _REQUIRED_STRING_FIELDS:
        value, error = _required_text_field(manifest, field_name)
        if error is not None:
            return {}, error
        normalized[field_name] = value
    default_branch = manifest.get("default_branch")
    if default_branch is not None:
        if not _non_empty_text(default_branch):
            return {}, "default_branch must be a non-empty string when present"
        if len(default_branch) > _MAX_STRING_LENGTH:
            return {}, "default_branch is too long"
    normalized["default_branch"] = default_branch

    source_origin = manifest.get("source_origin")
    if source_origin not in _SOURCE_ORIGINS:
        return {}, "source_origin is invalid"
    normalized["source_origin"] = source_origin

    intended_use = manifest.get("intended_use")
    if intended_use not in _INTENDED_USES:
        return {}, "intended_use is invalid"
    normalized["intended_use"] = intended_use

    repo_full_name = str(normalized["repo_full_name"])
    if not _REPO_FULL_NAME_RE.match(repo_full_name):
        return {}, "repo_full_name must be in owner/name format"

    domains = manifest.get("capability_domains")
    if not isinstance(domains, list) or not domains:
        return {}, "capability_domains must be a non-empty list"
    if len(domains) > _MAX_LIST_ITEMS:
        return {}, "capability_domains has too many entries"
    normalized_domains = []
    for domain in domains:
        if not isinstance(domain, str) or not domain:
            return {}, "capability_domains entries must be non-empty strings"
        if domain not in _CAPABILITY_DOMAINS:
            return {}, "capability_domains contains an unsupported domain"
        normalized_domains.append(domain)
    normalized["capability_domains"] = sorted(set(normalized_domains))

    declared_license = manifest.get("declared_license")
    if not _non_empty_text(declared_license):
        return {}, "declared_license must be a non-empty string"
    if len(str(declared_license)) > _MAX_STRING_LENGTH:
        return {}, "declared_license is too long"
    normalized["declared_license"] = declared_license

    for field_name in _DECLARED_LIST_FIELDS:
        values, error = _string_list_field(manifest, field_name)
        if error is not None:
            return {}, error
        normalized[field_name] = values

    evidence_notes = manifest.get("evidence_notes")
    if evidence_notes is not None:
        if not isinstance(evidence_notes, str):
            return {}, "evidence_notes must be a string when present"
        if len(evidence_notes) > _MAX_STRING_LENGTH:
            return {}, "evidence_notes is too long"
    normalized["evidence_notes"] = evidence_notes
    return normalized, None


def _required_text_field(
    manifest: dict[str, object],
    field_name: str,
) -> tuple[str, str | None]:
    value = manifest.get(field_name)
    if not _non_empty_text(value):
        return "", field_name + " must be a non-empty string"
    if len(str(value)) > _MAX_STRING_LENGTH:
        return "", field_name + " is too long"
    return str(value), None


def _string_list_field(
    manifest: dict[str, object],
    field_name: str,
) -> tuple[list[str], str | None]:
    values = manifest.get(field_name)
    if not isinstance(values, list):
        return [], field_name + " must be a list of strings"
    if len(values) > _MAX_LIST_ITEMS:
        return [], field_name + " has too many entries"
    normalized = []
    for value in values:
        if not isinstance(value, str):
            return [], field_name + " entries must be strings"
        if len(value) > _MAX_STRING_LENGTH:
            return [], field_name + " entry is too long"
        normalized.append(value)
    return normalized, None


def _candidate_repo_dir_error(repo_path: Path | None, output_path: Path) -> str | None:
    if repo_path is None:
        return None
    if repo_path.is_symlink():
        return "candidate_repo_dir must not be a symlink"
    if not repo_path.exists():
        return "candidate_repo_dir is missing"
    if not repo_path.is_dir():
        return "candidate_repo_dir is not a directory"
    try:
        repo_resolved = repo_path.resolve(strict=True)
        output_resolved = output_path.resolve(strict=True)
    except OSError as error:
        return "candidate_repo_dir/output_dir overlap check failed: " + _safe_text(error)
    if repo_resolved == output_resolved:
        return "candidate_repo_dir must not equal output_dir"
    if _path_is_inside(output_resolved, repo_resolved):
        return "output_dir must not be inside candidate_repo_dir"
    if _path_is_inside(repo_resolved, output_resolved):
        return "candidate_repo_dir must not be inside output_dir"
    return None


def _collect_local_repo_evidence(repo_path: Path | None) -> dict[str, object]:
    if repo_path is None:
        return {
            "files": [],
            "skipped_files": [],
            "file_count": 0,
            "total_bytes": 0,
            "unsafe_symlink_detected": False,
            "unsafe_symlink_path": None,
        }

    candidates = _evidence_candidates(repo_path)
    files: list[dict[str, object]] = []
    skipped: list[dict[str, object]] = []
    total_bytes = 0
    for relative_path, path in candidates:
        if path.is_symlink():
            return {
                "files": [],
                "skipped_files": [],
                "file_count": 0,
                "total_bytes": 0,
                "unsafe_symlink_detected": True,
                "unsafe_symlink_path": path.as_posix(),
            }
        if not path.is_file():
            skipped.append(_skipped_evidence(path, relative_path, "skipped_not_regular"))
            continue
        if len(files) >= _MAX_EVIDENCE_FILES:
            skipped.append(_skipped_evidence(path, relative_path, "skipped_file_limit"))
            continue
        try:
            size_bytes = path.stat().st_size
        except OSError:
            skipped.append(_skipped_evidence(path, relative_path, "skipped_unreadable"))
            continue
        if size_bytes > _MAX_BYTES_PER_EVIDENCE_FILE:
            skipped.append(
                _skipped_evidence(
                    path,
                    relative_path,
                    "skipped_oversize",
                    size_bytes=size_bytes,
                )
            )
            continue
        if total_bytes + size_bytes > _MAX_TOTAL_EVIDENCE_BYTES:
            skipped.append(
                _skipped_evidence(
                    path,
                    relative_path,
                    "skipped_total_bytes_cap",
                    size_bytes=size_bytes,
                )
            )
            continue
        try:
            data = _read_bounded_bytes(path, _MAX_BYTES_PER_EVIDENCE_FILE)
        except OSError:
            skipped.append(
                _skipped_evidence(
                    path,
                    relative_path,
                    "skipped_unreadable",
                    size_bytes=size_bytes,
                )
            )
            continue
        if len(data) > _MAX_BYTES_PER_EVIDENCE_FILE:
            skipped.append(
                _skipped_evidence(
                    path,
                    relative_path,
                    "skipped_oversize",
                    size_bytes=size_bytes,
                )
            )
            continue
        total_bytes += len(data)
        files.append(
            {
                "relative_path": relative_path,
                "path": path.as_posix(),
                "size_bytes": size_bytes,
                "read_bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "read_status": "read",
                "content_copied": False,
                "raw_content_indexed": False,
            }
        )
    return {
        "files": files,
        "skipped_files": skipped,
        "file_count": len(files),
        "total_bytes": total_bytes,
        "unsafe_symlink_detected": False,
        "unsafe_symlink_path": None,
    }


def _evidence_candidates(repo_path: Path) -> list[tuple[str, Path]]:
    candidates: list[tuple[str, Path]] = []
    for file_name in _ROOT_ALLOWLIST:
        path = repo_path / file_name
        if os.path.lexists(path):
            candidates.append((file_name, path))

    github_dir = repo_path / ".github"
    workflows_dir = github_dir / "workflows"
    if (
        os.path.lexists(workflows_dir)
        and not github_dir.is_symlink()
        and not workflows_dir.is_symlink()
        and workflows_dir.is_dir()
    ):
        for path in sorted(workflows_dir.iterdir(), key=lambda item: item.name):
            if path.suffix in {".yml", ".yaml"} and (
                path.is_symlink() or path.is_file()
            ):
                candidates.append(
                    (path.relative_to(repo_path).as_posix(), path)
                )
    return sorted(candidates, key=lambda item: item[0])


def _read_bounded_bytes(path: Path, max_bytes: int) -> bytes:
    with path.open("rb") as input_file:
        return input_file.read(max_bytes + 1)


def _skipped_evidence(
    path: Path,
    relative_path: str,
    reason: str,
    *,
    size_bytes: int | None = None,
) -> dict[str, object]:
    return {
        "relative_path": relative_path,
        "path": path.as_posix(),
        "reason": reason,
        "size_bytes": size_bytes,
        "content_copied": False,
        "raw_content_indexed": False,
    }


def _packet_payload(
    manifest: dict[str, object],
    *,
    intake_id: str,
    project_id: str | None,
    reviewer_id: str | None,
    operator_notes: str | None,
    candidate_manifest_path: Path,
    candidate_manifest_sha256: str,
    candidate_repo_dir: Path | None,
    evidence: dict[str, object],
) -> dict[str, object]:
    risks = _risk_fields(manifest)
    evidence_notes = manifest.get("evidence_notes")
    return {
        "intake_type": _INTAKE_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "intake_id": intake_id,
        "project_id": project_id,
        "reviewer_id": reviewer_id,
        "operator_notes_present": _non_empty_text(operator_notes),
        "operator_notes": operator_notes,
        "candidate_manifest_path": candidate_manifest_path.as_posix(),
        "candidate_manifest_sha256": candidate_manifest_sha256,
        "candidate_repo_dir": None
        if candidate_repo_dir is None
        else candidate_repo_dir.as_posix(),
        "candidate_repo_dir_provided": candidate_repo_dir is not None,
        "candidate_type": manifest["candidate_type"],
        "candidate_id": manifest["candidate_id"],
        "candidate_name": manifest["candidate_name"],
        "repo_url": manifest["repo_url"],
        "repo_full_name": manifest["repo_full_name"],
        "default_branch": manifest["default_branch"],
        "source_origin": manifest["source_origin"],
        "intended_use": manifest["intended_use"],
        "capability_domains": list(manifest["capability_domains"]),
        "declared_license": manifest["declared_license"],
        "declared_runtime_languages": list(manifest["declared_runtime_languages"]),
        "declared_external_services": list(manifest["declared_external_services"]),
        "declared_install_commands": list(manifest["declared_install_commands"]),
        "declared_run_commands": list(manifest["declared_run_commands"]),
        "declared_network_requirements": list(
            manifest["declared_network_requirements"]
        ),
        "declared_secret_requirements": list(
            manifest["declared_secret_requirements"]
        ),
        "declared_file_system_permissions": list(
            manifest["declared_file_system_permissions"]
        ),
        "declared_risks": list(manifest["declared_risks"]),
        "user_value_hypothesis": manifest["user_value_hypothesis"],
        "integration_hypothesis": manifest["integration_hypothesis"],
        "evidence_notes_present": _non_empty_text(evidence_notes),
        "evidence_notes": evidence_notes,
        "local_repo_evidence_files": list(evidence["files"]),
        "local_repo_evidence_file_count": evidence["file_count"],
        "local_repo_evidence_total_bytes": evidence["total_bytes"],
        "local_repo_evidence_skipped_files": list(evidence["skipped_files"]),
        "local_repo_symlink_evidence_detected": False,
        "license_review_required": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        "adapter_generation_allowed": False,
        "auto_adoption_allowed": False,
        "third_party_code_execution_allowed": False,
        "dependency_installation_allowed": False,
        "network_fetch_allowed": False,
        "clone_allowed": False,
        "model_api_allowed": False,
        "secret_access_allowed": False,
        "file_system_write_to_candidate_repo_allowed": False,
        "intake_status": _READY_STATUS,
        "intake_decision": _INTAKE_DECISION,
        "next_allowed_action": _NEXT_ALLOWED_ACTION,
        "required_human_approval": True,
        "required_human_review": True,
        "deterministic_ordering": True,
        "disallowed_actions": list(_DISALLOWED_ACTIONS),
        **risks,
        **dict(NO_SCOPE_FALSE_FIELDS),
    }


def _risk_fields(manifest: dict[str, object]) -> dict[str, str]:
    return {
        "declared_network_risk": "network_required"
        if manifest["declared_network_requirements"]
        else "none_declared",
        "declared_secret_risk": "secrets_required"
        if manifest["declared_secret_requirements"]
        else "none_declared",
        "declared_filesystem_risk": "filesystem_permissions_required"
        if manifest["declared_file_system_permissions"]
        else "none_declared",
        "declared_execution_risk": "run_commands_declared"
        if manifest["declared_run_commands"]
        else "no_run_commands_declared",
        "declared_installation_risk": "install_commands_declared"
        if manifest["declared_install_commands"]
        else "no_install_commands_declared",
        "declared_license_risk": "license_unknown_requires_review"
        if str(manifest["declared_license"]).lower() == "unknown"
        else "license_declared_requires_review",
    }


def _packet_manifest_payload(
    *,
    paths: dict[str, Path],
    packet: dict[str, object],
    candidate_manifest_path: Path,
    candidate_manifest_sha256: str,
) -> dict[str, object]:
    packet_path = paths[GITHUB_CAPABILITY_INTAKE_PACKET_FILE]
    summary_path = paths[GITHUB_CAPABILITY_INTAKE_PACKET_SUMMARY_FILE]
    checklist_path = paths[GITHUB_CAPABILITY_INTAKE_PACKET_CHECKLIST_FILE]
    return {
        "manifest_type": _MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "intake_id": packet["intake_id"],
        "candidate_id": packet["candidate_id"],
        "repo_full_name": packet["repo_full_name"],
        "candidate_manifest_path": candidate_manifest_path.as_posix(),
        "candidate_manifest_sha256": candidate_manifest_sha256,
        "packet_path": packet_path.as_posix(),
        "packet_sha256": sha256_file(packet_path),
        "summary_path": summary_path.as_posix(),
        "summary_sha256": sha256_file(summary_path),
        "checklist_path": checklist_path.as_posix(),
        "checklist_sha256": sha256_file(checklist_path),
        "intake_status": packet["intake_status"],
        "intake_decision": packet["intake_decision"],
        "next_allowed_action": packet["next_allowed_action"],
        "candidate_repo_dir": packet["candidate_repo_dir"],
        "candidate_repo_dir_provided": packet["candidate_repo_dir_provided"],
        "local_repo_evidence_file_count": packet["local_repo_evidence_file_count"],
        "local_repo_evidence_total_bytes": packet["local_repo_evidence_total_bytes"],
        "license_review_required": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        "adapter_generation_allowed": False,
        "auto_adoption_allowed": False,
        "required_human_approval": True,
        "required_human_review": True,
        "deterministic_ordering": True,
        **dict(NO_SCOPE_FALSE_FIELDS),
    }


def _artifact_index_payload(
    output_path: Path,
    paths: dict[str, Path],
) -> dict[str, object]:
    entries = [
        _generated_artifact_entry(output_path, role, paths[file_name])
        for role, file_name in _INTAKE_ARTIFACTS
    ]
    return {
        "index_type": _ARTIFACT_INDEX_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "job_dir": output_path.as_posix(),
        "artifact_index_strategy": "explicit_github_capability_intake_artifacts_only",
        "indexed_artifacts": len(entries),
        "entries": entries,
        "candidate_repo_evidence_files_indexed": False,
        "content_indexed": False,
        "raw_content_copied": False,
        "required_human_approval": True,
        "required_human_review": True,
        "next_allowed_action": _NEXT_ALLOWED_ACTION,
        **dict(NO_SCOPE_FALSE_FIELDS),
    }


def _artifact_index_manifest_payload(
    output_path: Path,
    paths: dict[str, Path],
    artifact_index: dict[str, object],
) -> dict[str, object]:
    index_path = paths[GITHUB_CAPABILITY_INTAKE_ARTIFACT_INDEX_FILE]
    entries = list(artifact_index["entries"])
    return {
        "manifest_type": _ARTIFACT_INDEX_MANIFEST_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "job_dir": output_path.as_posix(),
        "artifact_index_path": index_path.as_posix(),
        "artifact_index_sha256": sha256_file(index_path),
        "indexed_artifacts": len(entries),
        "artifact_roles": {
            str(entry["artifact_role"]): str(entry["path"]) for entry in entries
        },
        "indexed_relative_paths": [
            str(entry["relative_path"]) for entry in entries
        ],
        "candidate_repo_evidence_files_indexed": False,
        "deterministic_ordering": True,
        "content_indexed": False,
        "raw_content_copied": False,
        "required_human_approval": True,
        "required_human_review": True,
        "next_allowed_action": _NEXT_ALLOWED_ACTION,
        **dict(NO_SCOPE_FALSE_FIELDS),
    }


def _generated_artifact_entry(
    root_path: Path,
    role: str,
    path: Path,
) -> dict[str, object]:
    exists = path.exists() and path.is_file() and not path.is_symlink()
    return {
        "artifact_name": role,
        "artifact_role": role,
        "path": path.as_posix(),
        "relative_path": _relative_path(path, root_path),
        "extension": path.suffix,
        "size_bytes": path.stat().st_size if exists else None,
        "sha256": sha256_file(path) if exists else None,
        "content_indexed": False,
        "raw_content_copied": False,
        "candidate_repo_evidence_file": False,
        "required_human_approval": True,
        "required_human_review": True,
    }


def _launcher_payload_from_packet(
    packet: dict[str, object],
    paths: dict[str, Path],
) -> dict[str, object]:
    return {
        "complete": True,
        "github_capability_intake_packet_path": paths[
            GITHUB_CAPABILITY_INTAKE_PACKET_FILE
        ].as_posix(),
        "github_capability_intake_packet_manifest_path": paths[
            GITHUB_CAPABILITY_INTAKE_PACKET_MANIFEST_FILE
        ].as_posix(),
        "github_capability_intake_packet_summary_path": paths[
            GITHUB_CAPABILITY_INTAKE_PACKET_SUMMARY_FILE
        ].as_posix(),
        "github_capability_intake_packet_checklist_path": paths[
            GITHUB_CAPABILITY_INTAKE_PACKET_CHECKLIST_FILE
        ].as_posix(),
        "artifact_index_path": paths[
            GITHUB_CAPABILITY_INTAKE_ARTIFACT_INDEX_FILE
        ].as_posix(),
        "artifact_index_manifest_path": paths[
            GITHUB_CAPABILITY_INTAKE_ARTIFACT_INDEX_MANIFEST_FILE
        ].as_posix(),
        "intake_id": packet["intake_id"],
        "project_id": packet["project_id"],
        "reviewer_id": packet["reviewer_id"],
        "candidate_manifest_path": packet["candidate_manifest_path"],
        "candidate_manifest_sha256": packet["candidate_manifest_sha256"],
        "candidate_repo_dir": packet["candidate_repo_dir"],
        "candidate_repo_dir_provided": packet["candidate_repo_dir_provided"],
        "candidate_id": packet["candidate_id"],
        "candidate_name": packet["candidate_name"],
        "repo_full_name": packet["repo_full_name"],
        "intended_use": packet["intended_use"],
        "capability_domains": list(packet["capability_domains"]),
        "local_repo_evidence_file_count": packet["local_repo_evidence_file_count"],
        "local_repo_evidence_total_bytes": packet["local_repo_evidence_total_bytes"],
        "local_repo_symlink_evidence_detected": packet[
            "local_repo_symlink_evidence_detected"
        ],
        "declared_network_risk": packet["declared_network_risk"],
        "declared_secret_risk": packet["declared_secret_risk"],
        "declared_filesystem_risk": packet["declared_filesystem_risk"],
        "declared_execution_risk": packet["declared_execution_risk"],
        "declared_installation_risk": packet["declared_installation_risk"],
        "declared_license_risk": packet["declared_license_risk"],
        "license_review_required": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        "adapter_generation_allowed": False,
        "auto_adoption_allowed": False,
        "intake_status": packet["intake_status"],
        "intake_decision": packet["intake_decision"],
        "next_allowed_action": packet["next_allowed_action"],
        "required_human_approval": True,
        "required_human_review": True,
        **dict(NO_SCOPE_FALSE_FIELDS),
    }


def _structured_failure_result(
    manifest_path: Path,
    output_path: Path,
    failure_stage: str,
    error_message: str,
    *,
    intake_id: str,
    project_id: str | None,
    reviewer_id: str | None,
    operator_notes: str | None,
    candidate_repo_dir: Path | None,
) -> GitHubCapabilityIntakePacketResult:
    payload = {
        "complete": False,
        "intake_type": _INTAKE_TYPE,
        "authority": _AUTHORITY,
        "execution_capability": _EXECUTION_CAPABILITY,
        "intake_id": intake_id,
        "project_id": project_id,
        "reviewer_id": reviewer_id,
        "operator_notes_present": _non_empty_text(operator_notes),
        "candidate_manifest_path": manifest_path.as_posix(),
        "candidate_manifest_sha256": None,
        "candidate_repo_dir": None
        if candidate_repo_dir is None
        else candidate_repo_dir.as_posix(),
        "candidate_repo_dir_provided": candidate_repo_dir is not None,
        "intake_status": _BLOCKED_STATUS,
        "intake_decision": "fix_github_capability_intake_packet_preflight",
        "next_allowed_action": "fix_github_capability_intake_packet_preflight_and_retry",
        "failure_stage": failure_stage,
        "error_type": "ValueError",
        "error_message": _safe_text(error_message),
        "artifacts_written": False,
        "github_capability_intake_packet_path": None,
        "github_capability_intake_packet_manifest_path": None,
        "github_capability_intake_packet_summary_path": None,
        "github_capability_intake_packet_checklist_path": None,
        "artifact_index_path": None,
        "artifact_index_manifest_path": None,
        "local_repo_evidence_file_count": 0,
        "local_repo_evidence_total_bytes": 0,
        "local_repo_evidence_skipped_files": [],
        "local_repo_symlink_evidence_detected": (
            failure_stage == "preflight_candidate_repo_evidence_symlink"
        ),
        "license_review_required": True,
        "security_review_required": True,
        "sandbox_review_required": True,
        "adapter_generation_allowed": False,
        "auto_adoption_allowed": False,
        "required_human_approval": True,
        "required_human_review": True,
        **dict(NO_SCOPE_FALSE_FIELDS),
    }
    return GitHubCapabilityIntakePacketResult(
        candidate_manifest_path=manifest_path,
        output_dir=output_path,
        packet_path=None,
        packet_manifest_path=None,
        summary_path=None,
        checklist_path=None,
        artifact_index_path=None,
        artifact_index_manifest_path=None,
        complete=False,
        intake_status=_BLOCKED_STATUS,
        payload=payload,
    )


def _summary_markdown(packet: dict[str, object]) -> str:
    lines = [
        "# GitHub Capability Intake Packet",
        "",
        "Status: " + str(packet["intake_status"]),
        "Candidate: " + str(packet["candidate_name"]),
        "Repository: " + str(packet["repo_full_name"]),
        "Intended use: " + str(packet["intended_use"]),
        "Capability domains: " + ", ".join(packet["capability_domains"]),
        "Local repo evidence files read: "
        + str(packet["local_repo_evidence_file_count"]),
        "License review required: true",
        "Security review required: true",
        "Sandbox review required: true",
        "Adapter generation allowed: false",
        "Network fetch allowed: false",
        "Clone allowed: false",
        "Third-party code execution allowed: false",
        "Next allowed action: " + str(packet["next_allowed_action"]),
        "",
        "Boundary: local intake packet only; human approval required before any sandbox smoke or adapter planning.",
    ]
    return "\n".join(lines)


def _checklist_markdown(packet: dict[str, object]) -> str:
    lines = [
        "# GitHub Capability Intake Checklist",
        "",
        "- [ ] Confirm candidate identity and repository full name.",
        "- [ ] Review declared license; no license approval is inferred.",
        "- [ ] Review declared services, secrets, install commands, and run commands.",
        "- [ ] Decide whether a bounded sandbox smoke is appropriate.",
        "- [ ] Keep adapter generation disabled until separate human approval.",
        "",
        "Intake decision: " + str(packet["intake_decision"]),
        "Next allowed action: " + str(packet["next_allowed_action"]),
    ]
    return "\n".join(lines)


def _non_empty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _relative_path(path: Path, root_path: Path) -> str | None:
    try:
        return Path(path).resolve(strict=False).relative_to(
            Path(root_path).resolve(strict=False)
        ).as_posix()
    except (OSError, ValueError):
        return None


def _path_is_inside(candidate_path: Path, root_path: Path) -> bool:
    try:
        Path(candidate_path).resolve(strict=False).relative_to(
            Path(root_path).resolve(strict=False)
        )
    except (OSError, ValueError):
        return False
    return True


def _safe_text(value: object) -> str:
    text = " ".join(str(value).split())
    if "Traceback (most recent call last)" in text:
        text = text.split("Traceback (most recent call last)", 1)[0].strip()
    for marker in (
        "SECRET",
        "SENTINEL",
        "TOKEN",
        "PASSWORD",
        "CREDENTIAL",
        "API_KEY",
        "BEARER",
        "COOKIE",
    ):
        if marker in text.upper():
            return "[redacted-sensitive-token]"
    return text[:240] if text else "github capability intake failed"


def _write_json_exclusive(path: Path, payload: dict[str, object]) -> None:
    _write_text_exclusive(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _write_text_exclusive(path: Path, content: str) -> None:
    with Path(path).open("x", encoding="utf-8", newline="\n") as output_file:
        output_file.write(content)
        output_file.flush()
