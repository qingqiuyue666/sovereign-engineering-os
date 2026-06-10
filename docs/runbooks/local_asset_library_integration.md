# Local Asset Library Integration

## Purpose

This runbook documents how SEOS should reference the operator's local asset library without moving, deleting, copying, or committing user assets.

Known local asset root, expressed as an operator-local placeholder:

```text
$LOCAL_ASSET_ROOT
```

Known subareas:

```text
$LOCAL_ASSET_ROOT/通用素材库
$LOCAL_ASSET_ROOT/胡迪尼资产
$LOCAL_ASSET_ROOT/虚幻资产
$LOCAL_ASSET_ROOT/Blender资产
$LOCAL_ASSET_ROOT/音效库
```

## Policy

- Use path references and hashes.
- Do not copy large user assets into the repository.
- Do not move, rename, or delete user assets.
- Write generated registries under `work/` unless a tiny example fixture is intentionally committed.
- Treat scan outputs as runtime evidence, not source.

## Example Manifest

Use:

```text
examples/assets/local_asset_roots.example.json
```

The example records path refs only. It is safe to commit because it contains no asset payloads.

## Optional Scan Command

The existing SEOS asset scan command can create a runtime registry:

```bash
LOCAL_ASSET_ROOT="$HOME/Desktop/资产"
python3 seos.py asset scan "$LOCAL_ASSET_ROOT" --runtime-root work/local_asset_library_scan --json
```

Expected runtime output:

```text
work/local_asset_library_scan/asset_scans/<scan_id>/asset_registry.json
work/local_asset_library_scan/production_state.json
```

Do not commit those runtime registry files unless a future task explicitly creates a small fixture from sanitized metadata.

## Shot Usage

For production shots, refer to asset roots by path and bind selected assets into shot metadata as ArtifactRefs or asset registry entries. Keep large source media under the operator's local library and keep packages `artifact_refs_only`.
