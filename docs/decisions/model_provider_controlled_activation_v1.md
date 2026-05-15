# Model Provider Controlled Activation v1

## Verdict

`MODEL_PROVIDER_CONTROLLED_ACTIVATION_READY_FOR_LOCAL_TESTS`

This branch introduces a controlled activation package for live model provider boundaries. It does not call a live provider and does not enable model API execution by default.

## Scope

Implemented:

- Controlled activation package builder for live model provider boundaries.
- Activation plan artifact.
- Runtime admission artifact bundle reuse.
- Validation report for activation package invariants.
- Tests proving the package remains dry-run only and does not persist API key values.

Not implemented:

- Live OpenAI / Gemini / Claude / DeepSeek API calls.
- Network runtime execution.
- Tool calls from model output.
- File edits from model output.
- Credential persistence.
- Credential logging.

## Boundary

The activation package is a pre-live activation control surface. It prepares the artifacts needed for a future live smoke runner but deliberately refuses to become the live runner itself.

The package must preserve these invariants:

- `activation_enabled: false`
- `dry_run_only: true`
- `network_call_allowed: false`
- `network_call_performed: false`
- `live_provider_call_performed: false`
- `api_key_value_persisted: false`
- `api_key_value_logged: false`
- `tool_calls_allowed: false`
- `file_edits_allowed: false`
- runtime admission decision `activation_allowed: false`

## API Key Policy

The activation package may detect environment presence for a provider key, but it must not persist, log, or copy the key value.

For OpenAI, the current provider boundary expects:

- `OPENAI_API_KEY`

The package records key presence as a boolean only.

## Local Verification Commands

Run:

```bash
python3 -m unittest tests.personal_ai.test_model_provider_activation_package -v
python3 -m unittest discover -s tests/personal_ai -v
make ci
git diff --check
git status --short
```

Expected:

- Targeted tests pass.
- Full Personal AI tests pass.
- `make ci` passes.
- `git diff --check` passes.
- `git status --short` is clean after commit.

## Next Step

If this PR is merged, the next model-provider branch may introduce a disabled-by-default live smoke runner. That future runner must still require explicit environment configuration, explicit runtime admission, explicit human approval, timeout/budget/schema gates, and must remain excluded from normal tests.
