"""Keyring contract metadata only. No keyring access is performed."""

from __future__ import annotations

from typing import Mapping

from .secret_ref import validate_secret_ref

__all__ = ["validate_keyring_contract"]


def validate_keyring_contract(metadata: Mapping[str, object]) -> tuple[str, ...]:
    failures = list(validate_secret_ref(metadata))
    if metadata.get("keyring_access_performed") is True:
        failures.append("keyring_access_forbidden")
    if metadata.get("kms_runtime") is True or metadata.get("encryption_runtime") is True:
        failures.append("kms_or_encryption_runtime_forbidden")
    return tuple(sorted(set(failures)))
