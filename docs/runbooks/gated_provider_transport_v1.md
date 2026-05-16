# Gated Provider Transport v1

## Status

`GATED_PROVIDER_TRANSPORT_CONTRACT_READY`

This runbook defines a disabled by default provider transport gate.

It is manual dry run only.

It does not enable provider live calls.

## Boundary

This track allows contract validation only.

It does not allow:

- no provider live call
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

## Required controls

The provider transport gate requires:

- disabled by default
- manual approval required
- manual dry run
- sealed receipt required
- failure quarantine linkage required
- postcheck required
- canonical health after changes

## Valid contract states

Allowed states:

- disabled transport gate
- manual dry run preflight
- blocked live call attempt
- sealed receipt shape
- postcheck passed

## Invalid states

The gate must reject:

- provider enabled without approval
- network access claimed
- secret read claimed
- raw prompt persisted
- raw response persisted
- live call performed
- missing sealed receipt
- missing failure quarantine link

## Required local checks

```bash
python3 -m unittest tests.tracer_bullet.test_gated_provider_transport_contracts -v
make ci
git diff --check
git status --short
```

## Next track

After this contract track is merged and verified, the next branch should be:

`runtime-sealed-receipt-bundle-v1`

That branch should define the sealed receipt structure for transport attempts without opening live calls.
