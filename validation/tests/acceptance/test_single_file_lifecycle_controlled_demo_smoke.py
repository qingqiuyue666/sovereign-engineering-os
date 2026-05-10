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

_EXPECTED_TOP_LEVEL_KEYS = {
    "demo",
    "description",
    "ok",
    "paths",
    "apply",
    "rollback",
    "rollback_path",
    "verifier",
    "authority",
    "json_safe",
}

_EXPECTED_CONTROLLED_DEMO_FILES = {
    "apply_target.txt",
    "rollback_target.txt",
}

_EXPECTED_ARTIFACT_DIRS = {
    "controlled-demo-apply",
    "controlled-demo-rollback",
}

_EXPECTED_APPLY_ARTIFACT_FILES = {
    "proposal.json",
    "patch_body.txt",
    "preimage.txt",
    "validation_result.json",
    "final_seal.json",
}

_EXPECTED_ROLLBACK_ARTIFACT_FILES = _EXPECTED_APPLY_ARTIFACT_FILES | {
    "rollback.json",
}

_EXPECTED_AUTHORITY_KEYS = {
    "service_calls_authorized",
    "db_repository_uow_authorized",
    "executor_dispatch_authorized",
    "multi_file_lifecycle_authorized",
    "evidence_audit_append_authorized",
    "restore_service_authorized",
    "subprocess_authorized",
    "network_authorized",
    "cli_authorized",
    "adapter_authorized",
    "broad_physical_io_authorized",
    "durable_writes_authorized",
    "irreversible_actions_authorized",
    "authority_grant_usage_authorized",
    "capability_token_authorized",
    "new_governance_boundary_family_authorized",
    "autonomous_agent_runtime_authorized",
    "production_automation_platform_authorized",
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
    "kernel.approval",
    "kernel.evidence",
    "kernel.review",
    "kernel.revision",
    "kernel.capability",
    "kernel.authority",
}

_FORBIDDEN_POSITIVE_WORDING = (
    "general runtime",
    "agent runtime",
    "service runtime",
    "autonomous executor",
    "full AI execution OS",
    "multi-file patch system",
    "production automation platform",
    "runtime ready",
    "service ready",
    "DB ready",
    "executor ready",
    "multi-file ready",
    "production automation ready",
)

_DENIAL_WORDING = (
    "does not prove",
    "does not add",
    "do not treat",
    "not authorized",
    "not ready",
    "not approval",
    "remain later",
    "remains bounded",
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

            self.assertEqual(set(result), _EXPECTED_TOP_LEVEL_KEYS)
            self.assertTrue(result["ok"])
            self.assertEqual(
                result["demo"],
                "controlled single-file lifecycle demonstration",
            )
            self.assertIs(result["json_safe"], True)
            result_json = json.dumps(result, sort_keys=True, allow_nan=False)
            self.assertEqual(json.loads(result_json), result)
            self._assert_json_safe(result)

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
            self.assertEqual(
                result["rollback_path"],
                {
                    "validation_reason_code": "controlled_demo_validation_failed",
                    "validation_failures": ["validation_failed"],
                    "failure_reason_summary": "controlled_demo_validation_failed",
                    "rollback_status": "succeeded",
                    "target_restored": True,
                    "observed_target_content_matches_preimage": True,
                },
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

            self.assertEqual(set(result["authority"]), _EXPECTED_AUTHORITY_KEYS)
            for value in result["authority"].values():
                self.assertIs(type(value), bool)
                self.assertIs(value, False)

            self.assertIsNone(result["paths"]["apply"]["artifacts"]["rollback"])
            self.assertEqual(
                result["paths"]["rollback"]["artifacts"]["rollback"],
                "artifacts/controlled-demo-rollback/rollback.json",
            )

            observed_files = {
                path.relative_to(repo_root).as_posix()
                for path in repo_root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(observed_files, _EXPECTED_FILES)
            self.assertEqual(
                {
                    path.name
                    for path in (repo_root / "controlled_demo").iterdir()
                    if path.is_file()
                },
                _EXPECTED_CONTROLLED_DEMO_FILES,
            )
            self.assertEqual(
                {
                    path.name
                    for path in artifact_root.iterdir()
                    if path.is_dir()
                },
                _EXPECTED_ARTIFACT_DIRS,
            )
            self.assertEqual(
                {
                    path.name
                    for path in (artifact_root / "controlled-demo-apply").iterdir()
                    if path.is_file()
                },
                _EXPECTED_APPLY_ARTIFACT_FILES,
            )
            self.assertEqual(
                {
                    path.name
                    for path in (artifact_root / "controlled-demo-rollback").iterdir()
                    if path.is_file()
                },
                _EXPECTED_ROLLBACK_ARTIFACT_FILES,
            )
            self.assertFalse(
                (artifact_root / "controlled-demo-apply" / "rollback.json").exists()
            )
            self.assertTrue(
                (artifact_root / "controlled-demo-rollback" / "rollback.json").is_file()
            )
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

        readme_path = Path(__file__).resolve().parents[3] / "examples/README.md"
        readme = readme_path.read_text(encoding="utf-8")

        self.assertIn("controlled single-file lifecycle demonstration", source)
        self.assertIn("controlled single-file lifecycle demonstration", readme)
        self._assert_no_positive_forbidden_wording(source, module_path.as_posix())
        self._assert_no_positive_forbidden_wording(readme, readme_path.as_posix())

    def test_smoke_file_is_acceptance_discovery_compatible(self):
        self.assertTrue(Path(__file__).name.startswith("test_"))
        self.assertIn("validation/tests/acceptance", Path(__file__).as_posix())

    def _assert_json_safe(self, value):
        self.assertNotIsInstance(value, Path)
        self.assertNotIsInstance(value, bytes)
        self.assertNotIsInstance(value, BaseException)
        self.assertFalse(callable(value))

        if value is None:
            return
        if type(value) is bool:
            return
        if isinstance(value, str):
            return
        if isinstance(value, int):
            return
        if isinstance(value, float):
            self.assertEqual(value, value)
            self.assertNotEqual(value, float("inf"))
            self.assertNotEqual(value, float("-inf"))
            return
        if isinstance(value, list):
            for item in value:
                self._assert_json_safe(item)
            return
        if isinstance(value, dict):
            for key, item in value.items():
                self.assertIsInstance(key, str)
                self._assert_json_safe(item)
            return

        self.fail(f"non-JSON-safe value leaked: {type(value).__name__}")

    def _assert_no_positive_forbidden_wording(self, text, source_name):
        for line_number, line in enumerate(text.splitlines(), start=1):
            lowered = line.lower()
            for wording in _FORBIDDEN_POSITIVE_WORDING:
                if wording.lower() not in lowered:
                    continue
                if any(denial in lowered for denial in _DENIAL_WORDING):
                    continue
                self.fail(
                    f"positive forbidden wording in {source_name}:{line_number}: "
                    f"{wording}"
                )


if __name__ == "__main__":
    unittest.main()
