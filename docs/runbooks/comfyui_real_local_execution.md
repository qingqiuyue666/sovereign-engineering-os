# ComfyUI Real Local Execution

Run a service probe:

```bash
python3 seos.py rpc invoke examples/rpc/comfyui_service_probe.json --json
```

Submit the approved minimal workflow:

```bash
python3 seos.py rpc invoke examples/rpc/comfyui_submit_workflow.json --json
```

The adapter reads `config/local_adapters/comfyui_local.json`, checks `GET /system_stats`, optionally runs the configured `launch_command` when policy allows auto-provision, submits `POST /prompt`, polls `GET /history/{prompt_id}`, and downloads files through `GET /view`.

Outputs are written under the RPC output root. Every run writes `artifact_manifest.json` and `execution_receipt.json`; failed runs also write `failure_bundle.json`. If ComfyUI reports completion but no downloadable output is found, the adapter returns `OUTPUT_MISSING` instead of success.
