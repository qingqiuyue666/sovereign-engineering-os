"""Product IA tests for the unified Sovereign Console workspace."""

from __future__ import annotations

import os
import unittest

from apps.ui import QApplication, PYSIDE6_AVAILABLE


class SovereignConsoleWorkspaceIaTests(unittest.TestCase):
    def setUp(self) -> None:
        if PYSIDE6_AVAILABLE:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            self._app = QApplication.instance() or QApplication([])

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_shell_uses_five_primary_workspace_domains(self) -> None:
        from apps.ui.main_window import SovereignConsoleMainWindow

        window = SovereignConsoleMainWindow(language="en")
        self.assertEqual(tuple(window._page_indexes), ("workspace", "runs", "artifacts", "reviews", "settings"))
        self.assertEqual(window.navigation.visible_labels(), ("Workspace", "Runs", "Artifacts", "Reviews", "Settings"))
        self.assertEqual(window.workspace.currentIndex(), window._page_indexes["workspace"])
        window.close()

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_absorbed_domains_are_not_first_level_pages(self) -> None:
        from apps.ui.main_window import SovereignConsoleMainWindow

        window = SovereignConsoleMainWindow(language="en")
        removed = {
            "Dashboard",
            "System Health",
            "Job Queue",
            "HFX Factory",
            "HFX_008 Landing Chain",
            "Context Packs",
            "Human Review",
            "Failure Quarantine",
            "Artifact Store",
            "Asset Library",
            "Settings / Boundaries",
        }
        self.assertFalse(removed.intersection(window.navigation.visible_labels()))
        self.assertFalse(
            {
                "dashboard",
                "system_health",
                "job_queue",
                "hfx_factory",
                "hfx_landing_chain",
                "context_packs",
                "human_review",
                "failure_quarantine",
                "artifact_store",
                "asset_library",
            }.intersection(window._page_indexes)
        )
        window.close()

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_system_pulse_and_inspector_are_product_surfaces(self) -> None:
        from apps.ui.main_window import SovereignConsoleMainWindow

        window = SovereignConsoleMainWindow(language="en")
        self.assertTrue(window.pulse_bar.is_grouped_chip_surface())
        self.assertEqual(
            window.pulse_bar.chip_names(),
            ("Runtime", "WAL", "Runs", "Workers", "Memory", "Warnings", "Sync", "Next Action"),
        )
        self.assertEqual(
            window.inspector.empty_state_text(),
            "Select a run, artifact, review, or mission stage to inspect.",
        )
        window.close()


if __name__ == "__main__":
    unittest.main()
