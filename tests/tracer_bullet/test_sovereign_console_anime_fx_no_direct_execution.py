"""Execution-surface guards for the AI coding workspace UI."""

from __future__ import annotations

import unittest
from pathlib import Path


class SovereignConsoleAnimeFxNoDirectExecutionTests(unittest.TestCase):
    def test_gui_source_has_no_direct_process_or_shell_execution(self) -> None:
        source = _ui_source()
        for token in ("subprocess.run", "subprocess.Popen", "shell=True"):
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_gui_source_does_not_launch_external_dcc_or_network_clients(self) -> None:
        source = _ui_source().lower()
        for token in ("hython", "houdini", "comfyui", "davinci", "requests.", "httpx.", "urllib.request", "socket."):
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_gui_source_does_not_mutate_job_queue_or_artifact_store(self) -> None:
        source = _ui_source()
        for token in (
            ".create_job(",
            ".admit_job(",
            ".enqueue_job(",
            ".start_job(",
            ".succeed_job(",
            ".fail_job(",
            ".quarantine_job(",
            ".record_artifact(",
            "INSERT INTO jobs",
            "UPDATE jobs",
            "DELETE FROM jobs",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, source)


def _ui_source() -> str:
    paths = (Path("apps/sovereign_desktop.py"), *tuple(sorted(Path("apps/ui").glob("*.py"))))
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)


if __name__ == "__main__":
    unittest.main()
