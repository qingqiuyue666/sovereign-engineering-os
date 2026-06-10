"""Anime micro-FX foundation contract tests."""

from __future__ import annotations

import os
import unittest

from apps.ui import QApplication, PYSIDE6_AVAILABLE
from apps.ui.anime_micro_fx import (
    ANIME_FX_INTENSITY_OPTIONS,
    ANIME_MICRO_FX_CONTRACT,
    AnimeFxIntensity,
    AnimeStatusDot,
    CommandAura,
    SpeedLineHint,
    SweatDropMarker,
    TestGateStamp,
    TestGateStatus,
    TinySparkle,
    GateVisualState,
    effective_anime_fx_intensity,
)
from apps.ui.motion import SyncState


class SovereignConsoleAnimeMicroFxContractTests(unittest.TestCase):
    def setUp(self) -> None:
        if PYSIDE6_AVAILABLE:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            self._app = QApplication.instance() or QApplication([])

    def test_anime_fx_intensity_options_and_default_fallbacks(self) -> None:
        self.assertEqual(ANIME_FX_INTENSITY_OPTIONS, ("Off", "Minimal", "Standard", "Playful"))
        self.assertEqual(effective_anime_fx_intensity(None), AnimeFxIntensity.STANDARD)
        self.assertEqual(
            effective_anime_fx_intensity(AnimeFxIntensity.PLAYFUL, memory_pressure="High (2048 MB)"),
            AnimeFxIntensity.MINIMAL,
        )
        self.assertEqual(
            effective_anime_fx_intensity(AnimeFxIntensity.STANDARD, sync_state=SyncState.LOST),
            AnimeFxIntensity.MINIMAL,
        )
        self.assertEqual(
            effective_anime_fx_intensity(AnimeFxIntensity.OFF, sync_state=SyncState.LOST),
            AnimeFxIntensity.OFF,
        )

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_settings_surface_exposes_anime_fx_intensity(self) -> None:
        from apps.ui.settings_page import SettingsPage

        page = SettingsPage(language="en")
        self.assertEqual(page.anime_fx_options(), ("Off", "Minimal", "Standard", "Playful"))
        self.assertIn("Anime FX Intensity: Off / Minimal / Standard / Playful", page.required_fields())

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_required_micro_fx_widgets_exist(self) -> None:
        status_dot = AnimeStatusDot(state="Thinking")
        self.assertIn("Thinking", status_dot.supported_states())
        self.assertTrue(SpeedLineHint().is_local_only())
        self.assertLessEqual(TinySparkle().max_marks(), 3)
        sweat = SweatDropMarker(failed=True)
        self.assertTrue(sweat.is_failed())
        stamp = TestGateStamp(GateVisualState("Unit Tests", TestGateStatus.OK))
        self.assertTrue(stamp.is_ok_stamped())
        aura = CommandAura()
        aura.set_aura(True)
        self.assertTrue(aura.aura_active())

    def test_micro_fx_contract_rejects_heavy_or_character_driven_style(self) -> None:
        text = "\n".join(ANIME_MICRO_FX_CONTRACT)
        for phrase in (
            "no copyrighted anime character references",
            "no anime girl character art",
            "no full-screen speed lines",
            "no heavy particles",
            "no screen shake",
            "no cyberpunk drift",
            "no game HUD drift",
        ):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
