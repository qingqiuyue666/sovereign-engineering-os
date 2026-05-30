"""Blender adapter contract implementation."""

from __future__ import annotations

from creative.adapters.base.contract import AdapterContract, build_adapter_contract
from creative.adapters.base.result import AdapterResult
from creative.adapters.base.discovery import adapter_discovery_status

ADAPTER_NAME = "blender"
DEFAULT_LEVEL = "LEVEL_2_SMOKE_TEST"

class BlenderAdapter(AdapterContract):
    def __init__(self) -> None:
        super().__init__(name=ADAPTER_NAME, level=DEFAULT_LEVEL, supports_execute=False)

    def detect(self) -> AdapterResult:
        return AdapterResult(ADAPTER_NAME, "detect", str(adapter_discovery_status(ADAPTER_NAME).get("status", "FOUND_BUT_UNTESTED")))

    def dry_run(self, job: dict[str, object]) -> AdapterResult:
        return AdapterResult(
            ADAPTER_NAME,
            "dry_run",
            "DRY_RUN_READY",
            dry_run=True,
            evidence=("background_command_planned",),
            metadata={"job": job, "staged_output_only": True},
        )

def build_adapter() -> BlenderAdapter:
    return BlenderAdapter()

def adapter_contract() -> dict[str, object]:
    return build_adapter_contract(ADAPTER_NAME, DEFAULT_LEVEL).as_dict()
