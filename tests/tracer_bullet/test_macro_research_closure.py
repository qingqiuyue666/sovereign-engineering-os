"""Tracer-bullet tests for macro research closure."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.macro_research_closure import (
    MacroResearchClosure,
    build_macro_research_closure,
    render_macro_research_closure_markdown,
)


MACRO_DOCS = (
    "docs/operator/macro_research/README.md",
    "docs/operator/macro_research/research_note_001_template.md",
    "docs/operator/macro_research/evidence_pack_001_template.md",
    "docs/operator/macro_research/contradiction_pack_001_template.md",
    "docs/operator/macro_research/no_trade_reason_001_template.md",
    "docs/operator/macro_research/manual_decision_checklist_001.md",
)


def valid_material() -> dict[str, object]:
    gates = {
        "research_note_contract_exists": True,
        "readme_exists": True,
        "evidence_pack_template_exists": True,
        "contradiction_pack_template_exists": True,
        "no_trade_reason_template_exists": True,
        "manual_decision_checklist_exists": True,
        "forbidden_outputs_include_required_boundaries": True,
        "final_decision_remains_manual": True,
    }
    return {
        "closure_id": "macro-research-closure-test",
        "repository_url": "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os",
        "main_commit": "d98f29ebf25cae196098121ce1632de727393a2d",
        "closure_gates": gates,
        "workflow_docs": ["not a trading system", "final decision remains manual"],
        "forbidden_outputs": [
            "auto order execution",
            "broker/API execution",
            "leverage",
            "full-position instruction",
            "autonomous trading",
        ],
        "blocked_capabilities": ["broker/API execution blocked", "order execution blocked"],
        "completion_decision": "complete",
        "remaining_gaps": [],
        "rollback_notes": ["revert macro docs"],
        "policy_version": "macro-research-closure-v1",
        "code_version": "0.1.0",
    }


class MacroResearchClosureTests(unittest.TestCase):
    def test_valid_closure_builds_deterministic_object(self):
        closure = build_macro_research_closure(valid_material())

        self.assertIsInstance(closure, MacroResearchClosure)
        self.assertEqual(closure.content_hash, digest_payload(closure.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        self.assertEqual(
            build_macro_research_closure(valid_material(), observed_at="one").content_hash,
            build_macro_research_closure(valid_material(), observed_at="two").content_hash,
        )

    def test_markdown_deterministic(self):
        closure = build_macro_research_closure(valid_material())

        self.assertEqual(render_macro_research_closure_markdown(closure), render_macro_research_closure_markdown(closure))

    def test_closure_complete_blocked_if_manual_checklist_missing(self):
        material = valid_material()
        material["closure_gates"]["manual_decision_checklist_exists"] = False

        with self.assertRaises(ValueError):
            build_macro_research_closure(material)

    def test_readme_says_not_a_trading_system(self):
        text = Path("docs/operator/macro_research/README.md").read_text(encoding="utf-8").lower()

        self.assertIn("not a trading system", text)

    def test_manual_checklist_says_final_decision_remains_manual(self):
        text = Path("docs/operator/macro_research/manual_decision_checklist_001.md").read_text(encoding="utf-8").lower()

        self.assertIn("final decision remains manual", text)

    def test_no_trade_template_exists(self):
        self.assertTrue(Path("docs/operator/macro_research/no_trade_reason_001_template.md").is_file())

    def test_generated_docs_exist(self):
        for path in MACRO_DOCS:
            self.assertTrue(Path(path).is_file(), path)
        self.assertTrue(Path("docs/operator/generated/macro_research_closure.md").is_file())

    def test_runtime_source_safety_passes(self):
        source = Path("kernel/runtime/macro_research_closure.py").read_text(encoding="utf-8")
        for marker in ("subprocess", "socket", "requests", "httpx", "sqlite3", "os.environ", "os.getenv", "load_dotenv"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
