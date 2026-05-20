"""HFX_008 landing chain UI tests."""

from __future__ import annotations

import os
import unittest

from apps.ui import QApplication, PYSIDE6_AVAILABLE
from apps.ui.hfx_landing_chain_page import HFX_008_CHAIN_STAGES, HfxLandingChainPage
from apps.ui.read_models import fake_phase1_snapshot


class SovereignConsoleHfxLandingChainUiTests(unittest.TestCase):
    def setUp(self) -> None:
        if PYSIDE6_AVAILABLE:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            self._app = QApplication.instance() or QApplication([])

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_chain_displays_all_required_stages(self) -> None:
        page = HfxLandingChainPage()
        self.assertEqual(page.stage_names(), HFX_008_CHAIN_STAGES)
        self.assertEqual(
            page.stage_names(),
            (
                "Topology Audit",
                "Proof Artifact",
                "Artifact Validation",
                "Human Review",
                "Materialization Summary",
                "Final Claim Gate",
            ),
        )

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_chain_does_not_show_fake_final_claim(self) -> None:
        page = HfxLandingChainPage()
        page.render_snapshot(fake_phase1_snapshot())
        joined = "\n".join(page.stage_statuses().values())
        self.assertNotIn("Final Complete", joined)
        self.assertNotIn("Production Complete", joined)

    @unittest.skipUnless(PYSIDE6_AVAILABLE, "PySide6 not installed")
    def test_connector_state_is_status_driven_without_timing(self) -> None:
        page = HfxLandingChainPage()
        page.render_stage_statuses(
            {
                "Topology Audit": "Running",
                "Proof Artifact": "Pending",
                "Artifact Validation": "Pending",
                "Human Review": "Pending",
                "Materialization Summary": "Pending",
                "Final Claim Gate": "Blocked: Human Review Required",
            }
        )
        self.assertEqual(page.connector_states()[0], "running")


if __name__ == "__main__":
    unittest.main()
