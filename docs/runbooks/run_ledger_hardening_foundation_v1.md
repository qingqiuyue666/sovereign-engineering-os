# Run Ledger Hardening Foundation v1

## Purpose
Bounded local-only run ledger hardening foundation. Validates ledger
entries without writing to any ledger.

## Boundaries
- no missing run id
- no missing operator id
- no missing status
- no invalid transition
- no mutable ledger claim
- no missing evidence link
- no ledger write in v1

## Valid Status Transitions
pending → running, cancelled
running → completed, failed, cancelled
completed → rolled_back
failed → rolled_back, pending

## Operations
1. validate_run_ledger_entry — structural validation
2. validate_run_sequence_contract — sequence number check
3. validate_run_status_contract — transition validity
4. produce_run_ledger_receipt — full receipt production

## Scope
Contract-only. Does not write to any ledger.
