import ast
import json
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


class SingleFileLifecycleReplayVerifierTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self.repo_root = self.tmp_path / "repo"
        self.repo_root.mkdir()
        self.target = self.repo_root / "target.txt"
        self.target.write_text("before\n", encoding="utf-8")
        self.artifact_root = self.repo_root / "artifacts"
        self.patch_id = "patch-1"
        self.proposal = {
            "proposal_id": "proposal-1",
            "patch_id": self.patch_id,
            "target_path": "target.txt",
        }
        self.approval = {
            "approved": True,
            "proposal_id": "proposal-1",
            "patch_id": self.patch_id,
            "target_path": "target.txt",
            "expected_preimage_identity": _identity("before\n"),
        }

    def tearDown(self):
        self.tmp.cleanup()

    def run_lifecycle(self, **overrides):
        params = {
            "repo_root": self.repo_root,
            "artifact_root": self.artifact_root,
            "target_path": "target.txt",
            "new_content": "after\n",
            "proposal": self.proposal,
            "approval": self.approval,
            "validation_callable": lambda context: {
                "ok": True,
                "reason_code": "validation_passed",
            },
        }
        params.update(overrides)
        return run_single_file_patch_lifecycle(**params)

    def verify(self, **overrides):
        params = {
            "repo_root": self.repo_root,
            "artifact_root": self.artifact_root,
            "patch_id": self.patch_id,
        }
        params.update(overrides)
        return verify_single_file_patch_lifecycle_replay(**params)

    def artifact_dir(self):
        return self.artifact_root / self.patch_id

    def artifact_file(self, name):
        return self.artifact_dir() / name

    def read_json(self, name):
        return json.loads(self.artifact_file(name).read_text(encoding="utf-8"))

    def write_json(self, name, payload):
        self.artifact_file(name).write_text(
            json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )

    def artifact_snapshot(self):
        return {
            path.relative_to(self.artifact_dir()).as_posix(): path.read_bytes()
            for path in sorted(self.artifact_dir().iterdir())
            if path.is_file()
        }

    def test_happy_path_verifies_lifecycle_produced_applied_artifacts(self):
        self.run_lifecycle()
        result = self.verify()

        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["reason_code"], "verified")
        self.assertEqual(result["failures"], [])
        self.assertEqual(result["patch_id"], self.patch_id)
        self.assertEqual(result["target_path"], "target.txt")
        self.assertEqual(
            result["artifacts"],
            {
                "proposal": True,
                "patch_body": True,
                "preimage": True,
                "validation_result": True,
                "rollback": None,
                "final_seal": True,
            },
        )
        self.assertIs(result["identity"]["preimage_identity_matches"], True)
        self.assertIs(result["identity"]["postimage_identity_matches"], True)
        self.assertEqual(
            result["replay"],
            {
                "final_status": "applied",
                "validation_status": "pass",
                "rollback_status": "not_attempted",
            },
        )

    def test_verifier_does_not_mutate_target_file(self):
        self.run_lifecycle()
        before = self.target.read_bytes()
        self.verify()
        self.assertEqual(self.target.read_bytes(), before)

    def test_missing_proposal_fails(self):
        self.run_lifecycle()
        self.artifact_file("proposal.json").unlink()
        result = self.verify()

        self.assertFalse(result["ok"])
        self.assertIn("artifact_file_missing", result["failures"])
        self.assertIs(result["artifacts"]["proposal"], False)

    def test_missing_patch_body_fails(self):
        self.run_lifecycle()
        self.artifact_file("patch_body.txt").unlink()
        result = self.verify()

        self.assertFalse(result["ok"])
        self.assertIn("artifact_file_missing", result["failures"])
        self.assertIs(result["artifacts"]["patch_body"], False)

    def test_missing_preimage_fails(self):
        self.run_lifecycle()
        self.artifact_file("preimage.txt").unlink()
        result = self.verify()

        self.assertFalse(result["ok"])
        self.assertIn("artifact_file_missing", result["failures"])
        self.assertIs(result["artifacts"]["preimage"], False)

    def test_missing_validation_result_fails(self):
        self.run_lifecycle()
        self.artifact_file("validation_result.json").unlink()
        result = self.verify()

        self.assertFalse(result["ok"])
        self.assertIn("artifact_file_missing", result["failures"])
        self.assertIs(result["artifacts"]["validation_result"], False)

    def test_missing_final_seal_fails(self):
        self.run_lifecycle()
        self.artifact_file("final_seal.json").unlink()
        result = self.verify()

        self.assertFalse(result["ok"])
        self.assertIn("artifact_file_missing", result["failures"])
        self.assertIs(result["artifacts"]["final_seal"], False)

    def test_malformed_proposal_json_fails(self):
        self.run_lifecycle()
        self.artifact_file("proposal.json").write_text("{", encoding="utf-8")
        result = self.verify()

        self.assertFalse(result["ok"])
        self.assertEqual(result["failures"], ["artifact_json_invalid"])

    def test_malformed_validation_json_fails(self):
        self.run_lifecycle()
        self.artifact_file("validation_result.json").write_text("{", encoding="utf-8")
        result = self.verify()

        self.assertFalse(result["ok"])
        self.assertEqual(result["failures"], ["artifact_json_invalid"])

    def test_malformed_final_seal_json_fails(self):
        self.run_lifecycle()
        self.artifact_file("final_seal.json").write_text("{", encoding="utf-8")
        result = self.verify()

        self.assertFalse(result["ok"])
        self.assertEqual(result["failures"], ["artifact_json_invalid"])

    def test_invalid_utf8_patch_body_fails(self):
        self.run_lifecycle()
        self.artifact_file("patch_body.txt").write_bytes(b"\xff")
        result = self.verify()

        self.assertFalse(result["ok"])
        self.assertEqual(result["failures"], ["artifact_text_invalid"])

    def test_invalid_utf8_preimage_fails(self):
        self.run_lifecycle()
        self.artifact_file("preimage.txt").write_bytes(b"\xff")
        result = self.verify()

        self.assertFalse(result["ok"])
        self.assertEqual(result["failures"], ["artifact_text_invalid"])

    def test_unsafe_patch_id_rejected(self):
        self.run_lifecycle()
        result = self.verify(patch_id="bad/id")

        self.assertFalse(result["ok"])
        self.assertEqual(result["failures"], ["patch_id_invalid"])
        self.assertIsNone(result["patch_id"])

    def test_too_long_patch_id_rejected(self):
        self.run_lifecycle()
        result = self.verify(patch_id="p" * 129)

        self.assertFalse(result["ok"])
        self.assertEqual(result["failures"], ["patch_id_invalid"])
        self.assertIsNone(result["patch_id"])

    def test_artifact_root_outside_repo_rejected(self):
        outside = self.tmp_path / "outside"
        outside.mkdir()
        result = self.verify(artifact_root=outside)

        self.assertFalse(result["ok"])
        self.assertEqual(result["failures"], ["artifact_root_invalid"])

    def test_artifact_root_symlink_rejected(self):
        self.run_lifecycle()
        outside = self.tmp_path / "outside-artifacts"
        outside.mkdir()
        link = self.repo_root / "artifact-link"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"symlink unavailable: {exc}")

        result = self.verify(artifact_root=link)

        self.assertFalse(result["ok"])
        self.assertEqual(result["failures"], ["artifact_root_invalid"])

    def test_artifact_subdir_symlink_rejected(self):
        self.run_lifecycle()
        for path in self.artifact_dir().iterdir():
            path.unlink()
        self.artifact_dir().rmdir()
        outside_patch = self.tmp_path / "outside-patch"
        outside_patch.mkdir()
        try:
            self.artifact_dir().symlink_to(outside_patch, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"symlink unavailable: {exc}")

        result = self.verify()

        self.assertFalse(result["ok"])
        self.assertEqual(result["failures"], ["artifact_subdir_invalid"])

    def test_unexpected_artifact_file_rejected(self):
        self.run_lifecycle()
        self.artifact_file("extra.txt").write_text("unexpected\n", encoding="utf-8")
        result = self.verify()

        self.assertFalse(result["ok"])
        self.assertEqual(result["failures"], ["artifact_file_unexpected"])

    def test_preimage_identity_mismatch_detected(self):
        self.run_lifecycle()
        proposal = self.read_json("proposal.json")
        proposal["preimage_identity"] = "wrong"
        self.write_json("proposal.json", proposal)
        result = self.verify()

        self.assertFalse(result["ok"])
        self.assertIn("preimage_identity_mismatch", result["failures"])
        self.assertIs(result["identity"]["preimage_identity_matches"], False)

    def test_postimage_identity_mismatch_detected(self):
        self.run_lifecycle()
        seal = self.read_json("final_seal.json")
        seal["target"]["postimage_identity"] = "wrong"
        self.write_json("final_seal.json", seal)
        result = self.verify()

        self.assertFalse(result["ok"])
        self.assertIn("postimage_identity_mismatch", result["failures"])
        self.assertIs(result["identity"]["postimage_identity_matches"], False)

    def test_proposal_final_seal_patch_id_mismatch_detected(self):
        self.run_lifecycle()
        seal = self.read_json("final_seal.json")
        seal["replay"]["patch_id"] = "patch-2"
        self.write_json("final_seal.json", seal)
        result = self.verify()

        self.assertFalse(result["ok"])
        self.assertIn("patch_id_mismatch", result["failures"])

    def test_proposal_final_seal_target_mismatch_detected(self):
        self.run_lifecycle()
        seal = self.read_json("final_seal.json")
        seal["target"]["path"] = "other.txt"
        self.write_json("final_seal.json", seal)
        result = self.verify()

        self.assertFalse(result["ok"])
        self.assertIn("target_path_mismatch", result["failures"])

    def test_final_seal_replay_status_mismatch_detected(self):
        self.run_lifecycle()
        seal = self.read_json("final_seal.json")
        seal["status"] = "rolled_back"
        self.write_json("final_seal.json", seal)
        result = self.verify()

        self.assertFalse(result["ok"])
        self.assertIn("final_status_mismatch", result["failures"])

    def test_validation_status_mismatch_detected(self):
        self.run_lifecycle()
        seal = self.read_json("final_seal.json")
        seal["replay"]["validation_status"] = "fail"
        self.write_json("final_seal.json", seal)
        result = self.verify()

        self.assertFalse(result["ok"])
        self.assertIn("validation_status_mismatch", result["failures"])

    def test_rollback_status_mismatch_detected(self):
        self.run_lifecycle()
        seal = self.read_json("final_seal.json")
        seal["replay"]["rollback_status"] = "failed"
        self.write_json("final_seal.json", seal)
        result = self.verify()

        self.assertFalse(result["ok"])
        self.assertIn("rollback_status_mismatch", result["failures"])

    def test_rolled_back_lifecycle_requires_rollback_artifact(self):
        self.run_lifecycle(validation_callable=lambda context: {"ok": False})
        self.artifact_file("rollback.json").unlink()
        result = self.verify()

        self.assertFalse(result["ok"])
        self.assertIn("artifact_file_missing", result["failures"])
        self.assertIs(result["artifacts"]["rollback"], False)

    def test_applied_lifecycle_rejects_rollback_artifact(self):
        self.run_lifecycle()
        rollback = {
            "artifact_type": "single_file_patch_rollback",
            "attempted": True,
            "ok": True,
            "reason_code": "rollback_succeeded",
            "json_safe": True,
        }
        self.write_json("rollback.json", rollback)
        result = self.verify()

        self.assertFalse(result["ok"])
        self.assertIn("artifact_file_unexpected", result["failures"])
        self.assertIs(result["artifacts"]["rollback"], True)

    def test_malformed_rollback_json_fails(self):
        self.run_lifecycle(validation_callable=lambda context: {"ok": False})
        self.artifact_file("rollback.json").write_text("{", encoding="utf-8")
        result = self.verify()

        self.assertFalse(result["ok"])
        self.assertIn("artifact_json_invalid", result["failures"])

    def test_bounded_json_safe_output(self):
        self.run_lifecycle()
        long_path = "x" * 10000
        proposal = self.read_json("proposal.json")
        proposal["target_path"] = long_path
        self.write_json("proposal.json", proposal)
        seal = self.read_json("final_seal.json")
        seal["target"]["path"] = long_path
        seal["replay"]["target_path"] = long_path
        self.write_json("final_seal.json", seal)

        result = self.verify()
        encoded = json.dumps(result, sort_keys=True, allow_nan=False)

        self.assertTrue(result["ok"])
        self.assertLessEqual(len(result["target_path"]), 4109)
        self.assertNotIn(long_path, encoded)
        self.assertIn('"json_safe": true', encoded)

    def test_no_raw_exception_leakage(self):
        class BadPath:
            def __fspath__(self):
                raise RuntimeError("secret verifier path")

        result = self.verify(repo_root=BadPath())
        encoded = json.dumps(result, sort_keys=True)

        self.assertFalse(result["ok"])
        self.assertEqual(result["failures"], ["repo_root_invalid"])
        self.assertNotIn("secret verifier path", encoded)
        self.assertNotIn("RuntimeError", encoded)

    def test_deterministic_failure_ordering(self):
        self.run_lifecycle()
        self.artifact_file("proposal.json").unlink()
        self.artifact_file("extra.txt").write_text("unexpected\n", encoding="utf-8")
        result = self.verify()

        self.assertEqual(
            result["failures"],
            ["artifact_file_unexpected", "artifact_file_missing"],
        )

    def test_manifest_defensive_copy(self):
        manifest = single_file_lifecycle_replay_verifier_manifest()
        manifest["service_calls_authorized"] = True

        self.assertIs(
            single_file_lifecycle_replay_verifier_manifest()[
                "service_calls_authorized"
            ],
            False,
        )

    def test_import_boundary(self):
        module_path = (
            Path(__file__).resolve().parents[2]
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

    def test_no_service_repository_uow_db_executor_imports(self):
        module_path = (
            Path(__file__).resolve().parents[2]
            / "kernel/lifecycle/single_file_lifecycle_replay_verifier.py"
        )
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
        forbidden = ("kernel.services", "kernel.stores", "sqlite3", "executor")

        self.assertFalse(
            [name for name in imported if any(token in name for token in forbidden)]
        )

    def test_no_subprocess_network_time_datetime_imports(self):
        module_path = (
            Path(__file__).resolve().parents[2]
            / "kernel/lifecycle/single_file_lifecycle_replay_verifier.py"
        )
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
        forbidden = (
            "subprocess",
            "socket",
            "urllib",
            "requests",
            "httpx",
            "time",
            "datetime",
            "threading",
            "asyncio",
            "hmac",
            "secrets",
            "inspect",
            "importlib",
        )

        self.assertFalse(
            [name for name in imported if any(token in name for token in forbidden)]
        )

    def test_no_mutation_of_artifacts_during_verification(self):
        self.run_lifecycle()
        before = self.artifact_snapshot()
        self.verify()

        self.assertEqual(self.artifact_snapshot(), before)

    def test_no_mutation_of_target_during_verification(self):
        self.run_lifecycle()
        before = self.target.read_bytes()
        self.verify()

        self.assertEqual(self.target.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
