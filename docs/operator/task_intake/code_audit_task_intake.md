# Code Audit Task Intake

## task goal

Produce private code-audit assets or deterministic validators without expanding the kernel.

## allowed files

- docs/operator/**
- kernel/runtime/**
- tests/tracer_bullet/**

## forbidden files

- README.md
- Makefile
- governance/root/**
- health gate wiring files

## required tests

- focused tracer-bullet tests
- full tracer-bullet discovery
- schema discovery
- acceptance discovery
- make ci

## blocked capabilities

- no provider execution
- no production autonomy
- no network execution
- no subprocess execution

## output format

Deterministic docs, validators, and exact final report.

## rollback expectation

Rollback the code-audit slice as a unit.

## human review requirement

Human review required before merge.
