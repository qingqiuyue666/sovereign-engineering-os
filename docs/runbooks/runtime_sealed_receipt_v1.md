# Runtime Sealed Receipt v1

## Status

`RUNTIME_SEALED_RECEIPT_CONTRACT_READY`

This runbook defines the runtime sealed receipt contract layer.

It is contract-only and manual dry run only.

## Boundary

This track does not allow:

- no provider live call
- no transport execution
- no network access
- no secret read
- no secret persistence
- no environment read
- no raw prompt persistence
- no raw response persistence
- no SQLite schema migration
- no runtime audit append
- no protected storage implementation
- no real HMAC signing
- no real Merkle construction
- no zero-knowledge proof generation
- no production autonomy
- no raw evidence store

## Receipt types

Required receipt types:

- transport attempt receipt
- blocked attempt receipt
- postcheck receipt
- receipt chain

## Transport attempt receipt

A transport attempt receipt is valid only when:

- receipt id is present
- task id is present
- transport gate id is present
- policy id is present
- receipt type is `transport_attempt_receipt`
- runtime mode is disabled or manual dry run
- sealed is true
- postcheck is required
- failure quarantine linkage is required
- no forbidden runtime claim is true

## Blocked attempt receipt

A blocked attempt receipt is valid only when:

- blocked is true
- block reason is one of the allowed reasons
- sealed is true
- no forbidden runtime claim is true

Allowed block reasons:

- provider_disabled
- manual_approval_missing
- policy_missing
- forbidden_runtime_claim

## Postcheck receipt

A postcheck receipt is valid only when:

- postcheck result is passed
- sealed receipt is present
- failure quarantine link is present
- health gate is present
- sealed is true
- no forbidden runtime claim is true

## Receipt chain

A receipt chain is valid only when it includes:

- policy receipt reference
- transport receipt reference
- blocked attempt receipt reference
- postcheck receipt reference
- chain_complete true
- final verdict `sealed_receipt_chain_contract_ready` or `blocked_fail_closed`

## Required local checks

```bash
python3 -m unittest tests.tracer_bullet.test_runtime_sealed_receipt_contracts -v
make ci
git diff --check
git status --short
```

## Next track

After this contract track is merged and verified, the next branch should be:

`generic-audit-payload-full-typed-shadow-bundle-v1`

That branch should move generic audit payloads into full typed shadow validation before any full enforcement is enabled.
