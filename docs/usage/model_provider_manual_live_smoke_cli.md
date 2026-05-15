# Model Provider Manual Live Smoke CLI

## Purpose

This CLI provides a manually authorized model-provider live-smoke entrypoint.

It remains disabled by default and requires explicit flags plus environment gates before it can reach the OpenAI explicit transport path.

## Command

```bash
python3 -m kernel.personal_ai.model_provider_manual_live_smoke_cli \
  --plan-path <model_provider_live_smoke_plan.json> \
  --output-dir <output-dir> \
  --provider openai \
  --allow-live-smoke true \
  --allow-network true \
  --confirm-manual-live-smoke true \
  --use-stdlib-openai-transport true
```

## Required Environment For Actual OpenAI Transport

All of these must be present for the OpenAI transport path to proceed:

```bash
export SEOS_ENABLE_MODEL_PROVIDER_LIVE_SMOKE=true
export SEOS_ENABLE_OPENAI_EXPLICIT_TRANSPORT=true
export OPENAI_API_KEY=...
```

If any required flag or environment gate is missing, the CLI writes a denial result and does not call the OpenAI transport.

## Boundary

The CLI must not:

- persist API key values
- log API key values
- persist raw provider responses
- allow model-output tool calls
- allow model-output file edits
- bypass the existing disabled live-smoke runner
- bypass the explicit OpenAI transport gate

## Normal Tests

Normal tests do not call OpenAI.

They only exercise:

- exact flag rejection
- environment-gate denial
- output artifact shape
- no secret persistence

## Output Artifacts

The CLI writes runner artifacts in the output directory. It may also write an optional manual payload if `--output-payload-path` is supplied.

Generated artifacts are runtime evidence and should not be committed unless a specific review process requests them.
