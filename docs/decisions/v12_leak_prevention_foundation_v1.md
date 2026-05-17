# V12 Leak Prevention Foundation Decision

## Decision

Accept the V12 leak-prevention foundation as an executable, deterministic,
read-only gate layer before the remaining V12 foundation train.

## Rationale

The branch provides a shared scanner engine and routes the AI context firewall,
anti-exfiltration gate, and repository hygiene gate through that engine. The
Makefile health order now evaluates `test-leak-prevention-foundation` directly
after root integrity, before the broader V12 aggregate and before prior V11
runtime, provider, evidence, and autonomy gates.

## Non-Authorization

This decision does not authorize production autonomy, live provider calls, live
Telegram sending, network access, daemon execution, real vault/KMS/keyring use,
real SQLite WAL reading, OSINT ingestion, or dashboard runtime.
