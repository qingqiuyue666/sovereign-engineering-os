# Model Provider Disabled Live Smoke Runner v1

## Verdict

`MODEL_PROVIDER_DISABLED_LIVE_SMOKE_RUNNER_READY_FOR_LOCAL_TESTS`

This branch introduces a disabled-by-default live smoke runner for the model provider boundary.

It does not import a network client, does not persist credentials, and does not call a provider unless a caller supplies an explicit transport function after all gates pass.

## Implemented

- Default-denied live smoke runner.
- Live smoke plan validation before any smoke path.
- Explicit callsite enable gate.
- Explicit environment enable flag gate: `SEOS_ENABLE_MODEL_PROVIDER_LIVE_SMOKE=true`.
- Environment-only API key presence check.
- Explicit injected transport requirement.
- Schema validation for the returned smoke response.
- Denial artifacts for disabled paths.
- Failure quarantine for malformed plans.
- Tests proving default denial and explicit-transport-only execution.

## Not Implemented

- Direct OpenAI / Gemini / Claude / DeepSeek API client.
- `requests`, `urllib`, or SDK-based live network call.
- Credential persistence.
- Credential logging.
- Tool calls from model output.
- File edits from model output.
- Normal tests requiring API keys.

## Required Gates Before Injected Transport Path

All must be true:

1. Live smoke plan validates.
2. `allow_live_smoke=True` is passed by the caller.
3. `SEOS_ENABLE_MODEL_PROVIDER_LIVE_SMOKE=true` is present in the supplied environment.
4. Provider API key environment variable is present.
5. Explicit `live_transport` callable is supplied.

If any gate is missing, the runner writes a denial result and does not call the transport.

## Boundary Invariants

- `network_used_by_runner: false`
- `api_key_value_persisted: false`
- `api_key_value_logged: false`
- `tool_calls_allowed: false`
- `file_edits_allowed: false`
- raw provider response is not persisted
- human review remains required

## Local Verification Commands

```bash
python3 -m unittest tests.personal_ai.test_model_provider_disabled_live_smoke_runner -v
python3 -m unittest discover -s tests/personal_ai -v
make ci
git diff --check
git status --short
```

## Next Step

A later branch may add a real provider-specific transport adapter. That adapter must remain disabled by default, excluded from normal tests, and require explicit credentials, explicit admission, explicit human review, timeout, budget, schema validation, and failure quarantine.
