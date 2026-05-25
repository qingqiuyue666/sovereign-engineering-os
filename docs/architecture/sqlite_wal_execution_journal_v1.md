# SQLite WAL Execution Journal V1

## Purpose

Persist command admission, quarantine, and execution receipt evidence in a local
append-only SQLite database using WAL mode.

## Architecture

The journal owns three append-only tables:

- `admission_events`
- `quarantine_events`
- `execution_receipts`

Each row stores event metadata, a deterministic `content_hash`, and the previous
event hash. `created_at` is recorded for observation but excluded from content
hashing so the same logical append sequence produces stable hashes.

## Dependency status

This branch is stacked on Command Envelope Admission Router V1 and reuses
`CommandAdmissionReport` and `CommandExecutionReceipt`. It does not duplicate
the PR A dataclasses.

## Explicit non-goals

The journal does not execute commands, start schedulers, write into real
`artifacts/` by default, call providers, call network, automate browsers, store
credentials, or expose update/delete mutation APIs.
