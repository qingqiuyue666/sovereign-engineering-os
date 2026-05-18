"""Sanitized local runtime failure bundle contract."""

from __future__ import annotations

from dataclasses import dataclass
import re

from kernel.audit.hashchain import digest_payload
from kernel.runtime._strict_validation import strict_digest, strict_nonempty_string

__all__ = [
    "LocalRuntimeFailureBundle",
    "build_local_runtime_failure_bundle",
    "sanitize_exception_type",
    "validate_local_runtime_failure_bundle",
]

_POLICY_VERSION = "local-runtime-failure-bundle-v1"
_TYPE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")


@dataclass(frozen=True)
class LocalRuntimeFailureBundle:
    """File-safe in-memory failure descriptor with no raw failure payloads."""

    failure_code: str
    failure_stage: str
    sanitized_exception_type: str
    input_digest: str
    policy_version: str
    run_id: str
    task_id: str
    content_hash: str

    def deterministic_material(self) -> dict[str, object]:
        return {
            "failure_code": self.failure_code,
            "failure_stage": self.failure_stage,
            "input_digest": self.input_digest,
            "policy_version": self.policy_version,
            "run_id": self.run_id,
            "sanitized_exception_type": self.sanitized_exception_type,
            "task_id": self.task_id,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        return payload


def build_local_runtime_failure_bundle(
    *,
    failure_code: str,
    failure_stage: str,
    input_digest: str,
    run_id: str,
    task_id: str,
    exception: BaseException | None = None,
    exception_type: str | None = None,
    policy_version: str = _POLICY_VERSION,
) -> LocalRuntimeFailureBundle:
    """Build a sanitized failure bundle without exception text or traceback."""

    sanitized_type = sanitize_exception_type(
        exception.__class__.__name__ if exception is not None else exception_type
    )
    for field, value in (
        ("failure_code", failure_code),
        ("failure_stage", failure_stage),
        ("run_id", run_id),
        ("task_id", task_id),
        ("policy_version", policy_version),
    ):
        if not strict_nonempty_string(value):
            raise ValueError(f"{field}_must_be_nonempty_string")
    if not strict_digest(input_digest):
        raise ValueError("input_digest_must_be_valid_digest")

    material = {
        "failure_code": failure_code,
        "failure_stage": failure_stage,
        "input_digest": input_digest,
        "policy_version": policy_version,
        "run_id": run_id,
        "sanitized_exception_type": sanitized_type,
        "task_id": task_id,
    }
    return LocalRuntimeFailureBundle(content_hash=digest_payload(material), **material)


def sanitize_exception_type(value: str | None) -> str:
    """Return a class-name-only exception descriptor."""

    if value is None:
        return "None"
    if not isinstance(value, str):
        return "SanitizedException"
    candidate = value.rsplit(".", 1)[-1].strip()
    if _TYPE_RE.fullmatch(candidate):
        return candidate
    return "SanitizedException"


def validate_local_runtime_failure_bundle(bundle: LocalRuntimeFailureBundle) -> bool:
    """Validate that the bundle hash matches its deterministic material."""

    if not isinstance(bundle, LocalRuntimeFailureBundle):
        return False
    if not strict_digest(bundle.input_digest):
        return False
    for value in (
        bundle.failure_code,
        bundle.failure_stage,
        bundle.sanitized_exception_type,
        bundle.policy_version,
        bundle.run_id,
        bundle.task_id,
    ):
        if not strict_nonempty_string(value):
            return False
    return bundle.content_hash == digest_payload(bundle.deterministic_material())
