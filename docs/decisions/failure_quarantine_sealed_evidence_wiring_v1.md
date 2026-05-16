# Failure Quarantine Sealed Evidence Wiring v1

## Verdict

`FAILURE_QUARANTINE_SEALED_EVIDENCE_WIRING_READY_FOR_LOCAL_TESTS`

This branch wires failure quarantine manifests to an embedded sealed evidence payload.

## Scope

Failure quarantine evidence wiring only.

It does not:

- enable runtime execution
- access network
- read secret values
- persist secret values
- persist raw traceback dumps
- persist raw exception dumps
- mutate input files
- copy input file contents
- copy raw cell values
- execute subprocesses
- launch browsers
- launch creative software
- change SQLite schema
- checkpoint SQLite
- truncate WAL
- grant runtime authority
- implement encrypted vault storage

## Change

`write_failure_quarantine(...)` now embeds `sealed_evidence_payload` in `failure_manifest.json`.

The sealed evidence payload uses:

- `evidence_contract: sealed_redaction_v1`
- `classification: secret`
- `representation: redacted_digest`

The sealed payload records only:

- job id
- manifest type
- sanitized error type
- sanitized error-message SHA-256
- non-authority posture
- execution capability posture
- boundary flags
- human review requirement

It excludes:

- raw traceback
- raw exception dump
- secret values
- input file contents
- raw cell values
- runtime authority
- network access
- subprocess execution

## Boundary invariant

Failure quarantine manifests must not become a plaintext leak surface.

The sealed evidence builder rejects manifests that claim any of the following occurred:

- runtime execution
- network access
- subprocess execution
- runtime authority grant
- secret read
- secret persistence
- raw traceback persistence
- raw exception dump persistence
- input file mutation
- raw cell value copy

## Tests added

- failure manifest still writes normally
- sealed evidence payload is embedded and contract-valid
- secret markers and raw traceback-like text do not leak into sealed payload
- runtime boundary violation is rejected by the builder
- existing bad job id / truncation / sentinel redaction behavior remains intact
- source does not introduce runtime/network/secret-read surfaces

## Required local verification commands

```bash
python3 -m unittest tests.personal_ai.test_failure_quarantine -v
python3 -m unittest tests.tracer_bullet.test_sealed_evidence_redaction_contract -v
python3 -m unittest discover -s tests/personal_ai -v
python3 -m unittest discover -s tests/tracer_bullet -v
make ci
git diff --check
git status --short
```

## Next step

After merge, the next narrow slice should add a sealed evidence coverage map that identifies which reports are protected by sealed evidence payloads and which evidence surfaces remain unprotected.
