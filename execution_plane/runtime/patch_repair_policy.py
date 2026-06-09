"""Patch-repair policy extraction for failure convergence."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from execution_plane.runtime.token_policy import normalize_runtime_policy


@dataclass(frozen=True)
class PatchRepairPolicy:
    enabled: bool
    mode: str
    allowed_tools: tuple[str, ...]
    auto_apply: bool

    @classmethod
    def from_token(cls, token: Mapping[str, Any]) -> "PatchRepairPolicy":
        section = normalize_runtime_policy(token)["patch_repair"]
        return cls(
            enabled=bool(section["enabled"]),
            mode=str(section["mode"]),
            allowed_tools=tuple(str(tool) for tool in section["allowed_tools"]),
            auto_apply=bool(section["auto_apply"]),
        )

    def can_generate_patch(self) -> bool:
        return self.enabled and self.mode == "generate_patch_then_test" and bool(self.allowed_tools)
