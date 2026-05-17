# Operator Daily Run Foundation v1

## Purpose
Bounded local-only operator daily run foundation. Validates daily run
requests without executing any actions.

## Boundaries
- no autonomous production action
- no missing human review
- no missing runbook reference
- no missing evidence summary
- no action without approval
- no real execution in v1

## Operations
1. validate_operator_daily_run_request — structural validation
2. validate_operator_run_window — window validation
3. validate_operator_review_gate — review gate validation
4. produce_operator_daily_run_receipt — full receipt production

## Scope
Contract-only. Does not execute any actions.
