"""
Frozen schema pack for first-slice signable-path artifacts.

Schemas are JSON Schema (draft 2020-12) frozen from v11 §23.
Freeze tag: v11-slice1 (implementation foundation §3).

This package exposes `load_schema(name)` so kernel services can validate
artifacts at ingress and pre-persist boundaries (implementation foundation
§3.4 runtime enforcement).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA_FREEZE_TAG = "v11-slice1"

_SCHEMA_DIR = Path(__file__).resolve().parent


def load_schema(name: str) -> Mapping[str, Any]:
    """Load a frozen schema by logical artifact name (e.g. 'context_artifact').

    Raises FileNotFoundError if the schema is not present in the frozen pack.
    """
    path = _SCHEMA_DIR / f"{name}.schema.json"
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)
