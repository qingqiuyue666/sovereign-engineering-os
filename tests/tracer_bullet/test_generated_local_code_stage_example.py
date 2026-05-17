"""Tests for generated local code stage example."""

from __future__ import annotations

import json

import unittest

from pathlib import Path

DOC = Path("docs/runbooks/generated_local_code_stage_example_v1.md")

POLICY = Path("governance/local_train/generated_local_code_stage_example_v1.json")

class GeneratedLocalCodeStageExampleTests(unittest.TestCase):

    def test_generated_files_exist(self):

        self.assertTrue(DOC.is_file())

        self.assertTrue(POLICY.is_file())

    def test_generated_policy_is_active_and_local_only(self):

        payload = json.loads(POLICY.read_text(encoding="utf-8"))

        self.assertEqual(payload["artifact_version"], "v1")

        self.assertEqual(payload["status"], "active")

        self.assertFalse(payload["cloud_ai_used"])

        self.assertFalse(payload["freeform_shell_used"])

        self.assertFalse(payload["secret_read"])

    def test_generated_doc_records_boundaries(self):

        text = DOC.read_text(encoding="utf-8")

        self.assertIn("no cloud AI", text)

        self.assertIn("no freeform shell", text)

        self.assertIn("no secret reads", text)

        self.assertIn("does not implement production runtime behavior", text)

if __name__ == "__main__":

    unittest.main()

