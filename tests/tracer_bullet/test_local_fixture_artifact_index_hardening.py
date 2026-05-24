import json
import tempfile
import unittest
from pathlib import Path, PurePosixPath

from kernel.capabilities.admission_gated_local_adapter_registry_promotion import (
    ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_DENIED_SCOPE,
)
from kernel.capabilities.local_fixture_adapter_dry_run_invocation_plan import (
    LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_REVIEW_ATTESTATION,
    run_local_fixture_adapter_dry_run_invocation_plan,
)
from kernel.capabilities.local_fixture_adapter_execution_gate_plan import (
    LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_REVIEW_ATTESTATION,
    run_local_fixture_adapter_execution_gate_plan,
)
from kernel.capabilities.local_fixture_adapter_usage_receipt import (
    LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_DENIED_ADMISSION_FIELDS,
    LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_FORBIDDEN_PERFORMED_FIELDS,
    LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_REVIEW_ATTESTATION,
    run_local_fixture_adapter_usage_receipt,
)
from kernel.capabilities.local_fixture_human_approval_artifact import (
    LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ATTESTATION,
    run_local_fixture_human_approval_artifact,
)
from kernel.capabilities.local_fixture_runner_contract_draft import (
    LOCAL_FIXTURE_RUNNER_CONTRACT_DRAFT_REVIEW_ATTESTATION,
    run_local_fixture_runner_contract_draft,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically


FORBIDDEN_CONTENT_MARKERS = (
    "<!doctype html>",
    "candidate repository source",
    "candidate repo source",
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class LocalFixtureArtifactIndexHardeningTests(unittest.TestCase):
    def make_workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        dirs = {
            name: root / name
            for name in (
                "promotion-output",
                "usage-output",
                "dry-run-output",
                "execution-gate-output",
                "approval-output",
                "runner-contract-output",
            )
        }
        for path in dirs.values():
            path.mkdir()

        fixture_path = dirs["usage-output"] / "fixture.html"
        fixture_path.write_text(
            "<!doctype html><title>fixture</title>\n",
            encoding="utf-8",
        )
        promotion_result_path = (
            dirs["promotion-output"]
            / "admission_gated_local_adapter_registry_promotion_result.json"
        )
        write_json_atomically(
            promotion_result_path,
            self.valid_promotion_result(),
        )
        return dirs, fixture_path, promotion_result_path

    def valid_registry_record(self):
        return {
            "registry_entry_type": "local_fixture_only_adapter_registry_entry_v1",
            "registry_entry_status": "enabled_local_fixture_only",
            "allowed_scope": "local_fixture_only",
            "adapter_id": "bounded_playwright_worker_adapter_draft",
            "adapter_capability": "launch_bounded_playwright_worker_adapter_draft",
            "candidate_id": "github-candidate-microsoft-playwright-v1",
            "repo_full_name": "microsoft/playwright",
            "source_gate_decision_sha256": "a" * 64,
            "source_gate_decision_type": "local_fixture_playwright_adapter_admission_gate_decision_v1",
            "source_gate_passed": True,
            "registry_promotion_granted": True,
            "production_promotion_granted": False,
            "production_adapter": False,
            "denied_scope": list(
                ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_DENIED_SCOPE
            ),
            "local_fixture_only": True,
            "human_review_required": True,
            "required_human_approval": True,
            "aggregation_bound": True,
            "regression_bound": True,
            "non_production": True,
        }

    def valid_promotion_result(self):
        payload = {
            "promotion_type": "admission_gated_local_adapter_registry_promotion_v1",
            "promotion_status": "admission_gated_local_adapter_registry_promotion_completed",
            "promotion_decision": "promote_local_fixture_only_adapter_registration",
            "registry_promotion_granted": True,
            "production_promotion_granted": False,
            "source_gate_passed": True,
            "source_gate_decision_type": "local_fixture_playwright_adapter_admission_gate_decision_v1",
            "source_gate_decision_sha256": "a" * 64,
            "adapter_id": "bounded_playwright_worker_adapter_draft",
            "candidate_id": "github-candidate-microsoft-playwright-v1",
            "repo_full_name": "microsoft/playwright",
            "aggregation_bound": True,
            "regression_bound": True,
            "local_fixture_only": True,
            "human_review_required": True,
            "required_human_approval": True,
            "non_production": True,
            "production_adapter": False,
            "registry_record": self.valid_registry_record(),
        }
        payload.update(
            {
                field_name: False
                for field_name in LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_DENIED_ADMISSION_FIELDS
            }
        )
        payload.update(
            {
                field_name: False
                for field_name in LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_FORBIDDEN_PERFORMED_FIELDS
            }
        )
        return payload

    def produce_chain_outputs(self):
        dirs, fixture_path, promotion_result_path = self.make_workspace()

        usage = run_local_fixture_adapter_usage_receipt(
            promotion_result_path,
            dirs["usage-output"],
            "usage-hardening-001",
            review_attestation=LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_REVIEW_ATTESTATION,
            local_fixture_reference=fixture_path.as_posix(),
            project_id="project-hardening",
            reviewer_id="reviewer-hardening",
            operator_notes="artifact index hardening fixture",
        )
        self.assertTrue(usage.complete, usage.rejection_reasons)

        dry_run = run_local_fixture_adapter_dry_run_invocation_plan(
            usage.result_path,
            dirs["dry-run-output"],
            "dry-run-hardening-001",
            review_attestation=LOCAL_FIXTURE_ADAPTER_DRY_RUN_INVOCATION_PLAN_REVIEW_ATTESTATION,
            project_id="project-hardening",
            reviewer_id="reviewer-hardening",
            operator_notes="artifact index hardening fixture",
        )
        self.assertTrue(dry_run.complete, dry_run.rejection_reasons)

        execution_gate = run_local_fixture_adapter_execution_gate_plan(
            dry_run.result_path,
            dirs["execution-gate-output"],
            "execution-gate-hardening-001",
            review_attestation=LOCAL_FIXTURE_ADAPTER_EXECUTION_GATE_PLAN_REVIEW_ATTESTATION,
            project_id="project-hardening",
            reviewer_id="reviewer-hardening",
            operator_notes="artifact index hardening fixture",
        )
        self.assertTrue(execution_gate.complete, execution_gate.rejection_reasons)

        approval = run_local_fixture_human_approval_artifact(
            execution_gate.result_path,
            dirs["approval-output"],
            "approval-hardening-001",
            "reviewer-hardening",
            LOCAL_FIXTURE_HUMAN_APPROVAL_ARTIFACT_ATTESTATION,
            project_id="project-hardening",
            operator_notes="artifact index hardening fixture",
        )
        self.assertTrue(approval.complete, approval.rejection_reasons)

        runner_contract = run_local_fixture_runner_contract_draft(
            dirs["runner-contract-output"],
            "runner-contract-hardening-001",
            review_attestation=LOCAL_FIXTURE_RUNNER_CONTRACT_DRAFT_REVIEW_ATTESTATION,
            project_id="project-hardening",
            reviewer_id="reviewer-hardening",
            operator_notes="artifact index hardening fixture",
        )
        self.assertTrue(runner_contract.complete, runner_contract.rejection_reasons)

        return (
            {
                "name": "usage_receipt",
                "result": usage,
                "output_dir": dirs["usage-output"],
                "roles": [
                    "local_fixture_adapter_usage_receipt_plan",
                    "local_fixture_adapter_usage_receipt_result",
                    "local_fixture_adapter_usage_receipt_manifest",
                    "local_fixture_adapter_usage_receipt_summary",
                    "local_fixture_adapter_usage_receipt_checklist",
                ],
            },
            {
                "name": "dry_run_invocation_plan",
                "result": dry_run,
                "output_dir": dirs["dry-run-output"],
                "roles": [
                    "local_fixture_adapter_dry_run_invocation_plan_plan",
                    "local_fixture_adapter_dry_run_invocation_plan_result",
                    "local_fixture_adapter_dry_run_invocation_plan_manifest",
                    "local_fixture_adapter_dry_run_invocation_plan_summary",
                    "local_fixture_adapter_dry_run_invocation_plan_checklist",
                ],
            },
            {
                "name": "execution_gate_plan",
                "result": execution_gate,
                "output_dir": dirs["execution-gate-output"],
                "roles": [
                    "local_fixture_adapter_execution_gate_plan_plan",
                    "local_fixture_adapter_execution_gate_plan_result",
                    "local_fixture_adapter_execution_gate_plan_manifest",
                    "local_fixture_adapter_execution_gate_plan_human_approval_request",
                    "local_fixture_adapter_execution_gate_plan_summary",
                    "local_fixture_adapter_execution_gate_plan_checklist",
                ],
            },
            {
                "name": "human_approval_artifact",
                "result": approval,
                "output_dir": dirs["approval-output"],
                "roles": [
                    "local_fixture_human_approval_artifact",
                    "local_fixture_human_approval_artifact_result",
                    "local_fixture_human_approval_artifact_manifest",
                    "local_fixture_human_approval_artifact_summary",
                    "local_fixture_human_approval_artifact_checklist",
                ],
            },
            {
                "name": "runner_contract_draft",
                "result": runner_contract,
                "output_dir": dirs["runner-contract-output"],
                "roles": [
                    "local_fixture_runner_contract_draft",
                    "local_fixture_runner_contract_draft_result",
                    "local_fixture_runner_contract_draft_manifest",
                    "local_fixture_runner_contract_draft_summary",
                    "local_fixture_runner_contract_draft_checklist",
                    "artifact_index",
                    "artifact_index_manifest",
                ],
            },
        )

    def test_local_fixture_chain_writes_hardened_artifact_indexes(self):
        for case in self.produce_chain_outputs():
            with self.subTest(case=case["name"]):
                self.assert_artifact_index_contract(
                    case["result"],
                    case["output_dir"],
                    case["roles"],
                )

    def assert_artifact_index_contract(self, result, output_dir, expected_roles):
        artifact_index_path = result.artifact_index_path
        artifact_index_manifest_path = result.artifact_index_manifest_path

        self.assertEqual(artifact_index_path.name, "artifact_index.json")
        self.assertEqual(
            artifact_index_manifest_path.name,
            "artifact_index_manifest.json",
        )
        self.assertTrue(artifact_index_path.is_file())
        self.assertTrue(artifact_index_manifest_path.is_file())
        self.assert_path_inside(artifact_index_path, output_dir)
        self.assert_path_inside(artifact_index_manifest_path, output_dir)

        artifact_index = read_json(artifact_index_path)
        manifest = read_json(artifact_index_manifest_path)
        entries = artifact_index["entries"]

        self.assertIsInstance(artifact_index.get("index_type"), str)
        self.assertTrue(artifact_index["index_type"])
        self.assert_has_identity_marker(artifact_index)
        self.assertEqual(artifact_index.get("job_dir"), output_dir.as_posix())
        self.assertIsInstance(entries, list)
        self.assertEqual(artifact_index["indexed_artifacts"], len(entries))
        self.assertEqual(
            [entry["artifact_role"] for entry in entries],
            expected_roles,
        )
        self.assert_false_boundary_flags(artifact_index)
        self.assert_no_content_blobs(artifact_index)

        for entry in entries:
            self.assert_entry_contract(entry, output_dir)

        self.assertIsInstance(manifest.get("manifest_type"), str)
        self.assertTrue(manifest["manifest_type"])
        self.assert_has_identity_marker(manifest)
        self.assertEqual(manifest.get("job_dir"), output_dir.as_posix())
        self.assertEqual(
            Path(manifest["artifact_index_path"]).resolve(strict=False),
            artifact_index_path.resolve(strict=False),
        )
        self.assert_path_inside(Path(manifest["artifact_index_path"]), output_dir)
        self.assertEqual(manifest["artifact_index_sha256"], sha256_file(artifact_index_path))
        self.assertEqual(manifest["indexed_artifacts"], len(entries))
        self.assertIn("indexed_relative_paths", manifest)
        self.assertEqual(
            manifest["indexed_relative_paths"],
            [entry["relative_path"] for entry in entries],
        )
        self.assertIn("artifact_roles", manifest)
        self.assertEqual(set(manifest["artifact_roles"]), set(expected_roles))
        for path_value in manifest["artifact_roles"].values():
            self.assert_path_inside(Path(path_value), output_dir)
        self.assertTrue(manifest["deterministic_ordering"])
        self.assert_false_boundary_flags(manifest)
        self.assert_no_content_blobs(manifest)

        self.assert_self_reference_contract(entries)

    def assert_entry_contract(self, entry, output_dir):
        for field_name in (
            "artifact_name",
            "artifact_role",
            "path",
            "relative_path",
            "exists",
            "sha256",
            "content_indexed",
            "raw_content_copied",
            "candidate_repo_file",
            "external_candidate_artifact",
        ):
            self.assertIn(field_name, entry)

        self.assertEqual(entry["artifact_name"], entry["artifact_role"])
        self.assert_path_inside(Path(entry["path"]), output_dir)
        self.assert_safe_relative_path(entry["relative_path"])
        self.assertFalse(entry["content_indexed"])
        self.assertFalse(entry["raw_content_copied"])
        self.assertFalse(entry["candidate_repo_file"])
        self.assertFalse(entry["external_candidate_artifact"])

        deferred_hash = entry.get("hash_deferred_to_manifest") is True
        unavailable_self_hash = (
            entry.get("hash_unavailable_without_self_reference") is True
        )
        if entry["exists"] and not (deferred_hash or unavailable_self_hash):
            self.assertEqual(entry["sha256"], sha256_file(Path(entry["path"])))
        if not entry["exists"]:
            self.assertIsNone(entry["sha256"])

    def assert_self_reference_contract(self, entries):
        for entry in entries:
            relative_path = entry["relative_path"]
            if relative_path == "artifact_index.json":
                self.assertIsNone(entry["sha256"])
                self.assertTrue(entry.get("hash_deferred_to_manifest"))
            if relative_path == "artifact_index_manifest.json":
                self.assertIsNone(entry["sha256"])
                self.assertTrue(entry.get("hash_unavailable_without_self_reference"))

    def assert_has_identity_marker(self, payload):
        self.assertTrue(
            any(key.endswith("adapter_id") for key in payload),
            payload,
        )
        self.assertTrue(
            any(key.endswith("capability") for key in payload),
            payload,
        )

    def assert_false_boundary_flags(self, payload):
        for field_name in (
            "candidate_repo_files_indexed",
            "external_candidate_artifacts_indexed",
            "content_indexed",
            "raw_content_copied",
        ):
            self.assertIn(field_name, payload)
            self.assertFalse(payload[field_name], field_name)

    def assert_no_content_blobs(self, payload):
        encoded = json.dumps(payload, sort_keys=True)
        self.assertLess(len(max(encoded.split('"'), key=len, default="")), 2048)
        lowered = encoded.lower()
        for marker in FORBIDDEN_CONTENT_MARKERS:
            self.assertNotIn(marker, lowered)
        for key, value in self.walk_json(payload):
            if key in {
                "content",
                "raw_content",
                "file_content",
                "source_content",
                "candidate_repo_source_content",
            }:
                self.fail(f"unexpected raw content key {key!r}: {value!r}")

    def assert_path_inside(self, path, output_dir):
        self.assertTrue(path.is_absolute(), path)
        resolved_path = path.resolve(strict=False)
        resolved_output = output_dir.resolve(strict=False)
        self.assertTrue(
            resolved_path == resolved_output
            or resolved_output in resolved_path.parents,
            f"{path} is outside {output_dir}",
        )

    def assert_safe_relative_path(self, value):
        relative_path = PurePosixPath(value)
        self.assertFalse(relative_path.is_absolute(), value)
        self.assertNotEqual(relative_path.parts[:1], ("..",), value)
        self.assertNotIn("..", relative_path.parts, value)

    def walk_json(self, value):
        if isinstance(value, dict):
            for key, item in value.items():
                yield key, item
                yield from self.walk_json(item)
        elif isinstance(value, list):
            for item in value:
                yield from self.walk_json(item)


if __name__ == "__main__":
    unittest.main()
