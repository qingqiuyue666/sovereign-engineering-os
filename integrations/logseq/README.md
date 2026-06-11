# Logseq Integration

Logseq support is a P1-style mirror adapter for operators who prefer daily
journals and block-level task notes.

## Supported Role

- daily operations journal
- block-level task status view
- incident and blocker timeline
- plain Markdown page export

## Unsupported Role

- source of truth for approvals
- execution permit store
- local command executor
- default task database

## Runtime Path

```bash
python3 seos.py knowledge export-logseq \
  --workspace .seos-workspace \
  --root ~/Logseq-SEOS \
  --json
```

The adapter writes `pages/` and `journals/` files from the SEOS graph. It keeps
`execution_authority_granted: false` and does not rely on Logseq DB mode.
