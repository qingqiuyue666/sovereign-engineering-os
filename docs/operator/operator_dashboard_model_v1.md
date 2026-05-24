# Operator Dashboard Model V1

## Scope

Operator Dashboard Model V1 provides read-only data views for jobs, PR
readiness, artifacts, receipts, failures, approvals, and milestone state.

## Boundary

The model and CLI do not mutate records, merge pull requests, delete branches,
execute jobs, launch browsers, access networks, call providers, store
credentials, or grant production autonomy.

## Views

- `summary`
- `jobs`
- `pr_readiness`
- `artifacts`
- `receipts`
- `failures`
- `approvals`
- `milestones`

## CLI

```bash
python3 tools/operator_dashboard_viewer.py dashboard_fixture.json --view summary
```

The CLI reads one local JSON fixture and prints one redacted JSON view to stdout.
