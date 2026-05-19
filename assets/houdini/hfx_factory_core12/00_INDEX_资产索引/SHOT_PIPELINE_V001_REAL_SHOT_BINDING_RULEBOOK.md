# SHOT Pipeline v001 Real Shot Binding Rulebook

Status: SHOT_PIPELINE_V001_REAL_SHOT_BINDING_RULEBOOK_READY

Purpose:
Turn the sealed Houdini HFX asset library into a real shot production pipeline.

This layer binds:
- shot_id
- take_id
- plate
- camera
- Unreal scene/render
- Houdini hero HIP
- selected HFX assets
- EXR/render pass map
- AE/DaVinci/ComfyUI handoff
- validation checklist
- delivery manifest

Hard Rules:
- Do not modify Batch 01-05 final sealed release packages directly.
- Every real shot must get its own folder under 200_SHOTS.
- Every shot must have a shot_manifest.
- Hero shot HIP files must live under the shot folder, not inside final release packages.
- Render/export is blocked until shot_id, take_id, frame range, fps, camera, colorspace, and pass manifest are bound.
- EXR pass separation is required.
- Comp pass flattening is forbidden before final delivery review.
- ComfyUI is post/repair/stylization only, not source-of-truth geometry.
- Unreal handoff must be explicit if used.
- DaVinci handoff must be explicit for final grade.

Recommended shot workflow:
1. Duplicate SHOT_TEMPLATE_V001_REAL_SHOT_BINDING.
2. Rename folder to real shot id, for example SHOT_001_PORTAL_LANDING.
3. Fill shot_manifest_v001.json.
4. Bind plate and camera.
5. Select HFX assets.
6. Create hero HIP under 03_houdini/hero_hip.
7. Cache/render into shot-local folders only.
8. Generate EXR passes.
9. Composite in AE / DaVinci.
10. Validate and deliver.
