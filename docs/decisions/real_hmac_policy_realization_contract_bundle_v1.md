# Real HMAC Policy Realization Contract Bundle v1

## Verdict

`REAL_HMAC_POLICY_REALIZATION_CONTRACT_BUNDLE_READY_FOR_LOCAL_TESTS`

This branch adds the real HMAC policy-realization contract layer.

The branch moves readiness to:

`real_hmac_policy_realization_contract_ready`

It is not 100% complete.

## Scope

This branch includes:

- real HMAC policy-realization health gate
- real HMAC policy-realization contract map
- deterministic HMAC policy contract validators
- typed valid and invalid HMAC policy fixtures
- HMAC policy-realization runbook
- final runtime health alignment
- final completion audit update
- root manifest update for Makefile
- health wiring test updates

## Boundary

This branch is contract-only.

It introduces:

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

## External standard references

NIST FIPS 198-1 defines HMAC as a keyed-hash message authentication code using a shared secret key and an approved cryptographic hash function.

Python's `hmac` documentation recommends `compare_digest()` instead of equality comparison when verifying digests to reduce timing-attack exposure.

This bundle converts those requirements into contract constraints only. It does not call `hmac`, does not call `compare_digest()`, and does not create or verify real signatures.

## Health gate update

`Makefile` declares:

```make
test-real-hmac-policy-realization:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_real_hmac_policy_realization_contract -v
```

Canonical health order becomes:

```make
health: test-root-integrity test-sealed-evidence-coverage test-evidence-proof-contract test-evidence-proof-fixtures test-final-runtime-contracts test-gated-provider-transport test-runtime-sealed-receipt test-generic-payload-shadow test-protected-evidence-storage test-real-hmac-policy-realization test-schemas test-tracer-bullet test-acceptance diff-check
```

## Contract surfaces

Added:

- `governance/evidence/real_hmac_policy_realization_contract_v1.json`
- `kernel/evidence/real_hmac_policy_realization_contract.py`
- `governance/evidence/fixtures/real_hmac_policy_realization_fixtures_v1.json`
- `docs/runbooks/real_hmac_policy_realization_contract_v1.md`

The validators cover:

- real HMAC policy
- HMAC key policy
- signing authority policy
- verifier policy
- signature receipt contract
- rotation policy
- policy realization report

## Completion audit update

The final completion audit records:

- `readiness_band`: `real_hmac_policy_realization_contract_ready`
- `estimated_completion_percent`: `93`
- `test-real-hmac-policy-realization` as part of canonical health
- real HMAC policy-realization surfaces as contract-ready

It still refuses:

- 100% completion claim
- real HMAC signature execution
- key material access
- protected storage implementation
- live provider execution claim
- production autonomy claim

## Required local verification commands

```bash
python3 -m unittest tests.tracer_bullet.test_real_hmac_policy_realization_contract -v
python3 -m unittest tests.tracer_bullet.test_final_system_completion_audit -v
python3 -m unittest tests.tracer_bullet.test_final_runtime_contracts -v
python3 -m unittest tests.tracer_bullet.test_protected_evidence_storage_contract -v
python3 -m unittest tests.tracer_bullet.test_generic_payload_shadow_contract -v
python3 -m unittest tests.tracer_bullet.test_gated_provider_transport_contracts -v
python3 -m unittest tests.tracer_bullet.test_runtime_sealed_receipt_contracts -v
python3 -m unittest tests.tracer_bullet.test_root_integrity_health_gate_wiring -v
python3 -m unittest discover -s tests/tracer_bullet -v
make ci
git diff --check
git status --short
```

## Next step

After merge, the next branch should be:

`real-merkle-proof-realization-v1`

That branch should define Merkle proof realization contracts before any proof-tree implementation mutates evidence behavior.
