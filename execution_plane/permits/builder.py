"""Builder for SEOS execution permits."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
import hashlib
import re

from execution_plane.permits.digest import attach_permit_digest
from execution_plane.runtime.token_policy import default_runtime_policy, normalize_runtime_policy

EXECUTION_PERMIT_SCHEMA_VERSION = "seos_execution_permit_v1"
EXECUTION_POLICY_VERSION = "seos_execution_policy_v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc(value: str) -> datetime:
    text = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def stable_id(prefix: str, *parts: object) -> str:
    text = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16].upper()
    safe_prefix = re.sub(r"[^A-Z0-9_]", "_", prefix.upper()).strip("_")
    return f"{safe_prefix}_{digest}"


def create_execution_permit(
    *,
    task_id: str,
    operator_approval_id: str,
    allowed_adapter: str,
    allowed_action: str,
    allowed_output_root: str | Path,
    allowed_input_roots: Sequence[str | Path] = (),
    created_at: str | None = None,
    expires_at: str | None = None,
    max_runtime_seconds: int = 60,
    max_output_bytes: int = 104_857_600,
    max_files: int = 100,
    required_outputs: Sequence[Mapping[str, str]] | None = None,
    network_allowed: bool = False,
    destructive_action_allowed: bool = False,
    auto_provision: Mapping[str, Any] | None = None,
    concurrency: Mapping[str, Any] | None = None,
    retry: Mapping[str, Any] | None = None,
    patch_repair: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a digest-bound permit from approved task metadata."""

    issued_at = created_at or utc_now()
    if expires_at is None:
        expires_at = (
            parse_utc(issued_at) + timedelta(minutes=10)
        ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    required = list(required_outputs or ({"kind": "manifest", "path": "manifest.json"},))
    output_root = Path(allowed_output_root).as_posix()
    input_roots = [Path(root).as_posix() for root in allowed_input_roots]
    permit_id = stable_id(
        "PERMIT",
        task_id,
        operator_approval_id,
        allowed_adapter,
        allowed_action,
        output_root,
        issued_at,
    )
    runtime_policy = default_runtime_policy()
    for key, value in (
        ("auto_provision", auto_provision),
        ("concurrency", concurrency),
        ("retry", retry),
        ("patch_repair", patch_repair),
    ):
        if value is not None:
            runtime_policy[key].update(dict(value))
    runtime_policy = normalize_runtime_policy(runtime_policy)
    permit = {
        "schema_version": EXECUTION_PERMIT_SCHEMA_VERSION,
        "permit_id": permit_id,
        "task_id": task_id,
        "operator_approval_id": operator_approval_id,
        "created_at": issued_at,
        "expires_at": expires_at,
        "allowed_adapter": allowed_adapter,
        "allowed_action": allowed_action,
        "allowed_input_roots": input_roots,
        "allowed_output_root": output_root,
        "write_scope": "single_output_directory",
        "network_allowed": network_allowed,
        "destructive_action_allowed": destructive_action_allowed,
        "max_runtime_seconds": max_runtime_seconds,
        "max_output_bytes": max_output_bytes,
        "max_files": max_files,
        "required_outputs": required,
        "evidence_required": True,
        "policy_version": EXECUTION_POLICY_VERSION,
        "auto_provision": runtime_policy["auto_provision"],
        "concurrency": runtime_policy["concurrency"],
        "retry": runtime_policy["retry"],
        "patch_repair": runtime_policy["patch_repair"],
    }
    return attach_permit_digest(permit)


def create_permit_from_task_metadata(
    task_metadata: Mapping[str, Any],
    *,
    allowed_adapter: str,
    allowed_action: str,
    allowed_output_root: str | Path,
    allowed_input_roots: Sequence[str | Path] = (),
) -> dict[str, Any]:
    """Build a permit from a minimal approved task metadata object."""

    return create_execution_permit(
        task_id=str(task_metadata.get("task_id", "")),
        operator_approval_id=str(task_metadata.get("operator_approval_id", "")),
        allowed_adapter=allowed_adapter,
        allowed_action=allowed_action,
        allowed_output_root=allowed_output_root,
        allowed_input_roots=allowed_input_roots,
    )
