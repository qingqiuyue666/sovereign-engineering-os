# DCC Media Adapter Registry Integration V1

## Scope

This change integrates the existing creative adapter policy families into the
deterministic adapter registry as DCC/media policy boundaries.

Covered families:

- ComfyUI workflow API
- Blender Python/MCP
- Unreal Python editor utility commandlet
- Houdini HOM/hython/HDA
- After Effects ExtendScript/UXP/aerender
- ZBrush support handoff

## Runtime Boundary

Every generated DCC/media policy entry remains `deferred` and `policy_only`.
The entries record required controls for future admission, but they do not
admit real creative software control, subprocess launch, network endpoint use,
source asset mutation, overwrite, or generated media output.

The registry binding validator requires:

- one registry entry for every creative adapter policy family
- `policy_only` mode
- `creative_external_tool` risk class
- `deferred` admission status
- explicit future admission controls
- operation allowlist controls
- preview evidence controls
- no output writes
- no input mutation
- no overwrite

## Failure Path

Admission requests against these DCC/media policy entries fail closed because
the registry entries are not admitted and their request boundary is unsafe for
current-branch runtime execution.

## Independent Validation

This work does not depend on the unmerged replay browser, install/config,
AI worker router, worker registry, watchdog, operator console, WAL, job queue,
artifact store, snapshot replay, approval runtime, or failure bundle draft PRs.

Validated with:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.personal_ai.test_adapter_registry -v`
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest validation.tests.acceptance.test_dcc_media_adapter_registry_integration_v1 -v`
