
# Local Train Runner v1

## Purpose

The local train runner automates local verification, evidence capture, reporting, controlled feature-branch commit, and controlled feature-branch push.

It is not an AI agent.

It does not call cloud AI.

It does not design architecture.

It does not merge, push main, delete branches, read secrets, enable live providers, write vault data, or deploy.

## Supported Modes

### verify

Runs the selected suite and writes reports.

No commit.

No push.

### commit

Runs the selected suite.

If the suite passes and the current branch is not main, it may commit the current feature branch only when explicitly allowed.

### commit-push

Runs the selected suite.

If the suite passes and the current branch is not main, it may commit and push the current feature branch only when explicitly allowed.

### overnight

Runs a queue of predefined local tasks.

It stops on first failure.

It writes logs, markdown report, and JSON summary.

## Supported Suites

### local-core

Runs the local core operating foundation tests.

### full

Runs the full local verification suite:

- tracer bullet tests

- schema tests

- acceptance tests

- make ci

- git diff --check

## Outputs

The runner writes:

- `outputs/logs/local_train_runner.log`

- `outputs/reports/local_train_runner_report.md`

- `outputs/reports/local_train_runner_summary.json`

## Forbidden Actions

The runner must not perform:

- no cloud AI API calls

- no merge

- no push to main

- no branch deletion

- no secret reads

- `.env` reads

- provider live execution

- vault live write

- production autonomy

- deployment

## Merge Boundary

The runner may never merge to main.

The runner may never delete branches.

The runner may never push main.

Merge review remains human-controlled.

## Non-Overclaim

This runner automates local verification and limited feature-branch git operations.

It does not complete the system by itself.

It does not replace human review for merge.

