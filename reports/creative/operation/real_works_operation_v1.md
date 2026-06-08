# SEOS Real Works Operation

- Operation status: `ACTIVE_REPAIR_LOOP`
- Pressure status: `USABLE_WITH_MANUAL_REPAIR`
- Hardening status: `NEEDS_REPAIR_BEFORE_EXECUTION`
- Read-only: `True`

## Repeatability Summary

| Metric | Value |
| --- | ---: |
| workflow_count | 5 |
| complete_workflow_count | 5 |
| blocked_workflow_count | 0 |
| optional_runner_count | 5 |
| nonready_optional_runner_count | 5 |

## Workflows

| Workflow | Status | Missing Required | Candidates | Optional Runners |
| --- | --- | ---: | ---: | ---: |
| `energy_impact` | `READY_FOR_MANUAL_PLANNING` | 0 | 12 | 2 |
| `smoke_dust` | `READY_FOR_MANUAL_PLANNING` | 0 | 10 | 1 |
| `portal_lightning` | `READY_FOR_MANUAL_PLANNING` | 0 | 11 | 2 |
| `editorial_handoff` | `READY_FOR_MANUAL_PLANNING` | 0 | 7 | 0 |
| `asset_library` | `READY_FOR_MANUAL_PLANNING` | 0 | 23 | 0 |

## Development Needs

| Priority | Source | Need |
| --- | --- | --- |
| `P2` | `DUPLICATES_REQUIRE_REVIEW` | Review duplicate groups manually before deleting, archiving, or packaging anything. |
| `P1` | `ARCHIVE_PART_MISSING` | Restore missing archive parts before extraction or production use. |
| `P3` | `EMPTY_DIRECTORIES_PRESENT` | Decide whether empty directories are intentional placeholders or stale clutter. |
| `P1` | `INCOMPLETE_TEXTURE_SETS` | Fill missing texture maps or mark the lookdev set as intentionally partial. |
| `P1` | `INCOMPLETE_PRODUCTION_PACKS` | Resolve incomplete model/material/texture packs before binding them to shots. |
| `P1` | `LOCAL_RUNNER_NOT_READY` | Resolve local tool health for houdini_hython_smoke (NOT_FOUND) before using the optional runner. |
| `P1` | `LOCAL_RUNNER_NOT_READY` | Resolve local tool health for comfyui_workflow_smoke (CONFIG_REQUIRED) before using the optional runner. |
| `P2` | `ADAPTERS_CONTRACT_ONLY` | Treat optional adapters as contract-only until adapter-specific local proof exists. |

## Operation Loop

1. `python3 seos.py creative scan-assets --root ASSET_ROOT --mode public --output-json REGISTRY_JSON --output-md REPORT_MD`
2. `python3 seos.py creative production-dashboard --registry-json REGISTRY_JSON --output-md DASHBOARD_MD --output-html DASHBOARD_HTML`
3. `python3 seos.py creative shot plan --template TEMPLATE --shot-id SHOT_ID --registry-json REGISTRY_JSON`
4. `python3 seos.py creative pressure-test --registry-json REGISTRY_JSON --template TEMPLATE --shot-id SHOT_ID`
5. `python3 seos.py creative hardening-plan --pressure-json PRESSURE_JSON`
6. `Use optional runner commands only after explicit approval and tool-health readiness.`

## Next Actions

- Review duplicate groups manually before deleting, archiving, or packaging anything.
- Restore missing archive parts before extraction or production use.
- Decide whether empty directories are intentional placeholders or stale clutter.
- Fill missing texture maps or mark the lookdev set as intentionally partial.
- Resolve incomplete model/material/texture packs before binding them to shots.
- Resolve local tool health for houdini_hython_smoke (NOT_FOUND) before using the optional runner.
- Resolve local tool health for comfyui_workflow_smoke (CONFIG_REQUIRED) before using the optional runner.
- Treat optional adapters as contract-only until adapter-specific local proof exists.
- Rerun creative pressure-test after repairs and compare the new hardening plan.
- Keep final creative and production approval human-owned.
- Run the operation report again after repairs to confirm repeatability improved.
- Keep new development tied to a workflow blocker, pressure finding, hardening action, or real project need.

## Safety

- This operation report is read-only.
- It does not mutate assets, launch DCC tools, submit AI jobs, render, simulate, export, copy packages, or delete duplicates.
- Optional runner steps remain separate approval-gated commands.
