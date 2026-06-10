# Minimal Asset Inventory V1

## Purpose

Add asset awareness before real DCC, ComfyUI, provider, embedding, or thumbnail
runtime work exists.

## Architecture

`scan_asset_inventory()` accepts an explicit mapping of `root_id` to local root
path. Each file is inspected read-only and hashed in fixed-size chunks. Records
are sorted by root id and relative path so repeated scans are deterministic
except for `observed_at`, which is excluded from `content_hash`.

## Safety boundaries

- Home directory and filesystem root scans are rejected.
- Path traversal roots are rejected.
- Symlink escapes outside the supplied root are rejected.
- Files are not mutated.
- Large binaries are not loaded into memory all at once.
- Media class is extension-based only.

## Explicit non-goals

This does not compute embeddings, use LanceDB, run OpenUSD, launch Houdini,
ComfyUI, Blender, Unreal, DaVinci Resolve, After Effects, Photoshop, or ZBrush,
generate thumbnails, call network, call providers, or enable production
autonomy.
