"""Behavior tests for multimodal review artifacts."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from creative.common import write_json
from execution_plane.review_artifacts import create_review_artifact


class MultimodalReviewArtifactV1Tests(unittest.TestCase):
    def test_review_artifact_groups_artifact_refs_by_media_type(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            shot_dir = root / "runtime" / "shots" / "SHOT"
            run_dir = shot_dir / "runs" / "RUN"
            write_json(shot_dir / "shot.json", {"runs": [{"run_id": "RUN", "receipt_path": (run_dir / "shot_run_receipt.json").as_posix()}]})
            write_json(
                run_dir / "shot_run_receipt.json",
                {
                    "terminal_status": "TERMINAL_SUCCEEDED",
                    "artifact_refs": [
                        {"artifact_id": "TXT", "media_type": "text/plain"},
                        {"artifact_id": "IMG", "media_type": "image/png"},
                    ],
                },
            )
            created = create_review_artifact("SHOT", runtime_root=root / "runtime", output_root=root / "reviews")
            review = json.loads(Path(created["review_path"]).read_text(encoding="utf-8"))
            packet = Path(created["packet_path"]).read_text(encoding="utf-8")

        self.assertEqual(review["slots"]["text"][0]["artifact_id"], "TXT")
        self.assertEqual(review["slots"]["image"][0]["artifact_id"], "IMG")
        self.assertIn("Review", packet)


if __name__ == "__main__":
    unittest.main()
