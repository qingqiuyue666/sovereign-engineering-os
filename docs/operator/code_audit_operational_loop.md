# Code Audit Operational Loop

## Purpose

The Code Audit Operational Loop connects private worker handoff, branch review, merge readiness, human review, post-merge memory, and daily reporting into one deterministic operating loop.

## Required Loop Steps

1. AI worker receives handoff packet.
2. AI worker implements branch.
3. AI worker returns final report.
4. Operator builds AI worker result review packet.
5. Operator builds branch audit report.
6. Operator builds merge readiness report.
7. Human reviews.
8. Merge only if approved.
9. Post-merge retrospective is generated.
10. Daily report is updated.

## Required Reports

- AI worker handoff packet.
- AI worker result review packet.
- Branch audit report.
- Merge readiness report.
- Post-merge retrospective report.
- Code audit daily report.

## Required Verification

Verification is caller-provided and summarized. The loop records verification outputs but does not run tests, git, provider calls, network work, shell tools, or external actions internally.

## Human Review Points

Human review is required before merge, before any rollback decision, and before any change that touches protected files, governance files, schema files, blocked capability language, or root integrity expectations.

## Blocked Actions

The loop blocks production autonomy, external execution, live provider calls, secret access, raw prompt persistence, raw provider response persistence, financial execution, trading automation, and any merge that lacks required evidence.

## Success Criteria

The branch is reviewed with deterministic reports, protected boundaries remain intact, required verification is recorded, merge is approved only by a human, and daily reporting is updated after the retrospective.

## Stop Conditions

Stop if required evidence is missing, protected files are unsafe, blocked capability violations appear, sensitive fields appear, deterministic hashes are invalid, or the work attempts kernel expansion instead of production workbench activation.
