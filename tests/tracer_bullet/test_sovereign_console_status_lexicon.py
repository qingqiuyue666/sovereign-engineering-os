"""Status lexicon and fake-finality guard tests."""

from __future__ import annotations

import unittest
from pathlib import Path

from apps.ui.status_chip_delegate import ALLOWED_STATUS_LABELS, normalize_status_label, status_chip_colors

FORBIDDEN_LABELS = (
    "100% Complete",
    "Final Complete",
    "Production Complete",
    "Hollywood Grade",
    "Film Grade Complete",
    "Final HFX Complete",
    "Fully Automated",
)


class SovereignConsoleStatusLexiconTests(unittest.TestCase):
    def test_allowed_status_lexicon_is_complete(self) -> None:
        required = (
            "Not Started",
            "Pending",
            "Running",
            "Succeeded",
            "Failed",
            "Quarantined",
            "Requires Human Review",
            "Blocked: Missing Resource",
            "Blocked: Missing Visual Proof",
            "Blocked: Human Review Required",
            "Blocked: Placeholder Guide",
            "Dry Run Complete",
            "Materialization Required",
            "Materialized Valid",
            "Materialized Stale",
            "Ready for Real Run",
            "Ready for Review",
        )
        self.assertEqual(set(required), set(ALLOWED_STATUS_LABELS))

    def test_normalizer_maps_raw_projection_states_to_strict_labels(self) -> None:
        self.assertEqual(normalize_status_label("created"), "Not Started")
        self.assertEqual(normalize_status_label("pending"), "Pending")
        self.assertEqual(normalize_status_label("requires_human_review"), "Requires Human Review")
        self.assertEqual(normalize_status_label("unknown future state"), "Blocked: Placeholder Guide")
        self.assertEqual(status_chip_colors("Running")[0], "#0066CC")

    def test_forbidden_fake_completion_labels_are_absent_from_ui_source_spec_and_defaults(self) -> None:
        scanned_paths = (
            Path("apps/sovereign_desktop.py"),
            *tuple(sorted(Path("apps/ui").glob("*.py"))),
            Path("docs/ui/sovereign_console_ui_engineering_spec_v1.md"),
        )
        text = "\n".join(path.read_text(encoding="utf-8") for path in scanned_paths)
        for label in FORBIDDEN_LABELS:
            with self.subTest(label=label):
                self.assertNotIn(label, text)


if __name__ == "__main__":
    unittest.main()
