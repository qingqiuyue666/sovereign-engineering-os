.PHONY: ci test-root-integrity test-sealed-evidence-coverage test-evidence-proof-contract test-evidence-proof-fixtures test-final-runtime-contracts test-gated-provider-transport test-runtime-sealed-receipt test-generic-payload-shadow test-schemas test-tracer-bullet test-acceptance diff-check health

PYTHON ?= python3

ci: health

health: test-root-integrity test-sealed-evidence-coverage test-evidence-proof-contract test-evidence-proof-fixtures test-final-runtime-contracts test-gated-provider-transport test-runtime-sealed-receipt test-generic-payload-shadow test-schemas test-tracer-bullet test-acceptance diff-check

test-root-integrity:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_root_integrity_verifier -v

test-sealed-evidence-coverage:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_sealed_evidence_coverage_map -v

test-evidence-proof-contract:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_evidence_proof_contract -v

test-evidence-proof-fixtures:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_evidence_proof_fixtures -v

test-final-runtime-contracts:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_final_runtime_contracts -v

test-gated-provider-transport:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_gated_provider_transport_contracts -v

test-runtime-sealed-receipt:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_runtime_sealed_receipt_contracts -v

test-generic-payload-shadow:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_generic_payload_shadow_contract -v

test-schemas:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests/schemas

test-tracer-bullet:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests/tracer_bullet

test-acceptance:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s validation/tests/acceptance

diff-check:
	git diff --check
	test -z "$$(git status --short)"
