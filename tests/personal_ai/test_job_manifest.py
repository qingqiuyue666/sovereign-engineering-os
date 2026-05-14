import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.job_manifest import (
    FinalJobManifestResult,
    build_final_job_manifest,
)
from kernel.personal_ai.job_package import build_local_job_package


EXPECTED_MANIFEST_KEYS = {
    "manifest_type",
    "authority",
    "execution_capability",
    "required_human_approval",
    "job_dir",
    "artifacts",
    "artifact_presence",
    "complete",
    "missing_artifacts",
    "route_type",
    "recommended_processor_lane",
    "spreadsheet_plan_status",
    "spreadsheet_report_status",
    "spreadsheet_structural_report_status",
    "boundaries",
    "forbidden_actions",
    "next_allowed_action",
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class JobManifestTests(unittest.TestCase):
    def build_workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        input_dir = root / "input"
        output_root_dir = root / "packages"
        input_dir.mkdir()
        output_root_dir.mkdir()
        return input_dir, output_root_dir

    def build_package(self, sentinel="RAW_SENTINEL_CELL_VALUE_DO_NOT_COPY"):
        input_dir, output_root_dir = self.build_workspace()
        (input_dir / "data.csv").write_text(
            "account,value\n"
            f"alpha,{sentinel}\n",
            encoding="utf-8",
        )
        (input_dir / "notes.md").write_text("local notes", encoding="utf-8")
        return build_local_job_package(
            input_dir,
            output_root_dir,
            job_id="job-001",
        )

    def test_manifest_generated_with_expected_shape(self):
        result = self.build_package()
        manifest = read_json(result.final_job_manifest_path)

        self.assertTrue(result.final_job_manifest_path.exists())
        self.assertEqual(set(manifest), EXPECTED_MANIFEST_KEYS)
        self.assertEqual(
            manifest["manifest_type"],
            "personal_ai_local_v1_final_job_manifest",
        )
        self.assertEqual(manifest["authority"], "non_authority")
        self.assertEqual(manifest["execution_capability"], "not_introduced")
        self.assertIs(manifest["required_human_approval"], True)
        self.assertEqual(manifest["next_allowed_action"], "human_review_only")

    def test_manifest_records_all_artifacts_present_and_complete(self):
        result = self.build_package()
        manifest = read_json(result.final_job_manifest_path)

        self.assertIs(manifest["complete"], True)
        self.assertEqual(manifest["missing_artifacts"], [])
        self.assertTrue(all(manifest["artifact_presence"].values()))
        self.assertIn("final_job_manifest", manifest["artifacts"])
        self.assertEqual(
            Path(manifest["artifacts"]["final_job_manifest"]).name,
            "final_job_manifest.json",
        )

    def test_manifest_copies_route_and_status_fields_from_generated_artifacts(self):
        result = self.build_package()
        manifest = read_json(result.final_job_manifest_path)
        task_route = read_json(result.task_route_path)
        spreadsheet_plan = read_json(result.spreadsheet_processor_plan_path)
        report_plan = read_json(result.spreadsheet_report_plan_path)
        structural_report = read_json(result.spreadsheet_structural_report_json_path)

        self.assertEqual(manifest["route_type"], task_route["route_type"])
        self.assertEqual(
            manifest["recommended_processor_lane"],
            task_route["recommended_processor_lane"],
        )
        self.assertEqual(
            manifest["spreadsheet_plan_status"],
            spreadsheet_plan["plan_status"],
        )
        self.assertEqual(
            manifest["spreadsheet_report_status"],
            report_plan["report_status"],
        )
        self.assertEqual(
            manifest["spreadsheet_structural_report_status"],
            structural_report["report_status"],
        )

    def test_manifest_does_not_copy_raw_cell_values(self):
        sentinel = "RAW_SENTINEL_CELL_VALUE_DO_NOT_COPY"
        result = self.build_package(sentinel=sentinel)

        self.assertNotIn(
            sentinel,
            result.final_job_manifest_path.read_text(encoding="utf-8"),
        )

    def test_missing_artifact_scenario_records_incomplete_manifest(self):
        result = self.build_package()
        (result.job_dir / "human_next_steps.md").unlink()

        manifest_result = build_final_job_manifest(
            result.job_dir,
            result.final_job_manifest_path,
        )
        manifest = read_json(result.final_job_manifest_path)

        self.assertIsInstance(manifest_result, FinalJobManifestResult)
        self.assertIs(manifest_result.complete, False)
        self.assertIs(manifest["complete"], False)
        self.assertEqual(manifest["missing_artifacts"], ["human_next_steps.md"])
        self.assertIs(manifest["artifact_presence"]["human_next_steps"], False)


if __name__ == "__main__":
    unittest.main()
