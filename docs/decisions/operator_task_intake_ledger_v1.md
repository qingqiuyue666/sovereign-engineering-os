# V12 Operator Task Intake Ledger Decision

## Decision

Accept the local operator task intake and run ledger branch as a digest-only
foundation layer.

## Rationale

The branch creates task envelopes from normalized descriptor metadata, computes
deterministic digest refs, and writes caller-scoped ledger files without raw
input persistence or provider execution.

## Non-Authorization

This decision does not authorize network access, real secret reads, AI provider
calls, SQLite mutation, production autonomy, daemon execution, Telegram sending,
or OSINT ingestion.
