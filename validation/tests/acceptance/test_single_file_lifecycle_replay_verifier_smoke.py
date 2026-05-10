import ast
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

from kernel.lifecycle.single_file_lifecycle_replay_verifier import (
    single_file_lifecycle_replay_verifier_manifest,
    verify_single_file_patch_lifecycle_replay,
)
from kernel.lifecycle.single_file_patch_lifecycle import run_single_file_patch_lifecycle


def _identity(text):
    return sha256(text.encode("utf-8")).hexdigest()


class SingleFileLifecycleReplayVerifierSmokeTest(unittest.TestCase):
    def test_complete_lifecycle_artifacts_verify(self):
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

            lifecycle_result = run_single_file_patch_lifecycle(
                repo_root=repo_root,
                artifact_root=artifact_root,
                target_path="target.txt",
                new_content="after\n",
                proposal=proposal,
                approval=approval,
                validation_callable=lambda context: {
                    "ok": True,
                    "reason_code": "validation_passed",
                },
            )
            self.assertTrue(lifecycle_result["ok"])

            verifier_result = verify_single_file_patch_lifecycle_replay(
                repo_root=repo_root,
                artifact_root=artifact_root,
                patch_id="patch-smoke",
            )

            self.assertTrue(verifier_result["ok"])
            self.assertEqual(verifier_result["status"], "verified")
            self.assertEqual(verifier_result["failures"], [])
            self.assertIs(
                verifier_result["identity"]["preimage_identity_matches"], True
            )
            self.assertIs(
                verifier_result["identity"]["postimage_identity_matches"], True
            )
            self.assertEqual(verifier_result["replay"]["final_status"], "applied")
            self.assertEqual(verifier_result["replay"]["validation_status"], "pass")
            self.assertEqual(
                verifier_result["replay"]["rollback_status"], "not_attempted"
            )
            for value in verifier_result["authority"].values():
                self.assertIs(value, False)

            manifest = single_file_lifecycle_replay_verifier_manifest()
            self.assertIs(manifest["target_mutation_authorized"], False)
            self.assertIs(manifest["service_calls_authorized"], False)
            self.assertIs(manifest["db_repository_uow_authorized"], False)
            self.assertIs(manifest["executor_dispatch_authorized"], False)
            self.assertIs(manifest["subprocess_authorized"], False)
            self.assertIs(manifest["network_authorized"], False)

    def test_smoke_import_boundary_remains_narrow(self):
        module_path = (
            Path(__file__).resolve().parents[3]
            / "kernel/lifecycle/single_file_lifecycle_replay_verifier.py"
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

    def test_smoke_file_is_acceptance_discovery_compatible(self):
        self.assertTrue(Path(__file__).name.startswith("test_"))
        self.assertIn("validation/tests/acceptance", Path(__file__).as_posix())


if __name__ == "__main__":
    unittest.main()
