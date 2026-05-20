"""Motion and procedural-energy safety tests."""

from __future__ import annotations

from pathlib import Path
import unittest

from apps.ui.energy_widgets import ENERGY_STATE_COLORS, EnergyState, normalize_energy_state
from apps.ui.motion import MotionIntensity, SyncState, effective_motion_intensity, normalize_motion_intensity


class SovereignConsoleMotionSafetyTests(unittest.TestCase):
    def test_motion_intensity_enum_and_defaults(self) -> None:
        self.assertEqual(normalize_motion_intensity(None), MotionIntensity.STANDARD)
        self.assertEqual(normalize_motion_intensity("Minimal"), MotionIntensity.MINIMAL)
        self.assertEqual(normalize_motion_intensity("High Energy"), MotionIntensity.HIGH_ENERGY)

    def test_motion_degrades_safely_under_pressure_or_sync_loss(self) -> None:
        self.assertEqual(
            effective_motion_intensity(MotionIntensity.HIGH_ENERGY, memory_pressure="High (2048 MB)"),
            MotionIntensity.MINIMAL,
        )
        self.assertEqual(
            effective_motion_intensity(MotionIntensity.HIGH_ENERGY, sync_state=SyncState.LOST),
            MotionIntensity.MINIMAL,
        )

    def test_energy_state_mapping_is_status_driven(self) -> None:
        self.assertEqual(normalize_energy_state("Running"), EnergyState.RUNNING)
        self.assertEqual(normalize_energy_state("Dry Run Complete"), EnergyState.SUCCEEDED)
        self.assertEqual(normalize_energy_state("Blocked: Missing Visual Proof"), EnergyState.BLOCKED)
        self.assertIn(EnergyState.RUNNING, ENERGY_STATE_COLORS)

    def test_motion_components_are_not_timing_dependent(self) -> None:
        source = Path("apps/ui/energy_widgets.py").read_text(encoding="utf-8")
        self.assertNotIn("QTimer", source)
        self.assertNotIn("sleep(", source)


if __name__ == "__main__":
    unittest.main()
