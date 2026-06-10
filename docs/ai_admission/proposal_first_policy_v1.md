# Proposal First Policy V1

## Purpose

AI-assisted work must be proposal-first. The model may produce a bounded
proposal artifact, but it must not apply patches, execute tools, open PRs, or
claim authority.

## Required Flow

1. Create a request envelope from sanitized context.
2. Produce a model output artifact that is stored as proposal evidence.
3. Bind the output to a response receipt.
4. Require human approval before patch.
5. Run validation before PR.

## Rejected Flow

Any flow that applies a diff directly from model output, skips human review,
or treats provider text as a PASS result is rejected.

## Evidence Boundary

Proposal artifacts may include summaries, digests, and reviewer notes. They
must not include raw secrets, raw provider responses, or hidden private state.
