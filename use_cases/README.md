# Use Case Harness V1

This directory contains stable use case packets. Each packet defines the
problem, an input fixture, expected output fixture, acceptance notes, manual
baseline, automation gain, and failure modes.

The harness is documentation and JSON fixtures only. It does not run commands,
call networks, launch creative tools, control applications, mutate assets, or
provide a runner.

## Use Cases

- `uc_001_codex_pr_preflight`: evaluate a Codex-created PR before merge.
- `uc_002_local_test_receipt`: turn local test command results into receipts.
- `uc_003_github_pr_audit`: audit provided GitHub PR metadata, diff, and CI snapshots before merge.
- `uc_004_comfyui_workflow_static_check`: statically inspect ComfyUI workflow JSON without launching ComfyUI.
- `uc_005_creative_tool_inventory`: inventory installed creative tools without controlling them.

Future modules must name at least one stable use case ID before admission.
