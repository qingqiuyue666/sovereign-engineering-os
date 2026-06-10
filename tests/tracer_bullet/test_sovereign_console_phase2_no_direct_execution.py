"""Phase 2 source guards for the native console execution boundary."""

from __future__ import annotations

import importlib
from pathlib import Path
import socket
import subprocess
import unittest
from unittest.mock import patch

UI_SOURCE_PATHS = (Path("apps/sovereign_desktop.py"), *tuple(sorted(Path("apps/ui").glob("*.py"))))

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


class SovereignConsolePhase2NoDirectExecutionTests(unittest.TestCase):
    def test_importing_phase2_ui_modules_does_not_execute_process_or_network(self) -> None:
        modules = (
            "apps.ui.workspace_page",
            "apps.ui.runs_page",
            "apps.ui.artifacts_page",
            "apps.ui.reviews_page",
            "apps.ui.artifact_store_page",
            "apps.ui.hfx_factory_page",
            "apps.ui.hfx_landing_chain_page",
            "apps.ui.human_review_page",
            "apps.ui.failure_quarantine_page",
            "apps.ui.context_packs_page",
            "apps.ui.system_health_page",
            "apps.ui.settings_page",
        )
        with (
            patch.object(subprocess, "run") as subprocess_run,
            patch.object(subprocess, "Popen") as subprocess_popen,
            patch.object(socket, "create_connection") as socket_connect,
        ):
            imported = [importlib.import_module(module) for module in modules]
        self.assertTrue(all(imported))
        subprocess_run.assert_not_called()
        subprocess_popen.assert_not_called()
        socket_connect.assert_not_called()

    def test_ui_source_has_no_direct_process_shell_or_tool_calls(self) -> None:
        source = _ui_source()
        for token in ("shell=True", "subprocess.run", "subprocess.Popen"):
            with self.subTest(token=token):
                self.assertNotIn(token, source)
        lower = source.lower()
        for token in ("hython", "houdini", "comfyui", "davinci"):
            with self.subTest(token=token):
                self.assertNotIn(token, lower)

    def test_ui_source_has_no_network_clients_or_queue_mutation(self) -> None:
        source = _ui_source()
        lower = source.lower()
        for token in ("requests.", "httpx.", "urllib.request", "socket."):
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

    def test_forbidden_fake_completion_labels_are_absent_from_ui_and_spec(self) -> None:
        text = _ui_source() + "\n" + Path("docs/ui/sovereign_console_ui_engineering_spec_v1.md").read_text(encoding="utf-8")
        for label in FORBIDDEN_LABELS:
            with self.subTest(label=label):
                self.assertNotIn(label, text)

    def test_job_queue_keeps_table_model_contract(self) -> None:
        source = Path("apps/ui/runs_page.py").read_text(encoding="utf-8")
        models = Path("apps/ui/models.py").read_text(encoding="utf-8")
        self.assertIn("QTableView", source)
        self.assertIn("QAbstractTableModel", models)
        self.assertNotIn("QTableWidget", _ui_source())


def _ui_source() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in UI_SOURCE_PATHS)


if __name__ == "__main__":
    unittest.main()
