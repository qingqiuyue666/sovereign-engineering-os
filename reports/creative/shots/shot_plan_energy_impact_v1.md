# SEOS Shot Plan: Energy Impact

- Shot: `SHOT_ENERGY_IMPACT_FIXTURE`
- Template: `energy_impact`
- Complete: `True`
- Read-only: `True`

## Summary

| Metric | Value |
| --- | ---: |
| required_ready_count | 4 |
| missing_required_count | 0 |
| optional_ready_count | 2 |
| total_candidate_count | 12 |

## Required Assets

| Requirement | Status | Candidates |
| --- | --- | ---: |
| source plate | `READY` | 2 |
| Houdini or VDB effect source | `READY` | 2 |
| material or texture lookdev | `READY` | 4 |
| comp or finishing surface | `READY` | 2 |

## Optional Assets

| Requirement | Status | Candidates |
| --- | --- | ---: |
| impact sound | `READY` | 1 |
| ComfyUI repair workflow | `READY` | 1 |

## Manual Steps

1. Choose the plate and lock frame range.
2. Bind the Houdini/VDB effect source to the shot workspace.
3. Assign lookdev maps and HDRI reference.
4. Create comp handoff notes and editorial delivery checklist.

## Optional Runner Steps

- Houdini hython smoke: `NOT_FOUND`. Requires approval: `True`.
- ComfyUI workflow smoke: `CONFIG_REQUIRED`. Requires approval: `True`.

## Next Actions

- Create the shot workspace and bind the selected candidate assets.
- Resolve Houdini hython smoke tool health before using that optional runner.
- Resolve ComfyUI workflow smoke tool health before using that optional runner.
- Keep final creative approval human-owned.
