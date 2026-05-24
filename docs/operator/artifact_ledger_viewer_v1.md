# Artifact Ledger Viewer V1

## Scope

Artifact Ledger Viewer V1 provides read-only local visibility over JSON artifact
records. It supports artifact listing, filters by task, run, milestone, and
artifact kind, plus redacted receipt, failure bundle, and replay manifest views.

## Boundary

The viewer does not mutate artifacts, delete artifacts, execute commands, launch
browsers, access networks, call providers, store credentials, or grant
production autonomy.

## Supported Views

- artifact summary
- receipt view
- failure bundle view
- replay manifest view
- task-filtered view
- run-filtered view
- milestone-filtered view

## Secret Display Policy

Keys containing secret-like material, including `secret`, `token`, `api_key`,
`credential`, `password`, `raw_prompt`, or `raw_response`, are redacted in the
summary preview.

## CLI

```bash
python3 tools/artifact_ledger_viewer.py /path/to/artifacts --milestone A3
```

The CLI prints JSON to stdout only.
