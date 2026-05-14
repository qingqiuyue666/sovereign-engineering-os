# Approved XLSX Output Writer v1

## Status

- runtime: admitted for approved new `.xlsx` output generation
- adapter: `xlsx_output_writer`
- dependency: `openpyxl>=3.1,<4`
- input workbook mutation: forbidden
- existing output overwrite: forbidden
- output directory: must be outside the input directory
- source cell reading: not performed by the writer
- raw source cell values in audit artifacts: forbidden

## Flow

1. `plan_xlsx_output` binds an input workbook hash to an existing
   `xlsx_inspection.json` artifact and writes `xlsx_output_plan.json`.
2. `approve_xlsx_output` writes a human-review approval artifact bound to the
   plan hash.
3. `create_approved_xlsx_output` verifies the current input hash, plan hash,
   inspection hash, and approval hash before creating a new derived summary
   workbook.
4. `validate_xlsx_output` verifies the output workbook hash recorded in
   `xlsx_output_manifest.json`.

The only transformation in v1 is a metadata summary workbook derived from the
readonly inspection artifact. The writer does not open or copy source workbook
cell values.
