import ast
import json
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

from kernel.lifecycle import single_file_patch_lifecycle as lifecycle_module
from kernel.lifecycle.single_file_patch_lifecycle import (
    run_single_file_patch_lifecycle,
    single_file_patch_lifecycle_manifest,
)


def _identity(text):
    return sha256(text.encode("utf-8")).hexdigest()


class SingleFilePatchLifecycleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.tmp.name) / "repo"
        self.repo_root.mkdir()
        self.target = self.repo_root / "target.txt"
        self.target.write_text("before\n", encoding="utf-8")
        self.artifact_root = self.repo_root / "artifacts"
        self.proposal = {
            "proposal_id": "proposal-1",
            "patch_id": "patch-1",
            "target_path": "target.txt",
        }
        self.approval = {
            "approved": True,
            "proposal_id": "proposal-1",
            "patch_id": "patch-1",
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

    def artifact_path(self, result, key):
        value = result["artifacts"][key]
        self.assertIsInstance(value, str)
        return self.repo_root / value

    def test_happy_path_applies_one_file(self):
        result = self.run_lifecycle()
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "applied")
        self.assertEqual(self.target.read_text(encoding="utf-8"), "after\n")

    def test_artifacts_are_persisted(self):
        result = self.run_lifecycle()
        for key in (
            "proposal",
            "patch_body",
            "preimage",
            "validation_result",
            "final_seal",
        ):
            self.assertTrue(self.artifact_path(result, key).exists(), key)

    def test_final_seal_contains_preimage_and_postimage_identity(self):
        result = self.run_lifecycle()
        seal = json.loads(self.artifact_path(result, "final_seal").read_text())
        self.assertEqual(seal["target"]["preimage_identity"], _identity("before\n"))
        self.assertEqual(seal["target"]["postimage_identity"], _identity("after\n"))

    def test_replay_summary_reconstructs_lifecycle(self):
        result = self.run_lifecycle()
        replay = result["replay"]
        self.assertEqual(replay["proposal_id"], "proposal-1")
        self.assertEqual(replay["patch_id"], "patch-1")
        self.assertEqual(replay["target_path"], "target.txt")
        self.assertEqual(replay["validation_status"], "pass")
        self.assertEqual(replay["approval_status"], "approved")
        self.assertEqual(replay["rollback_status"], "not_attempted")
        self.assertEqual(replay["final_status"], "applied")
        self.assertEqual(len(replay["artifact_paths"]), 5)

    def test_final_seal_status_matches_returned_status(self):
        result = self.run_lifecycle()
        seal = json.loads(self.artifact_path(result, "final_seal").read_text())
        self.assertEqual(seal["replay"]["final_status"], result["status"])

    def test_approval_required(self):
        result = self.run_lifecycle(approval={})
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason_code"], "approval_invalid")

    def test_approval_bool_as_int_rejected(self):
        approval = dict(self.approval)
        approval["approved"] = 1
        result = self.run_lifecycle(approval=approval)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason_code"], "approval_not_true")

    def test_approval_false_rejected(self):
        approval = dict(self.approval)
        approval["approved"] = False
        result = self.run_lifecycle(approval=approval)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason_code"], "approval_not_true")

    def test_target_path_mismatch_rejected(self):
        approval = dict(self.approval)
        approval["target_path"] = "other.txt"
        result = self.run_lifecycle(approval=approval)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason_code"], "approval_target_mismatch")

    def test_proposal_target_path_mismatch_rejected_separately(self):
        proposal = dict(self.proposal, target_path="other.txt")
        result = self.run_lifecycle(proposal=proposal)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason_code"], "proposal_target_mismatch")

    def test_proposal_mismatch_rejected(self):
        approval = dict(self.approval)
        approval["proposal_id"] = "proposal-2"
        result = self.run_lifecycle(approval=approval)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason_code"], "approval_proposal_mismatch")

    def test_patch_mismatch_rejected(self):
        approval = dict(self.approval)
        approval["patch_id"] = "patch-2"
        result = self.run_lifecycle(approval=approval)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason_code"], "approval_patch_mismatch")

    def test_unsafe_approval_patch_id_not_echoed(self):
        approval = dict(self.approval)
        approval["patch_id"] = "bad/id"
        result = self.run_lifecycle(approval=approval)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason_code"], "approval_patch_mismatch")
        self.assertIsNone(result["approval"]["patch_id"])
        self.assertNotIn("bad/id", json.dumps(result, sort_keys=True))

    def test_preimage_mismatch_rejected(self):
        approval = dict(self.approval)
        approval["expected_preimage_identity"] = "wrong"
        result = self.run_lifecycle(approval=approval)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason_code"], "preimage_identity_mismatch")

    def test_absolute_target_path_rejected(self):
        result = self.run_lifecycle(target_path=str(self.target))
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason_code"], "target_path_invalid")
        self.assertIsNone(result["target"]["path"])
        self.assertIsNone(result["replay"]["target_path"])
        self.assertNotIn(str(self.tmp.name), json.dumps(result, sort_keys=True))

    def test_traversal_target_path_rejected(self):
        result = self.run_lifecycle(target_path="../target.txt")
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason_code"], "target_path_invalid")
        self.assertIsNone(result["target"]["path"])
        self.assertIsNone(result["replay"]["target_path"])
        self.assertNotIn("../target.txt", json.dumps(result, sort_keys=True))

    def test_windows_separator_target_path_rejected_without_echo(self):
        result = self.run_lifecycle(target_path="nested\\target.txt")
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason_code"], "target_path_invalid")
        self.assertIsNone(result["target"]["path"])
        self.assertIsNone(result["replay"]["target_path"])
        self.assertNotIn("nested\\target.txt", json.dumps(result, sort_keys=True))

    def test_symlink_target_rejected(self):
        link = self.repo_root / "link.txt"
        try:
            link.symlink_to(self.target)
        except OSError as exc:
            self.skipTest(f"symlink unavailable: {exc}")
        proposal = dict(self.proposal, target_path="link.txt")
        approval = dict(self.approval, target_path="link.txt")
        result = self.run_lifecycle(
            target_path="link.txt",
            proposal=proposal,
            approval=approval,
        )
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason_code"], "target_is_symlink")

    def test_missing_target_rejected(self):
        proposal = dict(self.proposal, target_path="missing.txt")
        approval = dict(self.approval, target_path="missing.txt")
        result = self.run_lifecycle(
            target_path="missing.txt",
            proposal=proposal,
            approval=approval,
        )
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason_code"], "target_missing")

    def test_directory_target_rejected(self):
        (self.repo_root / "folder").mkdir()
        proposal = dict(self.proposal, target_path="folder")
        approval = dict(self.approval, target_path="folder")
        result = self.run_lifecycle(
            target_path="folder",
            proposal=proposal,
            approval=approval,
        )
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason_code"], "target_not_file")

    def test_binary_target_rejected(self):
        self.target.write_bytes(b"before\x00after")
        approval = dict(self.approval)
        approval["expected_preimage_identity"] = _identity("before\n")
        result = self.run_lifecycle(approval=approval)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason_code"], "target_not_text")

    def test_unsafe_patch_id_rejected(self):
        proposal = dict(self.proposal, patch_id="bad/id")
        approval = dict(self.approval, patch_id="bad/id")
        result = self.run_lifecycle(proposal=proposal, approval=approval)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason_code"], "patch_id_invalid")

    def test_too_long_proposal_id_rejected(self):
        proposal = dict(self.proposal, proposal_id="p" * 129)
        approval = dict(self.approval, proposal_id="p" * 129)
        result = self.run_lifecycle(proposal=proposal, approval=approval)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason_code"], "proposal_id_invalid")
        self.assertIsNone(result["replay"]["proposal_id"])

    def test_too_long_patch_id_rejected(self):
        patch_id = "p" * 129
        proposal = dict(self.proposal, patch_id=patch_id)
        approval = dict(self.approval, patch_id=patch_id)
        result = self.run_lifecycle(proposal=proposal, approval=approval)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason_code"], "patch_id_invalid")
        self.assertIsNone(result["replay"]["patch_id"])

    def test_returned_identifiers_are_bounded(self):
        result = self.run_lifecycle()
        encoded = json.dumps(result, sort_keys=True)
        self.assertIn('"proposal_id": "proposal-1"', encoded)
        self.assertIn('"patch_id": "patch-1"', encoded)
        self.assertLessEqual(len(result["replay"]["proposal_id"]), 128)
        self.assertLessEqual(len(result["replay"]["patch_id"]), 128)

    def test_multi_file_patch_rejected(self):
        proposal = dict(
            self.proposal,
            target_paths=["target.txt", "other.txt"],
        )
        result = self.run_lifecycle(proposal=proposal)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason_code"], "proposal_invalid")

    def test_artifact_destination_exists_rejected(self):
        (self.artifact_root / "patch-1").mkdir(parents=True)
        result = self.run_lifecycle()
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason_code"], "artifact_destination_exists")

    def test_artifact_write_failure_before_mutation_rejected(self):
        original_write_json = lifecycle_module._write_json

        def fail_proposal_write(path, payload):
            if path.name == "proposal.json":
                raise OSError("secret artifact path")
            original_write_json(path, payload)

        lifecycle_module._write_json = fail_proposal_write
        try:
            result = self.run_lifecycle()
        finally:
            lifecycle_module._write_json = original_write_json

        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason_code"], "artifact_write_failed")
        self.assertEqual(self.target.read_text(encoding="utf-8"), "before\n")
        self.assertNotIn("secret artifact path", json.dumps(result, sort_keys=True))

    def test_validation_callable_required(self):
        result = self.run_lifecycle(validation_callable=None)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason_code"], "validation_callable_invalid")

    def test_validation_result_not_mapping_triggers_rollback(self):
        result = self.run_lifecycle(validation_callable=lambda context: "bad")
        self.assertEqual(result["status"], "rolled_back")
        self.assertEqual(result["validation"]["reason_code"], "validation_result_invalid")
        self.assertEqual(self.target.read_text(encoding="utf-8"), "before\n")

    def test_validation_ok_non_bool_triggers_rollback(self):
        result = self.run_lifecycle(validation_callable=lambda context: {"ok": 1})
        self.assertEqual(result["status"], "rolled_back")
        self.assertEqual(result["validation"]["reason_code"], "validation_result_invalid")
        self.assertEqual(self.target.read_text(encoding="utf-8"), "before\n")

    def test_validation_ok_false_triggers_rollback(self):
        result = self.run_lifecycle(
            validation_callable=lambda context: {
                "ok": False,
                "reason_code": "content_failed",
            }
        )
        self.assertEqual(result["status"], "rolled_back")
        self.assertEqual(result["reason_code"], "validation_failed")
        self.assertEqual(self.target.read_text(encoding="utf-8"), "before\n")

    def test_validation_exception_triggers_rollback(self):
        def validate(_context):
            raise RuntimeError("secret boom")

        result = self.run_lifecycle(validation_callable=validate)
        self.assertEqual(result["status"], "rolled_back")
        self.assertEqual(result["reason_code"], "validation_exception")
        self.assertEqual(self.target.read_text(encoding="utf-8"), "before\n")

    def test_rollback_restores_preimage_after_validation_failure(self):
        result = self.run_lifecycle(validation_callable=lambda context: {"ok": False})
        self.assertEqual(result["rollback"], {"attempted": True, "ok": True})
        self.assertEqual(self.target.read_text(encoding="utf-8"), "before\n")

    def test_rollback_failure_after_validation_failure_is_reported(self):
        original_write_text = lifecycle_module._write_text
        restore_attempts = []
        target_resolved = self.target.resolve(strict=True)

        def fail_restore_once(path, text):
            if path.resolve(strict=False) == target_resolved and text == "before\n":
                restore_attempts.append(path)
                raise OSError("secret rollback path")
            original_write_text(path, text)

        lifecycle_module._write_text = fail_restore_once
        try:
            result = self.run_lifecycle(validation_callable=lambda context: {"ok": False})
        finally:
            lifecycle_module._write_text = original_write_text

        self.assertEqual(result["status"], "rollback_failed")
        self.assertEqual(result["reason_code"], "rollback_failed")
        self.assertIn("rollback_failed", result["failures"])
        self.assertEqual(len(restore_attempts), 1)
        self.assertEqual(self.target.read_text(encoding="utf-8"), "after\n")
        self.assertNotIn("secret rollback path", json.dumps(result, sort_keys=True))

    def test_rollback_result_artifact_recorded(self):
        result = self.run_lifecycle(validation_callable=lambda context: {"ok": False})
        rollback = json.loads(self.artifact_path(result, "rollback").read_text())
        self.assertTrue(rollback["attempted"])
        self.assertTrue(rollback["ok"])

    def test_output_json_safe(self):
        result = self.run_lifecycle()
        encoded = json.dumps(result, sort_keys=True, allow_nan=False)
        self.assertIn('"json_safe": true', encoded)

    def test_utf8_write_identity_matches_final_file_bytes(self):
        content = "after\nsnowman: \u2603\n"
        result = self.run_lifecycle(new_content=content)
        seal = json.loads(self.artifact_path(result, "final_seal").read_text())
        self.assertEqual(
            sha256(self.target.read_bytes()).hexdigest(),
            seal["target"]["postimage_identity"],
        )
        self.assertEqual(self.target.read_bytes(), content.encode("utf-8"))

    def test_output_bounded(self):
        result = self.run_lifecycle(
            validation_callable=lambda context: {
                "ok": True,
                "reason_code": "validation_passed",
                "large": "x" * 100000,
            }
        )
        self.assertLess(len(json.dumps(result, sort_keys=True)), 5000)
        validation_text = self.artifact_path(result, "validation_result").read_text()
        self.assertLess(len(validation_text), 6000)

    def test_no_raw_exception_leakage(self):
        def validate(_context):
            raise RuntimeError("secret boom")

        result = self.run_lifecycle(validation_callable=validate)
        encoded = json.dumps(result, sort_keys=True)
        validation_text = self.artifact_path(result, "validation_result").read_text()
        self.assertNotIn("secret boom", encoded)
        self.assertNotIn("secret boom", validation_text)
        self.assertNotIn("Traceback", validation_text)

    def test_no_raw_callable_leakage(self):
        result = self.run_lifecycle(
            validation_callable=lambda context: {
                "ok": False,
                "callable": lambda value: value,
            }
        )
        encoded = json.dumps(result, sort_keys=True)
        validation_text = self.artifact_path(result, "validation_result").read_text()
        self.assertNotIn("<function", encoded)
        self.assertNotIn("<function", validation_text)

    def test_input_proposal_and_approval_mappings_are_not_mutated(self):
        proposal = dict(self.proposal)
        approval = dict(self.approval)
        original_proposal = dict(proposal)
        original_approval = dict(approval)
        self.run_lifecycle(proposal=proposal, approval=approval)
        self.assertEqual(proposal, original_proposal)
        self.assertEqual(approval, original_approval)

    def test_manifest_defensive_copy(self):
        manifest = single_file_patch_lifecycle_manifest()
        manifest["runtime_authorized"] = True
        self.assertIs(
            single_file_patch_lifecycle_manifest()["runtime_authorized"],
            False,
        )

    def test_module_imports_limited_to_allowed_imports(self):
        module_path = (
            Path(__file__).resolve().parents[2]
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

    def test_no_service_repository_uow_db_executor_imports(self):
        module_path = (
            Path(__file__).resolve().parents[2]
            / "kernel/lifecycle/single_file_patch_lifecycle.py"
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
            / "kernel/lifecycle/single_file_patch_lifecycle.py"
        )
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
        forbidden = ("subprocess", "socket", "urllib", "requests", "httpx", "time", "datetime")
        self.assertFalse(
            [name for name in imported if any(token in name for token in forbidden)]
        )

    def test_target_file_only_mutation_unrelated_file_unchanged(self):
        unrelated = self.repo_root / "unrelated.txt"
        unrelated.write_text("leave me\n", encoding="utf-8")
        self.run_lifecycle()
        self.assertEqual(self.target.read_text(encoding="utf-8"), "after\n")
        self.assertEqual(unrelated.read_text(encoding="utf-8"), "leave me\n")

    def test_artifact_root_outside_repo_rejected(self):
        outside = Path(self.tmp.name) / "outside-artifacts"
        result = self.run_lifecycle(artifact_root=outside)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason_code"], "artifact_root_invalid")

    def test_artifact_root_symlink_rejected_if_feasible(self):
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir()
        link = self.repo_root / "artifact-link"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"symlink unavailable: {exc}")
        result = self.run_lifecycle(artifact_root=link)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason_code"], "artifact_root_invalid")

    def test_failure_before_mutation_leaves_target_unchanged(self):
        result = self.run_lifecycle(validation_callable=None)
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(self.target.read_text(encoding="utf-8"), "before\n")
        self.assertFalse((self.artifact_root / "patch-1").exists())

    def test_make_ci_discovery_compatible(self):
        self.assertTrue(Path(__file__).name.startswith("test_"))
        self.assertIn("tests/tracer_bullet", Path(__file__).as_posix())


if __name__ == "__main__":
    unittest.main()
