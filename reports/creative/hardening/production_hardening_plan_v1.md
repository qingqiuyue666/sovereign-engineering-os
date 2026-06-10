# SEOS Production Hardening Plan

- Hardening status: `NEEDS_REPAIR_BEFORE_EXECUTION`
- Package status: `READY_FOR_HANDOFF`
- Read-only: `True`
- Output package manifest only: `True`

## Action Summary

| Metric | Value |
| --- | ---: |
| total_actions | 8 |
| p0_count | 0 |
| p1_count | 5 |
| p2_count | 2 |
| p3_count | 1 |

## Repair Actions

| Priority | Source | Workstream | Action |
| --- | --- | --- | --- |
| `P2` | `DUPLICATES_REQUIRE_REVIEW` | `asset_cleanup` | Review duplicate groups manually before deleting, archiving, or packaging anything. |
| `P1` | `ARCHIVE_PART_MISSING` | `asset_repair` | Restore missing archive parts before extraction or production use. |
| `P3` | `EMPTY_DIRECTORIES_PRESENT` | `asset_cleanup` | Decide whether empty directories are intentional placeholders or stale clutter. |
| `P1` | `INCOMPLETE_TEXTURE_SETS` | `lookdev_repair` | Fill missing texture maps or mark the lookdev set as intentionally partial. |
| `P1` | `INCOMPLETE_PRODUCTION_PACKS` | `asset_repair` | Resolve incomplete model/material/texture packs before binding them to shots. |
| `P1` | `LOCAL_RUNNER_NOT_READY` | `local_runner_readiness` | Resolve local tool health for houdini_hython_smoke (NOT_FOUND) before using the optional runner. |
| `P1` | `LOCAL_RUNNER_NOT_READY` | `local_runner_readiness` | Resolve local tool health for comfyui_workflow_smoke (CONFIG_REQUIRED) before using the optional runner. |
| `P2` | `ADAPTERS_CONTRACT_ONLY` | `adapter_proof` | Treat optional adapters as contract-only until adapter-specific local proof exists. |

## Package Summary

| Metric | Value |
| --- | ---: |
| artifact_count | 12 |
| missing_count | 0 |
| oversized_count | 0 |
| local_path_leak_count | 0 |
| total_size_bytes | 90074 |

## Package Manifest

| Path | Status | Size | Digest |
| --- | --- | ---: | --- |
| `reports/creative/assets/asset_library_report_v1.json` | `READY` | 25323 | `sha256:af8b84e3c058b77f96b69cfb38c0038df89a53ef5e6343a5a396b66a9d60c293` |
| `reports/creative/assets/asset_library_report_v1.md` | `READY` | 2535 | `sha256:9819c7e8a9fca053f02f5a84bbbc7d6a3f73fb24547691c8f7e1c9cd74903d65` |
| `reports/creative/assets/local_production_dashboard_v1.md` | `READY` | 3371 | `sha256:5e47a9a9dc1d0b0a8ce6710a763b0e3d4f5de13cc77d329b960404e2de642a78` |
| `reports/creative/assets/local_production_dashboard_v1.html` | `READY` | 5310 | `sha256:2ebe2c54844fa30fb57ee28249b49bb3c5023f70b8253a3b7654cc641a606e43` |
| `reports/creative/tool_health/local_tool_health_dashboard_v1.json` | `READY` | 6803 | `sha256:5b738210906462a91860227cd2333a772e1abb7d2343cfad56dc5599cec9adec` |
| `reports/creative/tool_health/local_tool_health_dashboard_v1.md` | `READY` | 3510 | `sha256:80bd83afda03a4e56aedaa14bebbe287aa612d69aea3b6808c88eb4d744c59ef` |
| `reports/creative/adapters/optional_adapter_contracts_v1.json` | `READY` | 11214 | `sha256:12d6c7bca43800466ba7cd2ea9e7dbefa22d5880570820435825f2109e0d8a37` |
| `reports/creative/adapters/optional_adapter_contracts_v1.md` | `READY` | 4847 | `sha256:325e28714683a9f210ee31fd95f4a9df5de1375af44f6e6f644b22862300a2bb` |
| `reports/creative/shots/shot_plan_energy_impact_v1.json` | `READY` | 7122 | `sha256:7b688714c20e1a369d175a7550c77b55c947f1e693edfcf6ad0e0867aecb352e` |
| `reports/creative/shots/shot_plan_energy_impact_v1.md` | `READY` | 1383 | `sha256:9acb839e242f1fa4e554e358085c48ef22f5c9b71ee8d1a730513eed1a57f247` |
| `reports/creative/pressure/real_project_pressure_test_v1.json` | `READY` | 15007 | `sha256:36c7c923f6dd230aed88728ae23ff1793355dc270ac5a717376f9190612604e6` |
| `reports/creative/pressure/real_project_pressure_test_v1.md` | `READY` | 3649 | `sha256:24461e07fc08c8a265576c67df47dbf9910a2a4e93524287fdf6422b0c4c1ee1` |

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

## Safety

- This hardening plan is read-only.
- It writes a manifest/report only; it does not copy, zip, delete, mutate, launch, render, or generate.
- Public package readiness is blocked if a package artifact leaks a local path marker.
