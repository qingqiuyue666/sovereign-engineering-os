"""Digest-only replay manifest validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

__all__ = ["ReplayManifestResult", "validate_replay_manifest"]

_REQUIRED = ("replay_id", "task_id", "run_id", "input_digest", "policy_version", "code_version", "event_digest_chain")


@dataclass(frozen=True)
class ReplayManifestResult:
    accepted: bool
    failures: tuple[str, ...]


def validate_replay_manifest(manifest: Mapping[str, object]) -> ReplayManifestResult:
    if not isinstance(manifest, Mapping):
        return ReplayManifestResult(False, ("replay_manifest_must_be_mapping",))
    failures: list[str] = []
    for field in _REQUIRED:
        if field not in manifest:
            failures.append(f"{field}_required")
    for field in ("replay_id", "task_id", "run_id", "input_digest", "policy_version", "code_version"):
        if field in manifest and (not isinstance(manifest.get(field), str) or not manifest.get(field)):
            failures.append(f"{field}_must_be_nonempty_string")
    if manifest.get("provider_requery_requested") is True:
        failures.append("provider_requery_forbidden")
    chain = manifest.get("event_digest_chain")
    if not isinstance(chain, list) or not all(isinstance(item, str) and item.startswith("sha256:") for item in chain):
        failures.append("event_digest_chain_must_be_digest_list")
    if "raw_content" in manifest or "raw_events" in manifest:
        failures.append("raw_content_comparison_forbidden")
    return ReplayManifestResult(not failures, tuple(sorted(set(failures))))
