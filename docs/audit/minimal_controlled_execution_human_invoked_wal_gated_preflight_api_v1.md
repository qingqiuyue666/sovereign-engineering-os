# Minimal Controlled Execution Human-Invoked WAL-Gated Preflight API V1

## Purpose

This PR adds a narrow human-invoked API for the existing WAL-gated preflight
wrapper. It does not wire the API into the existing preflight API yet and does
not change default preflight behavior.

## Added surface

- `kernel/execution/minimal_controlled_wal_gated_preflight_api.py`
- `run_human_invoked_minimal_controlled_wal_gated_preflight(payload, append_callable)`
- digest-only API response hash
- focused tracer-bullet coverage

## Required operator gates

The API rejects the request unless all of these fields are exactly `true`:

- `human_invoked`
- `single_run_scope`
- `approved_for_wal_gated_preflight`

The append function is not accepted from the payload. It must be injected as
the `append_callable` argument.

## Preserved constraints

- No default behavior change to `minimal_controlled_preflight_api.py`.
- No CLI, scheduler, daemon, provider, browser, DCC, MCP, real WAL, or runtime
  imports.
- No arbitrary argv, cwd, env, path, executable, timeout, or shell fields.
- No raw stdout, stderr, command line, prompt, provider response, secret, token,
  or environment material persistence.
- No new command IDs.

## Replay and audit binding

The API response binds directly to the existing wrapper result. The wrapper
result binds ordered WAL adapter record hashes, append result hashes, append
plan hash, batch hash, replay result hash, and integration result hash.

## Next safe PR

The next PR may add explicit opt-in wiring to the existing preflight API. That
PR must preserve default behavior and prove the opt-in boundary with focused
tests.
