# Evidence Proof Fixtures v1

## Verdict

`EVIDENCE_PROOF_FIXTURES_READY_FOR_LOCAL_TESTS`

This branch adds typed evidence proof record fixtures.

## Scope

Fixture and tests only.

It does not introduce:

- no runtime execution
- no network access
- no secret read
- no secret persistence
- no SQLite schema change
- no audit append
- no report builder mutation
- no runtime authority
- no encrypted vault
- no real HMAC
- no real HMAC key read
- no real Merkle tree
- no real Merkle proof
- no zero-knowledge-like proof
- no raw evidence store

## Added surface

- `governance/evidence/fixtures/evidence_proof_records_v1.json`
- `tests/tracer_bullet/test_evidence_proof_fixtures.py`

## Fixture posture

The fixture file declares:

`fixture_only_no_runtime`

It is a deterministic sample corpus for the proof contract validator. It is not a crypto implementation and it does not read keys, secrets, files, network, or runtime state.

## Valid fixture records

The valid fixture set covers:

- `sha256_digest`
- `redacted_digest`
- `hmac_placeholder`
- `merkle_placeholder`

## Invalid fixture records

The invalid fixture set covers:

- `real_hmac_key_present`
- `real_merkle_root_present`
- `encrypted_vault_claimed`
- `zero_knowledge_proof_claimed`
- `secret_value_read_claimed`
- `runtime_execution_claimed`
- `network_access_claimed`
- `raw_prompt_present`
- `plaintext_secret_marker_present`

## Boundary invariant

Fixtures must not normalize forbidden behavior.

Any sample claiming real HMAC, real Merkle, encrypted vault, zero-knowledge-like proof, secret read, runtime execution, network access, raw prompt, raw provider response, raw traceback, raw exception dump, or raw evidence storage must be an invalid fixture with an explicit expected failure code.

## Required local verification commands

```bash
python3 -m unittest tests.tracer_bullet.test_evidence_proof_fixtures -v
python3 -m unittest tests.tracer_bullet.test_evidence_proof_contract -v
python3 -m unittest tests.tracer_bullet.test_sealed_evidence_coverage_map -v
python3 -m unittest discover -s tests/tracer_bullet -v
make ci
git diff --check
git status --short
```

## Next step

After merge, the next narrow slice should decide whether proof fixtures need a dedicated health gate or whether full tracer-bullet coverage is enough for this stage.
