# V12 Operator CLI Foundation Decision

## Decision

Accept the local V12 operator CLI foundation as a dry-run and validation-only
surface.

## Rationale

The CLI routes through existing deterministic validators and task contract
helpers. It keeps legacy V12 foundation commands available while adding the
operator command forms required by the branch train.

## Non-Authorization

This decision does not authorize provider calls, network access, secret reads,
production autonomy, daemon execution, dashboard runtime, Telegram sending, or
OSINT ingestion.
