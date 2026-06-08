"""Deterministic digest helpers for execution permits."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

PERMIT_DIGEST_FIELD = "permit_digest"


def canonical_json(payload: Any) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def compute_permit_digest(permit: Mapping[str, Any]) -> str:
    """Compute a deterministic digest excluding the digest field itself."""

    material = {
        key: value
        for key, value in permit.items()
        if key != PERMIT_DIGEST_FIELD
    }
    digest = hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()
    return "sha256:" + digest


def attach_permit_digest(permit: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(permit)
    payload[PERMIT_DIGEST_FIELD] = compute_permit_digest(payload)
    return payload

