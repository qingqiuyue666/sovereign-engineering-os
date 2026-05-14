import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.local_mvp_cli import main


FINAL_ARTIFACTS = {
    "input_snapshot.json",
    "intake_ledger.jsonl",
    "artifact_profile.json",
    "work_order_proposal.json",
    "review_packet.json",
    "pipeline_manifest.json",
    "task_route.json",
    "spreadsheet_processor_plan.json",
    "spreadsheet_readonly_inspection.json",
    "spreadsheet_report_plan.json",
    "spreadsheet_structural_report.json",
    "spreadsheet_structural_report.md",
    "artifact_index.json",
    "artifact_index_manifest.json",
    "final_job_manifest.json",
    "job_summary.json",
    "human_next_steps.md",
    "job_package_validation.json",
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class LocalMVPEndToEndSmokeTests(unittest.TestCase):
    def build_workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        input_dir = root / "input"
        output_root_dir = root / "packages"
        input_dir.mkdir()
        output_root_dir.mkdir()
        return input_dir, output_root_dir

    def test_local_mvp_cli_smoke_preserves_inputs_and_emits_final_package(self):
        input_dir, output_root_dir = self.build_workspace()
        sentinel = "RAW_SENTINEL_CELL_VALUE_DO_NOT_COPY"
        nested_dir = input_dir / "nested"
        nested_dir.mkdir()
        data_csv = input_dir / "data.csv"
        notes_md = input_dir / "notes.md"
        extra_tsv = nested_dir / "extra.tsv"
        data_csv.write_text(
            "account,value\n"
            f"alpha,{sentinel}\n",
            encoding="utf-8",
        )
        notes_md.write_text("local notes", encoding="utf-8")
        extra_tsv.write_text(
            "name\tvalue\n"
            f"beta\t{sentinel}\n",
            encoding="utf-8",
        )
        before_bytes = {
            path: path.read_bytes()
            for path in (data_csv, notes_md, extra_tsv)
        }

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(
                [
                    "--input-dir",
                    input_dir.as_posix(),
                    "--output-root-dir",
                    output_root_dir.as_posix(),
                    "--job-id",
                    "job-001",
                    "--recursive",
                ]
            )
        cli_output = stdout.getvalue()
        payload = json.loads(cli_output)
        job_dir = Path(payload["job_dir"])
        final_manifest = read_json(job_dir / "final_job_manifest.json")

        self.assertEqual(exit_code, 0)
        self.assertIs(payload["complete"], True)
        self.assertEqual({path.name for path in job_dir.iterdir()}, FINAL_ARTIFACTS)
        self.assertIs(final_manifest["complete"], True)
        self.assertTrue((job_dir / "spreadsheet_structural_report.json").exists())
        self.assertTrue((job_dir / "spreadsheet_structural_report.md").exists())
        self.assertNotIn(sentinel, cli_output)

        for path, expected_bytes in before_bytes.items():
            self.assertEqual(path.read_bytes(), expected_bytes)
            self.assertTrue(path.exists())

        for artifact_path in job_dir.iterdir():
            artifact_text = artifact_path.read_text(encoding="utf-8")
            self.assertNotIn(sentinel, artifact_text, msg=artifact_path.name)
            self.assertNotIn("kernel/adapters", artifact_text)


if __name__ == "__main__":
    unittest.main()
