import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from kernel.landing_ready import approve_task, create_task, init_workspace, run_task


class KnowledgeAdapterSurfaceV1Tests(unittest.TestCase):
    def make_workspace(self, root: Path) -> Path:
        workspace = root / "workspace"
        self.assertTrue(init_workspace(workspace)["ok"])
        self.assertTrue(
            create_task(
                workspace,
                task_id="adapter_surface_task",
                title="Adapter surface task",
                objective="Mirror task into knowledge adapters without authority transfer.",
                source_refs=["README.md"],
            )["ok"]
        )
        self.assertTrue(approve_task(workspace, "adapter_surface_task", reason="adapter surface test")["ok"])
        run_payload = run_task(workspace, "adapter_surface_task", dry_run=True, command="adapter-surface-test")
        self.assertTrue(run_payload["ok"])
        self.assertFalse(run_payload["receipt"]["execution_performed"])
        return workspace

    def run_knowledge(self, *args: str) -> dict[str, object]:
        completed = subprocess.run(
            [sys.executable, "seos.py", "knowledge", *args, "--json"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        return json.loads(completed.stdout)

    def test_top_level_knowledge_cli_exports_adapter_mirrors_without_authority(self):
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            workspace = self.make_workspace(root)
            vault = root / "vault"
            logseq_root = root / "logseq"
            anytype_bundle = root / "anytype_bundle.json"
            anytype_import = root / "anytype_import.json"
            notion_sync = root / "notion_sync.json"

            vault_payload = self.run_knowledge("export-workspace", "--workspace", workspace.as_posix(), "--vault", vault.as_posix())
            self.assertTrue(vault_payload["ok"])
            self.assertTrue((vault / "99_Graph/seos_control_graph.json").exists())

            logseq_payload = self.run_knowledge("export-logseq", "--workspace", workspace.as_posix(), "--root", logseq_root.as_posix())
            self.assertTrue(logseq_payload["ok"])
            self.assertTrue((logseq_root / "pages/SEOS_Control.md").exists())
            self.assertTrue((logseq_root / "journals/seos_operations.md").exists())

            anytype_payload = self.run_knowledge("export-anytype", "--workspace", workspace.as_posix(), "--output", anytype_bundle.as_posix())
            self.assertTrue(anytype_payload["ok"])
            bundle = json.loads(anytype_bundle.read_text(encoding="utf-8"))
            self.assertEqual(bundle["authority"], "mirror")
            self.assertFalse(bundle["execution_authority_granted"])
            self.assertEqual(bundle["license_boundary"], "neutral_export_no_anytype_source_dependency")

            import_payload = self.run_knowledge("import-anytype", "--source", anytype_bundle.as_posix(), "--output", anytype_import.as_posix())
            self.assertTrue(import_payload["ok"], import_payload)
            imported = json.loads(anytype_import.read_text(encoding="utf-8"))
            self.assertEqual(imported["accepted_as"], "object_model_proposal_only")
            self.assertFalse(imported["task_created"])
            self.assertFalse(imported["approval_created"])
            self.assertFalse(imported["permit_created"])
            self.assertFalse(imported["execution_authority_granted"])

            notion_payload = self.run_knowledge(
                "sync-notion",
                "--mode",
                "readonly",
                "--source",
                anytype_import.as_posix(),
                "--output",
                notion_sync.as_posix(),
            )
            self.assertTrue(notion_payload["ok"])
            notion = json.loads(notion_sync.read_text(encoding="utf-8"))
            self.assertEqual(notion["mode"], "readonly_mirror_payload")
            self.assertFalse(notion["network_call_performed"])
            self.assertFalse(notion["credential_required_by_this_step"])
            self.assertFalse(notion["approval_created"])
            self.assertFalse(notion["permit_created"])
            self.assertFalse(notion["execution_authority_granted"])

    def test_obsidian_template_set_includes_release_note_boundary(self):
        template = Path("integrations/obsidian/templates/release.md")
        self.assertTrue(template.exists())
        text = template.read_text(encoding="utf-8")
        self.assertIn('seos_type: "release"', text)
        self.assertIn('authority: "mirror"', text)
        self.assertIn("execution_authority_granted: false", text)
        self.assertIn("does not approve a release", text)


if __name__ == "__main__":
    unittest.main()
