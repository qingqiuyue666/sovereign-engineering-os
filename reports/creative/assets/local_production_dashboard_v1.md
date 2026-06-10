# SEOS Local Production Dashboard

- Asset root: `<asset-root>`
- Read-only: `True`

## Summary

| Metric | Value |
| --- | ---: |
| total_assets | 23 |
| total_size_bytes | 704 |
| duplicate_group_count | 2 |
| archive_warning_count | 1 |
| empty_directory_count | 1 |
| texture_set_count | 1 |
| incomplete_texture_set_count | 1 |
| production_group_count | 1 |
| likely_incomplete_pack_count | 1 |

## Assets By Category

| Category | Count |
| --- | ---: |
| `after_effects` | 1 |
| `archives` | 2 |
| `audio` | 1 |
| `blender` | 1 |
| `comfyui` | 1 |
| `davinci` | 1 |
| `fbx_obj_usd_alembic` | 1 |
| `hdri` | 1 |
| `houdini` | 1 |
| `lut` | 1 |
| `materials` | 1 |
| `scripts` | 1 |
| `textures` | 2 |
| `unknown` | 3 |
| `unreal` | 1 |
| `vdb_cache` | 1 |
| `video` | 2 |
| `zbrush` | 1 |

## Largest Folders

| Folder | Size | Files |
| --- | ---: | ---: |
| `.` | 124 | 3 |
| `lookdev` | 111 | 4 |
| `archives` | 76 | 2 |
| `media` | 64 | 2 |
| `after_effects` | 39 | 1 |
| `davinci` | 36 | 1 |
| `blender` | 34 | 1 |
| `houdini` | 34 | 1 |
| `zbrush` | 32 | 1 |
| `cache` | 30 | 1 |

## Duplicate Groups

- `DUP_81C6626C12C0`: 2 files, manual review only
- `DUP_35689A01AA47`: 2 files, manual review only

## Empty Folders

- `empty/placeholder`

## Archive Warnings

- `fx_pack` missing parts `[2]`

## Texture And Pack Status

- Texture set `energy`: `LIKELY_TEXTURE_SET_INCOMPLETE`, missing `['roughness']`
- Pack `lookdev`: `LIKELY_INCOMPLETE_PACK`, missing `['complete_texture_set']`

## Production Readiness By Tool Category

| Tool | Status | Asset Count | Next Action |
| --- | --- | ---: | --- |
| `houdini` | `ASSETS_PRESENT_TOOL_HEALTH_NOT_CHECKED` | 2 | Run local tool doctor before execution. |
| `unreal` | `ASSETS_PRESENT_TOOL_HEALTH_NOT_CHECKED` | 2 | Run local tool doctor before execution. |
| `blender` | `ASSETS_PRESENT_TOOL_HEALTH_NOT_CHECKED` | 1 | Run local tool doctor before execution. |
| `zbrush` | `ASSETS_PRESENT_TOOL_HEALTH_NOT_CHECKED` | 1 | Run local tool doctor before execution. |
| `after_effects` | `ASSETS_PRESENT_TOOL_HEALTH_NOT_CHECKED` | 1 | Run local tool doctor before execution. |
| `davinci` | `ASSETS_PRESENT_TOOL_HEALTH_NOT_CHECKED` | 1 | Run local tool doctor before execution. |
| `comfyui` | `ASSETS_PRESENT_TOOL_HEALTH_NOT_CHECKED` | 1 | Run local tool doctor before execution. |

## Recommended Cleanup Actions

- Review duplicate groups manually before cleanup.
- Restore missing archive parts before using affected packs.
- Review empty folders for stale placeholders.
- Fill missing texture maps before lookdev or shot binding.
- Resolve incomplete production packs before shot planning.

## Next Actions

- Inspect duplicate groups manually before any cleanup; no deletion was performed.
- Restore missing multipart archive files before extracting or using those packs.
- Fill missing base color, normal, or roughness maps before final material/lookdev use.
- Review incomplete model/material/texture packs before binding them to a shot plan.
- Review empty directories and decide whether they are intentional placeholders.
- Verify licenses for real assets before publication, sharing, or commercial production.

## Safety

- Dashboard generation does not mutate input assets.
- Dashboard generation does not delete duplicates or extract archives.
- Dashboard generation does not execute DCC or AI tools.
