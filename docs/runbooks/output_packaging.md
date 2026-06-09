# Output Packaging Runbook

## Commands

```bash
python3 seos.py package run <run_id> --json
python3 seos.py package shot <shot_id> --json
```

## Expected Local Behavior

Packages are written under:

```text
work/packages/
```

Run packages include `manifest.json`, `shot_run_receipt.json`, `workflow_receipt.json` when present, and `artifact_refs.json`. Shot packages include `manifest.json`, `shot.json`, and aggregated ArtifactRefs from all shot runs.

The default `copy_policy` is `artifact_refs_only`; large outputs remain referenced by path/hash rather than copied.
