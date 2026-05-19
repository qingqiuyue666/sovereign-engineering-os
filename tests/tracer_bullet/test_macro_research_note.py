"""Tracer-bullet tests for macro research notes."""

from __future__ import annotations

from pathlib import Path
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.macro_research_note import (
    MacroResearchNote,
    build_macro_research_note,
    render_macro_research_note_markdown,
)


def valid_material() -> dict[str, object]:
    return {
        "note_id": "macro-note-test",
        "research_domain": "macro regime research",
        "thesis": "research-only thesis",
        "evidence_items": ["evidence item"],
        "contradiction_items": ["contradiction item"],
        "uncertainty_level": "high",
        "allowed_outputs": ["research note", "no-trade reason"],
        "forbidden_outputs": [
            "auto order execution",
            "broker/API execution",
            "leverage",
            "full-position instruction",
            "autonomous trading",
        ],
        "no_trade_reasons": ["uncertainty remains high"],
        "manual_decision_boundary": "final decision remains manual",
        "blocked_capabilities": ["broker/API execution blocked", "order execution blocked"],
        "policy_version": "macro-research-note-v1",
        "code_version": "0.1.0",
    }


class MacroResearchNoteTests(unittest.TestCase):
    def test_valid_note_builds_deterministic_object(self):
        note = build_macro_research_note(valid_material())

        self.assertIsInstance(note, MacroResearchNote)
        self.assertEqual(note.content_hash, digest_payload(note.deterministic_material()))

    def test_content_hash_excludes_observed_at(self):
        self.assertEqual(
            build_macro_research_note(valid_material(), observed_at="one").content_hash,
            build_macro_research_note(valid_material(), observed_at="two").content_hash,
        )

    def test_markdown_deterministic(self):
        note = build_macro_research_note(valid_material())

        self.assertEqual(render_macro_research_note_markdown(note), render_macro_research_note_markdown(note))

    def test_missing_contradiction_items_fails_closed(self):
        material = valid_material()
        del material["contradiction_items"]

        with self.assertRaises(ValueError):
            build_macro_research_note(material)

    def test_missing_no_trade_reasons_fails_closed(self):
        material = valid_material()
        del material["no_trade_reasons"]

        with self.assertRaises(ValueError):
            build_macro_research_note(material)

    def test_runtime_source_safety_passes(self):
        source = Path("kernel/runtime/macro_research_note.py").read_text(encoding="utf-8")
        for marker in ("subprocess", "socket", "requests", "httpx", "sqlite3", "os.environ", "os.getenv", "load_dotenv"):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
