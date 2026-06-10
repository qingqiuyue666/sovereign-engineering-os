# Sword Slash Skill Runbook

## Scope

`sword_slash` is a Phase 2 production-prototype skill for `sword_slash_001`. It uses existing verified SEOS execution paths and adapters only: `houdini_hython`, `comfyui_local`, and `davinci_resolve`.

## Workflow and RPC References

Use `examples/shots/sword_slash_001/workflow.json` for the shot workflow. Use `examples/rpc/houdini_smoke_cache_test.json`, `examples/rpc/comfyui_submit_workflow.json`, and `examples/rpc/davinci_project_probe.json` for individual local DCC evidence.

## Expected Outputs

Houdini should produce `smoke_cache.bgeo.sc`, `smoke_cache_preview.exr`, `smoke_cache_metadata.json`, and `smoke_cache_execution.log`. ComfyUI should produce PNG output plus ArtifactRefs. DaVinci Resolve should produce version/project probe JSON plus ArtifactRefs. SEOS package and review commands should produce a package manifest and review artifact.

## Commands

```bash
python3 seos.py rpc invoke examples/rpc/houdini_smoke_cache_test.json --json
python3 seos.py rpc invoke examples/rpc/comfyui_submit_workflow.json --json
python3 seos.py rpc invoke examples/rpc/davinci_project_probe.json --json
python3 seos.py skill show sword_slash
```

Runtime outputs belong under `work/phase2/sword_slash_001/` and must not be committed.

## Honest Limitation

This skill uses the existing Houdini smoke/cache output path as slash-trail physical prototype evidence. It does not claim a dedicated blade solver.
