# SEOS Knowledge Layer V1

SEOS Knowledge Layer turns governed SEOS artifacts into human-readable notes,
relation graphs, and public-safe control dashboards without moving authority out
of the SEOS core.

## Authority Boundary

SEOS core remains the authority for:

- task contracts
- approval and rejection receipts
- execution permits
- execution result envelopes
- materialization records
- evidence traces
- replay explanations
- release readiness decisions

Knowledge artifacts are only:

- `proposal`: human-authored intent that still requires normal SEOS task intake
- `mirror`: SEOS-generated read-only human view
- `receipt`: SEOS-generated receipt summary
- `invalid`: a note or object that failed validation

A Markdown note, Obsidian vault, Logseq page, Anytype object, or Notion page must
never become an execution permit, approval source of truth, or security boundary.

## Module Layout

```text
kernel/knowledge/
  object_model.py        # object/relation model and digests
  frontmatter.py         # dependency-free frontmatter scalar subset
  markdown_renderer.py   # Markdown notes with canonical JSON blocks
  redaction.py           # public path refs and shared secret-scan redaction
  graph.py               # workspace task/receipt graph builder
  vault.py               # Obsidian-compatible local Markdown vault exporter
  vault_scanner.py       # vault inventory and safety scan
  proposal_ingest.py     # proposal-note ingest without authority transfer
  cli.py                 # seos-knowledge entrypoint
```

## P0: Obsidian-Compatible Control Vault

The P0 integration is filesystem-first. It writes plain Markdown and JSON files to
an operator-owned local directory:

```text
SEOS-Control-Vault/
  00_Index/
  01_Tasks/
  02_Approvals/
  03_Permits/
  04_Evidence/
  05_Assets/
  06_Shots/
  07_Runs/
  08_Releases/
  09_Audit/
  99_Graph/
```

Obsidian is not required in CI. Any Markdown reader can inspect the output.
Obsidian simply provides local navigation, backlinks, graph view, and operator
experience.

## Public Safety Rules

Public exports must:

- use relative or redacted path references
- preserve digests instead of raw private evidence where possible
- mark `local_path_redacted: true`
- mark `execution_authority_granted: false`
- run the shared bounded secret scanner for notes
- keep raw task authority in `.seos/` artifacts, not in notes

Private exports are available through `--private`, but they are still not an
authority layer.

## Proposal Ingest

Proposal ingest reads a Markdown note with `authority: proposal` and records a
`seos_knowledge_proposal_v1` JSON artifact under `.seos/knowledge/proposals/`.
It deliberately records:

- `task_created: false`
- `approval_created: false`
- `permit_created: false`
- `execution_authority_granted: false`

The operator must still create a task through normal SEOS task intake and then
approve/run through normal gates.

## Future Integration Order

Recommended order:

1. Obsidian-compatible Markdown vault
2. Logseq Markdown/Org journal adapter
3. Anytype object export/import adapter, without source or license coupling
4. Notion read-only public/team mirror

The order keeps local-first control and avoids making cloud collaboration tools
part of the execution chain.
