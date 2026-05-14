# XLSX Readonly Runtime v1

## Status

- runtime: admitted for bounded local `.xlsx` metadata inspection
- adapter: `xlsx_readonly_runtime`
- dependency added: `openpyxl>=3.1,<4`
- network/API runtime: not introduced
- subprocess runtime: not introduced
- input mutation: forbidden
- existing output overwrite: forbidden
- raw workbook dump: forbidden

## Behavior

The runtime opens a local `.xlsx` workbook with `openpyxl` in readonly mode and
writes two artifacts outside the input directory:

- `xlsx_inspection.json`
- `xlsx_inspection_summary.md`

The JSON artifact records workbook filename, input SHA-256, sheet count, sheet
names, per-sheet dimensions, bounded formula/style scan results, extraction
limits, warnings, and bounded header preview metadata. The header preview does
not include raw cell values; it records type, blank state, text length, and
formula presence only.

## Boundaries

- no network calls
- no subprocess calls
- no external tool control
- no input file mutation
- no output overwrite
- no full raw spreadsheet cell copying into audit artifacts
- hash-bound input evidence is required
