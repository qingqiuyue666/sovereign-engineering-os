import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class OperatorCLITests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, "seos.py", *args], check=False, capture_output=True, text=True)

    def test_health_reports_plan_without_running_network_or_providers(self):
        result = self.run_cli("health")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["dry_run_only"])
        self.assertIn("test-root-integrity", payload["health_plan"])

    def test_task_validate_subcommand_uses_manifest_validator(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "task.json"
            path.write_text(
                json.dumps(
                    {
                        "objective": "x",
                        "requested_capabilities": ["local_validation"],
                        "classification": "PUBLIC",
                        "policy_version": "v12",
                        "code_version": "test",
                        "input_digest": "sha256:abc",
                    }
                ),
                encoding="utf-8",
            )
            result = self.run_cli("task", "validate", str(path))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["ok"])

    def test_task_create_and_run_ledger_create_are_dry_run_only(self):
        task = self.run_cli("task", "create", "--dry-run")
        ledger = self.run_cli("run-ledger", "create", "--dry-run")

        self.assertEqual(task.returncode, 0, task.stderr)
        self.assertTrue(json.loads(task.stdout)["dry_run"])
        self.assertEqual(ledger.returncode, 0, ledger.stderr)
        ledger_payload = json.loads(ledger.stdout)
        self.assertFalse(ledger_payload["ledger_write_performed"])
        self.assertFalse(ledger_payload["ai_provider_call_performed"])

    def test_audit_summary_and_legacy_status_commands_remain_available(self):
        audit = self.run_cli("audit", "summary")
        status = self.run_cli("status")

        self.assertEqual(audit.returncode, 0, audit.stderr)
        self.assertTrue(json.loads(audit.stdout)["forbidden_runtime_surfaces_absent"])
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertEqual(json.loads(status.stdout)["status"], "V12 foundation status")

    def test_invalid_operator_command_exits_nonzero(self):
        result = self.run_cli("task", "create")

        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
