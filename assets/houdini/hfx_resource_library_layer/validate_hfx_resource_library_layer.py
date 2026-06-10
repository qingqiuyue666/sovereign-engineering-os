"""Empty validator template for HFX Resource Library Layer.

This template intentionally contains no production validation logic yet. It is a
typed placeholder for future fail-closed checks over the layer's JSON contracts.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final


LAYER_DIRECTORY: Final[str] = "hfx_resource_library_layer"
SCHEMA_FILENAMES: Final[tuple[str, ...]] = ("hfx_desktop_inbox_scanner_manifest.schema.json",)


def validate_contract(payload: Mapping[str, object]) -> tuple[str, ...]:
    """Return validation failures for one layer contract payload.

    TODO: implement layer-specific validation gates.
    """
    _ = payload
    return ()
