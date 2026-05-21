"""Negative style guards for Sovereign Console UI contract drift."""

from __future__ import annotations

import unittest
from pathlib import Path

CONTRACT = Path("docs/ui/sovereign_console_ui_design_system_contract_v1.md")
SKILL = Path("docs/ui/sovereign_console_ui_skill_v1.md")
NEGATIVE = Path("docs/ui/sovereign_console_visual_reference_negative_examples_v1.md")

SCAN_PATHS = (
    Path("apps/sovereign_desktop.py"),
    *tuple(sorted(Path("apps/ui").glob("*.py"))),
    Path("docs/ui/sovereign_console_ui_engineering_spec_v1.md"),
    CONTRACT,
    SKILL,
    NEGATIVE,
)

FORBIDDEN_PRODUCT_FRAMES = (
    "mobile app",
    "web app",
    "SaaS dashboard",
    "chatbot clone",
    "plugin marketplace",
    "raw Qt form",
    "database admin panel",
    "black sci-fi concept screen",
    "cyberpunk console",
    "game HUD",
)

FORBIDDEN_FAKE_LABELS = (
    "100% Complete",
    "Final Complete",
    "Production Complete",
    "Hollywood Grade",
    "Film Grade Complete",
    "Final HFX Complete",
    "Fully Automated",
    "Bypass",
    "Force Complete",
)

FORBIDDEN_FIRST_LEVEL = (
    "Dashboard",
    "Job Queue",
    "HFX Factory",
    "HFX_008 Landing Chain",
    "Context Packs",
    "Human Review",
    "Failure Quarantine",
    "Artifact Store",
    "Asset Library",
    "System Health",
    "Boundaries",
)


class SovereignConsoleUiNegativeStyleGuardTests(unittest.TestCase):
    def test_negative_visual_reference_exists(self) -> None:
        self.assertTrue(NEGATIVE.exists())

    def test_wrong_product_frames_are_explicitly_rejected(self) -> None:
        text = _combined_contract_text()
        for frame in FORBIDDEN_PRODUCT_FRAMES:
            with self.subTest(frame=frame):
                self.assertIn(frame, text)

    def test_old_first_level_labels_are_only_documented_as_forbidden_or_absorbed(self) -> None:
        contract_text = CONTRACT.read_text(encoding="utf-8")
        negative_text = NEGATIVE.read_text(encoding="utf-8")
        self.assertIn("Forbidden first-level nav entries:", contract_text)
        self.assertIn("Forbidden First-Level Page Sprawl", negative_text)
        for label in FORBIDDEN_FIRST_LEVEL:
            with self.subTest(label=label):
                self.assertIn(f"- {label}", contract_text)
                self.assertIn(f"- {label}", negative_text)

    def test_forbidden_fake_completion_labels_remain_absent_from_ui_sources_and_docs(self) -> None:
        text = "\n".join(path.read_text(encoding="utf-8") for path in SCAN_PATHS)
        for label in FORBIDDEN_FAKE_LABELS:
            with self.subTest(label=label):
                self.assertNotIn(label, text)

    def test_negative_reference_replaces_forbidden_patterns_with_canonical_direction(self) -> None:
        text = NEGATIVE.read_text(encoding="utf-8")
        required = (
            "Apple Mission Control Workspace",
            "Finder/Xcode-style sidebar with five entries",
            "Raycast/Codex-style Command Bar",
            "Current Mission Card as the hero object",
            "compact HFX_008 Energy Chain",
            "steady Inspector",
            "collapsed structured Black Box",
            "light-gray Apple base and white mission cards",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


def _combined_contract_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in (CONTRACT, SKILL, NEGATIVE))


if __name__ == "__main__":
    unittest.main()
