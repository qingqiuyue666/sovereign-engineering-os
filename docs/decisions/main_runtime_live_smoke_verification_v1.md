# Main Runtime Live-Smoke Verification v1

## Verdict

`MAIN_RUNTIME_LIVE_SMOKE_VERIFICATION_READY_FOR_LOCAL_TESTS`

This branch records the post-merge mainline verification state after the model-provider manual live-smoke CLI entered `main`.

It does not add runtime functionality. It does not call OpenAI. It does not activate live network execution.

## Mainline Scope Under Verification

The model-provider live-smoke chain now includes:

- controlled activation package
- disabled live-smoke plan
- disabled live-smoke runner
- explicit transport contract
- OpenAI explicit transport adapter
- standalone manual live-smoke CLI

## Required Runtime Gates

The actual OpenAI transport path remains gated by all of the following:

1. valid live-smoke plan artifact
2. `--allow-live-smoke true`
3. `--allow-network true`
4. `--confirm-manual-live-smoke true`
5. `--use-stdlib-openai-transport true`
6. `SEOS_ENABLE_MODEL_PROVIDER_LIVE_SMOKE=true`
7. `SEOS_ENABLE_OPENAI_EXPLICIT_TRANSPORT=true`
8. `OPENAI_API_KEY` present in the environment
9. existing OpenAI explicit transport gate success

## Default-Denied Boundary

Normal execution remains default-denied:

- no normal-test OpenAI call
- no default live API execution
- no SDK dependency
- no API key persistence
- no API key logging
- no raw provider response persistence
- no model-output tool calls
- no model-output file edits

## Verification Test

This branch adds:

```text
tests/personal_ai/test_main_runtime_live_smoke_verification.py
```

The test verifies:

- manual CLI surface exists
- live-smoke chain files exist
- exact manual flags exist
- environment gates exist
- default-denied posture remains present
- tests cover denial/fake transport paths without hitting OpenAI
- docs exist

## Required Local Verification Commands

```bash
python3 -m unittest tests.personal_ai.test_main_runtime_live_smoke_verification -v
python3 -m unittest tests.personal_ai.test_model_provider_manual_live_smoke_cli -v
python3 -m unittest tests.personal_ai.test_model_provider_explicit_transport_suite -v
python3 -m unittest tests.personal_ai.test_model_provider_disabled_live_smoke_runner -v
python3 -m unittest discover -s tests/personal_ai -v
make ci
git diff --check
git status --short
```

## Merge Gate

This branch is merge-ready only if:

1. Targeted runtime live-smoke verification tests pass.
2. Manual live-smoke CLI tests pass.
3. Explicit transport tests pass.
4. Disabled live-smoke runner tests pass.
5. Full Personal AI tests pass.
6. `make ci` passes.
7. No live OpenAI call occurs during normal tests.
8. Worktree is clean.

## Next Branch After Merge

After this verification branch merges, the next runtime line should be:

```text
browser-controlled-local-smoke-runner-v1
```

That branch should remain loopback-only and disabled by default.
