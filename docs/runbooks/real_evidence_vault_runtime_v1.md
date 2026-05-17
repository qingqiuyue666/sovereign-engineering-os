# Real Evidence Vault Runtime v1

## Purpose
Real local-only append-only evidence vault runtime. Writes evidence envelopes
to a local filesystem directory with deterministic hashing, index management,
and integrity verification.

## Boundaries
- local filesystem only — no network access
- no encryption — digest-only protected storage envelope
- no key management
- no cloud API calls
- no subprocess execution
- no live provider surface
- no production autonomy
- no secret storage
- no plaintext secret material
- no destructive delete
- no overwrite of existing artifact payload
- append-only: existing artifact_id cannot be silently overwritten
- runtime_type: local-only
- module_version: v1

## Operations

### 1. Evidence Envelope Creation
- evidence_envelope.EvidenceEnvelope.create_envelope(payload) -> envelope
- Validates required fields, hash format, artifact type, and secret markers
- Rejects mutable or non-append-only records
- Produces deterministic envelope with envelope_hash

### 2. Content Hash Verification
- evidence_envelope.EvidenceEnvelope.verify_hash(envelope, content) -> result
- Verifies content hash matches expected hash in envelope
- Supports sha256, sha512, blake2b

### 3. Append-Only Storage
- local_evidence_vault.LocalEvidenceVault.write_artifact(payload) -> result
- Creates envelope, writes to disk, appends to index
- Rejects duplicate artifact_id (append-only, no overwrite)
- Writes both envelope and artifact payload files

### 4. Evidence Index
- evidence_index.EvidenceIndex.create_index_entry(envelope) -> entry
- evidence_index.EvidenceIndex.lookup(index_path, artifact_id) -> entry or None
- evidence_index.EvidenceIndex.append_entry(index_path, entry, policy) -> result
- evidence_index.EvidenceIndex.list_all(index_path) -> all entries

### 5. Read Path by artifact_id
- local_evidence_vault.LocalEvidenceVault.read_artifact(artifact_id) -> envelope
- Looks up artifact in index, reads payload, verifies envelope integrity

### 6. Corruption Detection
- evidence_integrity.EvidenceIntegrity.verify_payload_integrity(path, hash, algo) -> result
- evidence_integrity.EvidenceIntegrity.verify_index_integrity(index_path) -> result
- evidence_integrity.EvidenceIntegrity.verify_storage_envelope(envelope) -> result

### 7. Recovery Receipt
- evidence_recovery.EvidenceRecovery.generate_recovery_receipt(artifact_id, envelope) -> receipt

### 8. Migration Receipt
- evidence_recovery.EvidenceRecovery.generate_migration_receipt(foundation_payload) -> receipt
- Records transition from foundation contract (contract-only) to real runtime

### 9. Rollback Plan
- evidence_recovery.EvidenceRecovery.create_rollback_plan(artifact_id, storage_path) -> plan
- No destructive delete — artifact retained in append-only storage, flagged for review

## Required Fields
artifact_id, artifact_type, content_hash, hash_algorithm, created_at,
producer, lineage, immutable, append_only

## Evidence Artifact Contract
- artifact_id: unique identifier (non-empty string)
- artifact_type: classification (must not be forbidden type)
- content_hash: hex-encoded digest matching hash_algorithm
- hash_algorithm: sha256, sha512, or blake2b
- created_at: ISO 8601 timestamp
- producer: creator identifier
- lineage: ordered list of provenance references (non-empty)
- immutable: must be true
- append_only: must be true
- storage_path: resolved at write time
- envelope_hash: sha256 of canonical JSON envelope
- index_record_hash: deterministic hash of index entry fields

## Deterministic Hashing
All hashing uses deterministic algorithms:
- SHA-256, SHA-512, BLAKE2b
- Envelope hash: sha256 of sorted, canonical JSON
- Index record hash: sha256 of `artifact_id|envelope_hash|created_at`

## Runtime Constraints
REAL_EVIDENCE_VAULT_RUNTIME_READY — local-only append-only evidence vault runtime v1.

- no network
- no encryption
- no key management
- no cloud APIs
- no subprocess
- no live provider surface
- no production autonomy
- no secret storage
- no plaintext secrets
- append-only enforced
- digest-only protected storage
- migration receipt required for foundation contract transition
