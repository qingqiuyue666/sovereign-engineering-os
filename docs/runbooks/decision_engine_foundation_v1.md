# Decision Engine Foundation v1

## Purpose
Bounded local-only decision engine foundation. Validates decision
requests without executing trades.

## Boundaries
- no multiple actions
- no confidence overclaim (max 0.95)
- no offensive action when confidence below threshold (0.70)
- no missing friction fields
- no missing human review
- no production order execution
- no real trade execution in v1

## Allowed Actions
HOLD, FLAG, ESCALATE, REVIEW

## Forbidden Actions
BUY, SELL, EXECUTE, ORDER, TRADE, SHORT, COVER

## Operations
1. validate_decision_request — structural validation
2. validate_single_action_contract — single action enforcement
3. validate_confidence_gate — confidence threshold gate
4. validate_friction_gate — friction data gate
5. produce_decision_engine_receipt — full receipt production

## Scope
Contract-only. Does not execute any trades.
