# Real HMAC Policy Realization Contract v1

## Status

`REAL_HMAC_POLICY_REALIZATION_CONTRACT_READY`

This runbook defines contract-only HMAC policy realization.

It is not a real HMAC implementation.

## Contract-only HMAC policy realization

This track defines policy and validation contracts only.

It allows:

- HMAC key policy contract
- signing authority policy contract
- verifier policy contract
- signature receipt contract
- rotation policy contract
- policy realization report

It forbids:

- no real HMAC signature
- no HMAC verification runtime
- no key generation
- no key material read
- no key material persistence
- no secret read
- no secret persistence
- no plaintext secret storage
- no SQLite schema migration
- no runtime audit append
- no runtime execution
- no network access
- no provider live call
- no production autonomy

## Digest policy

Allowed digest algorithms in this contract slice:

- sha256
- sha384
- sha512

## Verification policy

constant-time compare required before real verification.

Real verification remains disabled in this slice.

## Protected storage prerequisite

protected storage contract required.

No key material may be read or persisted until a future explicitly authorized implementation slice.

## Required checks

```bash
python3 -m unittest tests.tracer_bullet.test_real_hmac_policy_realization_contract -v
make ci
git diff --check
git status --short
```

## Next track

After this bundle is merged and verified, the next branch should be:

`real-merkle-proof-realization-v1`

That branch should define real Merkle proof realization contracts before any proof tree implementation mutates evidence behavior.
