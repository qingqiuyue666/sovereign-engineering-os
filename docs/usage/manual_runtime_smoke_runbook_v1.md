# Manual Runtime Smoke Runbook v1

## Status

`MANUAL_RUNTIME_SMOKE_RUNBOOK_READY_FOR_LOCAL_TESTS`

This runbook documents how to execute runtime smoke checks manually after the real runtime smoke entry batch entered `main`.

It does not enable default live execution. It does not ask normal tests to call external runtimes.

## Global Rules

All runtime smoke execution must remain:

- Manual Execution Only
- Default Disabled
- Human Review Required
- explicit environment-gated
- artifact-gated
- per-runtime allow-gated
- no credential persistence
- no raw provider response persistence
- no raw image payload persistence
- no arbitrary subprocess
- no model/browser/ComfyUI/Blender output-triggered tool or file authority

## Global Batch Gate

The unified batch entry requires:

```text
allow_batch=True
SEOS_ENABLE_REAL_RUNTIME_SMOKE_EXECUTION_BATCH=true
```

Every runtime line also requires its own artifacts, explicit allow flag, and explicit transport.

## Model Provider Manual Smoke

### Purpose

Verify the model-provider smoke path can be manually activated without storing API key values, raw provider responses, or model-output tool/file authority.

### Required Inputs

- valid model-provider live-smoke plan artifact
- `OPENAI_API_KEY` available in environment only
- `SEOS_ENABLE_REAL_RUNTIME_SMOKE_EXECUTION_BATCH=true`
- `SEOS_ENABLE_MODEL_PROVIDER_LIVE_SMOKE=true`
- `SEOS_ENABLE_OPENAI_EXPLICIT_TRANSPORT=true`
- explicit `allow_batch=True`
- explicit `allow_model_smoke=True`
- explicit future manually authorized transport or explicit stdlib OpenAI transport flag

### Required Denials

The model-provider smoke path must deny or fail closed if:

- the batch gate is missing
- the model plan artifact is missing
- the model allow flag is missing
- the model live-smoke environment gate is missing
- the OpenAI explicit transport gate is missing
- `OPENAI_API_KEY` is missing

### Forbidden

- do not persist API key values
- do not log API key values
- do not persist raw provider responses
- do not allow model-output tool calls
- do not allow model-output file edits

## Browser / Playwright Loopback Manual Smoke

### Purpose

Verify the browser smoke path can be manually activated through a loopback-only Playwright package entry without using a real user profile or accessing the external network.

### Required Inputs

- valid browser Playwright package admission artifact
- `SEOS_ENABLE_REAL_RUNTIME_SMOKE_EXECUTION_BATCH=true`
- explicit `allow_batch=True`
- explicit `allow_browser_smoke=True`
- explicit browser transport
- loopback target only
- isolated temporary profile only

### Required Denials

The browser smoke path must deny or fail closed if:

- the batch gate is missing
- the browser admission artifact is missing
- the browser allow flag is missing
- the browser transport is missing
- target URL is not loopback
- real user profile is requested
- login, signup, payment, or account flow is requested

### Forbidden

- no external network
- no real user browser profile
- no persistent browser profile
- no credential persistence
- no login/signup/payment/account authority
- no raw DOM persistence
- no screenshot payload persistence by default

## ComfyUI Loopback Endpoint Manual Smoke

### Purpose

Verify the ComfyUI smoke path can be manually activated against a loopback endpoint through an explicit transport while preserving workflow restrictions.

### Required Inputs

- valid ComfyUI workflow artifact
- loopback endpoint such as `http://127.0.0.1:8188`
- `SEOS_ENABLE_REAL_RUNTIME_SMOKE_EXECUTION_BATCH=true`
- explicit `allow_batch=True`
- explicit `allow_comfyui_smoke=True`
- explicit ComfyUI transport

### Required Denials

The ComfyUI smoke path must deny or fail closed if:

- the batch gate is missing
- the workflow artifact is missing or malformed
- the endpoint is not loopback
- the ComfyUI allow flag is missing
- the ComfyUI transport is missing
- workflow nodes request external download, script execution, Python execution, subprocess, URL, or network behavior

### Forbidden

- no external downloads
- no arbitrary node execution
- no model downloads
- no raw image payload persistence
- no output-triggered file/tool authority

## Blender Runtime Manual Smoke

### Purpose

Verify the Blender smoke path can be manually activated through a gated runtime admission runner without granting subprocess or arbitrary Python authority.

### Required Inputs

- valid scene artifact: `.blend`, `.glb`, or `.gltf`
- valid operation plan artifact
- `SEOS_ENABLE_REAL_RUNTIME_SMOKE_EXECUTION_BATCH=true`
- explicit `allow_batch=True`
- explicit `allow_blender_smoke=True`
- explicit Blender transport

### Required Denials

The Blender smoke path must deny or fail closed if:

- the batch gate is missing
- the scene artifact is missing
- the operation plan artifact is missing or malformed
- the Blender allow flag is missing
- the Blender transport is missing
- the operation plan includes forbidden tokens such as `exec`, `eval`, `subprocess`, `python`, `os.`, `sys.`, `http`, `url`, or `network`

### Forbidden

- no subprocess authority
- no arbitrary Python authority
- no external network
- no source asset overwrite
- no output-triggered file/tool authority

## Creative Tools Manual Boundary

Creative tools remain handoff-only in this runbook.

- AE auto-control is not called
- Unreal auto-control is not called
- Houdini auto-control is not called
- ZBrush auto-control is not called

Allowed output is a human-reviewed handoff package or manifest. The system must not launch or mutate creative software projects by default.

## Normal Test Rule

Normal tests must use fake or injected transports only.

They must not:

- call OpenAI or any real model API
- launch Playwright or any browser
- call a real ComfyUI endpoint
- launch Blender
- launch AE / Unreal / Houdini / ZBrush
- access external network
- read or persist real secrets

## Required Verification Commands

```bash
python3 -m unittest tests.personal_ai.test_manual_runtime_smoke_runbook -v
python3 -m unittest tests.personal_ai.test_post_real_runtime_smoke_main_health -v
python3 -m unittest tests.personal_ai.test_real_runtime_smoke_execution_batch -v
python3 -m unittest discover -s tests/personal_ai -v
make ci
git diff --check
git status --short
```

## Final Label

After this runbook is merged, the runtime system may be described as:

`Real Runtime Smoke Entry Ready / Manual Runbook Documented / Default Disabled / Human Review Required`
