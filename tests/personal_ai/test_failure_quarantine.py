import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.failure_quarantine import (
    FailureQuarantineResult,
    write_failure_quarantine,
)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class FailureQuarantineTests(unittest.TestCase):
    def build_output_root(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        output_root = Path(temp_dir.name) / "packages"
        output_root.mkdir()
        return output_root

    def test_writes_failure_manifest(self):
        output_root = self.build_output_root()

        result = write_failure_quarantine(
            output_root,
            job_id="job-001",
            error_type="ValueError",
            error_message="input_dir is missing",
        )
        manifest = read_json(result.failure_manifest_path)

        self.assertIsInstance(result, FailureQuarantineResult)
        self.assertTrue(result.failure_manifest_path.exists())
        self.assertEqual(
            manifest["manifest_type"],
            "personal_ai_local_v1_failure_quarantine",
        )
        self.assertEqual(manifest["authority"], "non_authority")
        self.assertEqual(manifest["execution_capability"], "not_introduced")
        self.assertIs(manifest["required_human_approval"], True)
        self.assertEqual(manifest["error_type"], "ValueError")
        self.assertEqual(manifest["error_message"], "input_dir is missing")
        self.assertIs(manifest["partial_job_deleted"], False)
        self.assertIs(manifest["input_files_modified"], False)
        self.assertIs(manifest["raw_cell_values_copied"], False)

    def test_creates_failed_jobs_job_id_directory(self):
        output_root = self.build_output_root()

        result = write_failure_quarantine(
            output_root,
            job_id="job-001",
            error_type="ValueError",
            error_message="input_dir is missing",
        )

        self.assertEqual(
            result.quarantine_dir,
            output_root / "_failed_jobs" / "job-001",
        )
        self.assertTrue(result.quarantine_dir.is_dir())

    def test_rejects_bad_job_id(self):
        output_root = self.build_output_root()

        with self.assertRaisesRegex(ValueError, "job_id is invalid"):
            write_failure_quarantine(
                output_root,
                job_id="../bad",
                error_type="ValueError",
                error_message="input_dir is missing",
            )

    def test_truncates_long_error_message(self):
        output_root = self.build_output_root()
        long_message = "x" * 500

        result = write_failure_quarantine(
            output_root,
            job_id="job-001",
            error_type="ValueError",
            error_message=long_message,
        )
        manifest = read_json(result.failure_manifest_path)

        self.assertLessEqual(len(manifest["error_message"]), 240)
        self.assertTrue(manifest["error_message"].endswith("..."))

    def test_failure_manifest_does_not_copy_raw_sentinel_content(self):
        output_root = self.build_output_root()
        sentinel = "RAW_SENTINEL_CELL_VALUE_DO_NOT_COPY"

        result = write_failure_quarantine(
            output_root,
            job_id="job-001",
            error_type="ValueError",
            error_message=f"failed while reading {sentinel}",
        )

        self.assertNotIn(
            sentinel,
            result.failure_manifest_path.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
