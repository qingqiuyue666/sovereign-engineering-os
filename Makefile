.PHONY: ci test-root-integrity test-sealed-evidence-coverage test-schemas test-tracer-bullet test-acceptance diff-check health

PYTHON ?= python3

ci: health

health: test-root-integrity test-sealed-evidence-coverage test-schemas test-tracer-bullet test-acceptance diff-check

test-root-integrity:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_root_integrity_verifier -v

test-sealed-evidence-coverage:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest tests.tracer_bullet.test_sealed_evidence_coverage_map -v

test-schemas:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests/schemas

test-tracer-bullet:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests/tracer_bullet

test-acceptance:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s validation/tests/acceptance

diff-check:
	git diff --check
	test -z "$$(git status --short)"
