# Codex External Source Intake Registry

Layer id: `EXTERNAL_SOURCE_INTAKE_REGISTRY`

## Purpose

Maintain bounded, reviewable intake for external benchmarks, runtimes,
sandboxes, protocols, security frameworks, supply-chain controls, and
observability tools. This registry is an intake control, not an adoption claim.

## Connected Loop

external source intake -> frontier gap search
frontier gap search -> project absorption shortlist
project absorption shortlist -> benchmark criteria
benchmark criteria -> acceptance cases

The live evidence path is
`reports/checkpoints/external-source-intake-ledger-v1.md`, with freshness
limits recorded in `reports/checkpoints/global-source-freshness-audit-v1.md`.

## Evidence Gate

- Admitted sources must have purpose, URL/source note, status, review owner,
  license/provenance/security risk, benchmark contamination risk, and next
  action.
- Allowed statuses are `VERIFIED_CANONICAL_SOURCE`, `REFERENCE_ONLY`,
  `NEEDS_REVIEW`, `NOT_SEARCHED`, and `REJECTED_FOR_NOW`.
- Source absorption decisions must point to
  `reports/checkpoints/external-project-absorption-shortlist-v1.md`.

## Non-Claim Boundary

Reference-only intake does not prove external benchmark maturity, license
clearance, security clearance, or production suitability.
