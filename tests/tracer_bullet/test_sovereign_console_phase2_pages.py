"""Unified workspace page import and shell wiring tests."""

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
    "apps.ui.mission_widgets",
    "apps.ui.workspace_page",
    "apps.ui.runs_page",
    "apps.ui.artifacts_page",
    "apps.ui.reviews_page",
    "apps.ui.settings_page",
    "apps.ui.artifact_store_page",
    "apps.ui.hfx_factory_page",
    "apps.ui.hfx_landing_chain_page",
    "apps.ui.human_review_page",
    "apps.ui.failure_quarantine_page",
    "apps.ui.context_packs_page",
    "apps.ui.system_health_page",
)

EXPECTED_PAGE_IDS = {
    "workspace",
    "runs",
    "artifacts",
    "reviews",
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
        self.assertEqual(set(window._page_indexes), EXPECTED_PAGE_IDS)
        self.assertEqual(window.workspace.currentIndex(), window._page_indexes["workspace"])
        window.close()

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_language_switch_updates_visible_navigation_labels(self) -> None:
        from apps.ui.main_window import SovereignConsoleMainWindow

        window = SovereignConsoleMainWindow(language="en")
        self.assertEqual(window.navigation.visible_labels(), ("Workspace", "Runs", "Artifacts", "Reviews", "Settings"))
        window.set_language("zh")
        self.assertEqual(window.navigation.visible_labels(), ("工作台", "运行", "产物", "审查", "设置"))
        window.close()

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_workspace_displays_required_mission_fields(self) -> None:
        from apps.ui.workspace_page import WorkspacePage
        from apps.ui.read_models import fake_phase1_snapshot

        page = WorkspacePage()
        fields = set(page.required_fields())
        for field in (
            "current mission",
            "command area",
            "next required action",
            "HFX_008 compact chain",
            "recent runs",
            "recent artifacts",
            "pending reviews count",
            "quarantined count",
            "context packet quick actions",
        ):
            self.assertIn(field, fields)
        page.render_snapshot(fake_phase1_snapshot())
        self.assertEqual(page.rendered_mission()["mission_id"], "HFX_008")
        self.assertEqual(page.rendered_mission()["mission_name"], "HFX_008 Energy Shockwave")


if __name__ == "__main__":
    unittest.main()
