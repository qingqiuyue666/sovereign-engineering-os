# V12 Leak Prevention Foundation Runbook

## Purpose

This branch establishes deterministic leak-prevention gates before any V12 runtime,
provider, vault, domain, or notification surface is allowed to execute.

## Implemented Gates

- Security classification validation for PUBLIC, INTERNAL, CONFIDENTIAL, SECRET,
  and CROWN_JEWEL.
- Core secret scanning through one shared scanner engine.
- Pure environment sanitization over caller-provided mappings.
- AI context firewall redaction that preserves JSON shape.
- Anti-exfiltration blocking for contaminated outbound payloads.
- Read-only repository hygiene checks for forbidden paths and secret-like content.
- Aggregate Makefile gate: `test-leak-prevention-foundation`.

## Operator Procedure

1. Run `make test-leak-prevention-foundation`.
2. Run `python3 -m unittest discover -s tests/tracer_bullet -v`.
3. Run `python3 -m unittest discover -s tests/schemas -v`.
4. Run `python3 -m unittest discover -s validation/tests/acceptance -v`.
5. Run `make ci`.

## Boundaries

- No file quarantine, rewrite, deletion, or automatic repair is performed.
- No provider calls, network calls, daemon runtime, Telegram send, vault runtime,
  keyring runtime, KMS access, SQLite WAL reads, OSINT ingestion, or dashboard
  runtime is authorized by this foundation.
- SECRET requires redaction before AI context or external output.
- CROWN_JEWEL is forbidden from AI context and external output.
