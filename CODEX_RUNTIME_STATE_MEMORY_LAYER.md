# Codex Runtime State And Memory Layer

Layer id: `RUNTIME_STATE_MEMORY_LAYER`

## Purpose

Make future runs resume from repository state rather than chat-only memory.

## Connected Loop

real task ledger -> runtime state ledger

Runtime state is recorded in
`reports/checkpoints/runtime-state-ledger-v1.md`,
`reports/checkpoints/continuous-execution-state.md`, and final reports.

## Evidence Gate

- State records must include current branch, PR, preserved residue, executed
  checks, skipped checks, blockers, and next action.
- State does not replace source control, PR checks, or human review.

## Non-Claim Boundary

Repository memory can preserve run context. It does not prove long-term
autonomy or production-grade runtime state.
