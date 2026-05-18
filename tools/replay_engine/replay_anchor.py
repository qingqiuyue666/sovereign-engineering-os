"""Replay anchor — immutable replay request anchor point.

Anchors a replay request to an exact input snapshot, version tuple, and
environment fingerprint. Once created, anchors cannot be mutated.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, asdict
from typing import Any, Dict


@dataclass(frozen=True)
class ReplayAnchor:
    """Immutable anchor binding a replay request to its inputs."""

    anchor_id: str
    input_snapshot_hash: str
    policy_version: str
    code_version: str
    environment_fingerprint: str
    deterministic_mode: bool
    no_cloud_requery: bool
    evidence_vault_binding: str
    canonical_hash: str

    @staticmethod
    def create(
        input_snapshot_hash: str,
        policy_version: str,
        code_version: str,
        environment_fingerprint: str,
        *,
        deterministic_mode: bool = True,
        no_cloud_requery: bool = True,
        evidence_vault_binding: str = "",
    ) -> ReplayAnchor:
        if not input_snapshot_hash or len(input_snapshot_hash) != 64:
            raise ValueError("input_snapshot_hash must be 64-char hex sha256")
        if not policy_version.strip():
            raise ValueError("policy_version required")
        if not code_version.strip():
            raise ValueError("code_version required")
        if not environment_fingerprint.strip():
            raise ValueError("environment_fingerprint required")
        if not deterministic_mode:
            raise ValueError("nondeterministic replay rejected")
        if not no_cloud_requery:
            raise ValueError("cloud re-query rejected")

        raw = "|".join([
            input_snapshot_hash, policy_version, code_version,
            environment_fingerprint, str(deterministic_mode),
            str(no_cloud_requery), evidence_vault_binding,
        ])
        canonical = hashlib.sha256(raw.encode()).hexdigest()
        anchor_id = hashlib.blake2b(raw.encode(), digest_size=16).hexdigest()

        return ReplayAnchor(
            anchor_id=anchor_id,
            input_snapshot_hash=input_snapshot_hash,
            policy_version=policy_version,
            code_version=code_version,
            environment_fingerprint=environment_fingerprint,
            deterministic_mode=deterministic_mode,
            no_cloud_requery=no_cloud_requery,
            evidence_vault_binding=evidence_vault_binding,
            canonical_hash=canonical,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
