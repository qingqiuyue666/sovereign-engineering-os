# portal_lightning_001 Real Shot Runbook

## Purpose

Portal rim / lightning arc / energy pulse shot template for production-prototype compositing.

## Runtime Root Policy

Runtime outputs go under `work/phase2/portal_lightning_001/`. Generated media, DCC caches, runtime receipts, package directories, and review artifacts must not be committed. Package movement is represented by ArtifactRefs.

## Minimum DCC Smoke Commands

```bash
python3 seos.py rpc invoke examples/rpc/houdini_smoke_cache_test.json --json
python3 seos.py rpc invoke examples/rpc/comfyui_submit_workflow.json --json
python3 seos.py rpc invoke examples/rpc/davinci_project_probe.json --json
```

## Shot Workflow Commands

```bash
project_json=$(python3 seos.py project create "Portal Lightning Production" --runtime-root work/phase2/portal_lightning_001/runtime --json)
project_id=$(printf '%s\n' "$project_json" | jq -r '.project.project_id')
shot_json=$(python3 seos.py shot create "$project_id" portal_lightning_001 --runtime-root work/phase2/portal_lightning_001/runtime --json)
shot_id=$(printf '%s\n' "$shot_json" | jq -r '.shot.shot_id')
python3 seos.py shot attach-workflow "$shot_id" examples/shots/portal_lightning_001/workflow.json --runtime-root work/phase2/portal_lightning_001/runtime --json
run_json=$(python3 seos.py shot run "$shot_id" --runtime-root work/phase2/portal_lightning_001/runtime --json)
run_id=$(printf '%s\n' "$run_json" | jq -r '.run.run_id')
python3 seos.py package run "$run_id" --runtime-root work/phase2/portal_lightning_001/runtime --package-root work/phase2/portal_lightning_001/packages --json
python3 seos.py package shot "$shot_id" --runtime-root work/phase2/portal_lightning_001/runtime --package-root work/phase2/portal_lightning_001/packages --json
python3 seos.py review create "$shot_id" --runtime-root work/phase2/portal_lightning_001/runtime --package-root work/phase2/portal_lightning_001/packages --output-root work/phase2/portal_lightning_001/review_artifacts --json
```

## Expected Evidence

Houdini evidence: `.bgeo.sc`, `.exr`, `.json`, `.log`, ArtifactRefs, and `execution_receipt.json`. ComfyUI evidence: `.png` image output, ArtifactRefs, and `execution_receipt.json`. DaVinci Resolve evidence: project probe JSON, ArtifactRef, and `execution_receipt.json`. SEOS evidence: `workflow_receipt.json`, package manifest, review artifact, and review packet.

## Honest Limitation

Uses the existing Houdini smoke/cache action as the physical portal-energy prototype path; no unsupported lightning solver is claimed.
