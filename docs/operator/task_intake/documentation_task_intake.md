# Documentation Task Intake

## task goal

Produce or align bounded documentation artifacts without implementation drift.

## allowed files

- exact docs paths named in the task
- matching tests if doc coverage exists

## forbidden files

- runtime modules unless explicitly authorized
- README.md unless explicitly authorized
- Makefile

## required tests

- focused tracer-bullet doc tests
- full tracer-bullet discovery when adding coverage
- make ci

## blocked capabilities

- no provider execution
- no runtime rewrites
- no governance rewrites
- no hidden scope expansion

## output format

Docs-only change set plus exact verification results.

## rollback expectation

Rollback the docs slice as a unit.

## human review requirement

Human review required before merge.
