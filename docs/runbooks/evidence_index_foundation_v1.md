# Evidence Index Foundation v1

## Purpose
Bounded local-only evidence index foundation. Validates index entries
without writing to any vault.

## Boundaries
- no missing artifact id
- no missing content hash
- no missing index key
- no duplicate without explicit conflict policy
- no live vault write
- no vault write in v1

## Operations
1. validate_evidence_index_entry — structural validation
2. validate_evidence_lookup_contract — lookup key integrity
3. validate_index_consistency_contract — duplicate handling
4. produce_evidence_index_receipt — full receipt production

## Scope
Contract-only. Does not write to any vault.
