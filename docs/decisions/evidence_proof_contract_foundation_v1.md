# Evidence Proof Contract Foundation v1

## Verdict

`EVIDENCE_PROOF_CONTRACT_FOUNDATION_READY_FOR_LOCAL_TESTS`

This branch adds the first evidence proof record contract foundation.

## Scope

Contract and tests only.

It does not:

- implement encrypted vault storage
- read secret values
- persist secret values
- read real HMAC keys
- generate real HMAC signatures
- build real Merkle trees
- verify real Merkle proofs
- build zero-knowledge-like proofs
- access network
- execute runtime code
- change SQLite schema
- append audit records
- mutate report builders
- create raw evidence storage

## Added surface

- `kernel/evidence/evidence_proof_contract.py`
- `tests/tracer_bullet/test_evidence_proof_contract.py`

## Allowed proof kinds

The contract accepts only these proof kinds:

- `sha256_digest`
- `redacted_digest`
- `hmac_placeholder`
- `merkle_placeholder`

## Boundary invariant

This branch defines proof record shape and placeholder semantics only.

`hmac_placeholder` is not a real HMAC signature.

`merkle_placeholder` is not a real Merkle tree or proof.

No HMAC key, Merkle root, encrypted vault, secret value, runtime execution, network access, raw prompt, raw provider response, raw traceback, or raw exception dump may enter a proof record.

## Coverage map update

`governance/evidence/sealed_evidence_coverage_map_v1.json` now includes:

- `evidence_proof_contract_foundation` as `covered_contract_surface`

It still marks these as `not_implemented`:

- encrypted evidence vault
- real Merkle / HMAC evidence proofs
- zero-knowledge-like evidence proofs

## Required local verification commands

```bash
python3 -m unittest tests.tracer_bullet.test_evidence_proof_contract -v
python3 -m unittest tests.tracer_bullet.test_sealed_evidence_coverage_map -v
python3 -m unittest tests.tracer_bullet.test_sealed_evidence_coverage_health_gate_wiring -v
python3 -m unittest discover -s tests/tracer_bullet -v
make ci
git diff --check
git status --short
```

## Next step

After merge, the next narrow slice should wire the proof contract into the sealed evidence coverage health gate, not implement real cryptography yet.
