# Evidence Proof Contract Health Gate v1

## Verdict

`EVIDENCE_PROOF_CONTRACT_HEALTH_GATE_READY_FOR_LOCAL_TESTS`

This branch wires the evidence proof contract into the canonical health gate.

## Scope

Health-gate wiring only.

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

## Change

`Makefile` now declares:

```make
test-evidence-proof-contract:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_evidence_proof_contract -v
```

`health` now runs evidence proof contract after sealed evidence coverage and before schemas:

```make
health: test-root-integrity test-sealed-evidence-coverage test-evidence-proof-contract test-schemas test-tracer-bullet test-acceptance diff-check
```

`ci` remains:

```make
ci: health
```

## Boundary invariant

Evidence proof contract validation is now part of canonical `make ci` health.

This does not promote placeholder proof records into real cryptographic proof implementation.

`hmac_placeholder` remains placeholder-only.

`merkle_placeholder` remains placeholder-only.

Encrypted vault, real HMAC, real Merkle tree, and zero-knowledge-like proof remain not implemented.

## Root manifest update

`Makefile` is a root critical file.

This branch updates `governance/root/root_manifest_v1.json` to bind the new Makefile blob hash so the root integrity gate does not fail closed on the intended health-gate change.

## Required local verification commands

```bash
python3 -m unittest tests.tracer_bullet.test_evidence_proof_contract -v
python3 -m unittest tests.tracer_bullet.test_evidence_proof_contract_health_gate_wiring -v
python3 -m unittest tests.tracer_bullet.test_sealed_evidence_coverage_health_gate_wiring -v
python3 -m unittest tests.tracer_bullet.test_root_integrity_verifier -v
python3 -m unittest discover -s tests/tracer_bullet -v
make ci
git diff --check
git status --short
```

## Next step

After merge, the next narrow slice should add typed proof record fixtures or schemas, not real cryptographic execution.
