# Real Patch Application Runtime v1

## Purpose
Bounded local-only patch application runtime. Validates patch requests,
enforces allowlists, runs preflight checks, and produces deterministic
receipts. Does not perform actual patch application in v1.

## Boundaries
- dry-run only
- no actual patch application
- no network calls
- no git push/merge/branch delete
- no freeform shell
- no absolute paths
- no path traversal
- no forbidden root paths
- no main mutation
- no destructive mutation in v1
- no overclaim about actual patch application
- rollback bundle required
- tests required before approval

## Architecture

### PatchRequest
Immutable patch request with validated target path, patch content hash,
rollback bundle hash, and allowlist binding. Rejects unsafe paths.

### PatchAllowlist
Enforces allowed target paths. Only explicitly whitelisted paths may be patched.

### PatchPreflight
Preflight validation checks: allowlist, target path safety, rollback bundle,
test results, security gates. All must pass before approval.

### PatchRollback
Every patch must reference a valid rollback bundle with hash.

### PatchReceipt / PatchFailureReceipt
Deterministic receipts for patch operations. No raw payload. No wall-clock.

### PatchSecurity
Security boundary: no network, no git push/merge/branch delete, no freeform
shell, no destructive mutation, no secrets, no env reads.

### PatchCanonicalHash
Deterministic hash generation using blake2b, sha256, or sha512.

## Operations
1. create_request — immutable patch request with validated target
2. create_rollback — rollback bundle reference
3. validate_request — security + allowlist validation
4. run_preflight — full preflight gate check
5. approve — full approval pipeline producing receipt
6. produce_failure_receipt — failure receipt generation

## Receipt Types
- PatchReceipt: approval receipt (request, target, status, preflight results)
- PatchFailureReceipt: failure receipt with code and reason

## Scope
Dry-run only in v1. Does not apply patches. All receipts deterministic.
