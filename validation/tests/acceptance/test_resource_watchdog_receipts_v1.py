import json
import sys
import tempfile
import unittest
from pathlib import Path

from kernel.os_engine.memory_watchdog import ProcessLimits, ProcessSupervisor


class ResourceWatchdogReceiptsAcceptanceTests(unittest.IsolatedAsyncioTestCase):
    async def test_success_and_timeout_paths_write_audit_receipts(self):
        with tempfile.TemporaryDirectory() as temp_dir_name:
            root = Path(temp_dir_name)
            supervisor = ProcessSupervisor(
                crash_dir=root / "crashes",
                receipt_dir=root / "receipts",
                poll_interval_seconds=0.05,
            )

            success = await supervisor.run(
                [sys.executable, "-c", "print('ok')"],
                limits=ProcessLimits(max_runtime_seconds=5, memory_limit_mb=256),
            )
            timeout = await supervisor.run(
                [sys.executable, "-c", "import time; time.sleep(5)"],
                limits=ProcessLimits(max_runtime_seconds=0.2, memory_limit_mb=256),
            )

            self.assertTrue(success.ok)
            self.assertTrue(timeout.timed_out)
            for result in (success, timeout):
                self.assertIsNotNone(result.watchdog_receipt_path)
                receipt = json.loads(
                    result.watchdog_receipt_path.read_text(encoding="utf-8")
                )
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
            timeout_receipt = json.loads(
                timeout.watchdog_receipt_path.read_text(encoding="utf-8")
            )
            self.assertTrue(timeout_receipt["quarantined"])
            self.assertEqual(
                timeout_receipt["diagnostic_path"],
                str(timeout.diagnostic_path),
            )


if __name__ == "__main__":
    unittest.main()
