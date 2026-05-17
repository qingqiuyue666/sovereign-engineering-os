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
from typing import Any, Dict

from .evidence_envelope import EvidenceEnvelope, EvidenceEnvelopeError
from .evidence_index import EvidenceIndex, EvidenceIndexError
from .evidence_integrity import EvidenceIntegrity


class LocalEvidenceVaultError(Exception):
    """Raised when evidence vault runtime operations fail."""


STABLE_ENVELOPE_FIELDS = (
    "artifact_id", "artifact_type", "content_hash", "hash_algorithm",
    "created_at", "producer", "lineage", "immutable", "append_only",
)


def _recompute_envelope_hash(envelope: Dict[str, Any]) -> str:
    """Recompute envelope hash from stable fields only — shared by read and verify paths."""
    rebuild = {k: envelope[k] for k in STABLE_ENVELOPE_FIELDS if k in envelope}
    canonical = json.dumps(rebuild, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


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

    def _storage_envelope_path(self, artifact_id: str) -> str:
        safe_id = "".join(c for c in artifact_id if c.isalnum() or c in "-_.")
        return os.path.join(self._storage_dir, f"{safe_id}.envelope.json")

    # ------------------------------------------------------------------
    # DEFECT-1: write exactly one envelope file per artifact.
    # No duplicate <artifact_id>.json payload file.
    # ------------------------------------------------------------------

    def write_artifact(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Write an evidence artifact to the vault.

        Validates the payload, creates an envelope, appends to the index,
        and writes exactly one envelope file to disk. Rejects duplicate artifact_id.
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
        if os.path.exists(envelope_path):
            raise LocalEvidenceVaultError(
                f"duplicate_artifact_id_rejected: {artifact_id} — artifact already exists on disk"
            )

        # Create and validate envelope (raises if invalid)
        envelope = EvidenceEnvelope.create_envelope(payload)

        # Write exactly one envelope file — the single source of truth.
        with open(envelope_path, "w", encoding="utf-8") as f:
            json.dump(envelope, f, sort_keys=True, ensure_ascii=False, indent=2)

        # Create index entry
        index_entry = EvidenceIndex.create_index_entry(envelope)
        index_entry["storage_path"] = envelope_path

        # Append to index (reject duplicates)
        EvidenceIndex.append_entry(self._index_path, index_entry, conflict_policy="REJECT_DUPLICATE")

        return {
            "status": "sealed",
            "artifact_id": artifact_id,
            "envelope_hash": envelope["envelope_hash"],
            "storage_path": envelope_path,
            "index_path": self._index_path,
        }

    # ------------------------------------------------------------------
    # DEFECT-1 + DEFECT-4: read from indexed storage_path, enforce full
    # hash integrity via verify_storage_envelope.
    # ------------------------------------------------------------------

    def read_artifact(self, artifact_id: str) -> Dict[str, Any]:
        """Read an artifact from the vault by artifact_id.

        Resolves storage_path from the index entry, reads the single
        envelope file, and enforces full envelope integrity including
        hash recomputation.
        """
        entry = EvidenceIndex.lookup(self._index_path, artifact_id)
        if entry is None:
            raise LocalEvidenceVaultError(f"artifact_not_found: {artifact_id}")

        # DEFECT-1: read from indexed storage_path, not a hard-coded path.
        storage_path = entry.get("storage_path", "")
        if not storage_path or not os.path.isfile(storage_path):
            raise LocalEvidenceVaultError(f"payload_file_missing: {artifact_id}")

        try:
            with open(storage_path, "r", encoding="utf-8") as f:
                envelope = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            raise LocalEvidenceVaultError(f"payload_read_error: {artifact_id} — {e}")

        # DEFECT-4: verify_storage_envelope now recomputes envelope_hash.
        integrity = EvidenceIntegrity.verify_storage_envelope(envelope)
        if not integrity["valid"]:
            raise LocalEvidenceVaultError(f"envelope_integrity_failed: {artifact_id}")

        return envelope

    # ------------------------------------------------------------------
    # DEFECT-1 + DEFECT-4: read from indexed storage_path; use shared
    # canonical hash recomputation.
    # ------------------------------------------------------------------

    def verify_artifact_integrity(self, artifact_id: str) -> Dict[str, Any]:
        """Verify that a stored artifact has not been corrupted.

        Reads from the indexed storage_path, verifies envelope structure
        via EvidenceIntegrity.verify_storage_envelope (which now includes
        hash recomputation), and also independently recomputes the
        envelope hash for defense-in-depth.
        """
        entry = EvidenceIndex.lookup(self._index_path, artifact_id)
        if entry is None:
            return {"valid": False, "reason": "artifact_not_in_index", "artifact_id": artifact_id}

        # DEFECT-1: read from indexed storage_path.
        storage_path = entry.get("storage_path", "")
        if not storage_path or not os.path.isfile(storage_path):
            return {"valid": False, "reason": "payload_file_missing", "artifact_id": artifact_id}

        try:
            with open(storage_path, "r", encoding="utf-8") as f:
                envelope = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            return {"valid": False, "reason": f"payload_read_error: {e}", "artifact_id": artifact_id}

        # verify_storage_envelope now includes hash recomputation (DEFECT-4).
        structure = EvidenceIntegrity.verify_storage_envelope(envelope)

        # Defense-in-depth: recompute envelope hash independently.
        stored_hash = envelope.get("envelope_hash", "")
        computed_hash = _recompute_envelope_hash(envelope)
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
        if entry is None:
            return EvidenceRecovery.create_rollback_plan(artifact_id, "")
        storage_path = entry.get("storage_path", self._storage_envelope_path(artifact_id))
        return EvidenceRecovery.create_rollback_plan(artifact_id, storage_path)


# Late import — EvidenceRecovery is a peer module.
from .evidence_recovery import EvidenceRecovery  # noqa: E402
