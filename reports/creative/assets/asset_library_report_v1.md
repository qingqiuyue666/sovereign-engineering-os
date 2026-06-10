# SEOS Real Local Asset Library Report

- Mode: `public`
- Asset root: `<asset-root>`
- Read-only scan: `True`
- Destructive actions performed: `False`

## Summary

| Metric | Value |
| --- | ---: |
| total_assets | 23 |
| total_size_bytes | 704 |
| empty_directory_count | 1 |
| duplicate_group_count | 2 |
| duplicate_asset_count | 4 |
| archive_warning_count | 1 |
| texture_set_count | 1 |
| incomplete_texture_set_count | 1 |
| production_group_count | 1 |
| likely_incomplete_pack_count | 1 |

## Categories

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

- `DUP_81C6626C12C0`: 2 files, 32 bytes, manual review only
  - `media/plate_a.mkv`
  - `media/plate_b.mkv`
- `DUP_35689A01AA47`: 2 files, 33 bytes, manual review only
  - `demo_model.txt`
  - `demo_model_copy.txt`

## Archive Warnings

- `fx_pack` missing parts: `[2]`

## Empty Directories

- `empty/placeholder`

## Texture Sets

- `energy`: `LIKELY_TEXTURE_SET_INCOMPLETE`, maps `['base_color', 'normal']`, missing `['roughness']`

## Production Groups

- `PKG_213B9A19A40C` in `lookdev`: `LIKELY_INCOMPLETE_PACK`, categories `['hdri', 'materials', 'textures']`

## Next Actions

- Inspect duplicate groups manually before any cleanup; no deletion was performed.
- Restore missing multipart archive files before extracting or using those packs.
- Fill missing base color, normal, or roughness maps before final material/lookdev use.
- Review incomplete model/material/texture packs before binding them to a shot plan.
- Review empty directories and decide whether they are intentional placeholders.
- Verify licenses for real assets before publication, sharing, or commercial production.

## Safety Boundary

- This report does not delete duplicates.
- This report does not extract archives.
- This report does not execute DCC or AI tools.
- Public mode uses relative asset references and does not embed absolute local paths.
