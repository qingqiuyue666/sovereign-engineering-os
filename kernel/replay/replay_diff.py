"""Digest-chain diffing with no raw content comparison."""

from __future__ import annotations

__all__ = ["diff_digest_chains"]


def diff_digest_chains(expected: list[str], observed: list[str]) -> dict[str, object]:
    missing = [item for item in expected if item not in observed]
    extra = [item for item in observed if item not in expected]
    changed: list[dict[str, object]] = []
    for index, expected_item in enumerate(expected[: min(len(expected), len(observed))]):
        observed_item = observed[index]
        if expected_item != observed_item:
            changed.append({"index": index, "expected": expected_item, "observed": observed_item})
    return {"missing": missing, "extra": extra, "changed": changed}
