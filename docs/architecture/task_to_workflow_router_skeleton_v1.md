# Task-to-Workflow Router Skeleton V1

## Purpose

Create the first production-intelligence layer by converting structured task
intent into deterministic workflow graph descriptors.

## Architecture

`TaskIntent` captures task id, domain, objective, inputs, constraints, risk
tolerance, and desired outputs. `route_task_intent()` selects a domain template
and emits a `WorkflowGraphDescriptor` with nodes, edges, required tools,
required assets, approval requirements, evidence requirements, rollback plan,
evaluation plan, and deterministic graph hash.

## Safety boundaries

The descriptor is not executable. It does not encode raw commands, command
lines, argv, subprocess calls, network calls, provider calls, model calls, or
direct tool launches. High-risk workflow domains require operator approval
metadata before any future runtime promotion.

## Explicit non-goals

This does not run workflows, call providers, call models, call network, launch
DCC tools, launch ComfyUI, start daemons, start schedulers, or enable production
autonomy.
