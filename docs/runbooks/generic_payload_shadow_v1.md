# Generic Payload Shadow v1

## Status

`GENERIC_PAYLOAD_SHADOW_READY`

This runbook defines full typed shadow validation for generic payloads.

It is shadow validation only.

enforcement remains disabled.

ordinary payload behavior is unchanged.

## Boundary

This track does not allow:

- full enforcement
- ordinary payload behavior mutation
- audit append behavior mutation
- SQLite schema migration
- network access
- secret read
- secret persistence
- raw material persistence
- provider live call
- production autonomy

## Shadow categories

Allowed shadow categories:

- classification
- lifecycle_transition
- validation_receipt
- approval
- sealed_evidence
- provider_transport_receipt
- runtime_sealed_receipt
- compatibility_gap

## High-risk fail-closed keys

The following keys remain forbidden:

- raw_prompt
- raw_provider_response
- secret_value
- raw_traceback
- raw_exception_dump

## Compatibility gap rule

Unknown payloads must become compatibility gaps.

A compatibility gap must record:

- shadow mode enabled
- gap recorded
- enforcement blocked

A compatibility gap is not a production write-path failure in this slice.

## Required checks

```bash
python3 -m unittest tests.tracer_bullet.test_generic_payload_shadow_contract -v
make ci
git diff --check
git status --short
```

## Next track

After this bundle is merged and verified, the next branch should be:

`protected-evidence-storage-contract-bundle-v1`

That branch should define protected storage contracts before any protected storage implementation is introduced.
