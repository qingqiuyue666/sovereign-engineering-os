"""Bootstrap root integrity verifier.

This module verifies a small root manifest before higher-level policy,
runtime, model, or tool-control surfaces are trusted. It performs only local
filesystem reads, computes deterministic content hashes, and emits a structured
report. It does not execute runtime code, read secrets, access network, repair
files, or mutate the repository during verification.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import contextlib
import hashlib
import json
import os
import tempfile

__all__ = [
    "RootIntegrityResult",
    "compute_git_blob_sha1_for_path",
    "verify_root_integrity",
    "write_bootstrap_integrity_report",
]

_MANIFEST_TYPE = "seos_root_integrity_manifest_v1"
_REPORT_TYPE = "seos_bootstrap_integrity_report_v1"
_SUPPORTED_VERSION = "v1"
_SUPPORTED_HASH_ALGORITHM = "git_blob_sha1"
_DEFAULT_MANIFEST_PATH = Path("governance/root/root_manifest_v1.json")


@dataclass(frozen=True)
class RootIntegrityResult:
    repo_root: Path
    manifest_path: Path
    complete: bool
    trusted_startup_allowed: bool
    seed_recovery_required: bool
    runtime_execution_performed: bool
    network_accessed: bool
    secret_value_read: bool
    report: dict[str, object]


def compute_git_blob_sha1_for_path(path: Path) -> str:
    """Compute the Git blob SHA-1 for a file without invoking git."""

    data = Path(path).read_bytes()
    header = b"blob " + str(len(data)).encode("ascii") + b"\0"
    return hashlib.sha1(header + data).hexdigest()


def verify_root_integrity(
    repo_root: Path | str,
    manifest_path: Path | str | None = None,
) -> RootIntegrityResult:
    """Verify the root manifest against local critical-file content.

    Verification is intentionally narrow and bootstrap-safe: only local reads,
    JSON parsing, path normalization, and content hashing are performed.
    """

    root = Path(repo_root)
    manifest_rel = _DEFAULT_MANIFEST_PATH if manifest_path is None else Path(manifest_path)
    manifest_abs = manifest_rel if manifest_rel.is_absolute() else root / manifest_rel

    failures: list[str] = []
    manifest: Mapping[str, Any] | None = None
    try:
        parsed = json.loads(manifest_abs.read_text(encoding="utf-8"))
    except FileNotFoundError:
        failures.append("root_manifest_missing")
        parsed = None
    except json.JSONDecodeError:
        failures.append("root_manifest_malformed_json")
        parsed = None

    if parsed is not None:
        if not isinstance(parsed, dict):
            failures.append("root_manifest_must_be_object")
        else:
            manifest = parsed

    manifest_version = None
    hash_algorithm = None
    critical_files: object = None

    if manifest is not None:
        if manifest.get("manifest_type") != _MANIFEST_TYPE:
            failures.append("root_manifest_type_mismatch")
        manifest_version = manifest.get("version")
        if manifest_version != _SUPPORTED_VERSION:
            failures.append("root_manifest_version_unsupported")
        hash_algorithm = manifest.get("hash_algorithm")
        if hash_algorithm != _SUPPORTED_HASH_ALGORITHM:
            failures.append("root_manifest_hash_algorithm_unsupported")
        if manifest.get("runtime_execution_performed") is not False:
            failures.append("root_manifest_runtime_execution_flag_must_be_false")
        if manifest.get("network_accessed") is not False:
            failures.append("root_manifest_network_flag_must_be_false")
        if manifest.get("secret_value_read") is not False:
            failures.append("root_manifest_secret_read_flag_must_be_false")
        critical_files = manifest.get("critical_files")

    verified_files: list[dict[str, object]] = []
    if manifest is not None:
        if not isinstance(critical_files, list) or not critical_files:
            failures.append("critical_files_missing_or_empty")
        else:
            seen_paths: set[str] = set()
            for index, entry in enumerate(critical_files):
                entry_label = f"critical_file[{index}]"
                if not isinstance(entry, dict):
                    failures.append(entry_label + "_malformed")
                    continue
                rel_path = entry.get("path")
                expected_hash = entry.get("git_blob_sha1")
                if not isinstance(rel_path, str) or not rel_path:
                    failures.append(entry_label + "_path_missing")
                    continue
                normalized = _normalize_repo_path(rel_path)
                if normalized is None:
                    failures.append("critical_file_path_invalid:" + rel_path)
                    continue
                if normalized in seen_paths:
                    failures.append("critical_file_path_duplicate:" + normalized)
                    continue
                seen_paths.add(normalized)
                if not _is_valid_git_sha1(expected_hash):
                    failures.append("critical_file_hash_invalid:" + normalized)
                    continue
                file_path = root / normalized
                if file_path.is_symlink():
                    failures.append("critical_file_symlink_forbidden:" + normalized)
                    continue
                if not file_path.is_file():
                    failures.append("critical_file_missing:" + normalized)
                    continue
                actual_hash = compute_git_blob_sha1_for_path(file_path)
                hash_matches = actual_hash == expected_hash
                if not hash_matches:
                    failures.append("critical_file_hash_mismatch:" + normalized)
                verified_files.append(
                    {
                        "path": normalized,
                        "expected_git_blob_sha1": expected_hash,
                        "actual_git_blob_sha1": actual_hash,
                        "hash_matches": hash_matches,
                    }
                )

    complete = not failures
    report = {
        "report_type": _REPORT_TYPE,
        "complete": complete,
        "trusted_startup_allowed": complete,
        "seed_recovery_required": not complete,
        "manifest_path": manifest_abs.as_posix(),
        "manifest_type": None if manifest is None else manifest.get("manifest_type"),
        "manifest_version": manifest_version,
        "hash_algorithm": hash_algorithm,
        "critical_file_count": len(critical_files) if isinstance(critical_files, list) else 0,
        "verified_file_count": len(verified_files),
        "verified_files": verified_files,
        "failures": sorted(set(failures)),
        "runtime_execution_performed": False,
        "network_accessed": False,
        "secret_value_read": False,
        "secret_value_persisted": False,
        "file_mutation_performed": False,
        "automatic_repair_performed": False,
        "required_human_approval": True,
        "next_allowed_action": (
            "normal_startup_allowed_after_human_review"
            if complete
            else "read_only_seed_recovery_required"
        ),
    }
    return RootIntegrityResult(
        repo_root=root,
        manifest_path=manifest_abs,
        complete=complete,
        trusted_startup_allowed=complete,
        seed_recovery_required=not complete,
        runtime_execution_performed=False,
        network_accessed=False,
        secret_value_read=False,
        report=report,
    )


def write_bootstrap_integrity_report(
    *,
    repo_root: Path | str,
    output_path: Path | str,
    manifest_path: Path | str | None = None,
) -> RootIntegrityResult:
    """Write a bootstrap integrity report without repairing anything."""

    target = Path(output_path)
    if target.exists():
        raise ValueError("bootstrap integrity report already exists")
    if not target.parent.exists() or not target.parent.is_dir():
        raise ValueError("bootstrap integrity report parent is missing")
    result = verify_root_integrity(repo_root, manifest_path)
    _write_json_atomically(target, result.report)
    return result


def _normalize_repo_path(value: str) -> str | None:
    if value.startswith("/") or "\\" in value:
        return None
    parts = value.split("/")
    if not parts or any(part in ("", ".", "..") for part in parts):
        return None
    return "/".join(parts)


def _is_valid_git_sha1(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 40:
        return False
    return all(character in "0123456789abcdef" for character in value)


def _write_json_atomically(path: Path, payload: Mapping[str, object]) -> None:
    data = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    fd, tmp_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(data)
        os.replace(tmp_name, path)
    except Exception:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp_name)
        raise
