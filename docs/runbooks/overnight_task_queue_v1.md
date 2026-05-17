# Overnight Task Queue v1

## Purpose

The overnight task queue extends Local Train Runner from single-run verification into bounded unattended local execution.

It is local-only.

It does not call cloud AI.

It does not merge main.

It does not push main.

It does not delete branches.

It does not read secrets.

It does not enable provider live execution, vault live write, production autonomy, or deployment.

## Queue Model

The queue is defined in governance/local_train/overnight_task_queue_v1.json.

Each task must define:

- task_id
- stage_id
- suite
- mode
- commit_message
- allow_commit
- allow_push_feature_branch

## Runtime Boundaries

The queue must enforce:

- stop on first failure
- maximum runtime
- heartbeat output
- resume marker output
- per-stage reporting
- summary index output
- feature-branch-only push
- no main branch mutation

## Required Outputs

The queue writes:

- outputs/logs/overnight_task_queue.log
- outputs/reports/overnight_task_queue_report.md
- outputs/reports/overnight_task_queue_summary.json
- outputs/reports/overnight_task_queue_index.json
- outputs/state/overnight_task_queue_resume.json
- outputs/state/overnight_task_queue_heartbeat.json

## Safe Use

Run from a feature branch only.

Do not run overnight mode on main.

Use caffeinate on macOS to prevent sleep during long unattended runs.

Run caffeinate in one terminal:

caffeinate -dimsu

Then run the queue in another terminal:

python3 tools/local_train_runner.py --queue governance/local_train/overnight_task_queue_v1.json --mode overnight --allow-commit --allow-push-feature-branch

## Non-Overclaim

This queue automates bounded local execution and reporting only.

It does not design new architecture.

It does not replace human merge review.

It does not complete the system by itself.
