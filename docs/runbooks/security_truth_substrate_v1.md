# V12 Security Truth Substrate Runbook

## Purpose

Validate truth-substrate metadata before later runtime, evidence, and provider
contracts rely on it.

## Gates

- `test-wal-integrity-guard`
- `test-taint-propagation`
- `test-artifact-provenance`
- `test-wal-integrity-contract`
- `test-capability-token-policy`
- `test-security-truth-substrate`

## Operator Procedure

1. Run `make test-security-truth-substrate`.
2. Run `python3 -m unittest discover -s tests/tracer_bullet -v`.
3. Run `python3 -m unittest discover -s tests/schemas -v`.
4. Run `python3 -m unittest discover -s validation/tests/acceptance -v`.
5. Run `make ci`.

## Boundary

The WAL guard accepts only caller-supplied descriptors. It does not import
sqlite3, open files, read `.db` or `.db-wal` files, access secrets, contact
providers, or persist prompts or provider responses.
