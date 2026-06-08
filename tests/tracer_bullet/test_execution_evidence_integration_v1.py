"""Tests for execution result and materialization evidence integration."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from execution_plane.adapters.fake_dcc import run_fake_dcc
from execution_plane.evidence.collector import collect_execution_evidence
from execution_plane.permits.builder import create_execution_permit
from execution_plane.runner.result_envelope import sha256_file


class ExecutionEvidenceIntegrationV1Tests(unittest.TestCase):
    def test_fake_dcc_run_writes_result_and_materialization_records(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            permit = create_execution_permit(
                task_id="TASK_EVIDENCE",
                operator_approval_id="RCPT_EVIDENCE",
                allowed_adapter="fake_dcc",
                allowed_action="smoke_generate_file",
                allowed_output_root=root / "out",
                expires_at="2099-01-01T00:00:00Z",
            )
            result = run_fake_dcc(permit, job={"output_path": "output.txt", "content": "evidence\n"})
            collected = collect_execution_evidence(
                permit=permit,
                result=result,
                evidence_root=root / "reports" / "execution_plane",
                materialization_root=root / "reports" / "creative" / "materializations",
            )
            result_path = Path(collected["execution_result_path"])
            materialization_paths = [Path(path) for path in collected["materialization_paths"]]
            self.assertTrue(result_path.exists())
            self.assertEqual(len(materialization_paths), 1)
            self.assertTrue(materialization_paths[0].exists())

            stored_result = json.loads(result_path.read_text(encoding="utf-8"))
            materialization = json.loads(materialization_paths[0].read_text(encoding="utf-8"))
            output_record = next(item for item in stored_result["outputs"] if item["relative_path"] == "output.txt")
            output_hash = sha256_file(root / "out" / "output.txt")

        self.assertEqual(stored_result["permit_id"], permit["permit_id"])
        self.assertEqual(materialization["permit_id"], permit["permit_id"])
        self.assertEqual(materialization["run_id"], result["run_id"])
        self.assertEqual(materialization["lineage"]["task_id"], "TASK_EVIDENCE")
        self.assertEqual(materialization["sha256"], output_hash)
        self.assertEqual(output_record["sha256"], output_hash)
        self.assertNotIn(tempdir, json.dumps(stored_result, sort_keys=True))
        self.assertNotIn(tempdir, json.dumps(materialization, sort_keys=True))


if __name__ == "__main__":
    unittest.main()

