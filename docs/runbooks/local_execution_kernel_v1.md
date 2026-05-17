# Local Execution Kernel v1

## Purpose
Bounded local-only execution kernel. Validates execution requests
without running any commands.

## Boundaries
- no freeform shell
- no network commands
- no secrets
- no .env reads
- no main mutation
- no merge
- no push main
- no branch deletion
- no production execution
- no command execution in v1

## Operations
1. validate_local_execution_request — structural validation
2. classify_execution_request — risk classification
3. validate_command_allowlist — allowlist enforcement
4. validate_execution_preflight — preflight safety checks
5. produce_local_execution_receipt — full receipt production

## Scope
Contract-only. Does not execute any commands.
