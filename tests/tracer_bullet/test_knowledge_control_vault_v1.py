import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from kernel.knowledge import export_workspace_to_vault, scan_control_vault, write_workspace_graph
from kernel.knowledge.frontmatter import dump_frontmatter, split_frontmatter
from kernel.knowledge.object_model import KnowledgeObject, KnowledgeRelation
from kernel.knowledge.proposal_ingest import ingest_proposal_note
from kernel.landing_ready import approve_task, create_task, init_workspace, run_task

_AUTHORITY_SCAN_PROBLEMS = {"invalid_frontmatter", "invalid_authority", "knowledge_note_claims_execution_authority"}


class KnowledgeControlVaultV1Tests(unittest.TestCase):
    def test_object_model_rejects_execution_authority(self):
        with self.assertRaises(ValueError):
            KnowledgeObject(
                "seos.task",
                "TASK_FORBIDDEN",
                "mirror",
                execution_authority_granted=True,
            )

    def test_frontmatter_round_trip_uses_safe_scalar_subset(self):
        payload = {
            "authority": "proposal",
            "execution_authority_granted": False,
            "public": True,
            "seos_id": "TASK_FRONTMATTER",
            "seos_type": "task",
        }
        text = dump_frontmatter(payload) + "# Body\n"
        header, body = split_frontmatter(text)
        self.assertEqual(header, payload)
        self.assertEqual(body, "# Body\n")

    def test_workspace_exports_to_vault_graph_and_scan(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace = root / "workspace"
            vault = root / "vault"
            graph_path = root / "reports" / "knowledge" / "graph.json"

            self.assertTrue(init_workspace(workspace)["ok"])
            self.assertTrue(
                create_task(
                    workspace,
                    task_id="knowledge_demo_task",
                    title="Knowledge demo",
                    objective="Export dry-run evidence to a control vault",
                    source_refs=["README.md"],
                )["ok"]
            )
            self.assertTrue(approve_task(workspace, "knowledge_demo_task", reason="unit test approval")["ok"])
            run_payload = run_task(workspace, "knowledge_demo_task", dry_run=True, command="unit-test")
            self.assertTrue(run_payload["ok"])
            self.assertFalse(run_payload["receipt"]["execution_performed"])

            exported = export_workspace_to_vault(workspace, vault)
            self.assertTrue(exported["ok"], exported)
            task_note = vault / "01_Tasks" / "knowledge_demo_task.md"
            self.assertTrue(task_note.exists())
            self.assertIn("execution_authority_granted: false", task_note.read_text(encoding="utf-8"))

            graph = write_workspace_graph(workspace, graph_path)
            self.assertTrue(graph["ok"])
            self.assertFalse(graph["graph"]["execution_authority_granted"])
            self.assertGreaterEqual(graph["graph"]["node_count"], 2)
            self.assertGreaterEqual(graph["graph"]["edge_count"], 1)

            scan = scan_control_vault(vault)
            blockers = [item for item in scan["problems"] if item.get("problem") in _AUTHORITY_SCAN_PROBLEMS]
            self.assertFalse(blockers, json.dumps(blockers, sort_keys=True))
            self.assertGreaterEqual(scan["note_count"], 3)

    def test_proposal_ingest_never_creates_task_or_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workspace = root / "workspace"
            proposal = root / "proposal.md"
            self.assertTrue(init_workspace(workspace)["ok"])
            proposal.write_text(
                "---\n"
                "seos_type: \"task\"\n"
                "seos_id: \"TASK_PROPOSED\"\n"
                "authority: \"proposal\"\n"
                "title: \"Proposed task\"\n"
                "---\n\n"
                "# Proposed task\n\n"
                "Create a normal SEOS task later through the task CLI.\n",
                encoding="utf-8",
            )
            result = ingest_proposal_note(proposal, workspace)
            self.assertTrue(result["ok"], result)
            self.assertFalse(result["proposal"]["task_created"])
            self.assertFalse(result["proposal"]["approval_created"])
            self.assertFalse((workspace / ".seos" / "tasks" / "TASK_PROPOSED.json").exists())

    def test_knowledge_cli_help_and_validation_script(self):
        module_help = subprocess.run(
            [sys.executable, "-m", "kernel.knowledge.cli", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(module_help.returncode, 0, module_help.stderr)
        self.assertIn("SEOS knowledge CLI", module_help.stdout)

        seos_help = subprocess.run(
            [sys.executable, "seos.py", "knowledge", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(seos_help.returncode, 0, seos_help.stderr)
        self.assertIn("SEOS knowledge CLI", seos_help.stdout)

        check_result = subprocess.run(
            [sys.executable, "scripts/knowledge_control_vault_check_v1.py"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(check_result.returncode, 0, check_result.stderr)
        self.assertTrue(json.loads(check_result.stdout)["ok"])

    def test_relation_shape_is_explicit(self):
        relation = KnowledgeRelation("has_evidence", "seos.evidence_trace", "TRACE_1")
        self.assertEqual(
            relation.as_dict(),
            {"relation_type": "has_evidence", "target_type": "seos.evidence_trace", "target_id": "TRACE_1"},
        )


if __name__ == "__main__":
    unittest.main()
