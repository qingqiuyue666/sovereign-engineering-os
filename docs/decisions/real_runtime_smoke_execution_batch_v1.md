# Real Runtime Smoke Execution Batch v1

## Verdict

`REAL_RUNTIME_SMOKE_EXECUTION_BATCH_READY_FOR_LOCAL_TESTS`

This branch introduces manually gated smoke-entry wrappers for real runtime lines.

It does not default-enable live external execution. Normal tests use fake or injected transports.

## Status

`Real Runtime Smoke Entry Ready / Manual Execution Only / Default Disabled / Human Review Required`

## Runtime Lines

### Model Provider

- manual live-smoke entry
- environment-gated
- explicit transport only
- normal tests do not call real APIs
- no API key persistence
- no raw provider response persistence
- no model-output tool/file authority

### Browser

- Playwright loopback package entry
- loopback-only
- isolated profile required by package policy
- no real user profile
- no login/signup/payment/account authority
- normal tests do not launch real browsers

### ComfyUI

- loopback endpoint disabled runner entry
- explicit transport only
- no external downloads
- no arbitrary node execution
- no model downloads
- no raw image payload persistence

### Blender

- runtime admission disabled runner entry
- explicit transport only
- no subprocess authority
- no arbitrary Python authority
- no external network
- no source asset overwrite

### Creative Tools

Creative tools remain handoff-only in this branch.

- AE auto-control is not called
- Unreal auto-control is not called
- Houdini auto-control is not called
- ZBrush auto-control is not called

## Batch Gate

The batch requires:

- `allow_batch=True`
- `SEOS_ENABLE_REAL_RUNTIME_SMOKE_EXECUTION_BATCH=true`
- per-runtime explicit allow flags
- per-runtime artifacts
- per-runtime explicit fake/injected or future manually authorized transport

## Invariants

- Manual Execution Only
- Default Disabled
- Human Review Required
- normal tests use fake or injected transports
- no default model API call
- no default browser launch
- no default ComfyUI endpoint call
- no default Blender launch
- no creative software auto-control
- no credential persistence
- no raw provider response persistence
- no arbitrary subprocess
- no output-triggered tool/file authority

## Required Local Verification Commands

```bash
python3 -m unittest tests.personal_ai.test_real_runtime_smoke_execution_batch -v
python3 -m unittest discover -s tests/personal_ai -v
make ci
git diff --check
git status --short
```

## Merge Gate

This branch is merge-ready only if:

1. Targeted real runtime smoke execution batch tests pass.
2. Full Personal AI tests pass.
3. `make ci` passes.
4. No default live runtime execution is introduced.
5. No normal test launches external runtime.
6. No credential persistence is introduced.
7. No arbitrary subprocess is introduced.
8. Worktree is clean.
