# Decision Report Foundation v1

## Purpose
Bounded local-only decision report foundation. Validates decision
reports without publishing to production.

## Boundaries
- no missing decision id
- no missing evidence links
- no missing confidence rationale
- no missing friction summary
- no missing human review
- no unsupported action
- no overclaim (max confidence 0.95)
- no production report publication in v1

## Operations
1. validate_decision_report — structural validation
2. validate_report_evidence_links — evidence link check
3. validate_report_non_overclaim — confidence bounds
4. produce_decision_report_receipt — full receipt production

## Scope
Contract-only. Does not publish reports.
