# Local Asset Runtime v1

## Purpose

Local Asset Runtime v1 is the first narrow real local asset runtime slice.
It performs read-only filesystem scanning over a user-selected local input
directory and emits deterministic inventory artifacts into a separate output
directory.

It does not activate creative runtimes, browser runtimes, model runtimes,
network access, or desktop UI.

## Runtime Entry Point

```python
from pathlib import Path

from kernel.assets.local_asset_runtime import run_local_asset_runtime

result = run_local_asset_runtime(
    Path("/path/to/input_assets"),
    Path("/path/to/output_reports"),
    recursive=True,
    include_hidden=False,
    project_id="optional-project-id",
)
```

`output_dir` must already exist and must be outside `input_dir`.
The runtime fails closed if any required output file already exists.

## Inputs

- `input_dir`: existing local directory selected by the operator
- `output_dir`: existing local directory for reports only
- `recursive`: whether to traverse child directories
- `include_hidden`: defaults to `False`
- `project_id`: optional stable project label

## Emitted Artifacts

- `asset_manifest.json`
- `asset_index.json`
- `duplicates_report.json`
- `media_inventory.md`
- `asset_runtime_audit_log.jsonl`
- `asset_runtime_validation_report.json`
- `asset_runtime_quarantine_manifest.json`

All JSON is deterministic with sorted keys and stable list ordering.
The audit log uses deterministic sequence IDs and no wall-clock timestamps.

## Classifications

- `video`: `.mp4`, `.mov`, `.mkv`
- `image`: `.png`, `.jpg`, `.jpeg`, `.tif`, `.tiff`, `.exr`
- `audio`: `.wav`, `.mp3`, `.aiff`
- `dcc`: `.hip`, `.hiplc`, `.blend`, `.uproject`, `.aep`, `.drp`
- `comfyui_workflow`: `.json` only when conservative ComfyUI markers are present
- `color/lookdev`: `.cube`, `.ocio`, `.hdr`, `.hdri`, `.mtlx`
- `fx/cache`: `.vdb`, `.abc`, `.usd`, `.usda`, `.usdc`
- `script`: `.py`, `.sh`, `.jsx`
- `unknown`: everything else

## Safety Rules

The runtime never mutates, moves, renames, deletes, or overwrites input files.

The runtime skips or quarantines:

- `.git`
- `node_modules`
- `.venv`
- `__pycache__`
- secret-looking files or directories
- symlinks, including dangerous symlinks
- unsupported filesystem entries
- unreadable files or directories

Secret-looking files are not opened or hashed. Symlinks are not followed.

## Hard Boundaries

- no UI branch
- no desktop app branch
- no Electron, Tauri, or SwiftUI
- no ComfyUI, Blender, Houdini, browser, or model runtime launch
- no model API calls
- no external tools
- no network access
- no unrestricted filesystem automation
- no input mutation
- no output overwrite
- no production autonomy claim
- no final creative output readiness claim

## Required Validation

```bash
python3 -m unittest tests.tracer_bullet.test_local_asset_runtime -v
python3 -m unittest discover -s tests/tracer_bullet -v
python3 -m unittest discover -s tests/schemas -v
make ci
git diff --check
git status --short
```
