"""Digest-only replay verifier."""

from __future__ import annotations

from typing import Mapping

from .replay_diff import diff_digest_chains
from .replay_manifest import validate_replay_manifest

__all__ = ["verify_replay"]


def verify_replay(manifest: Mapping[str, object], observed_event_digest_chain: list[str]) -> dict[str, object]:
    validation = validate_replay_manifest(manifest)
    if not validation.accepted:
        return {"accepted": False, "verdict": "replay_manifest_invalid", "failures": list(validation.failures)}
    expected = list(manifest["event_digest_chain"])  # type: ignore[index]
    diff = diff_digest_chains(expected, observed_event_digest_chain)
    matches = not diff["missing"] and not diff["extra"] and not diff["changed"]
    return {"accepted": matches, "verdict": "replay_match" if matches else "replay_mismatch", "diff": diff}
