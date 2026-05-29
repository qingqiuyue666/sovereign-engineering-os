"""Local install/config runnable path for safe first-run operation.

This module owns the local bootstrap contract: a versioned config, a safe
runtime directory layout, dry-run and smoke-run receipts, and a guarded reset
path. It intentionally avoids package installation, subprocess execution,
network access, provider calls, environment reads, and background daemons.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from kernel.install_config.packaging_readiness import build_packaging_readiness_report
from kernel.os_engine.database import (
    DatabasePathError,
    UnsafePayloadError,
    stable_content_hash,
    validate_no_secret_like,
)

__all__ = [
    "DEFAULT_LOCAL_RUNTIME_CONFIG",
    "LOCAL_RUNTIME_CONFIG_VERSION",
    "LocalRuntimePathError",
    "LocalRuntimePathReceipt",
    "LocalRuntimeValidationReport",
    "bootstrap_local_runtime",
    "default_local_runtime_config",
    "render_local_runtime_config",
    "render_local_runtime_receipt",
    "reset_local_runtime",
    "run_local_runtime_smoke",
    "stop_local_runtime",
    "validate_local_runtime_config",
]


LOCAL_RUNTIME_CONFIG_VERSION = 1
LOCAL_RUNTIME_LAYOUT_VERSION = "local-runtime-layout-v1"
LOCAL_RUNTIME_MARKER = "runtime-root-marker-v1.json"
LOCAL_RUNTIME_CONFIG_FILE = "local-runtime-config-v1.json"

_RUNTIME_LAYOUT_DIRS = (
    "config",
    "wal",
    "queues",
    "artifacts",
    "snapshots",
    "receipts",
    "failure_bundles",
    "watchdog",
    "workers",
    "quarantine",
    "backups",
    "logs",
    "release",
)
_RELEASE_ARTIFACT_LAYOUT = (
    "dist/sovereign-engineering-os-{version}.tar.gz",
    "dist/sovereign-engineering-os-{version}-runtime-receipts.json",
    "reports/release/install_config_packaging_runnable_path_v1.json",
    "docs/runbooks/install_config_packaging_runnable_path_v1.md",
)
_MIGRATION_POLICY = {
    "automatic": False,
    "requires_backup": True,
    "requires_operator_receipt": True,
    "unknown_schema": "fail_closed",
}
_ROLLBACK_POLICY = {
    "supported": True,
    "requires_marker": True,
    "requires_operator_receipt": True,
    "preserve_quarantine": True,
}
_ALLOWED_CONFIG_KEYS = frozenset(
    {
        "schema_version",
        "runtime_root",
        "runtime_enabled",
        "default_mode",
        "network_access",
        "provider_execution",
        "background_daemon",
        "layout_version",
        "migration_policy",
        "rollback_policy",
        "release_artifact_layout",
    }
)

DEFAULT_LOCAL_RUNTIME_CONFIG: dict[str, object] = {
    "schema_version": LOCAL_RUNTIME_CONFIG_VERSION,
    "runtime_root": ".seos-runtime",
    "runtime_enabled": False,
    "default_mode": "dry_run",
    "network_access": False,
    "provider_execution": False,
    "background_daemon": False,
    "layout_version": LOCAL_RUNTIME_LAYOUT_VERSION,
    "migration_policy": dict(_MIGRATION_POLICY),
    "rollback_policy": dict(_ROLLBACK_POLICY),
    "release_artifact_layout": list(_RELEASE_ARTIFACT_LAYOUT),
}


class LocalRuntimePathError(ValueError):
    """Raised when the local runtime path contract is malformed."""


@dataclass(frozen=True, slots=True)
class LocalRuntimeValidationReport:
    report_type: str
    accepted: bool
    failure_codes: tuple[str, ...]
    repo_root: str
    runtime_root: str
    config_hash: str
    layout_hash: str
    schema_version: int | None
    layout_version: str
    runtime_enabled: bool
    default_mode: str
    network_access: bool
    provider_execution: bool
    background_daemon: bool
    runtime_layout_dirs: tuple[str, ...]
    runtime_layout_paths: tuple[str, ...]
    migration_policy: dict[str, object]
    rollback_policy: dict[str, object]
    release_artifact_layout: tuple[str, ...]
    packaging_readiness_hash: str

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["failure_codes"] = list(self.failure_codes)
        payload["runtime_layout_dirs"] = list(self.runtime_layout_dirs)
        payload["runtime_layout_paths"] = list(self.runtime_layout_paths)
        payload["release_artifact_layout"] = list(self.release_artifact_layout)
        return dict(sorted(payload.items()))

    @property
    def receipt_hash(self) -> str:
        return stable_content_hash(self.as_dict())


@dataclass(frozen=True, slots=True)
class LocalRuntimePathReceipt:
    report_type: str
    action: str
    accepted: bool
    failure_codes: tuple[str, ...]
    repo_root: str
    runtime_root: str
    config_path: str
    marker_path: str
    config_hash: str
    layout_hash: str
    validation_hash: str
    created_paths: tuple[str, ...]
    existing_paths: tuple[str, ...]
    removed_paths: tuple[str, ...]
    mutation_performed: bool
    dry_run_mode: bool
    smoke_run_mode: bool
    runtime_enabled: bool
    background_daemon_enabled: bool
    network_accessed: bool
    subprocess_spawned: bool
    dependency_install_performed: bool
    provider_execution_performed: bool
    entrypoint_executed: bool
    migration_policy: dict[str, object]
    rollback_policy: dict[str, object]
    release_artifact_layout: tuple[str, ...]
    one_command_bootstrap: str
    smoke_command: str
    stop_command: str
    reset_command: str

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["failure_codes"] = list(self.failure_codes)
        payload["created_paths"] = list(self.created_paths)
        payload["existing_paths"] = list(self.existing_paths)
        payload["removed_paths"] = list(self.removed_paths)
        payload["release_artifact_layout"] = list(self.release_artifact_layout)
        payload["receipt_hash"] = stable_content_hash(
            {
                key: value
                for key, value in payload.items()
                if key != "receipt_hash"
            }
        )
        return dict(sorted(payload.items()))

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))


def default_local_runtime_config(*, runtime_root: str = ".seos-runtime") -> dict[str, object]:
    config = json.loads(json.dumps(DEFAULT_LOCAL_RUNTIME_CONFIG, sort_keys=True))
    config["runtime_root"] = runtime_root
    return config


def render_local_runtime_config(config: Mapping[str, object] | None = None) -> str:
    payload = dict(config or DEFAULT_LOCAL_RUNTIME_CONFIG)
    validate_no_secret_like(payload)
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def render_local_runtime_receipt(receipt: LocalRuntimePathReceipt) -> str:
    if not isinstance(receipt, LocalRuntimePathReceipt):
        raise LocalRuntimePathError("receipt_must_be_local_runtime_path_receipt")
    return json.dumps(receipt.as_dict(), indent=2, sort_keys=True) + "\n"


def validate_local_runtime_config(
    repo_root: Path | str,
    config: Mapping[str, object] | None = None,
) -> LocalRuntimeValidationReport:
    root = _validate_repo_root(Path(repo_root))
    payload = dict(config or DEFAULT_LOCAL_RUNTIME_CONFIG)
    failures: list[str] = []
    try:
        validate_no_secret_like(payload)
    except UnsafePayloadError:
        failures.append("sensitive_config_material")

    unknown_keys = sorted(set(payload) - _ALLOWED_CONFIG_KEYS)
    missing_keys = sorted(_ALLOWED_CONFIG_KEYS - set(payload))
    failures.extend(f"unknown_config_key:{key}" for key in unknown_keys)
    failures.extend(f"missing_config_key:{key}" for key in missing_keys)

    schema_version = payload.get("schema_version")
    if isinstance(schema_version, bool) or not isinstance(schema_version, int):
        failures.append("schema_version_must_be_int")
        schema_value: int | None = None
    else:
        schema_value = schema_version
        if schema_version != LOCAL_RUNTIME_CONFIG_VERSION:
            failures.append("unsupported_config_schema_version")

    runtime_enabled = payload.get("runtime_enabled") is True
    if payload.get("runtime_enabled") is not False:
        failures.append("runtime_must_default_disabled")
    default_mode = str(payload.get("default_mode", ""))
    if default_mode != "dry_run":
        failures.append("default_mode_must_be_dry_run")
    network_access = payload.get("network_access") is True
    provider_execution = payload.get("provider_execution") is True
    background_daemon = payload.get("background_daemon") is True
    if payload.get("network_access") is not False:
        failures.append("network_access_must_be_disabled")
    if payload.get("provider_execution") is not False:
        failures.append("provider_execution_must_be_disabled")
    if payload.get("background_daemon") is not False:
        failures.append("background_daemon_must_be_disabled")

    layout_version = str(payload.get("layout_version", ""))
    if layout_version != LOCAL_RUNTIME_LAYOUT_VERSION:
        failures.append("layout_version_mismatch")

    migration_policy = _mapping(payload.get("migration_policy"))
    rollback_policy = _mapping(payload.get("rollback_policy"))
    if migration_policy != _MIGRATION_POLICY:
        failures.append("migration_policy_mismatch")
    if rollback_policy != _ROLLBACK_POLICY:
        failures.append("rollback_policy_mismatch")

    release_artifact_layout = tuple(
        str(item)
        for item in payload.get("release_artifact_layout", ())
        if isinstance(item, str)
    )
    if release_artifact_layout != _RELEASE_ARTIFACT_LAYOUT:
        failures.append("release_artifact_layout_mismatch")

    runtime_root = root / ".invalid-runtime"
    try:
        runtime_root = _validate_runtime_root(root, payload.get("runtime_root"))
    except (DatabasePathError, LocalRuntimePathError):
        failures.append("runtime_root_path_invalid")

    packaging = build_packaging_readiness_report(root)
    if not packaging.accepted:
        failures.append("packaging_readiness_failed")

    runtime_layout_paths = tuple((runtime_root / name).as_posix() for name in _RUNTIME_LAYOUT_DIRS)
    config_hash = _safe_hash_config(payload)
    layout_hash = stable_content_hash(
        {
            "layout_dirs": list(_RUNTIME_LAYOUT_DIRS),
            "layout_version": LOCAL_RUNTIME_LAYOUT_VERSION,
            "runtime_root": runtime_root.as_posix(),
        }
    )
    return LocalRuntimeValidationReport(
        report_type="install_config_packaging_runnable_path_validation_v1",
        accepted=not failures,
        failure_codes=tuple(sorted(set(failures))),
        repo_root=root.as_posix(),
        runtime_root=runtime_root.as_posix(),
        config_hash=config_hash,
        layout_hash=layout_hash,
        schema_version=schema_value,
        layout_version=layout_version,
        runtime_enabled=runtime_enabled,
        default_mode=default_mode,
        network_access=network_access,
        provider_execution=provider_execution,
        background_daemon=background_daemon,
        runtime_layout_dirs=_RUNTIME_LAYOUT_DIRS,
        runtime_layout_paths=runtime_layout_paths,
        migration_policy=dict(migration_policy),
        rollback_policy=dict(rollback_policy),
        release_artifact_layout=release_artifact_layout,
        packaging_readiness_hash=packaging.config_hash,
    )


def bootstrap_local_runtime(
    repo_root: Path | str,
    config: Mapping[str, object] | None = None,
    *,
    apply: bool = False,
) -> LocalRuntimePathReceipt:
    validation = validate_local_runtime_config(repo_root, config)
    runtime_root = Path(validation.runtime_root)
    config_path = runtime_root / "config" / LOCAL_RUNTIME_CONFIG_FILE
    marker_path = runtime_root / LOCAL_RUNTIME_MARKER
    if not validation.accepted:
        return _receipt(
            action="bootstrap",
            validation=validation,
            config_path=config_path,
            marker_path=marker_path,
            failure_codes=validation.failure_codes,
            dry_run_mode=True,
        )
    if not apply:
        return _receipt(
            action="bootstrap",
            validation=validation,
            config_path=config_path,
            marker_path=marker_path,
            dry_run_mode=True,
        )

    created: list[str] = []
    existing: list[str] = []
    if runtime_root.exists():
        existing.append(runtime_root.as_posix())
    else:
        runtime_root.mkdir(parents=True)
        created.append(runtime_root.as_posix())
    for directory_name in _RUNTIME_LAYOUT_DIRS:
        path = runtime_root / directory_name
        if path.exists():
            existing.append(path.as_posix())
        else:
            path.mkdir(parents=True)
            created.append(path.as_posix())
    config_payload = dict(config or DEFAULT_LOCAL_RUNTIME_CONFIG)
    _safe_write_json(config_path, config_payload)
    _safe_write_json(
        marker_path,
        {
            "layout_hash": validation.layout_hash,
            "layout_version": LOCAL_RUNTIME_LAYOUT_VERSION,
            "repo_root": validation.repo_root,
            "runtime_root": validation.runtime_root,
        },
    )
    receipt = _receipt(
        action="bootstrap",
        validation=validation,
        config_path=config_path,
        marker_path=marker_path,
        created_paths=tuple(created),
        existing_paths=tuple(existing),
        mutation_performed=True,
        dry_run_mode=False,
    )
    _safe_write_json(runtime_root / "receipts" / "bootstrap-receipt-v1.json", receipt.as_dict())
    return receipt


def run_local_runtime_smoke(
    repo_root: Path | str,
    config: Mapping[str, object] | None = None,
    *,
    apply: bool = False,
) -> LocalRuntimePathReceipt:
    validation = validate_local_runtime_config(repo_root, config)
    runtime_root = Path(validation.runtime_root)
    config_path = runtime_root / "config" / LOCAL_RUNTIME_CONFIG_FILE
    marker_path = runtime_root / LOCAL_RUNTIME_MARKER
    failures = list(validation.failure_codes)
    if validation.accepted:
        failures.extend(_runtime_presence_failures(runtime_root, config_path, marker_path))
    receipt = _receipt(
        action="smoke",
        validation=validation,
        config_path=config_path,
        marker_path=marker_path,
        failure_codes=tuple(sorted(set(failures))),
        mutation_performed=False,
        dry_run_mode=not apply,
        smoke_run_mode=True,
    )
    if apply and receipt.accepted:
        _safe_write_json(runtime_root / "receipts" / "smoke-run-receipt-v1.json", receipt.as_dict())
        receipt = _receipt(
            action="smoke",
            validation=validation,
            config_path=config_path,
            marker_path=marker_path,
            existing_paths=tuple(validation.runtime_layout_paths),
            mutation_performed=True,
            dry_run_mode=False,
            smoke_run_mode=True,
        )
        _safe_write_json(runtime_root / "receipts" / "smoke-run-receipt-v1.json", receipt.as_dict())
    return receipt


def stop_local_runtime(
    repo_root: Path | str,
    config: Mapping[str, object] | None = None,
    *,
    apply: bool = False,
) -> LocalRuntimePathReceipt:
    validation = validate_local_runtime_config(repo_root, config)
    runtime_root = Path(validation.runtime_root)
    config_path = runtime_root / "config" / LOCAL_RUNTIME_CONFIG_FILE
    marker_path = runtime_root / LOCAL_RUNTIME_MARKER
    failures = list(validation.failure_codes)
    if validation.accepted:
        failures.extend(_runtime_presence_failures(runtime_root, config_path, marker_path))
    receipt = _receipt(
        action="stop",
        validation=validation,
        config_path=config_path,
        marker_path=marker_path,
        failure_codes=tuple(sorted(set(failures))),
        mutation_performed=False,
        dry_run_mode=not apply,
    )
    if apply and receipt.accepted:
        _safe_write_json(runtime_root / "receipts" / "stop-receipt-v1.json", receipt.as_dict())
        receipt = _receipt(
            action="stop",
            validation=validation,
            config_path=config_path,
            marker_path=marker_path,
            existing_paths=tuple(validation.runtime_layout_paths),
            mutation_performed=True,
            dry_run_mode=False,
        )
        _safe_write_json(runtime_root / "receipts" / "stop-receipt-v1.json", receipt.as_dict())
    return receipt


def reset_local_runtime(
    repo_root: Path | str,
    config: Mapping[str, object] | None = None,
    *,
    apply: bool = False,
) -> LocalRuntimePathReceipt:
    validation = validate_local_runtime_config(repo_root, config)
    runtime_root = Path(validation.runtime_root)
    config_path = runtime_root / "config" / LOCAL_RUNTIME_CONFIG_FILE
    marker_path = runtime_root / LOCAL_RUNTIME_MARKER
    failures = list(validation.failure_codes)
    if validation.accepted:
        if not marker_path.is_file():
            failures.append("runtime_marker_missing")
        elif _read_marker(marker_path).get("layout_hash") != validation.layout_hash:
            failures.append("runtime_marker_layout_hash_mismatch")
    accepted = not failures
    removed = (runtime_root.as_posix(),) if accepted and apply and runtime_root.exists() else ()
    receipt = _receipt(
        action="reset",
        validation=validation,
        config_path=config_path,
        marker_path=marker_path,
        failure_codes=tuple(sorted(set(failures))),
        removed_paths=removed,
        mutation_performed=bool(removed),
        dry_run_mode=not apply,
    )
    if accepted and apply and runtime_root.exists():
        shutil.rmtree(runtime_root)
    return receipt


def _receipt(
    *,
    action: str,
    validation: LocalRuntimeValidationReport,
    config_path: Path,
    marker_path: Path,
    failure_codes: tuple[str, ...] = (),
    created_paths: tuple[str, ...] = (),
    existing_paths: tuple[str, ...] = (),
    removed_paths: tuple[str, ...] = (),
    mutation_performed: bool = False,
    dry_run_mode: bool = False,
    smoke_run_mode: bool = False,
) -> LocalRuntimePathReceipt:
    failures = tuple(sorted(set(failure_codes)))
    return LocalRuntimePathReceipt(
        report_type="install_config_packaging_runnable_path_receipt_v1",
        action=action,
        accepted=validation.accepted and not failures,
        failure_codes=failures,
        repo_root=validation.repo_root,
        runtime_root=validation.runtime_root,
        config_path=config_path.as_posix(),
        marker_path=marker_path.as_posix(),
        config_hash=validation.config_hash,
        layout_hash=validation.layout_hash,
        validation_hash=validation.receipt_hash,
        created_paths=created_paths,
        existing_paths=existing_paths,
        removed_paths=removed_paths,
        mutation_performed=mutation_performed,
        dry_run_mode=dry_run_mode,
        smoke_run_mode=smoke_run_mode,
        runtime_enabled=False,
        background_daemon_enabled=False,
        network_accessed=False,
        subprocess_spawned=False,
        dependency_install_performed=False,
        provider_execution_performed=False,
        entrypoint_executed=False,
        migration_policy=dict(validation.migration_policy),
        rollback_policy=dict(validation.rollback_policy),
        release_artifact_layout=validation.release_artifact_layout,
        one_command_bootstrap="python3 tools/local_runtime_setup.py bootstrap . --apply",
        smoke_command="python3 tools/local_runtime_setup.py smoke . --apply",
        stop_command="python3 tools/local_runtime_setup.py stop . --apply",
        reset_command="python3 tools/local_runtime_setup.py reset . --apply",
    )


def _runtime_presence_failures(runtime_root: Path, config_path: Path, marker_path: Path) -> tuple[str, ...]:
    failures: list[str] = []
    if not runtime_root.is_dir():
        failures.append("runtime_root_missing")
    if not config_path.is_file():
        failures.append("runtime_config_missing")
    if not marker_path.is_file():
        failures.append("runtime_marker_missing")
    for directory_name in _RUNTIME_LAYOUT_DIRS:
        path = runtime_root / directory_name
        if not path.is_dir():
            failures.append(f"runtime_layout_dir_missing:{directory_name}")
    return tuple(failures)


def _safe_write_json(path: Path, payload: Mapping[str, object]) -> None:
    if path.exists() and path.is_symlink():
        raise LocalRuntimePathError("refusing_to_write_symlink")
    if path.parent.exists() and path.parent.is_symlink():
        raise LocalRuntimePathError("refusing_to_write_inside_symlink")
    validate_no_secret_like(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_marker(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(payload) if isinstance(payload, dict) else {}


def _safe_hash_config(payload: Mapping[str, object]) -> str:
    try:
        return stable_content_hash(dict(payload))
    except UnsafePayloadError:
        return stable_content_hash({"config": "rejected"})


def _mapping(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, Mapping) else {}


def _validate_repo_root(repo_root: Path) -> Path:
    raw = repo_root.expanduser()
    if raw.exists() and raw.is_symlink():
        raise DatabasePathError("repo_root_cannot_be_symlink")
    resolved = raw.resolve(strict=False)
    if resolved.exists() and not resolved.is_dir():
        raise DatabasePathError("repo_root_must_be_directory")
    if not (resolved / "pyproject.toml").is_file():
        raise DatabasePathError("repo_root_missing_pyproject")
    return resolved


def _validate_runtime_root(repo_root: Path, runtime_root: object) -> Path:
    if not isinstance(runtime_root, str) or not runtime_root.strip():
        raise LocalRuntimePathError("runtime_root_required")
    raw = Path(runtime_root)
    if raw.is_absolute():
        raise LocalRuntimePathError("runtime_root_must_be_relative")
    if raw == Path(".") or ".." in raw.parts:
        raise LocalRuntimePathError("runtime_root_must_be_child")
    if any(part in {".env", ".env.local", ".envrc"} for part in raw.parts):
        raise LocalRuntimePathError("runtime_root_sensitive_path")
    candidate = repo_root / raw
    for path in _existing_path_chain(repo_root, candidate):
        if path.is_symlink():
            raise LocalRuntimePathError("runtime_root_symlink_rejected")
    resolved = candidate.resolve(strict=False)
    if not resolved.is_relative_to(repo_root):
        raise LocalRuntimePathError("runtime_root_escapes_repo")
    return resolved


def _existing_path_chain(repo_root: Path, candidate: Path) -> tuple[Path, ...]:
    try:
        relative = candidate.relative_to(repo_root)
    except ValueError:
        return ()
    paths: list[Path] = []
    current = repo_root
    for part in relative.parts:
        current = current / part
        if current.exists():
            paths.append(current)
    return tuple(paths)
