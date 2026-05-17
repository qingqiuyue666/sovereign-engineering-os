# Evidence Vault Foundation v1

## Purpose
Bounded local-only evidence vault foundation. Validates evidence records
without writing to any real vault storage.

## Boundaries
- no mutable records
- no missing hashes
- no unsupported hash algorithms
- no raw secret material
- no vault live write
- no actual vault storage write in v1

## Operations
1. validate_evidence_vault_record — structural validation
2. validate_evidence_hash_contract — hash format validation
3. validate_evidence_append_only_contract — append-only enforcement
4. validate_evidence_metadata_contract — metadata completeness
5. produce_evidence_vault_receipt — full receipt production

## Required Fields
artifact_id, artifact_type, content_hash, hash_algorithm,
created_at, producer, lineage, immutable, append_only

## Scope
Contract-only. Does not write to any vault storage.
