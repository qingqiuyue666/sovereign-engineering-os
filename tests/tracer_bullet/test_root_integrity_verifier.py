import json
import tempfile
import unittest
from pathlib import Path

from kernel.bootstrap.root_integrity_verifier import (
    compute_git_blob_sha1_for_path,
    verify_root_integrity,
    write_bootstrap_integrity_report,
)


class RootIntegrityVerifierTests(unittest.TestCase):
    def make_repo(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        (root / "kernel").mkdir()
        (root / "governance" / "root").mkdir(parents=True)
        return root

    def write_file(self, root: Path, rel_path: str, text: str) -> Path:
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def write_manifest(
        self,
        root: Path,
        *,
        critical_files: list[dict[str, object]],
        version: str = "v1",
        manifest_type: str = "seos_root_integrity_manifest_v1",
        hash_algorithm: str = "git_blob_sha1",
    ) -> Path:
        manifest_path = root / "governance" / "root" / "root_manifest_v1.json"
        manifest = {
            "manifest_type": manifest_type,
            "version": version,
            "hash_algorithm": hash_algorithm,
            "critical_files": critical_files,
            "runtime_execution_performed": False,
            "network_accessed": False,
            "secret_value_read": False,
            "secret_value_persisted": False,
            "required_human_approval": True,
        }
        manifest_path.write_text(
            json.dumps(manifest, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        return manifest_path

    def test_clean_manifest_allows_trusted_startup(self):
        root = self.make_repo()
        file_path = self.write_file(root, "kernel/policy.py", "POLICY = 'locked'\n")
        manifest_path = self.write_manifest(
            root,
            critical_files=[
                {
                    "path": "kernel/policy.py",
                    "git_blob_sha1": compute_git_blob_sha1_for_path(file_path),
                }
            ],
        )

        result = verify_root_integrity(root, manifest_path)

        self.assertTrue(result.complete, result.report["failures"])
        self.assertTrue(result.trusted_startup_allowed)
        self.assertFalse(result.seed_recovery_required)
        self.assertFalse(result.runtime_execution_performed)
        self.assertFalse(result.network_accessed)
        self.assertFalse(result.secret_value_read)
        self.assertEqual(result.report["verified_file_count"], 1)

    def test_modified_critical_file_fails_closed(self):
        root = self.make_repo()
        file_path = self.write_file(root, "kernel/policy.py", "POLICY = 'locked'\n")
        manifest_path = self.write_manifest(
            root,
            critical_files=[
                {
                    "path": "kernel/policy.py",
                    "git_blob_sha1": compute_git_blob_sha1_for_path(file_path),
                }
            ],
        )
        file_path.write_text("POLICY = 'modified'\n", encoding="utf-8")

        result = verify_root_integrity(root, manifest_path)

        self.assertFalse(result.complete)
        self.assertFalse(result.trusted_startup_allowed)
        self.assertTrue(result.seed_recovery_required)
        self.assertIn("critical_file_hash_mismatch:kernel/policy.py", result.report["failures"])
        self.assertEqual(result.report["next_allowed_action"], "read_only_seed_recovery_required")

    def test_missing_critical_file_fails_closed(self):
        root = self.make_repo()
        manifest_path = self.write_manifest(
            root,
            critical_files=[
                {
                    "path": "kernel/missing.py",
                    "git_blob_sha1": "a" * 40,
                }
            ],
        )

        result = verify_root_integrity(root, manifest_path)

        self.assertFalse(result.complete)
        self.assertIn("critical_file_missing:kernel/missing.py", result.report["failures"])

    def test_malformed_manifest_fails_closed(self):
        root = self.make_repo()
        manifest_path = root / "governance" / "root" / "root_manifest_v1.json"
        manifest_path.write_text("{not-json", encoding="utf-8")

        result = verify_root_integrity(root, manifest_path)

        self.assertFalse(result.complete)
        self.assertTrue(result.seed_recovery_required)
        self.assertIn("root_manifest_malformed_json", result.report["failures"])

    def test_unknown_manifest_version_fails_closed(self):
        root = self.make_repo()
        file_path = self.write_file(root, "kernel/policy.py", "POLICY = 'locked'\n")
        manifest_path = self.write_manifest(
            root,
            version="v999",
            critical_files=[
                {
                    "path": "kernel/policy.py",
                    "git_blob_sha1": compute_git_blob_sha1_for_path(file_path),
                }
            ],
        )

        result = verify_root_integrity(root, manifest_path)

        self.assertFalse(result.complete)
        self.assertIn("root_manifest_version_unsupported", result.report["failures"])

    def test_path_escape_is_rejected(self):
        root = self.make_repo()
        manifest_path = self.write_manifest(
            root,
            critical_files=[
                {
                    "path": "../outside.py",
                    "git_blob_sha1": "a" * 40,
                }
            ],
        )

        result = verify_root_integrity(root, manifest_path)

        self.assertFalse(result.complete)
        self.assertIn("critical_file_path_invalid:../outside.py", result.report["failures"])

    def test_write_report_refuses_overwrite_and_does_not_repair_or_execute(self):
        root = self.make_repo()
        file_path = self.write_file(root, "kernel/policy.py", "POLICY = 'locked'\n")
        manifest_path = self.write_manifest(
            root,
            critical_files=[
                {
                    "path": "kernel/policy.py",
                    "git_blob_sha1": compute_git_blob_sha1_for_path(file_path),
                }
            ],
        )
        report_path = root / "bootstrap_integrity_report.json"

        result = write_bootstrap_integrity_report(
            repo_root=root,
            manifest_path=manifest_path,
            output_path=report_path,
        )

        self.assertTrue(result.complete)
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertFalse(payload["runtime_execution_performed"])
        self.assertFalse(payload["network_accessed"])
        self.assertFalse(payload["secret_value_read"])
        self.assertFalse(payload["file_mutation_performed"])
        self.assertFalse(payload["automatic_repair_performed"])
        with self.assertRaisesRegex(ValueError, "already exists"):
            write_bootstrap_integrity_report(
                repo_root=root,
                manifest_path=manifest_path,
                output_path=report_path,
            )

    def test_repository_root_manifest_verifies_current_branch(self):
        result = verify_root_integrity(Path("."))

        self.assertTrue(result.complete, result.report["failures"])
        self.assertTrue(result.trusted_startup_allowed)
        self.assertFalse(result.runtime_execution_performed)
        self.assertFalse(result.network_accessed)
        self.assertFalse(result.secret_value_read)


if __name__ == "__main__":
    unittest.main()
