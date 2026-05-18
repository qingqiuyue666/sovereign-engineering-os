# Real Local Execution Kernel Runtime v1

## Purpose
Bounded local-only execution kernel runtime. Validates command requests,
enforces first-token allowlists, runs preflight checks, and produces
deterministic receipts. Does not execute any commands in v1.

## Boundaries
- no execution by default
- exact first-token allowlist only
- shlex parsing only
- no network commands (curl, wget, ssh, scp, nc, etc.)
- no main mutation (git checkout/switch/push/merge main)
- no branch delete
- no secrets (.env, API_KEY, SECRET, TOKEN, password)
- no production execution
- no freeform shell
- no actual command execution in v1

## Architecture

### ExecutionRequest
Immutable command request with validated category, shlex-parsed tokens,
and first-token extraction. Rejects forbidden first tokens and patterns.

### CommandAllowlist
Exact first-token allowlist. Only commands whose first token exactly
matches an entry in the allowlist are permitted. Uses shlex for parsing.

### ExecutionPreflight
Preflight validation: allowlist, network patterns, main mutation, secret
material, production execution. All gates must pass.

### ExecutionReceipt / ExecutionFailureReceipt
Deterministic receipts. No actual execution. No raw payload. No wall-clock.

### ExecutionSecurity
Security boundary: no network, no main mutation, no branch delete,
no secrets, no env reads, no production execution, no execution by default.

### ExecutionCanonicalHash
Deterministic hash generation using blake2b, sha256, or sha512.

## Operations
1. create_request — immutable execution request
2. validate_request — security + allowlist validation
3. run_preflight — full preflight gate check
4. approve — full approval pipeline producing receipt
5. produce_failure_receipt — failure receipt generation

## Special Cases
- python3 allowed only with exact "python3" in allowlist
- "pythonmalicious" rejected when allowlist contains "python" (exact match)
- "python3 tests/test_main.py" not rejected only because filename contains "main"
- git checkout/switch/push/merge main always rejected
- curl/wget/ssh/scp/nc always rejected
- API_KEY/SECRET/TOKEN/.env always rejected

## Receipt Types
- ExecutionReceipt: approval receipt (execution_id, status, category, preflight results)
- ExecutionFailureReceipt: failure receipt with code and reason

## Scope
Contract-only in v1. Does not execute commands. All receipts deterministic.
