"""Tracer bullet tests for the desktop GUI/execution boundary."""

from __future__ import annotations

import importlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

APP_SOURCE = Path(__file__).resolve().parents[2] / "apps" / "sovereign_desktop.py"


class OSEngineGuiExecutionSplitTests(unittest.TestCase):
    def test_import_does_not_start_gui_execution_subprocess_or_network(self) -> None:
        sys.modules.pop("apps.sovereign_desktop", None)
        with (
            patch("subprocess.run") as subprocess_run,
            patch("subprocess.Popen") as subprocess_popen,
            patch("socket.create_connection") as socket_connect,
        ):
            module = importlib.import_module("apps.sovereign_desktop")
        self.assertTrue(hasattr(module, "PYSIDE6_AVAILABLE"))
        subprocess_run.assert_not_called()
        subprocess_popen.assert_not_called()
        socket_connect.assert_not_called()

    def test_source_scan_proves_no_shell_true_or_direct_external_tool_calls(self) -> None:
        source = APP_SOURCE.read_text(encoding="utf-8").lower()
        forbidden = (
            "shell=true",
            "subprocess.",
            "hython",
            "houdini",
            "comfyui",
            "davinci",
            "requests.",
            "httpx.",
            "urllib.request",
            "socket.",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_job_submission_path_goes_through_event_sourced_queue_without_auto_execution(self) -> None:
        source = APP_SOURCE.read_text(encoding="utf-8")
        self.assertIn("DesktopOsEngineFacade", source)
        self.assertIn("self.queue.create_job", source)
        self.assertIn("self.queue.enqueue_job", source)
        self.assertNotIn("JobQueueManager", source)
        self.assertNotIn(".start_job(", source)
        self.assertNotIn("run(", source.lower().replace("asyncio.run", ""))

    def test_facade_submission_projects_pending_state_without_starting_worker(self) -> None:
        from apps.sovereign_desktop import DesktopOsEngineFacade

        with tempfile.TemporaryDirectory() as temp_dir_name:
            runtime_root = Path(temp_dir_name)
            facade = DesktopOsEngineFacade(repo_root=Path.cwd(), runtime_root=runtime_root)
            facade.initialize()
            state = facade.submit_job_request(
                job_type="git",
                inputs={"command": ["git", "status", "--short"]},
                max_runtime=30,
                memory_limit=256,
            )
            self.assertEqual(state.current_status, "pending")
            self.assertEqual(state.last_event_type, "JobQueued")
            self.assertEqual(state.event_count, 4)
            self.assertEqual(facade.list_job_states()[0].current_status, "pending")

    def test_no_env_file_read_or_raw_network_default_in_gui_source(self) -> None:
        source = APP_SOURCE.read_text(encoding="utf-8")
        self.assertNotIn('open(".env"', source)
        self.assertNotIn("Path('.env')", source)
        self.assertNotIn("dotenv", source.lower())
        self.assertNotIn("http://", source)
        self.assertNotIn("https://", source)


if __name__ == "__main__":
    unittest.main()
