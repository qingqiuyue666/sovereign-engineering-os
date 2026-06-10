# Houdini Physical Output Adapter

Run the smoke cache test:

```bash
python3 seos.py rpc invoke examples/rpc/houdini_smoke_cache_test.json --json
```

The adapter resolves `hython`, invokes the repo-owned script at `execution_plane/adapters/houdini_scripts/smoke_cache_test.py`, and writes all outputs under the approved output root.

Minimum physical outputs are `smoke_cache_metadata.json` and `smoke_cache_execution.log`. When Houdini APIs are available, the script attempts `smoke_cache.bgeo.sc` and `smoke_cache_preview.exr`; if those cache outputs cannot be produced, the limitation is recorded in the metadata instead of being hidden.

Each run writes `artifact_manifest.json` and `execution_receipt.json`; failed runs also write `failure_bundle.json`.
