# Local Operator CLI Extension Foundation v1

## Purpose
Bounded local-only operator CLI extension foundation. Validates CLI
commands without executing them.

## Boundaries
- no unregistered command
- no freeform shell
- no network
- no secret read
- no main mutation
- no production execution
- no actual CLI execution in v1

## Registered Commands
status, health, review, approve, reject, list, report, checkpoint,
rollback, evidence, index, run

## Operations
1. validate_cli_extension_request — structural validation
2. validate_cli_command_contract — command registration check
3. validate_cli_safety_boundary — safety boundary check
4. produce_operator_cli_extension_receipt — full receipt production

## Scope
Contract-only. Does not execute any CLI commands.
