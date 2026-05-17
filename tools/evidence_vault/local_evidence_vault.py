"""Local evidence vault runtime — append-only local filesystem evidence storage.

The real runtime implementation that writes evidence envelopes to a local
directory with deterministic hashing, index management, and integrity checks.

Constraints:
- Local filesystem only
- No network
- No encryption claim
- No key management claim
- No live provider surface
- No production autonomy
- No secret storage
- No plaintext secret material
- No destructive delete
- No overwrite of existing artifact payload
- Append-only: existing artifact_id cannot be silently overwritten
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .evidence_envelope import EvidenceEnvelope, EvidenceEnvelopeError
from .evidence_index import EvidenceIndex, EvidenceIndexError
from .evidence_integrity import EvidenceIntegrity, EvidenceIntegrityError
from .evidence_recovery import EvidenceRecovery


class LocalEvidenceVaultError(Exception):
    """Raised when evidence vault runtime operations fail."""


class LocalEvidenceVault:
    """Real local evidence vault runtime — append-only filesystem storage."""

    def __init__(self, storage_dir: str):
        self._storage_dir = os.path.abspath(storage_dir)
        self._index_path = os.path.join(self._storage_dir, "evidence_index.jsonl")
        os.makedirs(self._storage_dir, exist_ok=True)

    @property
    def storage_dir(self) -> str:
        return self._storage_dir

    @property
    def index_path(self) -> str:
        return self._index_path

    def _artifact_path(self, artifact_id: str) -> str:
        safe_id = "".join(c for c in artifact_id if c.isalnum() or c in "-_.")
        return os.path.join(self._storage_dir, f"{safe_id}.json")

    def _storage_envelope_path(self, artifact_id: str) -> str:
        safe_id = "".join(c for c in artifact_id if c.isalnum() or c in "-_.")
        return os.path.join(self._storage_dir, f"{safe_id}.envelope.json")

    def write_artifact(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Write an evidence artifact to the vault.

        Validates the payload, creates an envelope, appends to the index,
        and writes the artifact payload to disk. Rejects duplicate artifact_id.
        """
        if not isinstance(payload, dict):
            raise TypeError("payload must be a mapping")

        artifact_id = payload.get("artifact_id", "")

        # Reject duplicates (append-only — no overwrite)
        if EvidenceIndex.exists(self._index_path, artifact_id):
            raise LocalEvidenceVaultError(
                f"duplicate_artifact_id_rejected: {artifact_id} — append-only, cannot overwrite"
            )

        # Reject overwrite on disk
        envelope_path = self._storage_envelope_path(artifact_id)
        payload_path = self._artifact_path(artifact_id)
        if os.path.exists(envelope_path) or os.path.exists(payload_path):
            raise LocalEvidenceVaultError(
                f"duplicate_artifact_id_rejected: {artifact_id} — artifact already exists on disk"
            )

        # Create and validate envelope (raises if invalid)
        envelope = EvidenceEnvelope.create_envelope(payload)

        # Write the envelope
        with open(envelope_path, "w", encoding="utf-8") as f:
            json.dump(envelope, f, sort_keys=True, ensure_ascii=False, indent=2)

        # Create index entry
        index_entry = EvidenceIndex.create_index_entry(envelope)
        index_entry["storage_path"] = envelope_path

        # Append to index (reject duplicates)
        EvidenceIndex.append_entry(self._index_path, index_entry, conflict_policy="REJECT_DUPLICATE")

        # Write artifact payload to disk
        with open(payload_path, "w", encoding="utf-8") as f:
            json.dump(envelope, f, sort_keys=True, ensure_ascii=False, indent=2)

        return {
            "status": "sealed",
            "artifact_id": artifact_id,
            "envelope_hash": envelope["envelope_hash"],
            "storage_path": envelope_path,
            "index_path": self._index_path,
        }

    def read_artifact(self, artifact_id: str) -> Dict[str, Any]:
        """Read an artifact from the vault by artifact_id."""
        entry = EvidenceIndex.lookup(self._index_path, artifact_id)
        if entry is None:
            raise LocalEvidenceVaultError(f"artifact_not_found: {artifact_id}")

        payload_path = self._artifact_path(artifact_id)
        if not os.path.isfile(payload_path):
            raise LocalEvidenceVaultError(f"payload_file_missing: {artifact_id}")

        try:
            with open(payload_path, "r", encoding="utf-8") as f:
                envelope = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            raise LocalEvidenceVaultError(f"payload_read_error: {artifact_id} — {e}")

        # Verify integrity
        integrity = EvidenceIntegrity.verify_storage_envelope(envelope)
        if not integrity["valid"]:
            raise LocalEvidenceVaultError(f"envelope_integrity_failed: {artifact_id}")

        return envelope

    def verify_artifact_integrity(self, artifact_id: str) -> Dict[str, Any]:
        """Verify that a stored artifact has not been corrupted.

        Verifies envelope structure and recomputes envelope_hash from the
        canonical payload to detect any tampering.
        """
        entry = EvidenceIndex.lookup(self._index_path, artifact_id)
        if entry is None:
            return {"valid": False, "reason": "artifact_not_in_index", "artifact_id": artifact_id}

        payload_path = self._artifact_path(artifact_id)
        if not os.path.isfile(payload_path):
            return {"valid": False, "reason": "payload_file_missing", "artifact_id": artifact_id}

        try:
            with open(payload_path, "r", encoding="utf-8") as f:
                envelope = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            return {"valid": False, "reason": f"payload_read_error: {e}", "artifact_id": artifact_id}

        # Verify envelope structure
        structure = EvidenceIntegrity.verify_storage_envelope(envelope)

        # Recompute envelope hash: rebuild canonical payload (excluding runtime fields)
        # and verify against stored envelope_hash
        stored_hash = envelope.get("envelope_hash", "")
        rebuild = {
            k: envelope[k]
            for k in ("artifact_id", "artifact_type", "content_hash", "hash_algorithm",
                      "created_at", "producer", "lineage", "immutable", "append_only")
            if k in envelope
        }
        canonical = json.dumps(rebuild, sort_keys=True, ensure_ascii=False).encode("utf-8")
        computed_hash = hashlib.sha256(canonical).hexdigest()
        hash_match = computed_hash == stored_hash

        valid = structure["valid"] and hash_match
        return {
            "valid": valid,
            "reason": "hash_match" if valid else "hash_mismatch_corruption_detected",
            "artifact_id": artifact_id,
            "envelope_structure_valid": structure["valid"],
            "envelope_hash_match": hash_match,
        }

    def verify_index_integrity(self) -> Dict[str, Any]:
        """Verify the integrity of the entire evidence index."""
        return EvidenceIntegrity.verify_index_integrity(self._index_path)

    def get_recovery_receipt(self, artifact_id: str) -> Dict[str, Any]:
        """Generate a recovery receipt for a stored artifact."""
        entry = EvidenceIndex.lookup(self._index_path, artifact_id)
        if entry is None:
            raise LocalEvidenceVaultError(f"artifact_not_found_for_recovery: {artifact_id}")
        return EvidenceRecovery.generate_recovery_receipt(artifact_id, entry)

    def get_migration_receipt(self, foundation_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a migration receipt from a foundation contract payload."""
        if not isinstance(foundation_payload, dict):
            raise TypeError("foundation_payload must be a mapping")
        return EvidenceRecovery.generate_migration_receipt(foundation_payload)

    def get_rollback_plan(self, artifact_id: str) -> Dict[str, Any]:
        """Get a rollback plan for a specific artifact."""
        entry = EvidenceIndex.lookup(self._index_path, artifact_id)
        storage_path = self._artifact_path(artifact_id)
        return EvidenceRecovery.create_rollback_plan(artifact_id, storage_path)
