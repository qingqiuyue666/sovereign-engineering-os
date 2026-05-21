"""Negative style guards for AI coding workspace anime micro-FX."""

from __future__ import annotations

import unittest
from pathlib import Path

from apps.ui.anime_micro_fx import ANIME_MICRO_FX_CONTRACT


CONTRACT_DOCS = (
    Path("docs/ui/sovereign_console_ui_design_system_contract_v1.md"),
    Path("docs/ui/sovereign_console_ui_engineering_spec_v1.md"),
    Path("docs/ui/sovereign_console_ui_skill_v1.md"),
    Path("docs/ui/sovereign_console_visual_reference_negative_examples_v1.md"),
)


class SovereignConsoleAnimeFxNegativeStyleGuardTests(unittest.TestCase):
    def test_docs_preserve_professional_ai_coding_workspace_direction(self) -> None:
        text = _contract_text()
        for phrase in (
            "Claude / GPT / Codex style AI coding workspace",
            "mission thread",
            "Coding Activity Panel",
            "Test Gate Panel",
            "compact event Black Box",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_anime_fx_contract_rejects_style_drift(self) -> None:
        contract_text = "\n".join(ANIME_MICRO_FX_CONTRACT)
        docs_text = _contract_text()
        for phrase in (
            "no copyrighted anime character references",
            "no anime girl character art",
            "no mascot takeover",
            "no full-screen speed lines",
            "no heavy particles",
            "no screen shake",
            "no cyberpunk drift",
            "no game HUD drift",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, contract_text)
        for phrase in (
            "no full-screen effects",
            "no Japanese text gimmicks",
            "no cheap anime skin",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, docs_text)

    def test_no_web_shell_or_heavy_frontend_framework_is_introduced(self) -> None:
        source = _app_source()
        for token in ("QWebEngineView", "Tauri", "Electron", "React", "Vue"):
            with self.subTest(token=token):
                self.assertNotIn(token, source)


def _contract_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in CONTRACT_DOCS)


def _app_source() -> str:
    paths = (Path("apps/sovereign_desktop.py"), *tuple(sorted(Path("apps/ui").glob("*.py"))))
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)


if __name__ == "__main__":
    unittest.main()
