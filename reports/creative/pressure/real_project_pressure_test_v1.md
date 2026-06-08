# SEOS Real Project Pressure Test

- Scenario: `PROJECT_PRESSURE_ENERGY_IMPACT_FIXTURE`
- Shot: `SHOT_PRESSURE_ENERGY_IMPACT_FIXTURE`
- Template: `energy_impact`
- Pressure status: `USABLE_WITH_MANUAL_REPAIR`
- Ready for manual shot planning: `True`
- Ready for execution: `False`

## Asset And Shot Summary

| Metric | Value |
| --- | ---: |
| total_assets | 23 |
| duplicate_group_count | 2 |
| archive_warning_count | 1 |
| empty_directory_count | 1 |
| missing_required_count | 0 |
| total_candidate_count | 12 |

## Search Probes

| Probe | Result Type | Count | Purpose |
| --- | --- | ---: | --- |
| `houdini-fx-assets` | `assets` | 1 | Find Houdini source assets for FX binding. |
| `vdb-cache-assets` | `assets` | 1 | Find VDB/cache assets for smoke, dust, or impact elements. |
| `duplicate-video-audio` | `duplicate_groups` | 1 | Expose duplicate video or audio groups before cleanup. |
| `incomplete-archives` | `archive_warnings` | 2 | Expose missing archive parts before extraction or shot use. |
| `empty-directories` | `empty_directories` | 1 | Expose stale or placeholder folders before packaging. |
| `incomplete-packs` | `production_groups` | 1 | Expose model/material/texture packs that need repair. |
| `missing-texture-sets` | `texture_sets` | 1 | Expose incomplete texture sets before lookdev. |

## Findings

- `WARNING` `DUPLICATES_REQUIRE_REVIEW`: Duplicate groups were detected and need human cleanup decisions.
- `WARNING` `ARCHIVE_PART_MISSING`: Missing archive parts were detected.
- `INFO` `EMPTY_DIRECTORIES_PRESENT`: Empty directories were detected.
- `WARNING` `INCOMPLETE_TEXTURE_SETS`: Incomplete texture sets were detected.
- `WARNING` `INCOMPLETE_PRODUCTION_PACKS`: Likely incomplete model/material/texture packs were detected.
- `WARNING` `LOCAL_RUNNER_NOT_READY`: Houdini hython smoke is not ready: NOT_FOUND.
- `WARNING` `LOCAL_RUNNER_NOT_READY`: ComfyUI workflow smoke is not ready: CONFIG_REQUIRED.
- `INFO` `ADAPTERS_CONTRACT_ONLY`: Some optional adapters are contract-only and cannot execute from this pressure test.

## Regression Checks

| Check | Passed | Detail |
| --- | --- | --- |
| `asset_scan_has_assets` | `True` | The scenario has at least one scanned asset. |
| `search_probes_are_structured` | `True` | All practical asset-search probes returned structured counts. |
| `shot_plan_generated` | `True` | The shot planner returned a report. |
| `shot_plan_complete` | `True` | Required shot assets are present for the selected template. |
| `optional_runners_remain_approval_gated` | `True` | Optional local runners are represented as approval-gated command templates. |
| `local_execution_not_performed` | `True` | The pressure test did not launch DCC tools or submit AI jobs. |

## Next Actions

- Review duplicate groups manually before deleting or packaging anything.
- Restore missing archive parts before extraction or production use.
- Decide whether empty directories are intentional placeholders or stale clutter.
- Fill missing texture maps before lookdev binding.
- Resolve incomplete packs before shot planning.
- Use adapter-specific local proof PRs before claiming execution support.
- Create the shot workspace and bind the selected candidate assets.
- Resolve Houdini hython smoke tool health before using that optional runner.
- Resolve ComfyUI workflow smoke tool health before using that optional runner.
- Keep final creative and production approval human-owned.

## Safety

- This pressure test is read-only.
- It does not delete duplicates, extract archives, mutate assets, launch DCC tools, or submit AI jobs.
- Optional local runners require separate explicit approval.
