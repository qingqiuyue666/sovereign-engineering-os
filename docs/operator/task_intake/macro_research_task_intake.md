# Macro Research Task Intake

## task goal

Produce research-only templates for manual macro / XAUUSD signal review.

## allowed files

- docs/operator/examples/macro_signal_research/**
- docs/operator/forms/**
- tests/tracer_bullet/**

## forbidden files

- broker or API execution code
- trading automation code
- README.md
- Makefile

## required tests

- focused macro sample pack tests
- full tracer-bullet discovery
- make ci

## blocked capabilities

- no auto order execution
- no broker/API execution
- no leverage instructions
- final decisions remain manual

## output format

Templates and blocked-rule docs only.

## rollback expectation

Rollback the macro research template slice as a unit.

## human review requirement

Human review required before any manual use.
