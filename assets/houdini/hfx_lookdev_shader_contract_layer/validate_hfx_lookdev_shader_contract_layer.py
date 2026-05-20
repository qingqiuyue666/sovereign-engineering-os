"""Empty validator template for HFX Lookdev Shader Contract Layer.

This template intentionally contains no production validation logic yet. It is a
typed placeholder for future fail-closed checks over the layer's JSON contracts.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final


LAYER_DIRECTORY: Final[str] = "hfx_lookdev_shader_contract_layer"
SCHEMA_FILENAMES: Final[tuple[str, ...]] = ("hfx_material_binding.schema.json", "hfx_shader_parameter_contract.schema.json",)


def validate_contract(payload: Mapping[str, object]) -> tuple[str, ...]:
    """Return validation failures for one layer contract payload.

    TODO: implement layer-specific validation gates.
    """
    _ = payload
    return ()
