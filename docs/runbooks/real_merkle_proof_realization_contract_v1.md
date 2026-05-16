# Real Merkle Proof Realization Contract v1

## Status

`REAL_MERKLE_PROOF_REALIZATION_CONTRACT_READY`

This runbook defines contract-only Merkle proof realization.

It is not a real Merkle tree implementation.

## Contract-only Merkle proof realization

This track defines policy and validation contracts only.

It allows:

- Merkle tree manifest contract
- leaf digest policy contract
- node digest policy contract
- proof path contract
- verifier receipt contract
- root commitment receipt contract
- policy realization report

It forbids:

- no real Merkle tree build
- no Merkle proof verification runtime
- no root commitment publication
- no evidence append behavior mutation
- no raw evidence store
- no protected storage implementation
- no secret read
- no secret persistence
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

## Leaf policy

digest-only leaf payload policy.

Raw leaf payloads are forbidden.

## Node policy

Internal nodes require ordered child digest contracts before any real tree implementation.

Domain separation is required before a future real tree implementation.

## Proof path policy

Proof paths are sibling-digest path contracts only.

Raw sibling payloads are forbidden.

## Root commitment policy

Root commitment publication is forbidden in this slice.

Human authorization is required before any future root publication.

## Required checks

```bash
python3 -m unittest tests.tracer_bullet.test_real_merkle_proof_realization_contract -v
make ci
git diff --check
git status --short
```

## Next track

After this bundle is merged and verified, the next branch should be:

`generic-audit-payload-full-enforcement-bundle-v1`

That branch should promote generic payload typing from shadow validation to full enforcement only after compatibility inventory and migration receipts are present.
