# DaVinci Real Local API Adapter

Run a version probe:

```bash
python3 seos.py rpc invoke examples/rpc/davinci_version_probe.json --json
```

Run a project probe:

```bash
python3 seos.py rpc invoke examples/rpc/davinci_project_probe.json --json
```

The adapter attempts to import `DaVinciResolveScript`, checks whether Resolve is running, attaches through `scriptapp("Resolve")`, and then writes JSON artifacts for successful probes.

Failure classes are explicit: `DEPENDENCY_BLOCKED`, `APP_NOT_RUNNING`, `API_ATTACH_FAILED`, and `PROJECT_NOT_FOUND`. When policy allows auto-provision and the app is not running, the configured command `open -a "DaVinci Resolve"` is invoked and the attach probe is retried.

Every run writes `artifact_manifest.json` and `execution_receipt.json`; failed runs also write `failure_bundle.json`.
