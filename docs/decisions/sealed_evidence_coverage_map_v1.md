# Sealed Evidence Coverage Map v1

## Verdict

`SEALED_EVIDENCE_COVERAGE_MAP_READY_FOR_LOCAL_TESTS`

This branch adds the first sealed evidence coverage map.

## Scope

Coverage-map and tests only.

It does not:

- enable runtime execution
- access network
- read secret values
- persist secret values
- change SQLite schema
- append audit records
- mutate existing report builders
- expand runtime authority
- implement encrypted vault storage
- implement Merkle proofs
- implement HMAC proofs
- implement zero-knowledge-like proofs
- allow raw evidence storage

## Added surface

- `governance/evidence/sealed_evidence_coverage_map_v1.json`
- `tests/tracer_bullet/test_sealed_evidence_coverage_map.py`

## Coverage statuses

The map uses these explicit statuses:

- `covered`
- `selected_high_risk_only`
- `covered_contract_surface`
- `not_implemented`
- `forbidden`

## Covered surfaces

The map marks these surfaces as covered by embedded sealed evidence payloads:

- model-provider manual smoke report
- failure quarantine manifest

The map marks these as selected high-risk ingress only:

- AppendOnlyLedger high-risk payload ingress
- generic audit payloads

The map marks these as not implemented:

- encrypted evidence vault
- Merkle / HMAC evidence proofs
- zero-knowledge-like evidence proofs

The map marks this as forbidden:

- raw evidence store

## Boundary invariant

The coverage map must not overclaim.

It must explicitly distinguish:

1. fully covered embedded sealed payloads
2. selected high-risk ingress guards
3. future cryptographic proof/vault work that is not implemented
4. raw evidence storage that is forbidden

## Required local verification commands

```bash
python3 -m unittest tests.tracer_bullet.test_sealed_evidence_coverage_map -v
python3 -m unittest tests.tracer_bullet.test_sealed_evidence_redaction_contract -v
python3 -m unittest tests.tracer_bullet.test_sealed_evidence_ledger_ingress -v
python3 -m unittest discover -s tests/tracer_bullet -v
make ci
git diff --check
git status --short
```

## Next step

After merge, the next narrow slice should wire this coverage map into a health-gate check so sealed evidence coverage claims become part of canonical health.
