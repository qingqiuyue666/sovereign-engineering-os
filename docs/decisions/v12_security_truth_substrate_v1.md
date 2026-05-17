# V12 Security Truth Substrate Decision

## Decision

Accept the descriptor-only V12 security truth substrate as the next branch in
the V12 foundation train.

## Rationale

The branch adds a WAL integrity guard surface without granting WAL file or
SQLite access. It keeps the existing taint, provenance, WAL contract, and
capability token policy gates intact and wires the security truth substrate
directly after leak prevention in health order.

## Non-Authorization

This decision does not authorize real WAL readers, SQLite mutation, provider
calls, network access, secret reads, raw prompt persistence, or raw provider
response persistence.
