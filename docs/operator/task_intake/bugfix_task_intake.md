# Bugfix Task Intake

## task goal

Fix a bounded defect without broadening scope.

## allowed files

- exact bugfix target files
- matching tests

## forbidden files

- unrelated modules
- README.md
- Makefile
- root integrity files

## required tests

- focused failing tests first
- full tracer-bullet discovery if runtime surface changes
- make ci

## blocked capabilities

- no provider execution
- no network execution
- no subprocess execution
- no broad rewrite

## output format

Minimal patch plus exact verification results.

## rollback expectation

Rollback the bugfix patch as a unit.

## human review requirement

Human review required before merge.
