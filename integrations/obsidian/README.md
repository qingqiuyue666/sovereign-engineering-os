# Obsidian Integration

Obsidian is the P0 knowledge-tool integration for SEOS because it uses a local
folder of plain Markdown files. SEOS writes an Obsidian-compatible control vault,
but Obsidian is not part of the SEOS authority chain.

## Supported Role

- local human control room
- task, receipt, evidence, release, asset, and shot notes
- backlink and graph navigation
- public-safe review mirror
- proposal-note authoring

## Unsupported Role

- execution authority
- approval source of truth
- permit source of truth
- secret store
- RPA or desktop automation surface
- mandatory runtime dependency

## Runtime Path

Use the built-in knowledge CLI:

```bash
python3 seos.py knowledge init --vault ~/SEOS-Control-Vault --json
python3 seos.py knowledge export-workspace --workspace .seos-workspace --vault ~/SEOS-Control-Vault --json
python3 seos.py knowledge scan --vault ~/SEOS-Control-Vault --json
```

Templates in `templates/` document the expected Markdown frontmatter shape for
task, approval, permit, evidence, asset, shot, and release notes. The actual
exporter is implemented in `kernel/knowledge/vault.py` so the integration stays
local-first and dependency-free.
