"""Product IA source guards for the unified console."""

from __future__ import annotations

import unittest
from pathlib import Path

FORBIDDEN_LABELS = (
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


class SovereignConsoleProductIaNoDirectExecutionTests(unittest.TestCase):
    def test_ui_source_does_not_cross_execution_boundary(self) -> None:
        source = _ui_source()
        lower = source.lower()
        for token in ("shell=True", "subprocess.run", "subprocess.Popen"):
            with self.subTest(token=token):
                self.assertNotIn(token, source)
        for token in ("hython", "houdini", "comfyui", "davinci", "requests.", "httpx.", "urllib.request", "socket."):
            with self.subTest(token=token):
                self.assertNotIn(token, lower)
        for token in (
            ".create_job(",
            ".admit_job(",
            ".enqueue_job(",
            ".start_job(",
            ".succeed_job(",
            ".fail_job(",
            ".quarantine_job(",
            ".cancel_job(",
            ".record_artifact(",
            "INSERT INTO jobs",
            "UPDATE jobs",
            "DELETE FROM jobs",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_forbidden_completion_claims_are_absent_from_ui_and_spec(self) -> None:
        text = _ui_source() + "\n" + Path("docs/ui/sovereign_console_ui_engineering_spec_v1.md").read_text(encoding="utf-8")
        for label in FORBIDDEN_LABELS:
            with self.subTest(label=label):
                self.assertNotIn(label, text)

    def test_table_contract_remains_model_based(self) -> None:
        source = _ui_source()
        self.assertIn("QTableView", source)
        self.assertIn("QAbstractTableModel", source)
        self.assertNotIn("QTableWidget", source)


def _ui_source() -> str:
    paths = (Path("apps/sovereign_desktop.py"), *tuple(sorted(Path("apps/ui").glob("*.py"))))
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)


if __name__ == "__main__":
    unittest.main()
