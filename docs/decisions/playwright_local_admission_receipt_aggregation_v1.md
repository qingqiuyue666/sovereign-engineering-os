# Playwright Local Admission Receipt Aggregation v1

Status: accepted

## Decision

Add a non-authoritative Playwright local admission receipt aggregation record
that reads existing #424 local-only fixture scenario suite outputs and produces
a deterministic historical evidence packet for human review.

The aggregator accepts an ordered JSON suite-run-dirs manifest, an existing
output directory, an aggregation id, and an exact local-only review attestation.
It validates suite result types, local file fixture scope, false boundary
fields, artifact index path containment, symlink absence, recorded hashes,
candidate artifact flags, pass rate, flaky scenarios, regression sequence,
required core scenario coverage, and optional evidence staleness metadata.

## Boundary

This is artifact reading, validation, aggregation, and reporting only. It does
not execute #424 or #422, does not run browser automation, does not install
packages or download browsers, does not access candidate repository code, and
does not grant production, live website, or general browser automation
admission.

## Outputs

- `playwright_local_admission_receipt_aggregation_plan.json`
- `playwright_local_admission_receipt_aggregation_result.json`
- `playwright_local_admission_receipt_aggregation_manifest.json`
- `playwright_local_admission_receipt_aggregation_summary.md`
- `playwright_local_admission_receipt_aggregation_checklist.md`
- `artifact_index.json`
- `artifact_index_manifest.json`

Plan-only mode omits the result file and does not evaluate suite runs.

## Human Review

The required review attestation is:

`I_REVIEWED_LOCAL_ONLY_PLAYWRIGHT_SUITE_RUNS_NO_LIVE_WEBSITES_NO_ACCOUNTS_NO_SCRAPING_NO_BYPASS`

Aggregation success means the local fixture evidence packet passed its local
thresholds. It remains non-authoritative and requires human review before any
future scope expansion.
