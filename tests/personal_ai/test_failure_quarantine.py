import json
import tempfile
import unittest
from pathlib import Path

from kernel.evidence.sealed_redaction_contract import validate_sealed_evidence_record
from kernel.personal_ai.failure_quarantine import (
    FailureQuarantineResult,
    build_failure_quarantine_sealed_evidence_payload,
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
        self.assertIn("error_message_sha256", manifest)
        self.assertIs(manifest["partial_job_deleted"], False)
        self.assertIs(manifest["input_files_modified"], False)
        self.assertIs(manifest["raw_cell_values_copied"], False)
        self.assertIs(manifest["raw_traceback_persisted"], False)
        self.assertIs(manifest["raw_exception_dump_persisted"], False)
        self.assertIs(manifest["secret_value_read"], False)
        self.assertIs(manifest["secret_value_persisted"], False)
        self.assertIs(manifest["runtime_execution_performed"], False)
        self.assertIs(manifest["external_network_accessed"], False)
        self.assertIs(manifest["subprocess_executed"], False)
        self.assertIs(manifest["runtime_authority_granted"], False)
        self.assertIn("sealed_evidence_payload", manifest)

    def test_sealed_evidence_payload_is_embedded_and_contract_valid(self):
        output_root = self.build_output_root()

        result = write_failure_quarantine(
            output_root,
            job_id="job-001",
            error_type="ValueError",
            error_message="SECRET_TOKEN=sk-test-secret-value traceback raw stack",
        )
        manifest = read_json(result.failure_manifest_path)
        sealed_payload = manifest["sealed_evidence_payload"]

        self.assertEqual(sealed_payload["evidence_contract"], "sealed_redaction_v1")
        evidence = sealed_payload["evidence"]
        validation = validate_sealed_evidence_record(evidence)
        self.assertTrue(validation.accepted, validation.failures)
        self.assertEqual(evidence["classification"], "secret")
        self.assertEqual(evidence["representation"], "redacted_digest")
        self.assertTrue(str(evidence["digest"]).startswith("sha256:"))
        evidence_payload = evidence["payload"]
        self.assertEqual(evidence_payload["job_id"], "job-001")
        self.assertEqual(evidence_payload["manifest_type"], "personal_ai_local_v1_failure_quarantine")
        self.assertFalse(evidence_payload["raw_traceback_persisted"])
        self.assertFalse(evidence_payload["raw_exception_dump_persisted"])
        self.assertFalse(evidence_payload["secret_value_read"])
        self.assertFalse(evidence_payload["secret_value_persisted"])
        self.assertFalse(evidence_payload["runtime_execution_performed"])
        self.assertFalse(evidence_payload["external_network_accessed"])
        self.assertFalse(evidence_payload["subprocess_executed"])
        serialized = json.dumps(sealed_payload, sort_keys=True)
        self.assertNotIn("SECRET_TOKEN", serialized)
        self.assertNotIn("sk-test-secret-value", serialized)
        self.assertNotIn("traceback raw stack", serialized)

    def test_build_failure_quarantine_sealed_evidence_payload_rejects_runtime_true(self):
        manifest = {
            "manifest_type": "personal_ai_local_v1_failure_quarantine",
            "required_human_approval": True,
            "job_id": "job-001",
            "error_type": "ValueError",
            "error_message_sha256": "a" * 64,
            "authority": "non_authority",
            "execution_capability": "not_introduced",
            "boundaries": {"local_only": True},
            "partial_job_deleted": False,
            "input_files_modified": False,
            "input_file_contents_copied": False,
            "raw_cell_values_copied": False,
            "traceback_copied": False,
            "raw_traceback_persisted": False,
            "raw_exception_dump_persisted": False,
            "secret_value_read": False,
            "secret_value_persisted": False,
            "secret_value_serialized": False,
            "runtime_execution_performed": True,
            "external_network_accessed": False,
            "subprocess_executed": False,
            "runtime_authority_granted": False,
        }

        with self.assertRaisesRegex(ValueError, "runtime_execution_performed must be false"):
            build_failure_quarantine_sealed_evidence_payload(manifest)

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

    def test_source_does_not_introduce_runtime_network_or_secret_read_surface(self):
        source = Path("kernel/personal_ai/failure_quarantine.py").read_text(
            encoding="utf-8"
        )
        forbidden_markers = (
            "requests",
            "httpx",
            "urllib",
            "socket.",
            "subprocess",
            "os.system",
            "openai.",
            "getenv",
            "environ",
        )
        for marker in forbidden_markers:
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
