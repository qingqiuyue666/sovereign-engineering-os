# Personal AI Execution OS Local Launcher

The local launcher commands are convenience wrappers around bounded local
fixtures and validators. They do not activate live model providers, real
browsers, Playwright or Selenium, ComfyUI endpoints, Blender, creative software,
OS automation, network runtime, or arbitrary subprocess execution.

Every launcher command prints deterministic JSON to stdout and writes a
`launcher_summary.md` file in the requested output directory. Existing launcher
outputs are never overwritten.

## Office Workflow

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-office-workflow \
  --input-workbook /path/to/source.xlsx \
  --output-dir /path/to/output
```

This runs local XLSX metadata inspection and writes an output workbook plan. It
does not create an output workbook; that remains approval-gated.

## Model Fixture Workflow

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-model-fixture \
  --input-artifact-path /path/to/input_artifact.json \
  --output-dir /path/to/output \
  --schema-name job_route_classification_v1
```

This writes a typed request and runs the deterministic mock model fixture only.
Live provider calls remain disabled by default.

## Browser Fixture Workflow

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-browser-fixture \
  --fixture-path /path/to/local_fixture.html \
  --actions-path /path/to/actions.json \
  --output-dir /path/to/output
```

This interprets a local HTML fixture and action list. It does not start a real
browser and does not allow external navigation by default.

## Runtime Delivery Validation

```bash
python3 -m kernel.personal_ai.local_mvp_cli launch-runtime-delivery-validation \
  --package-dir /path/to/runtime_delivery_package \
  --output-dir /path/to/output
```

This validates the delivery manifest, artifact hashes, replay hash, package
policy, and leakage scan locally.
