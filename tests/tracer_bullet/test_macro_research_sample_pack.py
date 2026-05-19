"""Tracer-bullet tests for the macro research sample pack."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path("docs/operator/examples/macro_signal_research")


class MacroResearchSamplePackTests(unittest.TestCase):
    def test_macro_template_docs_exist(self):
        for name in (
            "README.md",
            "research_note_template.md",
            "evidence_pack_template.md",
            "contradiction_pack_template.md",
            "signal_strength_summary_template.md",
            "no_trade_reason_template.md",
            "scenario_map_template.md",
            "after_action_review_template.md",
            "manual_checklist_template.md",
            "blocked_execution_rules.md",
        ):
            with self.subTest(name=name):
                self.assertTrue((ROOT / name).is_file())

    def test_readme_says_not_a_trading_system(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8").lower()
        self.assertIn("this is not a trading system", text)

    def test_blocked_rules_forbid_auto_order_and_broker_api_execution(self):
        text = (ROOT / "blocked_execution_rules.md").read_text(encoding="utf-8").lower()
        self.assertIn("auto order execution is forbidden", text)
        self.assertIn("broker/api execution is forbidden", text)

    def test_manual_checklist_says_final_decisions_remain_manual(self):
        text = (ROOT / "manual_checklist_template.md").read_text(encoding="utf-8").lower()
        self.assertIn("final decisions remain manual", text)

    def test_no_trade_template_and_contradiction_pack_exist(self):
        self.assertTrue((ROOT / "no_trade_reason_template.md").is_file())
        self.assertTrue((ROOT / "contradiction_pack_template.md").is_file())


if __name__ == "__main__":
    unittest.main()
