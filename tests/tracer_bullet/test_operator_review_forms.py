"""Tracer-bullet tests for private operator review forms."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path("docs/operator/forms")


class OperatorReviewFormsTests(unittest.TestCase):
    def test_forms_readme_exists(self):
        self.assertTrue((ROOT / "README.md").is_file())

    def test_every_required_form_exists(self):
        for name in (
            "branch_review_form.md",
            "merge_readiness_form.md",
            "ai_worker_result_review_form.md",
            "post_merge_retrospective_form.md",
            "creative_asset_review_form.md",
            "macro_research_review_form.md",
            "rollback_decision_form.md",
            "human_approval_checklist.md",
        ):
            with self.subTest(name=name):
                self.assertTrue((ROOT / name).is_file())

    def test_human_approval_checklist_preserves_blocked_capabilities(self):
        text = (ROOT / "human_approval_checklist.md").read_text(encoding="utf-8").lower()
        self.assertIn("blocked capabilities remain blocked", text)

    def test_creative_review_form_has_pass_needs_fix_reject(self):
        text = (ROOT / "creative_asset_review_form.md").read_text(encoding="utf-8").lower()
        for term in ("pass", "needs_fix", "reject"):
            self.assertIn(term, text)

    def test_macro_review_form_says_final_decisions_remain_manual(self):
        text = (ROOT / "macro_research_review_form.md").read_text(encoding="utf-8").lower()
        self.assertIn("final decisions remain manual", text)

    def test_rollback_form_says_rollback_must_not_enable_blocked_capabilities(self):
        text = (ROOT / "rollback_decision_form.md").read_text(encoding="utf-8").lower()
        self.assertIn("rollback must not enable blocked capabilities", text)


if __name__ == "__main__":
    unittest.main()
