# Sealed Evidence Ledger Ingress Wiring v1

## Verdict

`SEALED_EVIDENCE_LEDGER_INGRESS_WIRING_READY_FOR_LOCAL_TESTS`

This branch wires the sealed/redacted evidence contract into selected high-risk `AppendOnlyLedger` payload ingress.

## Scope

Narrow ingress wiring only.

It does not:

- change SQLite schema
- change audit repository persistence semantics
- change ordinary audit payload behavior
- read secret values
- persist secret values
- encrypt or decrypt blobs
- access network
- execute runtime code
- launch browsers
- launch creative software
- execute subprocesses
- checkpoint SQLite
- truncate WAL
- grant runtime authority

## Change

`AppendOnlyLedger.append(...)` now checks payloads before persistence when they are selected as high-risk evidence payloads.

The sealed/redacted evidence contract is required when a payload:

- explicitly declares `evidence_contract: sealed_redaction_v1`
- contains raw plaintext evidence fields such as `raw_prompt`, `raw_provider_response`, or `raw_value`
- contains strong secret-risk keys such as `secret`, `token`, `password`, `api_key`, `credential`, `cookie`, or `private_key`
- contains an `evidence` mapping that itself requires the sealed contract

Plain audit payloads remain accepted.

A generic `classification` key alone does not trigger sealed evidence validation, to avoid breaking existing replay/classification audit records.

## Boundary invariant

Selected high-risk audit payloads cannot enter the append-only ledger unless they satisfy the sealed/redacted evidence contract.

Rejected payloads fail before persistence.

## Tests added

- ordinary payload still appends
- generic classification payload does not trigger sealed contract
- valid sealed evidence payload appends
- raw prompt payload is rejected before persistence
- plaintext secret marker is rejected before persistence
- sealed blob representation requires `sealed_ref`
- ledger source does not introduce network/runtime/secret-read surfaces

## Required local verification commands

```bash
python3 -m unittest tests.tracer_bullet.test_sealed_evidence_redaction_contract -v
python3 -m unittest tests.tracer_bullet.test_sealed_evidence_ledger_ingress -v
python3 -m unittest discover -s tests/tracer_bullet -v
make ci
git diff --check
git status --short
```

## Next step

After merge, the next narrow slice should extend sealed evidence ingress coverage to selected model-provider smoke reports and failure quarantine records without enabling live runtime execution.
