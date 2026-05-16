# Root Integrity Health Gate Wiring v1

## Verdict

`ROOT_INTEGRITY_HEALTH_GATE_WIRING_READY_FOR_LOCAL_TESTS`

This branch wires the existing root integrity verifier into the canonical `health` gate.

## Scope

This is health-gate wiring only.

It does not:

- change root verifier semantics
- execute runtime code
- access network
- read secret values
- persist secret values
- repair files
- grant runtime authority
- launch browsers
- launch creative software
- execute subprocesses beyond the existing unittest invocation surface
- checkpoint SQLite
- truncate WAL

## Change

`Makefile` now declares:

```make
test-root-integrity:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_root_integrity_verifier -v
```

`health` now runs root integrity first:

```make
health: test-root-integrity test-schemas test-tracer-bullet test-acceptance diff-check
```

`ci` remains:

```make
ci: health
```

## Boundary invariant

Root integrity verification now precedes schema, tracer-bullet, acceptance, and diff checks in the canonical health gate.

Failure of root integrity prevents normal trust in later health claims and requires:

`read_only_seed_recovery_required`

## Required local verification commands

```bash
python3 -m unittest tests.tracer_bullet.test_root_integrity_verifier -v
python3 -m unittest tests.tracer_bullet.test_root_integrity_health_gate_wiring -v
python3 -m unittest discover -s tests/tracer_bullet -v
make ci
git diff --check
git status --short
```

## Next step

After merge, the next narrow slice should add a sealed/redacted evidence contract so evidence can prove integrity without becoming a plaintext leak source.
