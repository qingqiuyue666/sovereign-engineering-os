import ast
import json
import tempfile
import unittest
from pathlib import Path

from examples.single_file_lifecycle_demo import (
    run_controlled_single_file_lifecycle_demo,
)


_EXPECTED_FILES = {
    "controlled_demo/apply_target.txt",
    "controlled_demo/rollback_target.txt",
    "artifacts/controlled-demo-apply/proposal.json",
    "artifacts/controlled-demo-apply/patch_body.txt",
    "artifacts/controlled-demo-apply/preimage.txt",
    "artifacts/controlled-demo-apply/validation_result.json",
    "artifacts/controlled-demo-apply/final_seal.json",
    "artifacts/controlled-demo-rollback/proposal.json",
    "artifacts/controlled-demo-rollback/patch_body.txt",
    "artifacts/controlled-demo-rollback/preimage.txt",
    "artifacts/controlled-demo-rollback/validation_result.json",
    "artifacts/controlled-demo-rollback/rollback.json",
    "artifacts/controlled-demo-rollback/final_seal.json",
}

_FORBIDDEN_IMPORTS = {
    "os",
    "sys",
    "subprocess",
    "sqlite3",
    "threading",
    "asyncio",
    "time",
    "datetime",
    "socket",
    "urllib",
    "requests",
    "httpx",
    "kernel.services",
    "kernel.repositories",
    "kernel.executor",
    "kernel.recovery",
}

_FORBIDDEN_WORDING = (
    "general runtime",
    "agent runtime",
    "service runtime",
    "autonomous executor",
    "full AI execution OS",
    "multi-file patch system",
    "production automation platform",
)


class SingleFileLifecycleControlledDemoSmokeTest(unittest.TestCase):
    def test_controlled_demo_runs_apply_rollback_and_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp) / "repo"
            repo_root.mkdir()
            artifact_root = repo_root / "artifacts"

            result = run_controlled_single_file_lifecycle_demo(
                repo_root=repo_root,
                artifact_root=artifact_root,
            )

            self.assertTrue(result["ok"])
            self.assertEqual(
                result["demo"],
                "controlled single-file lifecycle demonstration",
            )
            self.assertIs(result["json_safe"], True)
            json.dumps(result, sort_keys=True, allow_nan=False)

            self.assertEqual(result["apply"]["lifecycle_status"], "applied")
            self.assertIs(result["apply"]["verifier_ok"], True)
            self.assertEqual(result["apply"]["verifier_status"], "verified")
            self.assertEqual(
                result["apply"]["target_content_observed"],
                "controlled demo patched content\n",
            )

            self.assertEqual(result["rollback"]["lifecycle_status"], "rolled_back")
            self.assertIs(result["rollback"]["verifier_ok"], True)
            self.assertEqual(result["rollback"]["verifier_status"], "verified")
            self.assertEqual(
                result["rollback"]["target_content_observed"],
                "controlled demo original content\n",
            )

            self.assertEqual(result["verifier"]["apply"]["final_status"], "applied")
            self.assertEqual(result["verifier"]["apply"]["validation_status"], "pass")
            self.assertEqual(
                result["verifier"]["apply"]["rollback_status"],
                "not_attempted",
            )
            self.assertEqual(
                result["verifier"]["rollback"]["final_status"],
                "rolled_back",
            )
            self.assertEqual(
                result["verifier"]["rollback"]["validation_status"],
                "fail",
            )
            self.assertEqual(
                result["verifier"]["rollback"]["rollback_status"],
                "succeeded",
            )

            for value in result["authority"].values():
                self.assertIs(value, False)

            observed_files = {
                path.relative_to(repo_root).as_posix()
                for path in repo_root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(observed_files, _EXPECTED_FILES)
            for path_value in json.dumps(result, sort_keys=True).split('"'):
                if "/" in path_value:
                    self.assertFalse(Path(path_value).is_absolute(), path_value)
                    self.assertNotIn("..", Path(path_value).parts)

    def test_demo_import_boundary_and_wording_remain_controlled(self):
        module_path = (
            Path(__file__).resolve().parents[3]
            / "examples/single_file_lifecycle_demo.py"
        )
        source = module_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module)

        self.assertEqual(
            imports,
            [
                "pathlib",
                "hashlib",
                "kernel.lifecycle.single_file_patch_lifecycle",
                "kernel.lifecycle.single_file_lifecycle_replay_verifier",
            ],
        )
        for imported in imports:
            self.assertNotIn(imported, _FORBIDDEN_IMPORTS)
            self.assertFalse(imported.startswith("kernel.services"))
            self.assertFalse(imported.startswith("kernel.repositories"))
            self.assertNotIn("executor", imported)
            self.assertNotIn("recovery", imported)

        self.assertIn("controlled single-file lifecycle demonstration", source)
        for wording in _FORBIDDEN_WORDING:
            self.assertNotIn(wording, source)

    def test_smoke_file_is_acceptance_discovery_compatible(self):
        self.assertTrue(Path(__file__).name.startswith("test_"))
        self.assertIn("validation/tests/acceptance", Path(__file__).as_posix())


if __name__ == "__main__":
    unittest.main()
