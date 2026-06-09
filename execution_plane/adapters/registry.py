"""Adapter registry for controlled execution-plane dispatch."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from execution_plane.adapters.base import (
    COMFYUI_LOCAL_ADAPTER,
    DAVINCI_RESOLVE_ADAPTER,
    FAKE_DCC_ADAPTER,
    HOUDINI_HYTHON_ADAPTER,
    AdapterContract,
)
from execution_plane.adapters.comfyui_local import ComfyUILocalAdapter
from execution_plane.adapters.davinci_resolve import DaVinciResolveAdapter
from execution_plane.adapters.fake_dcc import FakeDccAdapter
from execution_plane.adapters.houdini_hython import HoudiniHythonAdapter


def adapter_registry() -> dict[str, AdapterContract]:
    return {
        FAKE_DCC_ADAPTER: FakeDccAdapter(),
        HOUDINI_HYTHON_ADAPTER: HoudiniHythonAdapter(),
        COMFYUI_LOCAL_ADAPTER: ComfyUILocalAdapter(),
        DAVINCI_RESOLVE_ADAPTER: DaVinciResolveAdapter(),
    }


def get_adapter(adapter_name: str) -> AdapterContract:
    registry = adapter_registry()
    if adapter_name not in registry:
        raise KeyError(f"adapter_not_found:{adapter_name}")
    return registry[adapter_name]


def dispatch_adapter(permit: Mapping[str, Any], payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    adapter = get_adapter(str(permit.get("allowed_adapter", "")))
    return adapter.execute(permit, payload)
