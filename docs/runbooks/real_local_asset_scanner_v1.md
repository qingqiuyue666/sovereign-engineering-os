# Real Local Asset Scanner v1 Runbook

## Purpose

Use SEOS to inspect a real local asset library without mutating it. The scanner
produces a sanitized JSON registry and a Markdown production report that help an
operator understand what assets exist, what looks broken, and what to do next.

## Command

```bash
ASSET_ROOT=./local_asset_library
python3 seos.py creative scan-assets \
  --root "$ASSET_ROOT" \
  --mode public \
  --output-json reports/creative/assets/local_asset_library.public.json \
  --output-md reports/creative/assets/local_asset_library.public.md
```

Use `--mode public` for shareable/sanitized artifacts. Use `--mode local` only
for private operator-local reports. Replace `./local_asset_library` with the
asset folder selected by the operator.

## What It Detects

- likely DCC and AI tool assets: Houdini, Unreal, Blender, ZBrush, After
  Effects, DaVinci, and ComfyUI;
- textures, materials, HDRI, VDB/cache, FBX/OBJ/USD/Alembic, video, audio, LUT,
  script, archive, and unknown files;
- empty directories;
- exact duplicate groups by size and SHA-256;
- missing multipart archive parts;
- likely texture sets and missing standard maps;
- likely model/material/texture production packs;
- largest folders and next cleanup or repair actions.

## Safety Boundary

The scanner:

- reads the configured asset root;
- writes reports only to operator-selected output paths outside the asset root;
- does not move, rename, delete, deduplicate, or organize files;
- does not extract archives;
- does not execute Houdini, Blender, ComfyUI, Unreal, After Effects, DaVinci, or
  ZBrush;
- does not claim license approval;
- does not claim that missing tools are available.

## Output Modes

Public mode:

- uses `<asset-root>` instead of absolute root paths;
- stores relative asset references;
- keeps private payloads out of reports.

Local mode:

- may include absolute paths for the local operator;
- should not be committed or shared publicly.

## Search Existing Registry

After a scan writes `reports/creative/assets/local_asset_library.public.json`,
query it without rescanning:

```bash
python3 seos.py creative search-assets \
  --registry-json reports/creative/assets/local_asset_library.public.json \
  --query missing-texture-sets
```

Useful query presets:

- `houdini-fx-assets`
- `vdb-cache-assets`
- `missing-texture-sets`
- `duplicate-video-audio`
- `incomplete-archives`
- `empty-directories`
- `incomplete-packs`

Generic filters:

```bash
python3 seos.py creative search-assets \
  --registry-json reports/creative/assets/local_asset_library.public.json \
  --category vdb_cache
```

Public mode strips local absolute paths from returned items. Local mode should
stay operator-private.

## Validation

```bash
make creative-real-asset-scanner-check
make creative-asset-search-check
python3 scripts/creative_asset_scan_v3.py --mode public
git diff --check
```

## Operator Review

After each scan:

1. Review missing archive warnings before extraction.
2. Review duplicate groups manually before deleting anything.
3. Fill missing texture maps before final lookdev.
4. Review incomplete model/material/texture packs before shot binding.
5. Verify licenses before sharing or commercial use.
