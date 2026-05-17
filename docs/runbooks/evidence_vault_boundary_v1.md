# Evidence Vault Boundary (V12-07)

## Overview
Deterministic evidence vault boundary with default-disabled protection. No real encryption, KMS, or secret material. Digest-only envelopes and receipt-only boundaries.

## Components

### Evidence Vault Boundary (`kernel/evidence/evidence_vault_boundary.py`)
- `validate_evidence_vault_boundary()` — default disabled, rejects vault_enabled=true

### Evidence Vault Receipt (`kernel/evidence/evidence_vault_receipt.py`)
- `validate_evidence_vault_receipt()` — descriptor only, approved=false by default

### Protected Storage Interface (`kernel/evidence/protected_storage_interface.py`)
- `validate_protected_storage_request()` — contract only, rejects live_write=true

## Local Verification
```bash
make test-evidence-vault-boundary
make test-evidence-vault-receipt
make test-protected-storage-interface
make test-evidence-vault-boundary-foundation
```
