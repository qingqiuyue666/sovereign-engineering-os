
# Code Train Runner Dispatch v1

## Purpose

This runbook documents the Local Train Runner dispatch extension for autonomous code train queues.

The dispatch layer allows the queue runner to recognize two stage kinds:

- verification

- code_stage

A code_stage must be executed through the registered local code stage executor.

A verification stage must be executed through the existing local verification suite.

## Boundaries

The dispatch layer is local-only.

It does not call cloud AI.

It does not run freeform shell commands.

It does not generate unbounded code.

It does not merge main.

It does not push main.

It does not delete branches.

It does not read secrets.

It does not enable provider live execution, vault live write, production autonomy, or deployment.

## Queue

The code train queue is:

governance/local_train/autonomous_code_train_queue_v1.json

## Dispatch Rules

For stage_kind verification:

- suite is required

- the runner dispatches the suite through the local train runner verification path

For stage_kind code_stage:

- code_stage_id is required

- the runner calls tools/local_code_stage_executor.py

- the code stage executor validates registry, path policy, line budget, and verification commands

- failure stops the queue

## Required Outputs

The dispatch layer writes through existing overnight queue outputs:

- outputs/reports/overnight_task_queue_summary.json

- outputs/reports/overnight_task_queue_report.md

- outputs/reports/overnight_task_queue_index.json

- outputs/state/overnight_task_queue_resume.json

- outputs/state/overnight_task_queue_heartbeat.json

## Non-Overclaim

This dispatch layer does not authorize freeform coding.

It does not authorize cloud AI.

It does not replace human merge review.

It only connects registered local code stages into the existing queue execution path.

