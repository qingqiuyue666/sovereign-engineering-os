"""Base adapter SDK for SEOS Creative Pipeline V3."""

from creative.adapters.base.contract import AdapterContract, build_adapter_contract
from creative.adapters.base.result import AdapterResult

__all__ = ["AdapterContract", "AdapterResult", "build_adapter_contract"]
