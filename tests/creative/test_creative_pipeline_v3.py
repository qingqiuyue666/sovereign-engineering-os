from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from creative.assets.asset_registry_builder import build_registry
from creative.validation import run_named_check

REPO = Path(__file__).resolve().parents[2]

class CreativePipelineV3Tests(unittest.TestCase):
    def test_total_check_passes(self) -> None:
        result = run_named_check("creative_total_check_v3")
        self.assertTrue(result["ok"], result["errors"])

    def test_asset_registry_fixture_is_read_only(self) -> None:
        rows = build_registry(REPO / "tests/fixtures/creative/assets")
        self.assertGreaterEqual(len(rows), 2)
        self.assertTrue(all(row["read_only"] for row in rows))

    def test_cli_health_and_shot_create(self) -> None:
        health = subprocess.run([sys.executable, "seos.py", "creative", "health", "--json"], cwd=REPO, check=False, capture_output=True, text=True)
        self.assertEqual(health.returncode, 0, health.stderr + health.stdout)
        self.assertTrue(json.loads(health.stdout)["ok"])
        with tempfile.TemporaryDirectory() as temp_dir:
            shot = subprocess.run(
                [sys.executable, "seos.py", "creative", "shot", "create", "--root", temp_dir, "--shot-id", "SHOT_UNIT"],
                cwd=REPO,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(shot.returncode, 0, shot.stderr + shot.stdout)
            self.assertTrue((Path(temp_dir) / "SHOT_UNIT" / "shot_contract.json").exists())

if __name__ == "__main__":
    unittest.main()
