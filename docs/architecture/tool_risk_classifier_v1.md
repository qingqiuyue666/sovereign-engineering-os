# Tool Risk Classifier V1

## Purpose

Classify tools, MCP servers, scripts, DCC apps, ComfyUI workflows, provider APIs,
browser automation surfaces, models, render tools, and plugins before any future
runtime admission.

## Behavior

`classify_tool_risk()` accepts a `ToolRiskDescriptor` and returns a
`ToolRiskAssessment` with risk classes, highest risk, approval/token flags,
production admission status, reasons, and a deterministic content hash.

## Risk Boundary

Read-only descriptors may be production admitted. File writes, process launch,
network access, browser control, provider API usage, DCC control, ComfyUI
execution, model execution, render execution, and plugin execution require
approval. Credential touching and unknown capabilities become `HIGH_RISK`.

Plugin execution requires an explicit sandbox strategy before admission.

## Non-Goals

This does not execute tools, spawn processes, accept raw commands, accept argv,
accept command lines, call network, automate browsers, call providers, store
credentials, launch DCC applications, launch ComfyUI, install dependencies,
vendor external systems, or enable production autonomy.
