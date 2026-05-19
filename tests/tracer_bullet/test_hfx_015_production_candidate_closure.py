"""Tracer-bullet tests for HFX_015 production candidate closure."""

from __future__ import annotations

from pathlib import Path
import json
import unittest


ROOT = Path("assets/houdini/hfx_factory_core12/300_PRODUCTION_UPGRADE/HFX_015_PORTAL_RING")
JSON_PATH = ROOT / "HFX_015_PRODUCTION_CANDIDATE_CLOSURE.json"
MD_PATH = ROOT / "HFX_015_PRODUCTION_CANDIDATE_CLOSURE.md"


class HFX015ProductionCandidateClosureTests(unittest.TestCase):
    def test_generated_hfx_015_closure_exists(self):
        self.assertTrue(JSON_PATH.is_file())
        self.assertTrue(MD_PATH.is_file())

    def test_hfx_015_does_not_fake_gold_status(self):
        payload = json.loads(JSON_PATH.read_text(encoding="utf-8"))

        self.assertEqual(payload["closure_status"], "production_candidate")
        self.assertNotEqual(payload["closure_status"], "gold_complete")

    def test_closure_records_missing_gates(self):
        payload = json.loads(JSON_PATH.read_text(encoding="utf-8"))

        self.assertIn("rollback_or_quarantine_route_exists", payload["missing_gates"])

    def test_closure_preserves_no_render_no_hython_boundary(self):
        payload = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        boundaries = set(payload["boundary_conditions"])

        self.assertIn("no_render_execution", boundaries)
        self.assertIn("no_hython_execution", boundaries)
        self.assertIn("no_houdini_launch", boundaries)
        self.assertIn("no_hip_or_hda_mutation", boundaries)

    def test_source_safety_passes(self):
        source = Path("tools/generate_hfx_015_production_candidate_closure.py").read_text(encoding="utf-8")
        for marker in ("subprocess", "socket", "requests", "httpx", "sqlite3", "os.environ", "os.getenv", "load_dotenv"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
