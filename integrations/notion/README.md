# Notion Integration

Notion support is a read-only mirror payload builder for operator-owned review
or later manual publishing. SEOS does not call the Notion API from this adapter,
does not read tokens, and does not make Notion a task or approval database.

## Supported Role

- public/team dashboard payload
- release or audit summary mirror
- reviewed handoff JSON for a separate operator-owned publishing step

## Unsupported Role

- task source of truth
- approval source of truth
- permit store
- raw evidence store
- cloud sync performed by SEOS
- credential storage

## Runtime Path

```bash
python3 seos.py knowledge sync-notion \
  --mode readonly \
  --source reports/knowledge/anytype_import_record.json \
  --output reports/knowledge/notion_readonly_sync_payload.json \
  --json
```

The payload records `network_call_performed: false`,
`credential_required_by_this_step: false`, and
`execution_authority_granted: false`.
