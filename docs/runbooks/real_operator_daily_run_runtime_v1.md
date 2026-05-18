# Real Operator Daily Run Runtime v1

## Purpose
Bounded local-only operator daily run runtime. Validates daily run requests,
enforces human review and approval gates, binds evidence/replay/patch/execution
receipts, and produces deterministic receipts. No autonomous production action.

## Boundaries
- no autonomous production action
- no trading
- no network
- no secret material
- no env reads
- human review required
- approval required
- single operator action plan only
- contract-only in v1

## Architecture

### DailyRunRequest
Immutable daily run request requiring: run_id, operator_id, evidence_summary,
replay_receipt, human_review, approval, action_plan. Rejects production,
trading, and network actions.

### RunWindow
Validates run time windows (daily_review, incident_response, scheduled_maintenance).

### ReviewGate
Human review and approval gate. Both must be present and valid.

### OperatorRunReceipt / OperatorRunFailureReceipt
Deterministic receipts. No production action. No wall-clock.

### OperatorRunSecurity
Security boundary: no autonomous production action, no trading, no network,
human review required, approval required.

### OperatorRunCanonicalHash
Deterministic hash generation.

## Operations
1. create_request — immutable daily run request
2. validate_window — run window validation
3. validate_review — review and approval gate validation
4. approve — full approval pipeline
5. produce_failure_receipt — failure receipt generation

## Required Fields
- run_id: unique run identifier (rejected if missing)
- operator_id: operator identifier (rejected if missing)
- evidence_summary_hash: evidence summary binding (rejected if missing)
- replay_receipt_hash: replay receipt binding (rejected if missing)
- human_review_id: human review identifier (rejected if missing)
- approval_id: approval identifier (rejected if missing)
- action_plan: single operator action plan

## Receipt Types
- OperatorRunReceipt: approval receipt (run, operator, evidence/replay binding, review/approval status)
- OperatorRunFailureReceipt: failure receipt with code and reason

## Scope
Contract-only in v1. No autonomous production action. All receipts deterministic.
