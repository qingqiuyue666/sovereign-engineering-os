# Runtime Receipt Spine v1

## Purpose
Validates the full runtime receipt compatibility chain from Evidence Vault
through Replay, Patch, Execution, to Operator Daily Run. Ensures each link
is present, hash-compatible, and free of raw payload.

## Chain Order
1. Evidence Vault receipt -> Replay receipt
2. Replay receipt -> Patch receipt
3. Patch receipt -> Execution receipt
4. Execution receipt -> Operator run receipt

## Boundaries
- no network
- no subprocess
- no live provider
- no trading
- no raw payload in any receipt
- missing chain links rejected
- mismatched artifact IDs rejected
- deterministic chain hash

## Architecture

### RuntimeReceiptChain
Manages the full 5-link receipt chain. Each link must be present.
Produces deterministic chain hash.

### RuntimeReceiptValidator
Validates compatibility between adjacent receipt pairs. Checks field
completeness and raw payload absence. Full spine validation available.

### RuntimeSpineCanonicalHash
Deterministic hash generation for chain and pair hashes.

### RuntimeSpineSecurity
Security boundary: no raw payload, no network, deterministic chain hash.

## Scope
Receipt chain validation only. Does not perform any runtime execution.
