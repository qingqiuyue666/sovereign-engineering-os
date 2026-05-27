"""Hardening tests for the out-of-process memory watchdog."""

from __future__ import annotations

import ast
import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path

from kernel.os_engine.memory_watchdog import (
    MAX_MEMORY_LIMIT_MB,
    ProcessLimits,
    ProcessSupervisor,
    ProcessSupervisorError,
    RETRY_POLICY_MAX_ATTEMPTS,
)


class OsEngineMemoryWatchdogTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.crash_dir = Path(tempfile.mkdtemp(prefix="seos-crashes-"))
        self.receipt_dir = Path(tempfile.mkdtemp(prefix="seos-watchdog-receipts-"))
        self.supervisor = ProcessSupervisor(crash_dir=self.crash_dir, poll_interval_seconds=0.05)

    async def test_timeout_budget_is_enforced_and_failure_bundle_is_generated(self) -> None:
        result = await self.supervisor.run(
            [sys.executable, "-c", "import time; time.sleep(5)"],
            limits=ProcessLimits(max_runtime_seconds=0.2, memory_limit_mb=256),
        )
        self.assertTrue(result.timed_out)
        self.assertTrue(result.quarantined)
        self.assertIn("runtime limit exceeded", result.termination_reason)
        self.assertIsNotNone(result.diagnostic_path)
        self.assertTrue(result.diagnostic_path and result.diagnostic_path.exists())

    async def test_stdout_and_stderr_caps_are_enforced(self) -> None:
        stdout_result = await self.supervisor.run(
            [sys.executable, "-c", "print('x' * 2000)"],
            limits=ProcessLimits(max_runtime_seconds=5, memory_limit_mb=256, stdout_limit_bytes=64),
        )
        self.assertTrue(stdout_result.stdout_overflow)
        self.assertTrue(stdout_result.quarantined)

        stderr_result = await self.supervisor.run(
            [sys.executable, "-c", "import sys; sys.stderr.write('e' * 2000)"],
            limits=ProcessLimits(max_runtime_seconds=5, memory_limit_mb=256, stderr_limit_bytes=64),
        )
        self.assertTrue(stderr_result.stderr_overflow)
        self.assertTrue(stderr_result.quarantined)

    async def test_nonzero_worker_failure_generates_bundle_without_crashing_main_process(self) -> None:
        result = await self.supervisor.run(
            [sys.executable, "-c", "import sys; sys.exit(7)"],
            limits=ProcessLimits(max_runtime_seconds=5, memory_limit_mb=256),
        )
        self.assertFalse(result.ok)
        self.assertFalse(result.quarantined)
        self.assertIn("nonzero", result.termination_reason)
        self.assertIsNotNone(result.diagnostic_path)
        self.assertEqual(result.partial_outputs_policy, "preserve_in_crash_bundle_when_available")

    async def test_watchdog_receipt_is_written_without_raw_stream_payloads(self) -> None:
        supervisor = ProcessSupervisor(
            crash_dir=self.crash_dir,
            receipt_dir=self.receipt_dir,
            poll_interval_seconds=0.05,
        )

        result = await supervisor.run(
            [sys.executable, "-c", "print('receipt ok')"],
            limits=ProcessLimits(max_runtime_seconds=5, memory_limit_mb=256),
        )

        self.assertTrue(result.ok)
        self.assertIsNotNone(result.watchdog_receipt_path)
        self.assertTrue(
            result.watchdog_receipt_path and result.watchdog_receipt_path.exists()
        )
        receipt = json.loads(result.watchdog_receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(
            receipt["receipt_type"],
            "os_engine_process_watchdog_receipt_v1",
        )
        self.assertTrue(receipt["content_hash"].startswith("sha256:"))
        self.assertTrue(receipt["command_sha256"].startswith("sha256:"))
        self.assertFalse(receipt["raw_stdout_stored"])
        self.assertFalse(receipt["raw_stderr_stored"])
        self.assertNotIn("stdout", receipt)
        self.assertNotIn("stderr", receipt)

    async def test_watchdog_timeout_receipt_binds_diagnostic_path(self) -> None:
        supervisor = ProcessSupervisor(
            crash_dir=self.crash_dir,
            receipt_dir=self.receipt_dir,
            poll_interval_seconds=0.05,
        )

        result = await supervisor.run(
            [sys.executable, "-c", "import time; time.sleep(5)"],
            limits=ProcessLimits(max_runtime_seconds=0.2, memory_limit_mb=256),
        )

        self.assertTrue(result.timed_out)
        self.assertIsNotNone(result.diagnostic_path)
        self.assertIsNotNone(result.watchdog_receipt_path)
        receipt = json.loads(result.watchdog_receipt_path.read_text(encoding="utf-8"))
        self.assertTrue(receipt["timed_out"])
        self.assertTrue(receipt["quarantined"])
        self.assertEqual(receipt["diagnostic_path"], str(result.diagnostic_path))

    def test_budget_policy_exists_and_invalid_budgets_fail_closed(self) -> None:
        for kwargs in (
            {"max_runtime_seconds": 0, "memory_limit_mb": 256},
            {"max_runtime_seconds": 5, "memory_limit_mb": 0},
            {"max_runtime_seconds": 5, "memory_limit_mb": MAX_MEMORY_LIMIT_MB + 1},
            {"max_runtime_seconds": 5, "memory_limit_mb": 256, "stdout_limit_bytes": 0},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ProcessSupervisorError):
                    ProcessLimits(**kwargs)
        self.assertEqual(RETRY_POLICY_MAX_ATTEMPTS, 1)

    def test_subprocess_uses_shell_false_and_no_infinite_retry_policy_exists(self) -> None:
        source = Path("kernel/os_engine/memory_watchdog.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.keyword) and node.arg == "shell":
                self.assertIsInstance(node.value, ast.Constant)
                self.assertIs(node.value.value, False)
        self.assertNotIn("create_subprocess_shell", source)
        self.assertNotIn("while True:\n            try:", source)


if __name__ == "__main__":
    unittest.main()
