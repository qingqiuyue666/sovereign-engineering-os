# Model Provider Real Smoke Manual Run v1

## Verdict

`MODEL_PROVIDER_REAL_SMOKE_MANUAL_RUN_READY_FOR_LOCAL_TESTS`

This branch adds a manual only model-provider real-smoke run planner.

It is default disabled and does not perform a model API call. It prepares a bounded manual-run report for human review before any future provider transport branch is allowed.

## Scope

This branch is planner/report only.

It does not:

- call model APIs
- read secret values
- persist secret values
- persist raw prompt text
- persist raw provider responses
- grant automatic runtime authority
- launch browsers
- launch creative software
- perform tool calls
- perform file edits
- execute subprocesses
- execute checkpoint
- truncate WAL
- mutate SQLite state

## Manual Readiness Conditions

The report can be marked ready for manual execution only when all explicit manual enablement flags are present:

- `SEOS_ENABLE_REAL_RUNTIME_SMOKE_EXECUTION_BATCH=true`
- `SEOS_ENABLE_MODEL_PROVIDER_LIVE_SMOKE=true`
- `SEOS_ENABLE_OPENAI_EXPLICIT_TRANSPORT=true`

The environment may indicate that `OPENAI_API_KEY` is present, but the value must not be read, serialized, hashed, or persisted.

## Recorded Metadata

The planner records:

- provider name
- model name
- request id
- prompt SHA-256
- prompt character length
- max output token bound
- temperature
- expected response contract
- manual flag presence
- secret presence only
- readiness status
- failure codes

## Boundary Invariants

The report always records:

- `runtime_execution_performed: false`
- `model_api_called: false`
- `external_network_accessed: false`
- `secret_value_read: false`
- `secret_value_persisted: false`
- `secret_value_serialized: false`
- `raw_prompt_persisted: false`
- `raw_provider_response_persisted: false`
- `file_or_tool_action_performed: false`
- `output_triggered_tool_or_file_authority: false`
- `automatic_runtime_authority_granted: false`
- `required_human_approval: true`

## Required Local Verification Commands

```bash
python3 -m unittest tests.personal_ai.test_model_provider_real_smoke_manual_run -v
python3 -m unittest tests.personal_ai.test_real_runtime_manual_smoke_preflight -v
python3 -m unittest tests.personal_ai.test_post_manual_smoke_preflight_main_health -v
python3 -m unittest tests.tracer_bullet.test_runtime_and_wal_main_health -v
python3 -m unittest discover -s tests/personal_ai -v
python3 -m unittest discover -s tests/tracer_bullet -v
make ci
git diff --check
git status --short
```

## Merge Gate

This branch is merge-ready only if:

1. Model provider manual smoke run tests pass.
2. Existing real-runtime manual preflight tests pass.
3. Runtime and WAL main health tests pass.
4. Full Personal AI tests pass.
5. Full tracer-bullet tests pass.
6. `make ci` passes.
7. No model API call is introduced.
8. No secret value read or persistence is introduced.
9. No output-triggered tool or file authority is introduced.
10. No runtime execution is introduced.
11. Worktree is clean.

## Post-Merge Status

After this branch merges, the runtime track may be described as:

`Model Provider Real Smoke Manual Run Ready / Default Disabled / Manual Only / Human Review Required / No Model API Call`
