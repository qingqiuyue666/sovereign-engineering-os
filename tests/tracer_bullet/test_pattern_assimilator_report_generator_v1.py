"""Behavior tests for pattern assimilator reports."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from creative.common import write_json
from execution_plane.pattern_assimilator import generate_pattern_report


class PatternAssimilatorReportGeneratorV1Tests(unittest.TestCase):
    def test_report_counts_failures_packages_reviews_and_actions(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            receipt = root / "runtime" / "shots" / "SHOT" / "runs" / "RUN" / "shot_run_receipt.json"
            write_json(
                root / "runtime" / "production_state.json",
                {
                    "projects": {"PROJ": {}},
                    "shots": {"SHOT": {"runs": [{"run_id": "RUN", "terminal_status": "TERMINAL_FAILED", "receipt_path": receipt.as_posix()}]}},
                },
            )
            write_json(receipt, {"workflow_receipt": {"failure_code": "ENV_NOT_FOUND"}})
            write_json(root / "packages" / "runs" / "RUN" / "manifest.json", {"package_kind": "run"})
            write_json(root / "reviews" / "REV" / "review_artifact.json", {"review_id": "REV"})
            report = generate_pattern_report(runtime_root=root / "runtime", package_root=root / "packages", review_root=root / "reviews", output_root=root / "patterns")
            loaded = json.loads(Path(report["report_path"]).read_text(encoding="utf-8"))

        self.assertEqual(loaded["failure_code_counts"]["ENV_NOT_FOUND"], 1)
        self.assertEqual(loaded["package_count"], 1)
        self.assertEqual(loaded["review_count"], 1)
        self.assertIn("Install or configure", loaded["suggested_actions"][0])


if __name__ == "__main__":
    unittest.main()
