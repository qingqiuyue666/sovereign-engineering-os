import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CLIFoundationTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, "seos.py", *args], check=False, capture_output=True, text=True)

    def test_status_command_reports_v12_foundation(self):
        result = self.run_cli("status")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "V12 foundation status")

    def test_validate_task_command_validates_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "task.json"
            path.write_text(json.dumps({"objective": "x", "requested_capabilities": ["local_dry_run"], "classification": "PUBLIC", "policy_version": "v12", "code_version": "test", "input_digest": "sha256:abc"}), encoding="utf-8")
            result = self.run_cli("validate-task", str(path))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["ok"])

    def test_invalid_command_exits_nonzero(self):
        result = self.run_cli("unknown")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
