# Token Budget Policy V1

## Purpose

Token use must be bounded before AI admission. The token budget ceiling is a
pre-request control, not a post-run accounting note.

## Required Controls

- token budget ceiling
- deterministic local estimate
- hard stop when budget is missing
- hard stop when estimated cost exceeds the budget
- no network call to discover budget

## Current Readiness Limit

The deterministic mock provider has a zero-cost budget. Live provider budgets
remain disabled until explicit future admission evidence exists.

## Failure Behavior

Missing, negative, or over-limit budgets fail closed before a request envelope
can be treated as admissible.
