"""Tracer-bullet tests for the private knowledge-base index."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path("docs/operator/knowledge_base")


class PrivateKnowledgeBaseIndexTests(unittest.TestCase):
    def test_knowledge_base_readme_exists(self):
        self.assertTrue((ROOT / "README.md").is_file())

    def test_all_indexes_exist(self):
        for name in (
            "system_status_index.md",
            "code_audit_index.md",
            "creative_factory_index.md",
            "macro_research_index.md",
            "blocked_capabilities_index.md",
            "ai_worker_rules_index.md",
        ):
            with self.subTest(name=name):
                self.assertTrue((ROOT / name).is_file())

    def test_indexes_link_to_relevant_docs(self):
        text = (ROOT / "code_audit_index.md").read_text(encoding="utf-8").lower()
        self.assertIn("code audit daily report workflow", text)
        self.assertIn("code audit examples", text)

    def test_readme_says_navigation_only_not_hidden_source_of_truth(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8").lower()
        self.assertIn("navigation only, not a hidden source of truth", text)

    def test_blocked_capabilities_index_preserves_blocked_language(self):
        text = (ROOT / "blocked_capabilities_index.md").read_text(encoding="utf-8").lower()
        self.assertIn("real provider execution remains blocked", text)
        self.assertIn("production autonomy remains blocked", text)


if __name__ == "__main__":
    unittest.main()
