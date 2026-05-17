"""Evidence recovery — recovery receipt, migration receipt, and rollback plan.

Local-only. No network. No encryption. No key material.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List


class EvidenceRecoveryError(ValueError):
    """Raised when evidence recovery operations fail."""


class EvidenceRecovery:
    """Generates recovery receipts, migration receipts, and rollback plans."""

    @staticmethod
    def _hash_id(*parts: str) -> str:
        return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]

    @classmethod
    def generate_recovery_receipt(cls, artifact_id: str, storage_envelope: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a recovery receipt for a stored artifact."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        receipt_id = cls._hash_id(artifact_id, "recovery", now)
        return {
            "receipt_id": receipt_id,
            "artifact_id": artifact_id,
            "receipt_type": "recovery",
            "created_at": now,
            "storage_path": storage_envelope.get("storage_path", ""),
            "content_hash": storage_envelope.get("content_hash", ""),
            "envelope_hash": storage_envelope.get("envelope_hash", ""),
            "hash_algorithm": storage_envelope.get("hash_algorithm", ""),
            "artifact_type": storage_envelope.get("artifact_type", ""),
            "producer": storage_envelope.get("producer", ""),
            "lineage": list(storage_envelope.get("lineage", [])),
            "module_version": "v1",
            "status": "recoverable",
        }

    @classmethod
    def generate_migration_receipt(
        cls, foundation_payload: Dict[str, Any], migrated_at: str = ""
    ) -> Dict[str, Any]:
        """Generate a migration receipt showing transition from foundation contract to real runtime.

        The foundation contract produced a receipt without actual storage write.
        This migration receipt records the transition from contract-only to runtime.
        """
        now = migrated_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        receipt_id = cls._hash_id(
            foundation_payload.get("artifact_id", "unknown"),
            "migration",
            now,
        )
        return {
            "receipt_id": receipt_id,
            "artifact_id": foundation_payload.get("artifact_id", "unknown"),
            "receipt_type": "migration",
            "migration_status": "migrated_from_foundation_contract",
            "migrated_at": now,
            "foundation_receipt_reference": foundation_payload.get("receipt_id", ""),
            "content_hash": foundation_payload.get("content_hash", ""),
            "hash_algorithm": foundation_payload.get("hash_algorithm", ""),
            "artifact_type": foundation_payload.get("artifact_type", ""),
            "module_version": "v1",
        }

    @classmethod
    def create_rollback_plan(cls, artifact_id: str, storage_path: str) -> Dict[str, Any]:
        """Create a rollback plan for a specific artifact.

        The rollback plan describes how to revert the artifact to a safe state.
        In this v1 runtime, rollback means the artifact record is retained
        (append-only, no destructive delete) and marked as flagged for review.
        """
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return {
            "plan_id": cls._hash_id(artifact_id, "rollback", now),
            "artifact_id": artifact_id,
            "plan_type": "rollback",
            "created_at": now,
            "storage_path": storage_path,
            "action": "mark_for_review",
            "description": "No destructive delete. Artifact retained in append-only storage. Flagged for review.",
            "steps": [
                "verify artifact integrity before rollback",
                "mark artifact as ROLLBACK_PENDING in index",
                "retain all existing payload data (append-only, no delete)",
                "no overwrite of artifact payload",
                "create rollback audit record",
            ],
            "module_version": "v1",
        }
