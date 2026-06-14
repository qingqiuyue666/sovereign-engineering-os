# Codex Strong Validation Layer

Layer id: `STRONG_VALIDATION_LAYER`

## Purpose

Make the internal execution loop machine-checkable through required files,
critical sections, report evidence, maturity verdicts, safety text checks, and
focused negative tests.

## Connected Loop

acceptance cases -> validation

Validation runs through `scripts/codex_execution_system_check_v1.py`,
`python3 -m py_compile`, focused unit tests, `make codex-execution-system-check`,
and `git diff --check`.

## Evidence Gate

- Required files and checkpoint reports must exist.
- Eleven layer files must contain `Connected Loop` and `Evidence Gate` sections.
- Gap gate files must contain `Gate`, `Evidence Path`, and `Non-Claim Boundary`.
- Final report, scorecard, source audit, throughput ledger, and maturity ladder
  are explicitly checked.
- Unsupported positive claims and local machine path markers are rejected.

## Non-Claim Boundary

Static validation is local repository evidence. It does not prove CI, branch
protection, production observability, or runtime sandbox enforcement.
