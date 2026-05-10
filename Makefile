.PHONY: ci test-schemas test-tracer-bullet test-acceptance diff-check health

PYTHON ?= python3

ci: health

health: test-schemas test-tracer-bullet test-acceptance diff-check

test-schemas:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests/schemas

test-tracer-bullet:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests/tracer_bullet

test-acceptance:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s validation/tests/acceptance

diff-check:
	git diff --check
	test -z "$$(git status --short)"
