"""Tracer-bullet tests for the workspace hygiene guide."""

from __future__ import annotations

from pathlib import Path
import unittest


class WorkspaceHygieneDocTests(unittest.TestCase):
    def test_workspace_hygiene_doc_exists(self):
        self.assertTrue(Path("docs/operator/workspace_hygiene.md").is_file())

    def test_doc_preserves_required_hygiene_rules(self):
        text = Path("docs/operator/workspace_hygiene.md").read_text(encoding="utf-8").lower()
        self.assertIn("no secrets", text)
        self.assertIn("no raw dumps", text)
        self.assertIn("no temporary extraction folders", text)
        self.assertIn("no repomix output committed unless explicitly requested", text)
        self.assertIn("no accidental desktop-local paths", text)


if __name__ == "__main__":
    unittest.main()
