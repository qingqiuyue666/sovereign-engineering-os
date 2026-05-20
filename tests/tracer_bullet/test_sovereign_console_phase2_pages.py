"""Phase 2 page import and shell wiring tests."""

from __future__ import annotations

import importlib
import os
import unittest

from apps.ui import QApplication, PYSIDE6_AVAILABLE

PHASE2_MODULES = (
    "apps.ui.i18n",
    "apps.ui.translations",
    "apps.ui.motion",
    "apps.ui.energy_widgets",
    "apps.ui.artifact_store_page",
    "apps.ui.hfx_factory_page",
    "apps.ui.hfx_landing_chain_page",
    "apps.ui.human_review_page",
    "apps.ui.failure_quarantine_page",
    "apps.ui.context_packs_page",
    "apps.ui.system_health_page",
    "apps.ui.settings_page",
)

EXPECTED_PAGE_IDS = {
    "dashboard",
    "job_queue",
    "system_health",
    "hfx_factory",
    "hfx_landing_chain",
    "context_packs",
    "human_review",
    "failure_quarantine",
    "artifact_store",
    "settings",
}


class SovereignConsolePhase2PagesTests(unittest.TestCase):
    def setUp(self) -> None:
        if PYSIDE6_AVAILABLE:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            self._app = QApplication.instance() or QApplication([])

    def test_phase2_modules_import_safely(self) -> None:
        for module_name in PHASE2_MODULES:
            with self.subTest(module=module_name):
                self.assertIsNotNone(importlib.import_module(module_name))

    def test_missing_pyside6_boundary_is_explicit(self) -> None:
        ui = importlib.import_module("apps.ui")
        self.assertIn(ui.PYSIDE6_AVAILABLE, {True, False})
        self.assertTrue(hasattr(ui, "QApplication"))

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_main_window_registers_phase2_pages(self) -> None:
        from apps.ui.main_window import SovereignConsoleMainWindow

        window = SovereignConsoleMainWindow()
        self.assertTrue(EXPECTED_PAGE_IDS.issubset(set(window._page_indexes)))
        self.assertFalse({"asset_library"}.intersection(window._page_indexes))
        window.close()

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_language_switch_updates_visible_navigation_labels(self) -> None:
        from apps.ui.main_window import SovereignConsoleMainWindow

        window = SovereignConsoleMainWindow(language="en")
        self.assertIn("Dashboard", window.navigation.visible_labels())
        window.set_language("zh")
        self.assertIn("仪表盘", window.navigation.visible_labels())
        window.close()

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_hfx_factory_displays_required_fields(self) -> None:
        from apps.ui.hfx_factory_page import HfxFactoryPage
        from apps.ui.read_models import fake_phase1_snapshot

        page = HfxFactoryPage()
        fields = set(page.required_fields())
        for field in (
            "Core12",
            "HFX_008 summary",
            "topology audit status",
            "proof artifact status",
            "validation status",
            "human review status",
            "resource package status",
            "final_claim_allowed",
            "next action",
            "blocked reason",
        ):
            self.assertIn(field, fields)
        page.render_snapshot(fake_phase1_snapshot())
        self.assertEqual(page.rendered_values()["final_claim_allowed"], "False")


if __name__ == "__main__":
    unittest.main()
