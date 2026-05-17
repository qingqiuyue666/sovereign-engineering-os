"""Deterministic replay diff descriptor foundation.

Compares expected and actual output digests to detect replay mismatches.
Reports version mismatches and output digest mismatches as failures.
Strict field typing enforced.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from kernel.runtime._strict_validation import (
    strict_nonempty_string,
    validate_required_digest_fields,
    validate_required_string_fields,
)

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

_REQUIRED_STRING_FIELDS = (
    "policy_version",
    "code_version",
)

_REQUIRED_DIGEST_FIELDS = (
    "expected_output_digest",
    "actual_output_digest",
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


def validate_replay_diff(payload: Mapping[str, object]) -> ReplayDiffReceipt:
    """Validate and compare a replay diff descriptor with strict typing.

    All string fields must be non-empty, non-None strings.
    All digest fields must match sha256:<64 lowercase hex>.
    bound_version_tuple must be non-empty list of non-empty strings.
    """
    payload_dict = dict(payload)
    failures: list[str] = []

    for field in _FORBIDDEN_FIELDS:
        if field in payload_dict:
            failures.append(f"{field}_forbidden")

    validate_required_string_fields(payload_dict, _REQUIRED_STRING_FIELDS, failures)
    validate_required_digest_fields(payload_dict, _REQUIRED_DIGEST_FIELDS, failures)

    # bound_version_tuple strict validation
    bvt = payload_dict.get("bound_version_tuple")
    if bvt is None:
        failures.append("bound_version_tuple_must_not_be_none")
    elif not isinstance(bvt, (list, tuple)):
        failures.append("bound_version_tuple_must_be_list")
    elif len(bvt) == 0:
        failures.append("bound_version_tuple_must_be_nonempty")
    else:
        for i, entry in enumerate(bvt):
            if entry is None:
                failures.append(f"bound_version_tuple[{i}]_must_not_be_none")
            elif not isinstance(entry, str):
                failures.append(f"bound_version_tuple[{i}]_must_be_string")
            elif not entry or not entry.strip():
                failures.append(f"bound_version_tuple[{i}]_must_be_nonempty_string")

    if failures:
        return ReplayDiffReceipt(False, False, tuple(failures))

    expected = payload_dict["expected_output_digest"]
    actual = payload_dict["actual_output_digest"]
    replay_match = (expected == actual)

    if not replay_match:
        diff_failures = list(failures)
        diff_failures.append("output_digest_mismatch")
        return ReplayDiffReceipt(True, False, tuple(diff_failures))

    return ReplayDiffReceipt(True, True, ())
