import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.snapshot_utils import (
    canonical_snapshot_json,
    normalize_snapshot_payload,
)


class SnapshotUtilsTests(unittest.TestCase):
    def test_normalizes_temp_paths_without_changing_values(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        payload = {
            "path": (root / "input" / "data.csv").as_posix(),
            "nested": [
                {
                    "job_dir": (root / "packages" / "job-001").as_posix(),
                    "count": 1,
                }
            ],
        }

        normalized = normalize_snapshot_payload(
            payload,
            path_replacements={root: "<tmp>"},
        )

        self.assertEqual(normalized["path"], "<tmp>/input/data.csv")
        self.assertEqual(normalized["nested"][0]["job_dir"], "<tmp>/packages/job-001")
        self.assertEqual(normalized["nested"][0]["count"], 1)

    def test_canonical_snapshot_json_is_sorted_and_stable(self):
        payload = {
            "b": 2,
            "a": {
                "z": "last",
                "m": "middle",
            },
        }

        snapshot = canonical_snapshot_json(payload)

        self.assertEqual(json.loads(snapshot), {"a": {"m": "middle", "z": "last"}, "b": 2})
        self.assertTrue(snapshot.endswith("\n"))
