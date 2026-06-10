# Energy Impact 001 Real Shot Runbook

## Purpose

`energy_impact_001` is a small real local DCC proof shot. It verifies the existing execution plane with Houdini, ComfyUI, DaVinci Resolve, SEOS packaging, and SEOS review artifacts without adding new framework features.

## Committed Templates

- `examples/projects/energy_impact_project_v1.json`
- `examples/shots/energy_impact_001/shot.json`
- `examples/shots/energy_impact_001/workflow.json`
- `examples/shots/energy_impact_001/README.md`
- `skills/energy_impact_001/skill.json`

## Runtime Root Policy

Runtime outputs go under:

```text
work/energy_impact_001/
```

Do not commit generated files from `work/`. The package copy policy is `artifact_refs_only`.

## Exact Run Commands

Create the runtime project:

```bash
project_json=$(python3 seos.py project create "Energy Impact Project" --runtime-root work/energy_impact_001/runtime --json)
project_id=$(printf '%s\n' "$project_json" | jq -r '.project.project_id')
```

Create the shot and attach the real DCC workflow:

```bash
shot_json=$(python3 seos.py shot create "$project_id" energy_impact_001 --runtime-root work/energy_impact_001/runtime --json)
shot_id=$(printf '%s\n' "$shot_json" | jq -r '.shot.shot_id')
python3 seos.py shot attach-workflow "$shot_id" examples/shots/energy_impact_001/workflow.json --runtime-root work/energy_impact_001/runtime --json
```

Run the shot:

```bash
run_json=$(python3 seos.py shot run "$shot_id" --runtime-root work/energy_impact_001/runtime --json)
run_id=$(printf '%s\n' "$run_json" | jq -r '.run.run_id')
```

Package and review:

```bash
python3 seos.py package run "$run_id" --runtime-root work/energy_impact_001/runtime --package-root work/energy_impact_001/packages --json
python3 seos.py package shot "$shot_id" --runtime-root work/energy_impact_001/runtime --package-root work/energy_impact_001/packages --json
python3 seos.py review create "$shot_id" --runtime-root work/energy_impact_001/runtime --package-root work/energy_impact_001/packages --output-root work/energy_impact_001/review_artifacts --json
```

## Expected Evidence

The workflow should produce:

- Houdini: `.bgeo.sc`, `.exr`, `.json`, `.log`, ArtifactRefs, and `execution_receipt.json`.
- ComfyUI: `.png` image output, ArtifactRefs, and `execution_receipt.json`.
- DaVinci Resolve: project probe JSON, ArtifactRef, and `execution_receipt.json`.
- SEOS: `workflow_receipt.json`, `shot_run_receipt.json`, run package manifest, shot package manifest, review artifact, and review packet.

Artifact handoff is via ArtifactRefs and metadata. This runbook does not claim direct media transfer into DaVinci.

## Validation

```bash
make ci
git diff --check
git status --short
```
