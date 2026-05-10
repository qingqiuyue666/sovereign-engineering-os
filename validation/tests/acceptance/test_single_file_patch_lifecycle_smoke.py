import ast
import json
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

from kernel.lifecycle.single_file_patch_lifecycle import (
    run_single_file_patch_lifecycle,
    single_file_patch_lifecycle_manifest,
)


def _identity(text):
    return sha256(text.encode("utf-8")).hexdigest()


class SingleFilePatchLifecycleSmokeTest(unittest.TestCase):
    def test_complete_single_file_lifecycle_smoke(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp) / "repo"
            repo_root.mkdir()
            target = repo_root / "target.txt"
            target.write_text("before\n", encoding="utf-8")
            artifact_root = repo_root / "artifacts"
            proposal = {
                "proposal_id": "proposal-smoke",
                "patch_id": "patch-smoke",
                "target_path": "target.txt",
            }
            approval = {
                "approved": True,
                "proposal_id": "proposal-smoke",
                "patch_id": "patch-smoke",
                "target_path": "target.txt",
                "expected_preimage_identity": _identity("before\n"),
            }

            result = run_single_file_patch_lifecycle(
                repo_root=repo_root,
                artifact_root=artifact_root,
                target_path="target.txt",
                new_content="after\n",
                proposal=proposal,
                approval=approval,
                validation_callable=lambda context: {
                    "ok": True,
                    "reason_code": "ok",
                },
            )

            self.assertTrue(result["ok"])
            self.assertEqual(result["status"], "applied")
            self.assertEqual(target.read_text(encoding="utf-8"), "after\n")

            for key in (
                "proposal",
                "patch_body",
                "preimage",
                "validation_result",
                "final_seal",
            ):
                self.assertIsInstance(result["artifacts"][key], str)
                self.assertTrue((repo_root / result["artifacts"][key]).exists())

            proposal_artifact = json.loads(
                (repo_root / result["artifacts"]["proposal"]).read_text()
            )
            validation_artifact = json.loads(
                (repo_root / result["artifacts"]["validation_result"]).read_text()
            )
            final_seal = json.loads(
                (repo_root / result["artifacts"]["final_seal"]).read_text()
            )

            self.assertEqual(
                proposal_artifact["artifact_type"],
                "single_file_patch_proposal",
            )
            self.assertEqual(validation_artifact["reason_code"], "ok")
            self.assertEqual(final_seal["replay"]["final_status"], "applied")

            repo_resolved = repo_root.resolve(strict=True)
            for artifact_path in result["replay"]["artifact_paths"]:
                self.assertFalse(Path(artifact_path).is_absolute())
                self.assertNotIn("..", Path(artifact_path).parts)
                resolved = (repo_root / artifact_path).resolve(strict=False)
                resolved.relative_to(repo_resolved)

            manifest = single_file_patch_lifecycle_manifest()
            self.assertIs(manifest["service_calls_authorized"], False)
            self.assertIs(manifest["db_repository_uow_authorized"], False)
            self.assertIs(manifest["executor_dispatch_authorized"], False)

    def test_smoke_file_is_acceptance_discovery_compatible(self):
        self.assertTrue(Path(__file__).name.startswith("test_"))
        self.assertIn("validation/tests/acceptance", Path(__file__).as_posix())

    def test_smoke_import_boundary_remains_narrow(self):
        module_path = (
            Path(__file__).resolve().parents[3]
            / "kernel/lifecycle/single_file_patch_lifecycle.py"
        )
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        imports = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module)
        self.assertEqual(
            imports,
            [
                "collections.abc",
                "copy",
                "hashlib",
                "pathlib",
                "json",
            ],
        )


if __name__ == "__main__":
    unittest.main()
