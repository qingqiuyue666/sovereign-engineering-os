# Creative Asset Factory Production Bible v1

## Purpose

This production bible defines the first private Creative Asset Factory sample as a planning/spec/report asset only. No external tool execution is performed.

## Sample Target

- 8-12 seconds.
- Cinematic VFX/AI/3D hybrid.
- One strong hero frame.
- Motivated transition from field emergence into the hero frame, then into a clean resolve.
- No cheap AI artifact look.
- No random prompt-only generation.

## Story Beat

A controlled energy field wakes in darkness, condenses into a single readable hero frame, then transitions through motivated particle motion into a finished cinematic resolve.

## Tool Roles

- Houdini: particle, VDB, and field assets.
- ComfyUI: controlled enhancement and stylization using passes and references.
- DaVinci Resolve: finishing, color, contrast, export checks.
- AE: assembly or final polish only if needed.

## Required Assets

- Hero frame description and reference language.
- Shot list with timing.
- Houdini pass requirements.
- Controlled ComfyUI pass map.
- DaVinci finishing checklist.
- Review rubric.
- Rollback plan.

## Quality Gates

- Duration remains 8-12 seconds.
- The hero frame is readable at thumbnail size.
- Motion transition is motivated by the shot physics.
- Stylization enhances controlled passes and does not replace them.
- AI artifacts, warped detail, flicker, mush, and random texture drift are rejection triggers.
- No raw prompts or raw outputs are persisted.

## Blocked Execution

No external tool execution is allowed in this bible. Do not launch Houdini, ComfyUI, DaVinci Resolve, After Effects, Blender, Unreal, shell tools, browser tools, local GUI tools, provider calls, network actions, production autonomy, financial execution, or trading automation.

## Delivery Outputs

- Production bible.
- Houdini asset specification.
- ComfyUI workflow specification.
- DaVinci finishing checklist.
- Creative asset review rubric.
- Private sprint plan.

## Rollback Plan

Rollback is document-only and validator-only: revert the bible, deterministic builder, and tests together. Rollback must not delete media, execute tools, or enable external production.
