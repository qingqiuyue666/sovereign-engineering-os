# Real Runtime Manual Smoke Preflight v1

## Verdict

`REAL_RUNTIME_MANUAL_SMOKE_PREFLIGHT_READY_FOR_LOCAL_TESTS`

This branch introduces a unified manual preflight checker for real runtime smoke execution.

It does not execute real runtimes. It only checks whether the manually gated smoke inputs are ready.

## Scope

Preflight only.

The preflight must not:

- call model APIs
- launch browsers
- call ComfyUI endpoints
- launch Blender
- launch AE / Unreal / Houdini / ZBrush
- access external network
- read secret values
- persist secret values
- execute arbitrary subprocesses
- grant output-triggered tool/file authority

## Runtime Checks

### Model Provider

The preflight checks:

- model plan artifact exists
- `SEOS_ENABLE_REAL_RUNTIME_SMOKE_EXECUTION_BATCH=true`
- `SEOS_ENABLE_MODEL_PROVIDER_LIVE_SMOKE=true`
- `SEOS_ENABLE_OPENAI_EXPLICIT_TRANSPORT=true`
- `OPENAI_API_KEY` exists in environment

The preflight only checks `OPENAI_API_KEY` presence. It does not read or persist the value.

### Browser

The preflight checks:

- browser admission artifact exists
- loopback-only posture is true
- isolated temporary profile posture is true
- external network is forbidden
- real user profile is forbidden
- credential persistence is forbidden
- login/signup/account/payment flows are forbidden

### ComfyUI

The preflight checks:

- workflow artifact exists
- endpoint is loopback
- workflow nodes exist
- workflow nodes do not request download, exec, http, network, python, script, subprocess, or url behavior

### Blender

The preflight checks:

- scene artifact exists
- scene extension is allowed: `.blend`, `.glb`, `.gltf`
- operation plan artifact exists
- operations are allowlisted
- operations do not contain forbidden tokens: `exec`, `eval`, `python`, `subprocess`, `os.`, `sys.`, `url`, `network`

### Creative Tools

Creative tools remain handoff-only:

- AE auto-control is not called
- Unreal auto-control is not called
- Houdini auto-control is not called
- ZBrush auto-control is not called

## Output

The preflight writes:

```text
real_runtime_manual_smoke_preflight_report.json
```

The report records:

- per-runtime readiness
- per-runtime failures
- runtime execution performed: false
- model API called: false
- browser launched: false
- ComfyUI endpoint called: false
- Blender launched: false
- creative software auto-control called: false
- external network accessed: false
- secret value read: false
- required human approval: true

## Required Local Verification Commands

```bash
python3 -m unittest tests.personal_ai.test_real_runtime_manual_smoke_preflight -v
python3 -m unittest tests.personal_ai.test_manual_runtime_smoke_runbook -v
python3 -m unittest tests.personal_ai.test_real_runtime_smoke_execution_batch -v
python3 -m unittest discover -s tests/personal_ai -v
make ci
git diff --check
git status --short
```

## Merge Gate

This branch is merge-ready only if:

1. Manual smoke preflight tests pass.
2. Manual smoke runbook tests pass.
3. Real runtime smoke batch tests pass.
4. Full Personal AI tests pass.
5. `make ci` passes.
6. No runtime execution is introduced.
7. No secret-value read/persistence is introduced.
8. No external network/tool launch/subprocess is introduced.
9. Worktree is clean.

## Post-Merge Status

After this branch merges, the runtime system may be described as:

`Real Runtime Smoke Entry Ready / Manual Preflight Ready / Manual Runbook Documented / Default Disabled / Human Review Required`
