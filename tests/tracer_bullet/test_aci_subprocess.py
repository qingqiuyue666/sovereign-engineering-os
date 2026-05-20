"""Tracer-bullet tests for the desktop ACI subprocess proxy."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
import unittest

from kernel.ipc.aci_subprocess import (
    ALLOWED_COMMANDS,
    CommandRejected,
    run_whitelisted_command,
)


class _FakeProcess:
    returncode = 0

    def communicate(self, timeout: float | int | None = None) -> tuple[str, str]:
        return "ok\n", ""

    def kill(self) -> None:
        return None


class AciSubprocessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[2]

    def test_exact_validation_commands_are_allowlisted(self) -> None:
        with patch("kernel.ipc.aci_subprocess.subprocess.Popen", return_value=_FakeProcess()) as popen:
            for command in sorted(ALLOWED_COMMANDS):
                with self.subTest(command=command):
                    result = run_whitelisted_command(command, cwd=self.repo_root, timeout_seconds=1)

                    self.assertTrue(result.ok)
                    self.assertEqual(result.stdout, "ok\n")

        self.assertEqual(popen.call_count, len(ALLOWED_COMMANDS))
        for call in popen.call_args_list:
            self.assertFalse(call.kwargs["shell"])

    def test_shell_injection_tokens_are_rejected_before_spawn(self) -> None:
        malicious_commands = (
            "make ci && rm -rf /",
            "make ci | cat",
            "make ci > /tmp/out",
            "python3 -m unittest discover -s tests/tracer_bullet -v; rm -rf .",
            "python3 -m unittest discover -s tests/tracer_bullet -v `whoami`",
            "python3 -m unittest discover -s tests/tracer_bullet -v $(whoami)",
        )
        with patch("kernel.ipc.aci_subprocess.subprocess.Popen") as popen:
            for command in malicious_commands:
                with self.subTest(command=command):
                    with self.assertRaises(CommandRejected):
                        run_whitelisted_command(command, cwd=self.repo_root, timeout_seconds=1)

        popen.assert_not_called()

    def test_near_miss_commands_are_rejected_before_spawn(self) -> None:
        rejected_commands = (
            "python3 -m pytest -q",
            "python3 -m unittest discover -s tests/tracer_bullet",
            "python -m unittest discover -s tests/tracer_bullet -v",
            "make test",
            "git status --short",
        )
        with patch("kernel.ipc.aci_subprocess.subprocess.Popen") as popen:
            for command in rejected_commands:
                with self.subTest(command=command):
                    with self.assertRaises(CommandRejected):
                        run_whitelisted_command(command, cwd=self.repo_root, timeout_seconds=1)

        popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
