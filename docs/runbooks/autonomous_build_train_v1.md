
# Autonomous Build Train v1

## Purpose

The autonomous build train defines a bounded local-only execution train for predefined development stages.

It is not a cloud AI agent.

It does not design new architecture by itself.

It does not generate unbounded code.

It does not merge main.

It does not push main.

It does not delete branches.

It does not read secrets.

It does not call cloud AI APIs.

It does not enable provider live execution, vault live write, production autonomy, or deployment.

## Train Model

The train plan is defined in:

governance/local_train/autonomous_build_train_plan_v1.json

Each stage must define:

- task_id

- stage_id

- stage_type

- suite

- mode

- commit_message

- allow_commit

- allow_push_feature_branch

## Required Boundaries

The train must enforce:

- predefined stage queue required

- stop on first failure

- max runtime

- heartbeat output

- resume marker output

- stage reports

- no main branch mutation

- no cloud AI call

- no secret read

- no merge

- no branch deletion

- no unbounded generation

## Relationship to Local Train Runner

The autonomous build train is executed through Local Train Runner and Overnight Task Queue mechanics.

It uses local reports, local summaries, local heartbeat, and local resume markers.

It remains local-only.

## Current v1 Scope

v1 contains verification stages only:

- local-core verification

- full verification

It does not yet execute code generation stages.

## Non-Overclaim

This train is a bounded local automation layer.

It does not complete the system by itself.

It does not replace human merge review.

It does not authorize cloud AI to see C-layer protected assets.

