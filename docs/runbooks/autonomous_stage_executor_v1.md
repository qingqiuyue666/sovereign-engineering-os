# Autonomous Stage Executor v1

## Purpose

The autonomous stage executor runs only predefined and allowlisted local stage scripts.

It is local-only.

It does not call cloud AI.

It does not run freeform shell commands.

It does not merge main.

It does not push main.

It does not delete branches.

It does not read secrets.

It does not enable provider live execution, vault live write, production autonomy, or deployment.

## Registry

The stage registry is:

governance/local_train/stage_script_registry_v1.json

Every executable stage must be registered there.

## Allowed Stage Types

- verification
- local_script

## Forbidden Stage Types

- cloud_ai
- freeform_shell
- production_execution
- provider_live_execution
- vault_live_write
- deployment

## Allowed Script Path

Stage scripts must live under:

tools/local_stage_scripts/

Absolute paths are forbidden.

Path traversal is forbidden.

Only Python stage scripts are allowed in v1.

## v1 Registered Scripts

- verify-local-core
- verify-full

## Outputs

The executor writes:

- outputs/logs/autonomous_stage_executor.log
- outputs/reports/autonomous_stage_executor_report.md
- outputs/reports/autonomous_stage_executor_summary.json

## Non-Overclaim

This executor does not generate new architecture.

It does not write unbounded code.

It does not replace human merge review.

It only executes registered local stage scripts.
