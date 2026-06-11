import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from kernel.agent_intake.boundary import evaluate_agent_request
from kernel.agent_intake.mcp_manifest import build_agent_intake_manifest, write_agent_intake_manifest
from kernel.agent_intake.proposals import write_agent_proposal
from kernel.landing_ready import init_workspace


class AgentIntakeBoundaryV1Tests(unittest.TestCase):
    def test_allowed_request_is_accepted_only_as_proposal(self):
        decision = evaluate_agent_request(
            {
                "request_id": "agent_req_001",
                "intent": "patch_proposal",
                "title": "Propose README repair",
                "objective": "Suggest a small documentation repair",
            }
        )
        self.assertTrue(decision["accepted"])
        self.assertEqual(decision["terminal_status"], "ACCEPTED_AS_PROPOSAL")
        self.assertFalse(decision["approval_created"])
        self.assertFalse(decision["permit_created"])
        self.assertFalse(decision["execution_performed"])
        self.assertFalse(decision["execution_authority_granted"])

    def test_forbidden_execution_request_is_rejected(self):
        decision = evaluate_agent_request(
            {
                "request_id": "agent_req_002",
                "intent": "execute",
                "run_command": "python3 -m unittest",
                "execution_authority_granted": True,
            }
        )
        self.assertFalse(decision["accepted"])
        self.assertEqual(decision["terminal_status"], "REJECTED_BY_AGENT_BOUNDARY")
        self.assertIn("forbidden_intent:execute", decision["reasons"])
        self.assertIn("forbidden_key:request.run_command", decision["reasons"])
        self.assertIn("forbidden_key:request.execution_authority_granted", decision["reasons"])

    def test_write_agent_proposal_does_not_create_authority_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            self.assertTrue(init_workspace(workspace)["ok"])
            payload = write_agent_proposal(
                workspace,
                {
                    "request_id": "agent_req_003",
                    "intent": "evidence_request",
                    "title": "Request evidence summary",
                    "objective": "Ask operator to review missing trace evidence",
                },
            )
            self.assertTrue(payload["ok"], payload)
            proposal = payload["proposal"]
            self.assertFalse(proposal["task_created"])
            self.assertFalse(proposal["approval_created"])
            self.assertFalse(proposal["permit_created"])
            self.assertFalse(proposal["execution_performed"])
            self.assertFalse(proposal["execution_authority_granted"])
            self.assertTrue((workspace / ".seos" / "agent_intake" / "proposals" / "agent_req_003.json").exists())
            self.assertFalse((workspace / ".seos" / "tasks" / "agent_req_003.json").exists())

    def test_mcp_manifest_is_dependency_free_and_proposal_only(self):
        manifest = build_agent_intake_manifest()
        self.assertFalse(manifest["dependency_required"])
        self.assertFalse(manifest["execution_authority_granted"])
        self.assertGreaterEqual(len(manifest["resources"]), 1)
        self.assertGreaterEqual(len(manifest["tools"]), 1)
        for resource in manifest["resources"]:
            self.assertTrue(resource["read_only"])
            self.assertFalse(resource["side_effects"])
        for tool in manifest["tools"]:
            self.assertFalse(tool["creates_task"])
            self.assertFalse(tool["creates_approval"])
            self.assertFalse(tool["creates_permit"])
            self.assertFalse(tool["executes_command"])

    def test_agent_cli_and_manifest_writer(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request = root / "request.json"
            manifest_path = root / "manifest.json"
            request.write_text(
                json.dumps({"request_id": "agent_cli_req", "intent": "proposal", "title": "CLI proposal"}),
                encoding="utf-8",
            )
            help_result = subprocess.run(
                [sys.executable, "-m", "kernel.agent_intake.cli", "--help"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(help_result.returncode, 0, help_result.stderr)
            self.assertIn("SEOS agent-intake CLI", help_result.stdout)

            seos_help = subprocess.run(
                [sys.executable, "seos.py", "agent", "--help"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(seos_help.returncode, 0, seos_help.stderr)
            self.assertIn("SEOS agent-intake CLI", seos_help.stdout)

            evaluate = subprocess.run(
                [sys.executable, "-m", "kernel.agent_intake.cli", "evaluate", str(request), "--json"],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(evaluate.returncode, 0, evaluate.stderr)
            self.assertTrue(json.loads(evaluate.stdout)["ok"])

            write_result = write_agent_intake_manifest(manifest_path)
            self.assertTrue(write_result["ok"])
            self.assertTrue(manifest_path.exists())


if __name__ == "__main__":
    unittest.main()
