import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kernel.capabilities.github_capability_intake_packet import (
    GITHUB_CAPABILITY_INTAKE_ARTIFACT_INDEX_FILE,
    GITHUB_CAPABILITY_INTAKE_ARTIFACT_INDEX_MANIFEST_FILE,
    GITHUB_CAPABILITY_INTAKE_PACKET_CHECKLIST_FILE,
    GITHUB_CAPABILITY_INTAKE_PACKET_FILE,
    GITHUB_CAPABILITY_INTAKE_PACKET_MANIFEST_FILE,
    GITHUB_CAPABILITY_INTAKE_PACKET_SUMMARY_FILE,
    NO_SCOPE_FALSE_FIELDS,
    build_github_capability_intake_packet,
)
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.task_graph import run_local_task_graph_fixture


OUTPUT_FILES = (
    GITHUB_CAPABILITY_INTAKE_PACKET_FILE,
    GITHUB_CAPABILITY_INTAKE_PACKET_MANIFEST_FILE,
    GITHUB_CAPABILITY_INTAKE_PACKET_SUMMARY_FILE,
    GITHUB_CAPABILITY_INTAKE_PACKET_CHECKLIST_FILE,
    GITHUB_CAPABILITY_INTAKE_ARTIFACT_INDEX_FILE,
    GITHUB_CAPABILITY_INTAKE_ARTIFACT_INDEX_MANIFEST_FILE,
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class GitHubCapabilityIntakePacketTests(unittest.TestCase):
    def workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        output_dir = root / "output"
        output_dir.mkdir()
        manifest_path = root / "candidate_manifest.json"
        write_json_atomically(manifest_path, self.valid_manifest())
        return root, manifest_path, output_dir

    def valid_manifest(self, **overrides):
        payload = {
            "candidate_type": "github_capability_candidate_v1",
            "candidate_id": "candidate-001",
            "candidate_name": "Useful GitHub Worker",
            "repo_url": "https://github.com/example/useful-worker",
            "repo_full_name": "example/useful-worker",
            "default_branch": "main",
            "source_origin": "manual",
            "intended_use": "worker_adapter",
            "capability_domains": ["github_automation"],
            "declared_license": "unknown",
            "declared_runtime_languages": ["Python"],
            "declared_external_services": [],
            "declared_install_commands": [],
            "declared_run_commands": [],
            "declared_network_requirements": [],
            "declared_secret_requirements": [],
            "declared_file_system_permissions": [],
            "declared_risks": [],
            "user_value_hypothesis": "It may provide useful automation patterns.",
            "integration_hypothesis": "Review first, then consider sandbox smoke.",
            "evidence_notes": "Provided manually by a user.",
        }
        payload.update(overrides)
        return payload

    def write_manifest(self, path, **overrides):
        write_json_atomically(path, self.valid_manifest(**overrides))
        return path

    def build(self, manifest_path, output_dir, **kwargs):
        return build_github_capability_intake_packet(
            manifest_path,
            output_dir,
            kwargs.pop("intake_id", "intake-001"),
            project_id=kwargs.pop("project_id", "project-001"),
            reviewer_id=kwargs.pop("reviewer_id", "reviewer-001"),
            operator_notes=kwargs.pop("operator_notes", "review this candidate"),
            **kwargs,
        )

    def assert_output_files_exist(self, output_dir):
        for file_name in OUTPUT_FILES:
            self.assertTrue((output_dir / file_name).exists(), file_name)

    def assert_no_artifacts(self, output_dir):
        if not output_dir.exists():
            return
        for file_name in OUTPUT_FILES:
            self.assertFalse((output_dir / file_name).exists(), file_name)

    def assert_no_scope_false(self, payload):
        for field_name in NO_SCOPE_FALSE_FIELDS:
            self.assertIn(field_name, payload)
            self.assertFalse(payload[field_name], field_name)

    def make_candidate_repo(self, root):
        repo = root / "candidate-repo"
        repo.mkdir()
        return repo

    def test_valid_manifest_without_candidate_repo_dir_creates_ready_intake_packet(self):
        _root, manifest_path, output_dir = self.workspace()

        result = self.build(manifest_path, output_dir)
        packet = read_json(result.packet_path)
        manifest = read_json(result.packet_manifest_path)

        self.assertTrue(result.complete)
        self.assertEqual(packet["intake_status"], "github_capability_intake_packet_ready")
        self.assertEqual(packet["intake_decision"], "submit_github_capability_for_human_review")
        self.assertFalse(packet["candidate_repo_dir_provided"])
        self.assertEqual(packet["local_repo_evidence_file_count"], 0)
        self.assertEqual(manifest["candidate_manifest_sha256"], packet["candidate_manifest_sha256"])
        self.assert_output_files_exist(output_dir)

    def test_valid_manifest_with_bounded_local_repo_evidence_creates_ready_packet(self):
        root, manifest_path, output_dir = self.workspace()
        repo = self.make_candidate_repo(root)
        (repo / "README.md").write_text("readme\n", encoding="utf-8")
        (repo / "package.json").write_text('{"scripts":{}}\n', encoding="utf-8")
        workflows = repo / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci.yml").write_text("name: ci\n", encoding="utf-8")

        result = self.build(manifest_path, output_dir, candidate_repo_dir=repo)
        packet = read_json(result.packet_path)
        rels = [record["relative_path"] for record in packet["local_repo_evidence_files"]]

        self.assertTrue(result.complete)
        self.assertEqual(packet["local_repo_evidence_file_count"], 3)
        self.assertEqual(rels, [".github/workflows/ci.yml", "README.md", "package.json"])
        self.assertGreater(packet["local_repo_evidence_total_bytes"], 0)

    def test_reads_only_allowlisted_files(self):
        root, manifest_path, output_dir = self.workspace()
        repo = self.make_candidate_repo(root)
        (repo / "README").write_text("allowed\n", encoding="utf-8")
        (repo / "notes.md").write_text("not allowlisted\n", encoding="utf-8")

        result = self.build(manifest_path, output_dir, candidate_repo_dir=repo)
        packet = read_json(result.packet_path)
        rels = [record["relative_path"] for record in packet["local_repo_evidence_files"]]

        self.assertEqual(rels, ["README"])

    def test_does_not_recursively_scan_arbitrary_repo_files(self):
        root, manifest_path, output_dir = self.workspace()
        repo = self.make_candidate_repo(root)
        nested = repo / "nested"
        nested.mkdir()
        (nested / "README.md").write_text("nested readme\n", encoding="utf-8")
        (repo / "README.md").write_text("root readme\n", encoding="utf-8")

        result = self.build(manifest_path, output_dir, candidate_repo_dir=repo)
        packet = read_json(result.packet_path)
        rels = [record["relative_path"] for record in packet["local_repo_evidence_files"]]

        self.assertEqual(rels, ["README.md"])

    def test_does_not_read_non_allowlisted_files(self):
        root, manifest_path, output_dir = self.workspace()
        repo = self.make_candidate_repo(root)
        (repo / "README.md").write_text("allowed\n", encoding="utf-8")
        (repo / "secret.txt").write_text("DO_NOT_READ_THIS\n", encoding="utf-8")

        result = self.build(manifest_path, output_dir, candidate_repo_dir=repo)
        packet_text = result.packet_path.read_text(encoding="utf-8")

        self.assertNotIn("secret.txt", packet_text)
        self.assertNotIn("DO_NOT_READ_THIS", packet_text)

    def test_output_contains_all_anti_execution_and_adoption_false_fields(self):
        _root, manifest_path, output_dir = self.workspace()

        result = self.build(manifest_path, output_dir)
        packet = read_json(result.packet_path)

        self.assert_no_scope_false(result.payload)
        self.assert_no_scope_false(packet)

    def test_candidate_manifest_missing_blocks_with_no_artifacts(self):
        root, _manifest_path, output_dir = self.workspace()

        result = self.build(root / "missing.json", output_dir)

        self.assertFalse(result.complete)
        self.assertEqual(result.payload["failure_stage"], "preflight_candidate_manifest")
        self.assert_no_artifacts(output_dir)

    def test_candidate_manifest_symlink_blocks_with_no_artifacts(self):
        root, manifest_path, output_dir = self.workspace()
        link = root / "manifest-link.json"
        link.symlink_to(manifest_path)

        result = self.build(link, output_dir)

        self.assertFalse(result.complete)
        self.assert_no_artifacts(output_dir)

    def test_candidate_manifest_malformed_json_blocks_with_no_artifacts(self):
        root, _manifest_path, output_dir = self.workspace()
        bad_manifest = root / "bad.json"
        bad_manifest.write_text("{bad json", encoding="utf-8")

        result = self.build(bad_manifest, output_dir)

        self.assertFalse(result.complete)
        self.assert_no_artifacts(output_dir)

    def test_candidate_manifest_wrong_candidate_type_blocks_with_no_artifacts(self):
        root, _manifest_path, output_dir = self.workspace()
        bad_manifest = self.write_manifest(root / "bad-type.json", candidate_type="wrong")

        result = self.build(bad_manifest, output_dir)

        self.assertFalse(result.complete)
        self.assert_no_artifacts(output_dir)

    def test_candidate_manifest_missing_required_fields_blocks_with_no_artifacts(self):
        root, _manifest_path, output_dir = self.workspace()
        payload = self.valid_manifest()
        payload.pop("candidate_name")
        bad_manifest = root / "missing-field.json"
        write_json_atomically(bad_manifest, payload)

        result = self.build(bad_manifest, output_dir)

        self.assertFalse(result.complete)
        self.assert_no_artifacts(output_dir)

    def test_invalid_repo_full_name_blocks(self):
        root, _manifest_path, output_dir = self.workspace()
        bad_manifest = self.write_manifest(root / "bad-repo.json", repo_full_name="example")

        result = self.build(bad_manifest, output_dir)

        self.assertFalse(result.complete)
        self.assert_no_artifacts(output_dir)

    def test_empty_capability_domains_blocks(self):
        root, _manifest_path, output_dir = self.workspace()
        bad_manifest = self.write_manifest(root / "bad-domain.json", capability_domains=[])

        result = self.build(bad_manifest, output_dir)

        self.assertFalse(result.complete)
        self.assert_no_artifacts(output_dir)

    def test_invalid_intended_use_blocks(self):
        root, _manifest_path, output_dir = self.workspace()
        bad_manifest = self.write_manifest(root / "bad-use.json", intended_use="everything")

        result = self.build(bad_manifest, output_dir)

        self.assertFalse(result.complete)
        self.assert_no_artifacts(output_dir)

    def test_output_dir_missing_returns_structured_failure_and_writes_no_artifacts(self):
        root, manifest_path, _output_dir = self.workspace()
        missing_output = root / "missing-output"

        result = self.build(manifest_path, missing_output)

        self.assertFalse(result.complete)
        self.assertEqual(result.payload["failure_stage"], "preflight_output_dir")
        self.assert_no_artifacts(missing_output)

    def test_existing_output_file_blocks_with_no_overwrite(self):
        _root, manifest_path, output_dir = self.workspace()
        existing = output_dir / GITHUB_CAPABILITY_INTAKE_PACKET_FILE
        existing.write_text("keep me\n", encoding="utf-8")

        result = self.build(manifest_path, output_dir)

        self.assertFalse(result.complete)
        self.assertEqual(existing.read_text(encoding="utf-8"), "keep me\n")
        for file_name in OUTPUT_FILES:
            if file_name != GITHUB_CAPABILITY_INTAKE_PACKET_FILE:
                self.assertFalse((output_dir / file_name).exists(), file_name)

    def test_output_symlink_collision_blocks(self):
        root, manifest_path, output_dir = self.workspace()
        target = root / "target.json"
        link = output_dir / GITHUB_CAPABILITY_INTAKE_PACKET_FILE
        link.symlink_to(target)

        result = self.build(manifest_path, output_dir)

        self.assertFalse(result.complete)
        for file_name in OUTPUT_FILES:
            if file_name != GITHUB_CAPABILITY_INTAKE_PACKET_FILE:
                self.assertFalse((output_dir / file_name).exists(), file_name)

    def test_candidate_repo_dir_symlink_blocks(self):
        root, manifest_path, output_dir = self.workspace()
        repo = self.make_candidate_repo(root)
        link = root / "repo-link"
        link.symlink_to(repo)

        result = self.build(manifest_path, output_dir, candidate_repo_dir=link)

        self.assertFalse(result.complete)
        self.assert_no_artifacts(output_dir)

    def test_candidate_repo_dir_output_dir_overlap_blocks(self):
        root, manifest_path, _output_dir = self.workspace()
        repo = self.make_candidate_repo(root)
        output_inside_repo = repo / "output"
        output_inside_repo.mkdir()

        result = self.build(manifest_path, output_inside_repo, candidate_repo_dir=repo)

        self.assertFalse(result.complete)
        self.assert_no_artifacts(output_inside_repo)

    def test_local_repo_evidence_file_symlink_blocks(self):
        root, manifest_path, output_dir = self.workspace()
        repo = self.make_candidate_repo(root)
        target = root / "real-readme.md"
        target.write_text("real\n", encoding="utf-8")
        (repo / "README.md").symlink_to(target)

        result = self.build(manifest_path, output_dir, candidate_repo_dir=repo)

        self.assertFalse(result.complete)
        self.assertTrue(result.payload["local_repo_symlink_evidence_detected"])
        self.assert_no_artifacts(output_dir)

    def test_oversize_evidence_file_is_skipped_and_not_read_fully(self):
        root, manifest_path, output_dir = self.workspace()
        repo = self.make_candidate_repo(root)
        (repo / "README.md").write_bytes(b"x" * 262145)

        result = self.build(manifest_path, output_dir, candidate_repo_dir=repo)
        packet = read_json(result.packet_path)

        self.assertTrue(result.complete)
        self.assertEqual(packet["local_repo_evidence_file_count"], 0)
        self.assertEqual(packet["local_repo_evidence_total_bytes"], 0)
        self.assertEqual(
            packet["local_repo_evidence_skipped_files"][0]["reason"],
            "skipped_oversize",
        )

    def test_unreadable_evidence_file_is_skipped_unreadable_and_does_not_crash(self):
        root, manifest_path, output_dir = self.workspace()
        repo = self.make_candidate_repo(root)
        (repo / "README.md").write_text("unreadable\n", encoding="utf-8")

        with patch(
            "kernel.capabilities.github_capability_intake_packet._read_bounded_bytes",
            side_effect=OSError("permission denied"),
        ):
            result = self.build(manifest_path, output_dir, candidate_repo_dir=repo)
        packet = read_json(result.packet_path)

        self.assertTrue(result.complete)
        self.assertEqual(packet["local_repo_evidence_file_count"], 0)
        self.assertEqual(
            packet["local_repo_evidence_skipped_files"][0]["reason"],
            "skipped_unreadable",
        )

    def test_evidence_file_ordering_is_deterministic(self):
        root, manifest_path, output_dir = self.workspace()
        repo = self.make_candidate_repo(root)
        (repo / "README.md").write_text("readme\n", encoding="utf-8")
        (repo / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
        workflows = repo / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "b.yaml").write_text("name: b\n", encoding="utf-8")
        (workflows / "a.yml").write_text("name: a\n", encoding="utf-8")

        result = self.build(manifest_path, output_dir, candidate_repo_dir=repo)
        packet = read_json(result.packet_path)
        rels = [record["relative_path"] for record in packet["local_repo_evidence_files"]]

        self.assertEqual(
            rels,
            [
                ".github/workflows/a.yml",
                ".github/workflows/b.yaml",
                "Dockerfile",
                "README.md",
            ],
        )

    def test_risk_classifications_are_deterministic(self):
        root, _manifest_path, output_dir = self.workspace()
        manifest_path = self.write_manifest(
            root / "risky.json",
            declared_license="MIT",
            declared_install_commands=["pip install ."],
            declared_run_commands=["python main.py"],
            declared_network_requirements=["api.github.com"],
            declared_secret_requirements=["GITHUB_TOKEN"],
            declared_file_system_permissions=["write cache"],
        )

        result = self.build(manifest_path, output_dir)
        packet = read_json(result.packet_path)

        self.assertEqual(packet["declared_network_risk"], "network_required")
        self.assertEqual(packet["declared_secret_risk"], "secrets_required")
        self.assertEqual(
            packet["declared_filesystem_risk"],
            "filesystem_permissions_required",
        )
        self.assertEqual(packet["declared_execution_risk"], "run_commands_declared")
        self.assertEqual(packet["declared_installation_risk"], "install_commands_declared")
        self.assertEqual(
            packet["declared_license_risk"],
            "license_declared_requires_review",
        )

    def test_declared_license_unknown_requires_review_and_no_adapter_generation(self):
        _root, manifest_path, output_dir = self.workspace()

        result = self.build(manifest_path, output_dir)
        packet = read_json(result.packet_path)

        self.assertTrue(packet["license_review_required"])
        self.assertEqual(
            packet["declared_license_risk"],
            "license_unknown_requires_review",
        )
        self.assertFalse(packet["adapter_generation_allowed"])

    def test_declared_license_present_still_requires_license_review(self):
        root, _manifest_path, output_dir = self.workspace()
        manifest_path = self.write_manifest(root / "license.json", declared_license="Apache-2.0")

        result = self.build(manifest_path, output_dir)
        packet = read_json(result.packet_path)

        self.assertTrue(packet["license_review_required"])
        self.assertEqual(
            packet["declared_license_risk"],
            "license_declared_requires_review",
        )

    def write_graph(self, graph_path, manifest_path, node_output):
        write_json_atomically(
            graph_path,
            {
                "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
                "graph_id": "github-intake-graph",
                "execution_mode": "fixture_execution",
                "authority": "non_authority",
                "required_human_approval": True,
                "nodes": [
                    {
                        "node_id": "github_intake",
                        "adapter_id": "github_capability_intake_packet",
                        "capability": "launch_github_capability_intake_packet",
                        "execution_mode": "fixture",
                        "depends_on": [],
                        "approval_checkpoint_required": True,
                        "inputs": {
                            "candidate_manifest": manifest_path.as_posix(),
                            "output_dir": node_output.as_posix(),
                            "intake_id": "graph-intake-001",
                            "project_id": "project-001",
                            "reviewer_id": "reviewer-001",
                            "operator_notes": "graph smoke",
                        },
                    }
                ],
            },
        )

    def test_task_graph_node_writes_artifact_outputs(self):
        root, manifest_path, _output_dir = self.workspace()
        node_output = root / "node-output"
        graph_output = root / "graph-output"
        node_output.mkdir()
        graph_output.mkdir()
        graph_path = root / "graph.json"
        self.write_graph(graph_path, manifest_path, node_output)

        result = run_local_task_graph_fixture(graph_path, graph_output)
        execution = read_json(result.execution_manifest_path)
        artifact_outputs = read_json(result.artifact_outputs_manifest_path)
        node = execution["nodes"][0]
        roles = {
            artifact["artifact_role"]
            for artifact in artifact_outputs["artifacts"]
            if artifact["node_id"] == "github_intake"
        }

        self.assertTrue(result.success)
        self.assertEqual(node["status"], "completed")
        self.assertTrue(Path(node["github_capability_intake_packet_path"]).exists())
        self.assertIn("github_capability_intake_packet", roles)
        self.assertIn("github_capability_intake_packet_manifest", roles)
        self.assertIn("artifact_index", roles)

    def test_no_scope_boundary_fields_remain_false_across_outputs_and_task_graph(self):
        root, manifest_path, output_dir = self.workspace()
        result = self.build(manifest_path, output_dir)
        packet = read_json(result.packet_path)
        manifest = read_json(result.packet_manifest_path)
        artifact_index = read_json(result.artifact_index_path)
        artifact_index_manifest = read_json(result.artifact_index_manifest_path)
        for payload in (
            result.payload,
            packet,
            manifest,
            artifact_index,
            artifact_index_manifest,
        ):
            self.assert_no_scope_false(payload)

        node_output = root / "node-output"
        graph_output = root / "graph-output"
        node_output.mkdir()
        graph_output.mkdir()
        graph_path = root / "graph.json"
        self.write_graph(graph_path, manifest_path, node_output)
        graph_result = run_local_task_graph_fixture(graph_path, graph_output)
        node = read_json(graph_result.execution_manifest_path)["nodes"][0]
        self.assert_no_scope_false(node)

    def test_builder_structured_failure_writes_no_artifacts(self):
        root, _manifest_path, output_dir = self.workspace()
        bad_manifest = self.write_manifest(root / "bad.json", intended_use="bad")

        result = self.build(bad_manifest, output_dir)

        self.assertFalse(result.complete)
        self.assertFalse(result.payload["artifacts_written"])
        self.assert_no_artifacts(output_dir)

    def test_full_cli_smoke_path_works(self):
        _root, manifest_path, output_dir = self.workspace()

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(
                [
                    "launch-github-capability-intake-packet",
                    "--candidate-manifest",
                    manifest_path.as_posix(),
                    "--output-dir",
                    output_dir.as_posix(),
                    "--intake-id",
                    "cli-intake-001",
                    "--project-id",
                    "project-001",
                ]
            )
        payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["complete"])
        self.assertTrue(Path(payload["github_capability_intake_packet_path"]).exists())
        self.assertEqual(payload["intake_id"], "cli-intake-001")

    def test_artifact_index_includes_only_generated_intake_artifacts(self):
        root, manifest_path, output_dir = self.workspace()
        repo = self.make_candidate_repo(root)
        (repo / "README.md").write_text("candidate evidence\n", encoding="utf-8")

        result = self.build(manifest_path, output_dir, candidate_repo_dir=repo)
        artifact_index = read_json(result.artifact_index_path)
        relative_paths = {
            entry["relative_path"] for entry in artifact_index["entries"]
        }

        self.assertEqual(
            relative_paths,
            {
                GITHUB_CAPABILITY_INTAKE_PACKET_FILE,
                GITHUB_CAPABILITY_INTAKE_PACKET_MANIFEST_FILE,
                GITHUB_CAPABILITY_INTAKE_PACKET_SUMMARY_FILE,
                GITHUB_CAPABILITY_INTAKE_PACKET_CHECKLIST_FILE,
            },
        )
        self.assertNotIn("README.md", relative_paths)
        self.assertFalse(artifact_index["candidate_repo_evidence_files_indexed"])


if __name__ == "__main__":
    unittest.main()
