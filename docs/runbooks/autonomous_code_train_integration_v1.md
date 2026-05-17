
# Autonomous Code Train Integration v1

## Purpose

This runbook connects Autonomous Code Stage execution into the local build train.

It allows a predefined train queue to schedule registered local code stages and verification stages.

It remains local-only.

It does not call cloud AI.

It does not run freeform shell commands.

It does not generate unbounded code.

It does not merge main.

It does not push main.

It does not delete branches.

It does not read secrets.

It does not enable provider live execution, vault live write, production autonomy, or deployment.

## Queue

The queue is defined in:

governance/local_train/autonomous_code_train_queue_v1.json

The queue supports two stage kinds in v1:

- code_stage

- verification

## Code Stage

A code stage must reference a registered code stage id from:

governance/local_train/code_stage_registry_v1.json

The code stage is executed through:

tools/local_code_stage_executor.py

## Verification Stage

A verification stage runs through the existing local train runner verification suite.

v1 requires verification after code stage execution.

## Required Boundaries

The integration must enforce:

- code stage must be registered

- verification after code stage is required

- stop on first failure

- stage report written

- diff report written

- main branch mutation rejected

- cloud AI calls forbidden

- secrets forbidden

- merge forbidden

- branch deletion forbidden

- unbounded generation forbidden

## Required Outputs

The integration writes:

- outputs/reports/autonomous_code_train_integration_report.md

- outputs/reports/autonomous_code_train_integration_summary.json

- outputs/reports/autonomous_code_train_integration_index.json

- outputs/state/autonomous_code_train_integration_resume.json

- outputs/state/autonomous_code_train_integration_heartbeat.json

## Non-Overclaim

This integration does not allow freeform coding.

It does not authorize cloud AI.

It does not replace human merge review.

It only schedules predefined local code stages and verification stages.

