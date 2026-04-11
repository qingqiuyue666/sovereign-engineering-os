"""
Canonical `version_tuple_hash` composition (P0, must-fix before coding).

Constitutional anchors:
- v11 §8.2 (Version tuple field set, exact composition order)
- v11 §8.3 (Version drift is a governance event)
- v11 §22.10 (invariant binding support)
- foundation §3 item 9 (single shared import path; sentinel rule)

Rules enforced here:
- Every artifact-producing service must route through `compose_version_tuple`
  and `compose_version_tuple_hash` defined in this module. No service-local
  sentinel values, ever.
- The ordered composition is the exact §8.2 field order. Any field not
  yet live in phase 1 MUST use `PHASE1_VERSION_SENTINEL`, never `None`
  and never omitted.
- The hash is deterministic: SHA-256 over a JSON serialization that is
  canonical (`sort_keys=True`, tight separators). Determinism here is
  load-bearing for replay admissibility (§22.5 / INV-010).
- Any difference between two composed tuples emits a drift-classification
  input at the caller level; detection helper is provided as
  `detect_drift`.

Scope lock:
- This module is pure computation. It does not read policy state, reach
  the filesystem, or emit AuditRecords. Callers own audit emission.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, MutableMapping


#: Phase-1 sentinel for any §8.2 version-tuple field whose policy surface
#: is not yet live. Required by foundation §3 item 9.
PHASE1_VERSION_SENTINEL = "phase1-unset-v1"


#: Exact §8.2 ordered field names. This tuple is the single source of
#: truth; iteration order here must match §8.2 in the constitution.
VERSION_TUPLE_FIELDS: tuple[str, ...] = (
    "kernel_schema_version",
    "journal_schema_version",
    "execution_policy_version",
    "approval_policy_version",
    "replay_policy_version",
    "memory_policy_version",
    "packing_policy_version",
    "toolchain_policy_version",
    "scrubbing_policy_version",
    "retry_policy_version",
    "taint_policy_version",
    "scheduling_policy_version",
    "anti_swap_policy_version",
    "diagnostic_adapter_version",
    "review_render_policy_version",
    "feature_flag_set",
    "capability_policy_version",
    "retention_policy_version",
)


class VersionTupleError(ValueError):
    """Raised when an illegal version-tuple composition is attempted."""


@dataclass(frozen=True)
class VersionTuple:
    ordered_fields: tuple[tuple[str, Any], ...]

    def as_mapping(self) -> Mapping[str, Any]:
        return dict(self.ordered_fields)

    def canonical_json(self) -> str:
        # Canonical serialization: preserve §8.2 order by using an
        # explicit list of pairs rather than a dict. This differs from
        # naive `json.dumps(sort_keys=True)` because we enforce the
        # constitutional order, not alphabetical order.
        return json.dumps(
            {k: v for k, v in self.ordered_fields},
            sort_keys=False,
            separators=(",", ":"),
        )


def compose_version_tuple(overrides: Mapping[str, Any] | None = None) -> VersionTuple:
    """Compose a canonical §8.2 version tuple.

    - Every field listed in `VERSION_TUPLE_FIELDS` must appear in the
      result, in order.
    - Fields not present in `overrides` are filled with
      `PHASE1_VERSION_SENTINEL`.
    - A `None` override is illegal (foundation §3 item 9 forbids
      service-local sentinel invention).
    - Unknown keys in `overrides` are rejected to prevent silent
      expansion of the tuple surface.
    """
    overrides = overrides or {}
    unknown = set(overrides) - set(VERSION_TUPLE_FIELDS)
    if unknown:
        raise VersionTupleError(
            f"unknown version-tuple fields: {sorted(unknown)}"
        )
    ordered: list[tuple[str, Any]] = []
    for field in VERSION_TUPLE_FIELDS:
        if field in overrides:
            value = overrides[field]
            if value is None:
                raise VersionTupleError(
                    f"version-tuple field {field!r} is None; use "
                    f"PHASE1_VERSION_SENTINEL explicitly"
                )
            ordered.append((field, value))
        else:
            ordered.append((field, PHASE1_VERSION_SENTINEL))
    return VersionTuple(ordered_fields=tuple(ordered))


def compose_version_tuple_hash(
    overrides: Mapping[str, Any] | None = None,
) -> str:
    """Return the deterministic `version_tuple_hash` for the composed tuple."""
    tup = compose_version_tuple(overrides)
    digest = hashlib.sha256(tup.canonical_json().encode("utf-8")).hexdigest()
    return f"vth1:{digest}"


def detect_drift(
    expected: VersionTuple, observed: VersionTuple
) -> tuple[str, ...]:
    """Return the field names that differ between two tuples.

    Callers are responsible for turning any non-empty diff into a
    DriftEventRecord (§23.19) at the appropriate enforcement point.
    """
    diffs: list[str] = []
    exp_map = dict(expected.ordered_fields)
    obs_map = dict(observed.ordered_fields)
    for field in VERSION_TUPLE_FIELDS:
        if exp_map.get(field) != obs_map.get(field):
            diffs.append(field)
    return tuple(diffs)
