# V12 Operator Task Intake Ledger Runbook

## Purpose

Provide local operator task intake and run ledger records without persisting raw
task input or enabling runtime/provider autonomy.

## Procedure

1. Prepare a text, file, or repo descriptor that contains digest refs only.
2. Run `make test-operator-task-ledger`.
3. Run the tracer-bullet, schema, acceptance, and `make ci` gates before commit.

## Boundaries

- Raw task input, raw prompts, raw provider responses, env values, and secret
  values are rejected.
- Run ledgers write only under a caller-provided output directory and refuse
  overwrite.
- Reports contain digest refs and hard-false network, provider, secret, SQLite,
  and production autonomy flags.
