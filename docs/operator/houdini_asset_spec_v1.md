# Houdini Asset Specification v1

## Purpose

This document defines the planning-only Houdini asset specification for the first 8-12 second cinematic VFX/AI/3D hybrid sample.

## No Houdini Execution

No Houdini/hython/tool execution is performed. This spec does not launch Houdini, does not run hython, does not execute shell tools, does not open local GUI tools, and does not generate files through external tool automation.

## Required Asset Classes

- particle_field
- vdb_smoke_or_energy
- velocity_pass
- depth_pass
- normal_pass
- emission_pass
- camera_metadata

## Particle Requirements

- Field motion must support a motivated transition into the hero frame.
- Particles should have readable directional flow.
- Density must avoid random noisy scatter.

## VDB And Field Requirements

- VDB smoke or energy volumes must support subject separation.
- Field assets must provide readable depth and motion cues.
- Energy must be designed for compositing passes, not uncontrolled prompt-only generation.

## Pass Exports

- Velocity pass.
- Depth pass.
- Normal pass.
- Emission pass.
- Reference frame metadata.
- Camera metadata.

## Naming And Directory Contract

Names must encode project, shot, asset class, pass, version, and frame range. Directories must separate source notes, pass specifications, review notes, and delivery outputs. This contract is a plan only and does not create directories.

## Quality Gates

- All required asset classes are present.
- Pass exports map to ComfyUI and finishing review needs.
- Camera metadata is explicit enough for downstream review.
- Blocked execution remains explicit.

## Rollback Plan

Revert this specification, runtime builder, and tests together if the asset boundary is rejected.
