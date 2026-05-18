"""Tracer-bullet tests for macro signal research boundaries."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.macro_signal_research_boundary import (
    MacroSignalResearchBoundary,
    build_macro_signal_research_boundary,
    render_macro_signal_research_boundary_markdown,
)


def valid_material() -> dict[str, object]:
    return {
        "boundary_id": "macro-signal-research-boundary-v1",
        "research_domain": "macro and XAUUSD signal research for manual review",
        "allowed_outputs": [
            "research notes",
            "evidence packs",
            "contradiction packs",
            "signal strength summaries",
            "no-trade reasons",
            "scenario maps",
            "after-action review templates",
            "manual checklist",
        ],
        "forbidden_outputs": [
            "auto order execution",
            "broker/API execution",
            "full-position instructions",
            "leverage instructions",
            "autonomous trading",
            "guaranteed certainty claims",
            "execution bypass",
            "secret/env/API credential handling",
        ],
        "evidence_requirements": [
            "caller-provided evidence summaries only",
            "contradiction checks required",
        ],
        "manual_decision_boundary": "final decisions remain manual",
        "no_trade_conditions": [
            "missing evidence",
            "conflicting evidence",
        ],
        "blocked_execution": [
            "no automatic financial execution",
            "no trading automation",
        ],
        "risk_controls": [
            "include no-trade reasons",
            "avoid certainty claims",
        ],
        "policy_version": "macro-signal-research-boundary-v1",
        "code_version": "0.1.0",
    }


class MacroSignalResearchBoundaryTests(unittest.TestCase):
    def test_valid_boundary_builds_deterministic_object(self):
        boundary = build_macro_signal_research_boundary(
            valid_material(),
            observed_at="2026-05-19T00:00:00+08:00",
        )

        self.assertIsInstance(boundary, MacroSignalResearchBoundary)
        self.assertTrue(boundary.content_hash.startswith("sha256:"))
        self.assertEqual(boundary.content_hash, digest_payload(boundary.deterministic_material()))

    def test_markdown_rendering_deterministic(self):
        material = valid_material()

        first = render_macro_signal_research_boundary_markdown(
            build_macro_signal_research_boundary(material, observed_at="2026-05-19T00:00:00+08:00")
        )
        second = render_macro_signal_research_boundary_markdown(
            build_macro_signal_research_boundary(material, observed_at="2026-05-19T00:00:00+08:00")
        )

        self.assertEqual(first, second)

    def test_content_hash_excludes_observed_at(self):
        material = valid_material()

        first = build_macro_signal_research_boundary(material, observed_at="2026-05-19T00:00:00+08:00")
        second = build_macro_signal_research_boundary(material, observed_at="2027-05-19T00:00:00+08:00")

        self.assertNotEqual(first.observed_at, second.observed_at)
        self.assertEqual(first.content_hash, second.content_hash)

    def test_missing_boundary_id_fails_closed(self):
        material = valid_material()
        del material["boundary_id"]

        with self.assertRaises(ValueError):
            build_macro_signal_research_boundary(material)

    def test_missing_forbidden_outputs_fails_closed(self):
        material = valid_material()
        del material["forbidden_outputs"]

        with self.assertRaises(ValueError):
            build_macro_signal_research_boundary(material)

    def test_missing_manual_decision_boundary_fails_closed(self):
        material = valid_material()
        del material["manual_decision_boundary"]

        with self.assertRaises(ValueError):
            build_macro_signal_research_boundary(material)

    def test_forbidden_raw_and_sensitive_fields_fail_closed(self):
        for field_name in (
            "raw_prompt",
            "raw_response",
            "raw_exception",
            "raw_traceback",
            "env",
            "secret",
            "token",
            "api_key",
            "password",
            "private_key",
            "authorization",
        ):
            with self.subTest(field_name=field_name):
                material = valid_material()
                material[field_name] = "blocked"

                with self.assertRaises(ValueError):
                    build_macro_signal_research_boundary(material)

    def test_generated_macro_boundary_doc_exists(self):
        self.assertTrue(Path("docs/operator/macro_signal_research_boundary.md").is_file())

    def test_doc_says_this_is_not_a_trading_system(self):
        text = Path("docs/operator/macro_signal_research_boundary.md").read_text(encoding="utf-8").lower()

        self.assertIn("this is not a trading system", text)

    def test_doc_says_auto_order_execution_is_forbidden(self):
        text = Path("docs/operator/macro_signal_research_boundary.md").read_text(encoding="utf-8").lower()

        self.assertIn("auto order execution is forbidden", text)

    def test_doc_says_final_decisions_remain_manual(self):
        text = Path("docs/operator/macro_signal_research_boundary.md").read_text(encoding="utf-8").lower()

        self.assertIn("final decisions remain manual", text)

    def test_source_safety_checks_pass(self):
        source = Path("kernel/runtime/macro_signal_research_boundary.py").read_text(encoding="utf-8")

        for marker in (
            "subprocess",
            "socket",
            "requests",
            "httpx",
            "sqlite3",
            "os.environ",
            "os.getenv",
            "load_dotenv",
        ):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
