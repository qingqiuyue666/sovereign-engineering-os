# Energy Impact Skill Runbook

## Scope

`energy_impact` is a reusable template for small local DCC proof shots. It uses existing SEOS commands and adapters only:

- `houdini_hython`
- `comfyui_local`
- `davinci_resolve`

It does not add a skill executor. If `python3 seos.py skill run energy_impact` is unavailable, run the existing RPC or project/shot commands below.

## Required Local Configs

- `config/local_adapters/comfyui_local.json`
- `config/local_adapters/davinci_resolve.json`
- `config/local_adapters/houdini_hython.json`

## Individual DCC Smoke Commands

```bash
python3 seos.py rpc invoke examples/rpc/houdini_smoke_cache_test.json --json
python3 seos.py rpc invoke examples/rpc/comfyui_submit_workflow.json --json
python3 seos.py rpc invoke examples/rpc/davinci_project_probe.json --json
```

## Shot Workflow Commands

```bash
project_json=$(python3 seos.py project create "Energy Impact Project" --runtime-root work/energy_impact_001/runtime --json)
project_id=$(printf '%s\n' "$project_json" | jq -r '.project.project_id')
shot_json=$(python3 seos.py shot create "$project_id" energy_impact_001 --runtime-root work/energy_impact_001/runtime --json)
shot_id=$(printf '%s\n' "$shot_json" | jq -r '.shot.shot_id')
python3 seos.py shot attach-workflow "$shot_id" examples/shots/energy_impact_001/workflow.json --runtime-root work/energy_impact_001/runtime --json
run_json=$(python3 seos.py shot run "$shot_id" --runtime-root work/energy_impact_001/runtime --json)
run_id=$(printf '%s\n' "$run_json" | jq -r '.run.run_id')
python3 seos.py package run "$run_id" --runtime-root work/energy_impact_001/runtime --package-root work/energy_impact_001/packages --json
python3 seos.py package shot "$shot_id" --runtime-root work/energy_impact_001/runtime --package-root work/energy_impact_001/packages --json
python3 seos.py review create "$shot_id" --runtime-root work/energy_impact_001/runtime --package-root work/energy_impact_001/packages --output-root work/energy_impact_001/review_artifacts --json
```

## Expected Outputs

- Houdini cache/preview.
- ComfyUI image output.
- DaVinci project/version probe artifact.
- SEOS package manifest.
- Review artifact.

All media movement is represented by ArtifactRefs. Direct media transfer into DaVinci is not claimed by this skill.
