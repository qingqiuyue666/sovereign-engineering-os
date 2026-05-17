"""Vault contract metadata only. No secret values are read."""

from __future__ import annotations

from typing import Mapping

from .secret_ref import validate_secret_ref

__all__ = ["validate_vault_contract"]


def validate_vault_contract(metadata: Mapping[str, object]) -> tuple[str, ...]:
    failures = list(validate_secret_ref(metadata))
    if metadata.get("vault_runtime") not in (None, "contract_only"):
        failures.append("real_vault_runtime_forbidden")
    if metadata.get("secret_value_read") is True:
        failures.append("secret_value_read_forbidden")
    return tuple(sorted(set(failures)))
