# Personal AI Local v1 Usage

Personal AI Local MVP v1 builds a deterministic local job package from a real
folder. It records local file metadata, proposes non-executing review work,
routes the package, inspects CSV/TSV spreadsheet structure read-only, and writes
JSON/Markdown artifacts outside the input directory.

Run:

```bash
python3 -m kernel.personal_ai.local_mvp_cli --input-dir ./input-folder --output-root-dir ./job-packages --job-id local-job-001
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

## Approval-gated output package

The approval-gated output package creates a delivery directory only after an
explicit human approval decision validates the local v1 job id and approved
action. It packages approved generated delivery artifacts from an existing job
package into a separate output package directory outside the input directory.
It does not write spreadsheet outputs and does not copy raw input file contents
or raw cell values.

Example `approval_decision.json`:

```json
{
  "approved": true,
  "approved_action": "create_approved_output_package",
  "decision_type": "personal_ai_local_output_approval_decision",
  "human_reviewed": true,
  "job_id": "local-job-001"
}
```

Run approval-gated output package mode:

```bash
python3 -m kernel.personal_ai.local_mvp_cli --input-dir ./input-folder --output-root-dir ./job-packages --job-id local-job-001 --approval-decision ./approval_decision.json --output-package-root-dir ./approved-output-packages --output-package-id approved-local-job-001
```

Approved output package artifacts:

- `approved_output_manifest.json`
- `delivery_summary.json`
- `approval_receipt.json`
- `spreadsheet_structural_report.json`
- `spreadsheet_structural_report.md`
- `final_job_manifest.json`

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
- `final_job_manifest.json`
- `job_summary.json`
- `human_next_steps.md`

Spreadsheet boundary:

- CSV and TSV are the only spreadsheet formats inspected.
- XLSX, XLSM, and XLS are not read.
- No spreadsheet output files are written.
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
- No pandas, openpyxl, xlrd, or pyarrow.
- No kernel/adapters integration or changes.

This is not a full external-tool OS. It does not control browsers, operating
system apps, APIs, LLM agents, adapters, or external tools. It does not modify
input files.
