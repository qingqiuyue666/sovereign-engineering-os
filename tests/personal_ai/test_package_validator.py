import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.job_package import build_local_job_package
from kernel.personal_ai.package_validator import (
    JobPackageValidationResult,
    build_job_package_validation,
)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class JobPackageValidationTests(unittest.TestCase):
    def build_job(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        input_dir = root / "input"
        output_root_dir = root / "packages"
        input_dir.mkdir()
        output_root_dir.mkdir()
        sentinel = "RAW_SENTINEL_CELL_VALUE_DO_NOT_COPY"
        (input_dir / "data.csv").write_text(
            "account,value\n"
            f"alpha,{sentinel}\n",
            encoding="utf-8",
        )
        result = build_local_job_package(
            input_dir,
            output_root_dir,
            job_id="job-001",
        )
        return result, sentinel

    def test_writes_complete_job_package_validation(self):
        job_result, sentinel = self.build_job()
        validation = read_json(job_result.job_package_validation_path)

        self.assertEqual(
            validation["validation_type"],
            "personal_ai_local_v1_job_package_validation",
        )
        self.assertIs(validation["complete"], True)
        self.assertEqual(validation["missing_artifacts"], [])
        self.assertEqual(validation["malformed_artifacts"], [])
        self.assertIs(validation["final_manifest_complete"], True)
        self.assertIs(validation["artifact_index_manifest_verified"], True)
        self.assertIs(validation["boundaries_verified"], True)
        self.assertIs(validation["raw_sentinel_leakage_detected"], False)
        self.assertIs(validation["raw_cell_values_copied"], False)
        self.assertIs(validation["spreadsheet_output_written"], False)
        self.assertNotIn(
            sentinel,
            job_result.job_package_validation_path.read_text(encoding="utf-8"),
        )

    def test_detects_generated_artifact_sentinel_leakage(self):
        job_result, sentinel = self.build_job()
        leak_path = job_result.job_dir / "leak.json"
        leak_path.write_text(
            json.dumps({"leak": sentinel}) + "\n",
            encoding="utf-8",
        )

        result = build_job_package_validation(
            job_result.job_dir,
            raw_sentinel_values=[sentinel],
        )
        validation = read_json(result.output_validation_path)

        self.assertIsInstance(result, JobPackageValidationResult)
        self.assertIs(result.complete, False)
        self.assertIs(result.raw_sentinel_leakage_detected, True)
        self.assertIs(validation["raw_sentinel_leakage_detected"], True)

    def test_detects_spreadsheet_output_files(self):
        job_result, _ = self.build_job()
        (job_result.job_dir / "forbidden_output.xlsx").write_text(
            "not allowed",
            encoding="utf-8",
        )

        result = build_job_package_validation(job_result.job_dir)

        self.assertIs(result.complete, False)
        self.assertEqual(result.spreadsheet_output_files, ["forbidden_output.xlsx"])
