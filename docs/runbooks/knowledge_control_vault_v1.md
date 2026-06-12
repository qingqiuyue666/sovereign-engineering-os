# Knowledge Control Vault Runbook V1

This runbook explains the P0 SEOS Knowledge Layer workflow. The layer creates a
local Markdown control vault and relation graph for human review. It does not
approve work, create execution permits, execute tools, or replace SEOS evidence.

## Initialize A Vault

```bash
python3 -m kernel.knowledge.cli init \
  --vault ~/SEOS-Control-Vault \
  --profile obsidian \
  --json
```

This creates the directory layout, `.obsidian/app.json`, and a vault manifest.
Obsidian is optional; the files are plain Markdown and JSON.

## Export A Workspace

```bash
python3 -m kernel.knowledge.cli export-workspace \
  --workspace .seos-workspace \
  --vault ~/SEOS-Control-Vault \
  --profile obsidian \
  --json
```

The export writes task notes, receipt notes, evidence-trace notes, a workspace
dashboard, and `99_Graph/seos_control_graph.json`.

## Export One Task

```bash
python3 -m kernel.knowledge.cli export-task TASK_ID \
  --workspace .seos-workspace \
  --vault ~/SEOS-Control-Vault \
  --profile obsidian \
  --json
```

Use this after a task has receipts or evidence that should be mirrored for human
review.

## Build A Graph Without A Vault

```bash
python3 -m kernel.knowledge.cli graph build \
  --workspace .seos-workspace \
  --output reports/knowledge/seos_control_graph.json \
  --json
```

The graph is a mirror artifact with nodes and edges for tasks, receipts, and
evidence references.

## Scan A Vault

```bash
python3 -m kernel.knowledge.cli scan \
  --vault ~/SEOS-Control-Vault \
  --output-json reports/knowledge/control_vault_scan.json \
  --json
```

The scan checks Markdown frontmatter, authority values, and secret-like content.
A clean scan reports `ok: true`.

## Export Logseq Pages

```bash
python3 seos.py knowledge export-logseq \
  --workspace .seos-workspace \
  --root ~/Logseq-SEOS \
  --json
```

The Logseq adapter writes `pages/` and `journals/` Markdown files only. It does
not use Logseq DB mode and does not treat blocks as commands.

## Export And Import Anytype-Style Objects

```bash
python3 seos.py knowledge export-anytype \
  --workspace .seos-workspace \
  --output reports/knowledge/anytype_object_bundle.json \
  --json

python3 seos.py knowledge import-anytype \
  --source reports/knowledge/anytype_object_bundle.json \
  --output reports/knowledge/anytype_import_record.json \
  --json
```

The export is a neutral object/type/relation bundle. Import records the bundle
as `object_model_proposal_only`; it does not create tasks, approvals, permits,
receipts, or execution authority.

## Build A Notion Readonly Mirror Payload

```bash
python3 seos.py knowledge sync-notion \
  --mode readonly \
  --source reports/knowledge/anytype_import_record.json \
  --output reports/knowledge/notion_readonly_sync_payload.json \
  --json
```

This command writes a local JSON payload for optional operator review. It does
not call the Notion API, read tokens, sync pages, or make Notion a source of
truth.

## Ingest A Proposal Note

Proposal ingest is intentionally not exposed as execution authority. It records a
non-authoritative JSON proposal under `.seos/knowledge/proposals/`. A normal SEOS
task still has to be created and approved separately.

The expected frontmatter shape is:

```yaml
---
seos_type: "task"
seos_id: "TASK_PROPOSED"
authority: "proposal"
title: "Proposed task"
---
```

## Validation

```bash
python3 scripts/knowledge_control_vault_check_v1.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.tracer_bullet.test_knowledge_control_vault_v1 -v
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.tracer_bullet.test_knowledge_adapter_surface_v1 -v
```

The validation path exercises workspace creation, task creation, approval,
dry-run receipt creation, vault export, graph build, vault scan, and proposal-note
ingest while asserting that proposal/knowledge artifacts do not create task,
approval, permit, or execution authority.

## Safety Boundary

- `authority: proposal` means human intent only.
- `authority: mirror` means SEOS-generated read-only view.
- `authority: receipt` means SEOS-generated receipt summary.
- `authority: invalid` means a note failed validation.

Knowledge notes must not be treated as approval receipts, permits, credential
stores, local execution requests, or security boundaries.
