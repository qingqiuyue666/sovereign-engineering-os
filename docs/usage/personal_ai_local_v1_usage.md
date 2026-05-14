# Personal AI Local v1 Usage

Personal AI Local MVP v1 builds a deterministic local job package from a real
folder. It records local file metadata, proposes non-executing review work,
routes the package, inspects CSV/TSV spreadsheet structure read-only, and writes
JSON/Markdown artifacts outside the input directory. It also writes a
metadata-only artifact index and local validation report for generated package
artifacts.

## Personal AI Execution OS v2 runtime extension

The `personal-ai-execution-os-v2-system-longrun-v1` branch adds a bounded local
runtime foundation beside the v1 job package flow. The v1 package remains
non-authority and human-review-only; the v2 runtime commands add local `.xlsx`
metadata inspection, approved new `.xlsx` summary workbook generation, a
deterministic mock typed-schema model fixture, a deterministic local HTML
fixture browser runtime, and runtime delivery package validation.

V2 runtime commands:

- `inspect-xlsx`
- `plan-xlsx-output`
- `approve-xlsx-output`
- `create-approved-xlsx-output`
- `validate-xlsx-output`
- `run-model-fixture`
- `run-browser-fixture`
- `validate-runtime-delivery`
- `show-adapter-registry`
- `validate-tool-intake`

V2 XLSX output writing is fail-closed: `approve-xlsx-output` requires
explicit `--approved true`, `--human-reviewed true`, and a non-placeholder
`--reviewer-id` before `create-approved-xlsx-output` can write a new workbook.
There is no default or implicit approval path.

The v2 runtime foundation adds `openpyxl>=3.1,<4` for bounded local XLSX
read/write operations. It does not add live model providers, external network
browser automation, creative software runtime, subprocess runtime, unrestricted
external tool control, secrets, or third-party source vendoring.

Run:

```bash
python3 -m kernel.personal_ai.local_mvp_cli --input-dir ./input-folder --output-root-dir ./job-packages --job-id local-job-001
```

Equivalent explicit subcommand:

```bash
python3 -m kernel.personal_ai.local_mvp_cli run-local --input-dir ./input-folder --output-root-dir ./job-packages --job-id local-job-001
```

Optional flags:

- `--recursive` includes files under nested directories.
- `--include-hidden` includes hidden files.

Inputs:

- `--input-dir` must point to an existing local directory.
- Input files are read only for metadata, hashing, and bounded CSV/TSV
  structural inspection.
- Input files are not modified, moved, deleted, renamed, cleaned, or
  transformed.

Outputs:

- `--output-root-dir` must point to an existing directory outside the input
  directory.
- The CLI writes one job directory under the output root using `--job-id`.
- CLI failures write `_failed_jobs/<job-id>/failure_manifest.json` only when the
  output root exists.

## Local artifact index and validation

Each job package includes:

- `artifact_index.json`
- `artifact_index_manifest.json`
- `job_package_validation.json`

The artifact index records generated artifact names, relative paths, sizes,
hashes, extensions, and filename-derived search terms only. It does not index
raw file contents, raw input contents, raw cell values, or source spreadsheet
values.

Validate an existing job package:

```bash
python3 -m kernel.personal_ai.local_mvp_cli validate-job --job-dir ./job-packages/local-job-001
```

Rebuild the metadata-only index for an existing job package:

```bash
python3 -m kernel.personal_ai.local_mvp_cli index-artifacts --job-dir ./job-packages/local-job-001
```

## Approval-gated output package

The approval-gated output package creates a delivery directory only after a
hash-bound human approval decision validates the local v1 job id, approval
request hash, and generated artifact hashes. It packages approved generated
delivery artifacts from an existing job package into a separate output package
directory outside the input directory. It does not write spreadsheet outputs
and does not copy raw input file contents or raw cell values.

## Hash-bound approval provenance

This is local hash-bound provenance. It is not private-key cryptographic
signing. It uses no secrets, credentials, network, API, external tool control,
input mutation, raw cell value copying, or spreadsheet output writing.

1. Run the local MVP:

```bash
python3 -m kernel.personal_ai.local_mvp_cli --input-dir ./input-folder --output-root-dir ./job-packages --job-id local-job-001
```

2. Write `approval_request.json`:

```bash
python3 -m kernel.personal_ai.local_mvp_cli --input-dir ./input-folder --output-root-dir ./job-packages --job-id local-job-001 --write-approval-request ./approval_request.json
```

Equivalent explicit subcommand for an existing job package:

```bash
python3 -m kernel.personal_ai.local_mvp_cli write-approval-request --job-dir ./job-packages/local-job-001 --output-path ./approval_request.json
```

3. Read the approval request hashes from the CLI output and from
   `approval_request.json`.

4. Create `approval_decision.json` with the required hash fields:

Example `approval_decision.json`:

```json
{
  "approved": true,
  "approved_action": "create_approved_output_package",
  "approval_request_sha256": "<approval_request_sha256_excluding_self>",
  "decision_type": "personal_ai_local_output_approval_decision",
  "decision_version": 1,
  "final_job_manifest_sha256": "<final_job_manifest_sha256>",
  "human_reviewed": true,
  "job_id": "local-job-001",
  "spreadsheet_structural_report_json_sha256": "<spreadsheet_structural_report_json_sha256>",
  "spreadsheet_structural_report_md_sha256": "<spreadsheet_structural_report_md_sha256>"
}
```

5. Run approval-gated output package mode:

```bash
python3 -m kernel.personal_ai.local_mvp_cli --input-dir ./input-folder --output-root-dir ./job-packages --job-id local-job-001 --approval-request ./approval_request.json --approval-decision ./approval_decision.json --output-package-root-dir ./approved-output-packages --output-package-id approved-local-job-001
```

Equivalent explicit subcommand for an existing job package:

```bash
python3 -m kernel.personal_ai.local_mvp_cli create-approved-output --job-dir ./job-packages/local-job-001 --approval-request ./approval_request.json --approval-decision ./approval_decision.json --output-package-root-dir ./approved-output-packages --output-package-id approved-local-job-001
```

6. Inspect `provenance_chain.json` and `approved_output_validation.json` in the approved output package.

Validate an existing approved output package:

```bash
python3 -m kernel.personal_ai.local_mvp_cli validate-output --output-package-dir ./approved-output-packages/approved-local-job-001
```

Approved output package artifacts:

- `approved_output_manifest.json`
- `delivery_summary.json`
- `approval_receipt.json`
- `provenance_chain.json`
- `spreadsheet_structural_report.json`
- `spreadsheet_structural_report.md`
- `final_job_manifest.json`
- `approved_output_validation.json`

Approval-gated output package boundaries:

- No input mutation.
- No raw cell value copy.
- No spreadsheet output writing.
- No spreadsheet cleaning or transformation.
- No API or network calls.
- No external tool control.
- Human review only.

Final artifacts:

- `input_snapshot.json`
- `intake_ledger.jsonl`
- `artifact_profile.json`
- `work_order_proposal.json`
- `review_packet.json`
- `pipeline_manifest.json`
- `task_route.json`
- `spreadsheet_processor_plan.json`
- `spreadsheet_readonly_inspection.json`
- `spreadsheet_report_plan.json`
- `spreadsheet_structural_report.json`
- `spreadsheet_structural_report.md`
- `artifact_index.json`
- `artifact_index_manifest.json`
- `final_job_manifest.json`
- `job_summary.json`
- `human_next_steps.md`
- `job_package_validation.json`

Spreadsheet boundary:

- CSV and TSV are the only spreadsheet formats inspected.
- XLSX, XLSM, and XLS are not read.
- V1 job packages do not write spreadsheet output files; v2 approved XLSX
  output writing creates only new derived summary workbooks outside input
  directories after explicit reviewer approval with no default or implicit
  approval.
- No spreadsheet cleaning or transformation is performed.
- Raw cell values and raw header values are not copied into job artifacts.

Boundary:

- Local filesystem only.
- Non-authority.
- Human review only.
- Required human approval is true.
- No runtime authority.
- No arbitrary execution capability.
- No external tool control.
- No network.
- No API calls.
- No subprocess.
- No browser automation.
- No AI classification.
- No semantic classification.
- No issue severity assignment.
- No business semantic interpretation.
- No external OSS dependency is required for the v1 index, validators, snapshot
  helpers, or registry.
- No pandas, xlrd, or pyarrow.
- V2 adds `openpyxl>=3.1,<4` and `kernel/personal_ai/adapters/` for bounded
  local runtime adapters.

This is not a full external-tool OS. It does not control browsers, operating
system apps, APIs, LLM agents, adapters, or external tools. It does not modify
input files.
