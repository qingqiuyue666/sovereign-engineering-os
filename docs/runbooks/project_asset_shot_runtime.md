# Project Asset Shot Runtime Runbook

## Commands

```bash
python3 seos.py project create seos_demo_project --json
python3 seos.py asset scan examples/production_assets --project-id <project_id> --json
python3 seos.py shot create <project_id> shot_001 --json
python3 seos.py shot attach-workflow <shot_id> examples/workflows/cross_dcc_workflow_v1.json --json
python3 seos.py shot run <shot_id> --json
```

## Expected Local Behavior

The runtime writes durable local state under:

```text
work/production_runtime/
```

`asset scan` hashes files into an asset registry. `shot create` links the latest asset registry to the shot. `shot attach-workflow` stores the workflow path and workflow id. `shot run` executes the real workflow runner, writes a shot run receipt, and attaches workflow receipt paths plus ArtifactRefs to the shot record.

If local DCC dependencies are unavailable, `shot run` still completes the control-plane command and records a truthful failed workflow receipt under the shot run directory.
