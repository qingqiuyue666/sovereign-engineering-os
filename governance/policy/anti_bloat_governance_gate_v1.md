# Anti-Bloat Governance Gate V1

## Purpose

This gate prevents SEOS from expanding because a feature sounds impressive,
complete, or future-proof. New runtime modules and architecture surfaces are
rejected by default unless hard evidence proves that existing modules cannot
solve the current operator problem.

## Default Decision

Default decision: `REJECT_NEW_RUNTIME_MODULE`.

An exception is allowed only when all checklist items below are satisfied and
the release readiness evidence references the proof.

## Required Checklist

- Real external use case evidence exists and identifies the blocker.
- Existing modules, scripts, docs, and CLI surfaces were checked first.
- The proposed change is lower complexity than available alternatives.
- Local-first operation remains possible without a cloud service dependency.
- Human approval gates for risky execution remain intact.
- AI-related changes record token, cost, and risk impact.
- The change does not introduce Kubernetes, Temporal, FoundationDB, DBOS,
  Rekor, OPA, SpiceDB, or a similar heavy dependency.
- The change does not claim OS-level sandboxing, RPA, computer control, secret
  management, EDR, or filesystem permission enforcement.
- The change is the smallest repair for a hard evidence blocker, not a
  speculative product expansion.

## Release Readiness Use

Release readiness must cite this gate and record either:

- `ANTI_BLOAT_GATE_PASSED`, with evidence for every checklist item; or
- `ANTI_BLOAT_GATE_BLOCKED`, with the blocker and required human decision.

Missing anti-bloat evidence fails closed.
