# ComfyUI Workflow Specification v1

## Purpose

This document defines a controlled ComfyUI workflow specification for the first private creative sample.

## No ComfyUI Execution

No ComfyUI/model/network execution is performed. The workflow spec does not run ComfyUI, does not load local model files, does not download models, does not access the network, and does not execute nodes.

## Required Constraints

- No prompt-only generation.
- No model download.
- No network.
- No execution.
- No raw prompt persistence.
- No raw output persistence.

## Required Input Passes

- depth
- normal
- emission_or_mask
- reference_frame

## Control Maps

Depth, normal, emission or mask, and reference frame controls must drive enhancement. Prompt text, if ever authorized later, may only describe style intent and must not be persisted raw.

## Style Reference Policy

Use style references as bounded visual language. Do not use random prompt-only generation, untracked model swaps, or uncontrolled image synthesis.

## Review Criteria

- Controlled passes remain visible in the result.
- No obvious AI artifact look.
- No flicker, mush, distorted geometry, or texture crawling.
- Output can be reviewed without persisting raw prompts or raw outputs.

## Blocked Execution

The spec blocks ComfyUI execution, model download, network access, raw prompt persistence, raw output persistence, provider calls, production autonomy, and external action execution.

## Rollback Plan

Revert this spec, runtime builder, and tests together. Do not delete models, launch tools, or execute workflows as rollback.
