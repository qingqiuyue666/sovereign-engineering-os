"""Secret reference metadata validation."""

from __future__ import annotations

from typing import Mapping

__all__ = ["validate_secret_ref"]

_REQUIRED = ("key_ref", "secret_ref", "scope", "expiry", "rotation_policy")


def validate_secret_ref(metadata: Mapping[str, object]) -> tuple[str, ...]:
    if not isinstance(metadata, Mapping):
        return ("secret_ref_metadata_must_be_mapping",)
    failures: list[str] = []
    for field in _REQUIRED:
        if not isinstance(metadata.get(field), str) or not metadata.get(field):
            failures.append(f"{field}_required")
    if "secret_value" in metadata or "plaintext" in metadata:
        failures.append("plaintext_secret_value_forbidden")
    return tuple(sorted(set(failures)))
