# V12 Operator CLI Foundation Runbook

## Purpose

Expose local-only operator commands for status, health planning, task
validation, dry-run task creation, dry-run run-ledger creation, and audit
summary reporting.

## Commands

- `python3 seos.py status`
- `python3 seos.py health`
- `python3 seos.py task validate path/to/task.json`
- `python3 seos.py task create --dry-run`
- `python3 seos.py run-ledger create --dry-run`
- `python3 seos.py audit summary`

## Boundary

The CLI does not call providers, access the network, read real secrets, start a
daemon, mutate SQLite, send Telegram messages, or enable production autonomy.
