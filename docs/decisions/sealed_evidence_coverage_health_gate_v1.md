# Sealed Evidence Coverage Health Gate v1

## Verdict

`SEALED_EVIDENCE_COVERAGE_HEALTH_GATE_READY_FOR_LOCAL_TESTS`

This branch wires the sealed evidence coverage map into the canonical health gate.

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
- no Merkle proof
- no HMAC proof
- no zero-knowledge-like proof
- no raw evidence store

## Change

`Makefile` now declares:

```make
test-sealed-evidence-coverage:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_sealed_evidence_coverage_map -v
```

`health` now runs sealed evidence coverage immediately after root integrity and before schemas, tracer-bullet, acceptance, and diff checks:

```make
health: test-root-integrity test-sealed-evidence-coverage test-schemas test-tracer-bullet test-acceptance diff-check
```

`ci` remains:

```make
ci: health
```

## Boundary invariant

Sealed evidence coverage claims are now checked as part of canonical `make ci` health.

The coverage map must continue to distinguish:

- covered embedded sealed payloads
- selected high-risk-only ingress guards
- covered contract surfaces
- not implemented cryptographic proof/vault work
- forbidden raw evidence storage

## Root manifest update

`Makefile` is a root critical file.

This branch updates `governance/root/root_manifest_v1.json` to bind the new Makefile blob hash so the root integrity gate does not fail closed on the intended health-gate change.

## Required local verification commands

```bash
python3 -m unittest tests.tracer_bullet.test_sealed_evidence_coverage_map -v
python3 -m unittest tests.tracer_bullet.test_sealed_evidence_coverage_health_gate_wiring -v
python3 -m unittest tests.tracer_bullet.test_root_integrity_verifier -v
python3 -m unittest discover -s tests/tracer_bullet -v
make ci
git diff --check
git status --short
```

## Next step

After merge, the next narrow slice should start cryptographic proof planning as a contract-only layer, without implementing an encrypted vault or reading secrets.
