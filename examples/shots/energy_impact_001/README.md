# energy_impact_001

Small production-proof shot template for the local DCC execution plane.

The committed files are templates and run instructions only. Runtime outputs are written under `work/energy_impact_001/` and remain uncommitted.

## Real Local Run

```bash
python3 seos.py project create "Energy Impact Project" --runtime-root work/energy_impact_001/runtime --json
python3 seos.py shot create <project_id> energy_impact_001 --runtime-root work/energy_impact_001/runtime --json
python3 seos.py shot attach-workflow <shot_id> examples/shots/energy_impact_001/workflow.json --runtime-root work/energy_impact_001/runtime --json
python3 seos.py shot run <shot_id> --runtime-root work/energy_impact_001/runtime --json
python3 seos.py package run <run_id> --runtime-root work/energy_impact_001/runtime --package-root work/energy_impact_001/packages --json
python3 seos.py package shot <shot_id> --runtime-root work/energy_impact_001/runtime --package-root work/energy_impact_001/packages --json
python3 seos.py review create <shot_id> --runtime-root work/energy_impact_001/runtime --package-root work/energy_impact_001/packages --output-root work/energy_impact_001/review_artifacts --json
```

## Expected Evidence

- Houdini physical cache, preview, metadata, log, ArtifactRefs, and execution receipt.
- ComfyUI image output, collection metadata, ArtifactRefs, and execution receipt.
- DaVinci project probe JSON, ArtifactRef, and execution receipt.
- Shot workflow receipt and shot run receipt.
- Run package manifest, shot package manifest, and review artifact.
