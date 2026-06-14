# Codex Product Delivery Layer

Layer id: `PRODUCT_DELIVERY_LAYER`

## Purpose

Define how a Codex change becomes a reviewable repository delivery with scoped
diffs, validation, commit, push, PR evidence, and explicit non-claims.

## Connected Loop

product delivery layer -> validation matrix

This layer routes through `CODEX_DELIVERY_PROTOCOL.md`,
`CODEX_VALIDATION_MATRIX.md`, `CODEX_RUNNABLE_PRODUCT_SLICE_GATE.md`, and the
final report.

## Evidence Gate

- Branch, commit SHA, PR link, changed files, local checks, and CI state must be
  recorded.
- Runnable product/tool slice maturity is partial unless a real runnable slice
  has been smoke-tested with evidence.
- PR remains draft unless human review says otherwise.

## Non-Claim Boundary

Repository delivery is not deployment, customer validation, paid signal, or
production acceptance.
