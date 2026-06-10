# Router WAL Binding V1

## Purpose

Bind the Command Envelope Admission Router to the SQLite WAL Execution Journal
so dry-run admission, quarantine, and optional execution receipt evidence becomes
durable and replayable.

## Boundary

`bind_router_envelope_to_wal()` accepts an XML envelope, calls the existing
router, and appends exactly one admission or quarantine event to the existing
WAL journal. If `execute=True` and the router returns a registry-owned execution
receipt, the binding also appends one receipt event.

The binding does not parse command text, choose argv, set cwd, set env, set
paths, set executable, set timeouts, or bypass router admission checks.

## Journal Material

The journal stores structured report and receipt digests plus safe metadata. Raw
XML and payload material are not written to the journal.

## Non-Goals

This does not enable production autonomy, network access, browser automation,
provider calls, credential storage, ComfyUI, DCC launches, schedulers, daemons,
or real artifact writes by default.
