import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from kernel.landing_ready import release_check


class LandingReadyProgramV1Tests(unittest.TestCase):
    def run_cli(self, *args, cwd=None):
        return subprocess.run(
            [sys.executable, "seos.py", *args],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_workspace_task_approval_run_and_trace_flow(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)

            init = self.run_cli("init", "--workspace", str(workspace), "--json")
            self.assertEqual(init.returncode, 0, init.stderr)
            self.assertTrue(json.loads(init.stdout)["created"])

            created = self.run_cli(
                "task",
                "create",
                "--workspace",
                str(workspace),
                "--task-id",
                "landing_demo_task",
                "--title",
                "Landing demo",
                "--objective",
                "Govern a local validation dry run",
                "--source",
                "README.md",
                "--json",
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            self.assertEqual(json.loads(created.stdout)["task"]["task_id"], "landing_demo_task")

            unapproved_run = self.run_cli(
                "run",
                "--workspace",
                str(workspace),
                "landing_demo_task",
                "--dry-run",
                "--json",
            )
            self.assertNotEqual(unapproved_run.returncode, 0)
            self.assertEqual(json.loads(unapproved_run.stdout)["error"], "approval_required")

            approval = self.run_cli("approve", "--workspace", str(workspace), "landing_demo_task", "--json")
            self.assertEqual(approval.returncode, 0, approval.stderr)
            self.assertEqual(json.loads(approval.stdout)["receipt"]["receipt_type"], "approval")

            run = self.run_cli(
                "run",
                "--workspace",
                str(workspace),
                "landing_demo_task",
                "--dry-run",
                "--command",
                "python3 -m unittest",
                "--json",
            )
            self.assertEqual(run.returncode, 0, run.stderr)
            run_payload = json.loads(run.stdout)
            self.assertFalse(run_payload["receipt"]["execution_performed"])

            trace = self.run_cli("evidence", "trace", "--workspace", str(workspace), "landing_demo_task", "--json")
            self.assertEqual(trace.returncode, 0, trace.stderr)
            self.assertEqual(json.loads(trace.stdout)["trace_status"], "complete")

            replay = self.run_cli("replay", "explain", "--workspace", str(workspace), "landing_demo_task", "--json")
            self.assertEqual(replay.returncode, 0, replay.stderr)
            self.assertTrue(json.loads(replay.stdout)["can_reconstruct"])

    def test_reject_receipt_and_receipt_show_are_auditable(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            self.assertEqual(self.run_cli("init", "--workspace", str(workspace), "--json").returncode, 0)
            self.assertEqual(
                self.run_cli(
                    "task",
                    "create",
                    "--workspace",
                    str(workspace),
                    "--task-id",
                    "reject_demo_task",
                    "--title",
                    "Reject demo",
                    "--objective",
                    "Prove rejection receipt",
                    "--json",
                ).returncode,
                0,
            )

            rejected = self.run_cli("reject", "--workspace", str(workspace), "reject_demo_task", "--json")
            self.assertEqual(rejected.returncode, 0, rejected.stderr)
            self.assertEqual(json.loads(rejected.stdout)["receipt"]["receipt_type"], "rejection")

            latest = self.run_cli("receipt", "show", "--workspace", str(workspace), "latest", "--json")
            self.assertEqual(latest.returncode, 0, latest.stderr)
            self.assertIn("sha256", json.loads(latest.stdout))

    def test_ai_context_repo_map_token_roi_and_failure_bundle(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            self.assertEqual(self.run_cli("init", "--workspace", str(workspace), "--json").returncode, 0)
            self.assertEqual(
                self.run_cli(
                    "task",
                    "create",
                    "--workspace",
                    str(workspace),
                    "--task-id",
                    "ai_demo_task",
                    "--title",
                    "AI bundle demo",
                    "--objective",
                    "Build a minimal context bundle",
                    "--json",
                ).returncode,
                0,
            )

            bundle = self.run_cli(
                "ai",
                "bundle",
                "--workspace",
                str(workspace),
                "ai_demo_task",
                "--source",
                "README.md",
                "--budget",
                "4000",
                "--json",
            )
            self.assertEqual(bundle.returncode, 0, bundle.stderr)
            self.assertFalse(json.loads(bundle.stdout)["context_bundle"]["raw_file_contents_included"])

            repo_map = self.run_cli("ai", "repo-map", "--workspace", str(workspace), "--json")
            self.assertEqual(repo_map.returncode, 0, repo_map.stderr)
            self.assertGreater(json.loads(repo_map.stdout)["repo_map"]["file_count"], 0)

            roi = self.run_cli("ai", "token-roi", "--workspace", str(workspace), "--json")
            self.assertEqual(roi.returncode, 0, roi.stderr)
            self.assertEqual(json.loads(roi.stdout)["token_roi_report"]["bundle_count"], 1)

            failure = self.run_cli(
                "failure",
                "compress",
                "--workspace",
                str(workspace),
                "--command",
                "python3 -m unittest",
                "--exit-code",
                "1",
                "--log",
                "FAILED test_example",
                "--json",
            )
            self.assertEqual(failure.returncode, 0, failure.stderr)
            explained = self.run_cli("failure", "explain", "--workspace", str(workspace), "latest", "--json")
            self.assertEqual(explained.returncode, 0, explained.stderr)
            self.assertEqual(json.loads(explained.stdout)["root_symptom"], "FAILED test_example")

    def test_status_is_fail_closed_when_release_evidence_is_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            payload = release_check(Path(temp), Path(temp))
        self.assertFalse(payload["release_ready"])
        self.assertIn("release_readiness_evidence_missing", payload["blockers"])

    def test_operator_cli_supports_direct_and_module_help(self):
        direct = subprocess.run(
            [sys.executable, "apps/operator_cli/main.py", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        module = subprocess.run(
            [sys.executable, "-m", "apps.operator_cli.main", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(direct.returncode, 0, direct.stderr)
        self.assertIn("SEOS operator CLI", direct.stdout)
        self.assertEqual(module.returncode, 0, module.stderr)
        self.assertIn("SEOS operator CLI", module.stdout)
        self.assertNotIn("RuntimeWarning", module.stderr)

    def test_boundary_and_anti_bloat_gate_are_operator_visible(self):
        readme = Path("README.md").read_text(encoding="utf-8")
        policy = Path("governance/policy/anti_bloat_governance_gate_v1.json").read_text(encoding="utf-8")

        self.assertIn("not an OS-level sandbox", readme)
        self.assertIn("not a computer-control framework", readme)
        self.assertIn("not RPA", readme)
        self.assertIn("REJECT_NEW_RUNTIME_MODULE", policy)


if __name__ == "__main__":
    unittest.main()
