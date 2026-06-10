# Production Shot Dogfood Fixture

This fixture is a small, committable production-style shot packet for exercising the local execution plane end to end.

Run:

```bash
python3 seos.py dogfood run examples/dogfood/production_shot_fixture_v1.json
```

Expected local outputs:

- `work/production_dogfood/runs/*/dogfood_receipt.json`
- `work/production_dogfood/runs/*/dogfood_manifest.json`
- `work/production_dogfood/packages/runs/*/manifest.json`
- `work/production_dogfood/packages/shots/*/manifest.json`
- `work/production_dogfood/review_artifacts/*/review_artifact.json`

The workflow uses the CI-safe `fake_dcc` adapter. It still writes real files, state ledger entries, package manifests, review packets, and ArtifactRefs.
