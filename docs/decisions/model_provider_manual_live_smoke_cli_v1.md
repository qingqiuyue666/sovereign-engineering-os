# Model Provider Manual Live Smoke CLI v1

## Verdict

`MODEL_PROVIDER_MANUAL_LIVE_SMOKE_CLI_READY_FOR_LOCAL_TESTS`

This branch introduces a manual live-smoke CLI for the model provider chain.

It does not make normal tests call OpenAI and does not add default live API execution.

## Implemented

- Standalone CLI module: `kernel.personal_ai.model_provider_manual_live_smoke_cli`.
- Exact-true confirmation flags.
- Manual live-smoke output payload.
- Integration with existing disabled live-smoke runner.
- Integration with existing OpenAI explicit transport only through the runner path.
- Tests for denied and fail-closed paths.
- Usage documentation.

## Required Runtime Gates

The actual OpenAI transport path requires:

1. `--allow-live-smoke true`
2. `--allow-network true`
3. `--confirm-manual-live-smoke true`
4. `--use-stdlib-openai-transport true`
5. `SEOS_ENABLE_MODEL_PROVIDER_LIVE_SMOKE=true`
6. `SEOS_ENABLE_OPENAI_EXPLICIT_TRANSPORT=true`
7. `OPENAI_API_KEY` present in the environment
8. Valid live-smoke plan artifact
9. Existing OpenAI explicit transport gate success

## Non-Goals

This branch does not:

- add normal-test OpenAI calls
- persist API keys
- log API keys
- persist raw provider responses
- allow model-output tool calls
- allow model-output file edits
- bypass approval/admission artifacts
- bypass the disabled live-smoke runner

## Local Verification Commands

```bash
python3 -m unittest tests.personal_ai.test_model_provider_manual_live_smoke_cli -v
python3 -m unittest tests.personal_ai.test_model_provider_explicit_transport_suite -v
python3 -m unittest tests.personal_ai.test_model_provider_disabled_live_smoke_runner -v
python3 -m unittest discover -s tests/personal_ai -v
make ci
git diff --check
git status --short
```

## Merge Gate

This branch is merge-ready only if targeted tests, full Personal AI tests, and `make ci` pass; no live API call happens during normal tests; and no credential persistence/logging is introduced.
