"""Deterministic replay diff descriptor foundation.

Compares expected and actual output digests to detect replay mismatches.
Reports version mismatches and output digest mismatches as failures.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import hashlib
import json

__all__ = [
    "ReplayDiffReceipt",
    "ReplayDiffRejection",
    "validate_replay_diff",
]

_FORBIDDEN_FIELDS = (
    "raw_prompt",
    "raw_provider_response",
    "secret_value",
    "env_value",
)

_REQUIRED_FIELDS = (
    "expected_output_digest",
    "actual_output_digest",
    "policy_version",
    "code_version",
    "bound_version_tuple",
)


class ReplayDiffRejection(ValueError):
    """Raised when a replay diff violates policy boundaries."""


@dataclass(frozen=True)
class ReplayDiffReceipt:
    accepted: bool
    replay_match: bool
    failures: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "replay_match": self.replay_match,
            "failures": list(self.failures),
        }


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest_payload(payload: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def validate_replay_diff(payload: Mapping[str, object]) -> ReplayDiffReceipt:
    """Validate and compare a replay diff descriptor.

    Checks:
    - No forbidden fields
    - All required fields present
    - Digest fields have sha256: prefix
    - expected_output_digest == actual_output_digest (replay_match)
    - bound_version_tuple must be present (version mismatch otherwise)
    """
    failures: list[str] = []

    for field in _FORBIDDEN_FIELDS:
        if field in payload:
            failures.append(f"{field}_forbidden")

    for field in _REQUIRED_FIELDS:
        if field not in payload:
            failures.append(f"{field}_required")

    # Digest format checks
    for field in ("expected_output_digest", "actual_output_digest"):
        if field in payload:
            val = payload[field]
            if isinstance(val, str) and val and not val.startswith("sha256:"):
                failures.append(f"{field}_must_be_sha256_prefixed")

    # Bound version tuple must be present and non-empty
    bvt = payload.get("bound_version_tuple")
    if bvt is not None and (not isinstance(bvt, (list, tuple)) or len(bvt) == 0):
        failures.append("bound_version_tuple_must_be_nonempty")

    if failures:
        return ReplayDiffReceipt(False, False, tuple(failures))

    expected = str(payload["expected_output_digest"])
    actual = str(payload["actual_output_digest"])

    replay_match = (expected == actual)

    if not replay_match:
        diff_failures = list(failures)
        diff_failures.append("output_digest_mismatch")
        return ReplayDiffReceipt(True, False, tuple(diff_failures))

    return ReplayDiffReceipt(True, True, ())
