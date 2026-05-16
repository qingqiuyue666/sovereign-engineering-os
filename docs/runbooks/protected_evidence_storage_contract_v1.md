# Protected Evidence Storage Contract v1

## Status

`PROTECTED_EVIDENCE_STORAGE_CONTRACT_READY`

This runbook defines a contract-only storage boundary for protected evidence.

It does not implement protected storage.

## Contract-only storage boundary

This track defines policy and validation contracts only.

It allows:

- storage manifest contract
- access policy contract
- recovery policy contract
- deletion policy contract
- storage contract report

It forbids:

- no encrypted vault
- no protected storage implementation
- no key material read
- no key material persistence
- no plaintext secret storage
- no raw prompt storage
- no raw provider response storage
- no SQLite schema migration
- no runtime audit append
- no runtime execution
- no network access
- no provider live call
- no real HMAC signing
- no real Merkle construction
- no production autonomy

## Required contract controls

The storage contract requires:

- storage manifest required
- access policy required
- recovery policy required
- deletion policy required
- migration receipt required before implementation

## Manifest rules

A protected storage manifest must include:

- manifest id
- task id
- storage policy id
- contract-only marker
- access policy requirement
- recovery policy requirement
- deletion policy requirement

## Access policy

Access policy must keep:

- plaintext access disabled
- key material access disabled
- implementation disabled

## Recovery policy

Recovery policy must remain policy-only.

No recovery execution is allowed in this slice.

migration receipt required before implementation.

## Deletion policy

Deletion policy must remain policy-only.

No delete execution is allowed in this slice.

Tombstone receipt is required before future implementation.

## Required checks

```bash
python3 -m unittest tests.tracer_bullet.test_protected_evidence_storage_contract -v
make ci
git diff --check
git status --short
```

## Next track

After this bundle is merged and verified, the next branch should be:

`real-hmac-policy-realization-contract-bundle-v1`

That branch should define real HMAC policy-realization contracts without reading key material or producing real signatures in an ungated path.
