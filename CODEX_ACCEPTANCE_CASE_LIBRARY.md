# Codex Acceptance Case Library

Layer id: `ACCEPTANCE_CASE_LIBRARY`

## Purpose

Convert the source-intake and delivery-loop requirements into cases that can be
validated by the Codex execution-system check and human review.

## Connected Loop

acceptance cases -> validation

Cases map to `scripts/codex_execution_system_check_v1.py`,
`CODEX_VALIDATION_MATRIX.md`, and
`reports/checkpoints/real-delivery-benchmark-sample-plan-v1.md`.

## Evidence Gate

| Case | Required evidence | Gate |
| --- | --- | --- |
| Missing required layer file | Validator fails on absent file | Static check |
| Missing source freshness audit | Validator fails on absent report | Static check |
| Local path or overclaim text | Validator flags unsafe text | Unit test |
| Run 01 missing result | Throughput ledger fails phrase gate | Static check |
| Maturity score claims 100 without evidence | Ladder and scorecard require explanation | Review gate |

## Non-Claim Boundary

Acceptance cases prove repository evidence shape. They do not prove benchmark
scores, production safety, or independent approval.
