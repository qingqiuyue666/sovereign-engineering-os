# Local Spreadsheet Readonly Inspector MVP Decision Audit v1

Verdict: `APPROVE_LOCAL_SPREADSHEET_READONLY_INSPECTOR_MVP_IMPLEMENTATION`

## Decision

This package is implementation, but only local-only non-authority read-only
inspection implementation.

This package adds deterministic read-only CSV/TSV spreadsheet inspection over
existing job package artifacts.

This package authorizes reading CSV/TSV text content only for inspection
metrics.

This package does not authorize XLSX/XLSM/XLS content reading.

This package does not authorize spreadsheet processing execution.

This package does not authorize spreadsheet output writing.

This package does not authorize spreadsheet cleaning or transformation.

This package does not authorize pandas/openpyxl/xlrd/pyarrow integration.

This package does not authorize runtime authority.

This package does not authorize execution capability.

This package does not authorize external tool control.

This package does not authorize adapter implementation.

This package does not authorize API calls.

This package does not authorize AI classification.

This package does not authorize semantic classification.

This package does not authorize file mutation.

This package does not authorize destructive actions.

This package does not authorize copying raw input file contents into the job
package.

This package does not authorize Business / Creative / Research OS.

This package does not authorize full Personal AI Execution OS implementation.

The only new physical-world contact is read-only CSV/TSV content inspection
for bounded structural metrics.

## Selected MVP Components

1. deterministic spreadsheet_readonly_inspection.json
2. CSV/TSV-only read-only inspection
3. spreadsheet_processor_plan compatibility gate
4. bounded row sampling limit for metrics
5. no raw cell content copied into output
6. job package integration
7. end-to-end local temporary-file tests

## Boundary

- authority status: non-authority
- execution status: no execution capability
- runtime status: no runtime authority
- external tool control: not introduced
- network: not introduced
- API calls: not introduced
- subprocess: not introduced
- browser automation: not introduced
- AI classification: not introduced
- semantic classification: not introduced
- adapter implementation: not introduced
- kernel/adapters: unchanged
- spreadsheet content read: bounded CSV/TSV structural inspection only
- raw cell value copying: not introduced
- spreadsheet output write: not introduced
- spreadsheet cleaning or transformation: not introduced
- XLSX/XLSM/XLS reading: not introduced
- pandas/openpyxl/xlrd/pyarrow: not introduced
- input files: never modified / moved / deleted / renamed
- input file contents: raw contents not copied into job package
- next allowed action: human_review_only
- required human approval: true

## Authorized Output Shape

The local job package may add only:

- `spreadsheet_readonly_inspection.json`

The spreadsheet readonly inspection output is limited to deterministic
source-artifact paths, selected artifact counts, CSV/TSV structural metrics,
unsupported extension records for XLSX/XLSM/XLS selections, missing-file
records, parse-error type names, fixed forbidden actions, fixed boundaries,
and `human_review_only` as the next allowed action.

Supported read-only spreadsheet extensions are:

- `.csv`
- `.tsv`

Unsupported spreadsheet extensions in this package are:

- `.xlsx`
- `.xlsm`
- `.xls`

No spreadsheet processing execution, XLSX/XLSM/XLS content reading,
spreadsheet output writing, spreadsheet cleaning or transformation,
pandas/openpyxl/xlrd/pyarrow integration, runtime authority, execution
capability, external tool control, network access, API calls, AI
classification, semantic classification, adapter implementation, destructive
file operation, input file mutation, raw input content copying, raw cell value
copying, Business Delivery OS, Creative Production OS, Research Decision OS,
or full Personal AI Execution OS implementation is authorized by this
decision.
