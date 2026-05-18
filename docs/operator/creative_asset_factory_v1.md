# Creative Asset Factory v1

## Purpose

Creative Asset Factory v1 is a private planning layer for operator-directed media production. It defines targets, tool roles, quality gates, and rollback notes without executing creative tools.

## First Sample Target

The first sample target is an 8-12 second VFX/AI/3D hybrid sample.

## Tool Roles

- Houdini for particle/VDB/field design.
- ComfyUI for image/video style enhancement.
- DaVinci Resolve for finishing/color.
- AE only for final assembly if needed.
- Blender and Unreal may be considered in later planning documents, but this v1 plan performs no execution.

## Execution Boundary

No Houdini/ComfyUI/DaVinci execution is performed. This module and document do not execute Houdini, ComfyUI, DaVinci Resolve, AE, Blender, Unreal, or any external tool.

The planning layer also performs:

- No subprocess execution.
- No tool launching.
- No file deletion.
- No provider execution.
- No network execution.
- No production autonomy.

## Plan Fields

- Plan ID.
- Project name.
- Target output.
- Duration seconds.
- Visual style.
- Shot plan.
- Tool roles.
- Asset requirements.
- Production steps.
- Blocked execution.
- Quality gates.
- Rollback notes.
- Policy version.
- Code version.

## Production Steps

1. Define the visual target and sample duration.
2. Draft a shot plan with timing, motion, and transition notes.
3. Assign tool roles without launching tools.
4. List required assets and evidence placeholders.
5. Define quality gates for visual coherence, timing, safety boundaries, and delivery readiness.
6. Use human review before any external production execution is considered in a separate authorized slice.

## Quality Gates

- Duration target remains within 8-12 seconds.
- Tool role assignments are planning-only.
- No external execution is implied.
- No raw prompts or provider responses are stored.
- Rollback is document-only and validator-only.

## Rollback Notes

Revert the planning document, deterministic builder, and tests together if the boundary is rejected. Rollback must not delete media files, launch tools, or enable provider execution.
