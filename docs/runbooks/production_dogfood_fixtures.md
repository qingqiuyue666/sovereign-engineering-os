# Production Dogfood Fixtures Runbook

This runbook exercises a complete local project/asset/shot/package/review path with a committable fixture and a CI-safe adapter.

Command:

```bash
python3 seos.py dogfood run examples/dogfood/production_shot_fixture_v1.json
```

Optional isolated workspace:

```bash
python3 seos.py dogfood run examples/dogfood/production_shot_fixture_v1.json --runtime-root work/production_dogfood/runtime --package-root work/production_dogfood/packages --output-root work/production_dogfood/runs --review-root work/production_dogfood/review_artifacts
```

Expected outputs:

- `work/production_dogfood/runs/*/dogfood_receipt.json`
- `work/production_dogfood/runs/*/dogfood_manifest.json`
- `work/production_dogfood/runs/*/artifact_manifest.json`
- `work/production_dogfood/runs/*/dogfood_state_ledger.jsonl`
- `work/production_dogfood/packages/runs/*/manifest.json`
- `work/production_dogfood/packages/shots/*/manifest.json`
- `work/production_dogfood/review_artifacts/*/review_artifact.json`

Failure behavior:

- Missing fixture fields, missing asset roots, missing workflow files, or terminal workflow failures write `failure_bundle.json`.
- Failure receipts use `TERMINAL_FAILED`; the command exits non-zero.
- The local CI fixture uses `fake_dcc` so tests can assert the full behavior without requiring Houdini, ComfyUI, or DaVinci Resolve.
