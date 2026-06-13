# Evidence and No-Fake-Completion Rules

## Purpose

Define evidence levels and prevent agents from converting repository artifacts
into unsupported completion claims.

## Evidence Levels

### Level 0: AI Self-Report

AI self-report is not enough. A statement from an agent is a claim, not
evidence.

### Level 1: Local Command Output

Local command output can prove a local check ran in the current workspace. It
does not prove CI, external validation, customer feedback, delivery acceptance,
payment, or production deployment.

### Level 2: Git Diff and Commit

`git diff`, staged diff, and commit hashes prove repository changes exist in a
branch. They do not prove the changes were merged, accepted, deployed, or used
by real customers.

### Level 3: CI and GitHub Checks

CI / GitHub checks provide remote engineering verification for a branch or PR.
If CI is pending, failed, skipped, or unavailable, report that state directly.

### Level 4: Real-World Source Evidence

Real user, customer, payment, acceptance, delivery, audit, or market evidence
requires source records with date, actor, scope, outcome, and permission or
redaction status where needed.

## No-Fake-Completion Rules

- No CI, no engineering completion.
- No customer feedback, no real validation.
- No payment, no commercial validation.
- No acceptance, no delivery completion.
- No production deployment record, no production deployment claim.
- No source record, no external evidence claim.
- No repeated buyer records, no market-proof claim.
- No human approval at a high-risk gate, no authority to cross that gate.

## Repository-Ready vs Real-World-Ready

Repository files can make a protocol, checklist, template, or command layer
ready for review. That does not make the underlying market, delivery,
customer, payment, deployment, or maturity claim true.

## Required Evidence Language

Use precise labels:

- `READY_FOR_REVIEW` for repository artifacts that are complete enough to
  inspect.
- `HUMAN_ACTION_REQUIRED` when the next action requires human execution.
- `EVIDENCE_PENDING` when a stronger claim depends on future source records.
- `MARKET_PROOF_PENDING` when buyer and paid-signal evidence is missing.
- `REAL_DELIVERY_PENDING` when accepted delivery evidence is missing.

Do not replace these labels with stronger language unless matching evidence
exists.
