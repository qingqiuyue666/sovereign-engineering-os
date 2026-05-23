import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from kernel.assets.local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate import (
    build_local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.task_graph import run_local_task_graph_fixture
from tests.tracer_bullet import (
    test_local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate as contract_helpers,
)


REVIEW_OUTPUTS = (
    "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate.json",
    "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_manifest.json",
    "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_summary.md",
    "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_checklist.md",
    "artifact_index.json",
    "artifact_index_manifest.json",
)
REVIEW_ROLES = (
    "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate",
    "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_manifest",
    "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_summary",
    "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_checklist",
)
NO_SCOPE_FIELDS = (
    "production_scan_approved",
    "production_promotion_granted",
    "automatic_approval_performed",
    "autonomous_execution_performed",
    "runner_execution_performed_by_human_review",
    "cycle_contract_reexecution_performed",
    "candidate_input_path_checked_by_human_review",
    "candidate_input_path_listed_by_human_review",
    "candidate_input_file_read_by_human_review",
    "candidate_input_file_hashing_performed_by_human_review",
    "raw_candidate_content_read_by_human_review",
    "bounded_smoke_iteration_performed_by_human_review",
    "input_mutation_performed",
    "upstream_output_mutation_performed",
    "file_move_performed",
    "file_rename_performed",
    "file_delete_performed",
    "duplicate_deletion_performed",
    "media_organizer_behavior_performed",
    "output_overwrite_performed",
    "network_access_performed",
    "model_api_called",
    "external_runtime_invoked",
    "production_scan_performed",
    "production_scan_recommended",
)
SOURCE_CONTRACT_FILE = (
    "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate.json"
)
SOURCE_CONTRACT_MANIFEST_FILE = (
    "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_manifest.json"
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    Path(path).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class LocalAssetNextBoundedSmokeCycleContractHumanReviewFromRunPromotionGateTests(
    unittest.TestCase
):
    def helper(self):
        return contract_helpers.LocalAssetNextBoundedSmokeCycleContractFromRunPromotionGateTests(
            methodName="test_full_chain_from_run_promotion_gate_creates_contract_artifacts"
        )

    def run_cli(self, args):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(args)
        return exit_code, json.loads(stdout.getvalue())

    def build_ready_source_cycle_contract(self, root):
        helper = self.helper()
        gate_output, _review, _runner_output, _actual = (
            helper.build_ready_promotion_gate(root)
        )
        cycle_contract_output = Path(root) / "next-cycle-contract"
        cycle_contract_output.mkdir()
        exit_code, payload = helper.run_contract(
            gate_output,
            cycle_contract_output,
            cycle_contract_id="ready-next-cycle-contract-1",
        )
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["complete"])
        return cycle_contract_output, gate_output

    def run_human_review(
        self,
        cycle_contract_output,
        output_dir,
        *,
        human_review_id="next-cycle-contract-review-1",
        project_id="cycle-test",
        reviewer_id="reviewer-1",
        operator_notes="approve bounded admission for later step",
    ):
        args = [
            "launch-local-asset-next-bounded-smoke-cycle-contract-human-review-from-run-promotion-gate",
            "--cycle-contract-output-dir",
            Path(cycle_contract_output).as_posix(),
            "--output-dir",
            Path(output_dir).as_posix(),
            "--human-review-id",
            human_review_id,
        ]
        if project_id is not None:
            args.extend(["--project-id", project_id])
        if reviewer_id is not None:
            args.extend(["--reviewer-id", reviewer_id])
        if operator_notes is not None:
            args.extend(["--operator-notes", operator_notes])
        return self.run_cli(args)

    def rewrite_contract_manifest_hash(self, cycle_contract_output):
        cycle_contract_output = Path(cycle_contract_output)
        contract_path = cycle_contract_output / SOURCE_CONTRACT_FILE
        manifest_path = cycle_contract_output / SOURCE_CONTRACT_MANIFEST_FILE
        manifest = read_json(manifest_path)
        manifest["contract_sha256"] = sha256_file(contract_path)
        write_json(manifest_path, manifest)

    def rewrite_index_manifest_hash(self, cycle_contract_output):
        cycle_contract_output = Path(cycle_contract_output)
        index_path = cycle_contract_output / "artifact_index.json"
        manifest_path = cycle_contract_output / "artifact_index_manifest.json"
        manifest = read_json(manifest_path)
        manifest["artifact_index_sha256"] = sha256_file(index_path)
        write_json(manifest_path, manifest)

    def write_graph(self, graph_path, nodes):
        write_json_atomically(
            graph_path,
            {
                "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
                "graph_id": "next-cycle-contract-human-review-graph",
                "execution_mode": "fixture_execution",
                "authority": "non_authority",
                "required_human_approval": True,
                "nodes": nodes,
            },
        )

    def human_review_node(self, *, node_id, cycle_contract_output, output_dir):
        return {
            "node_id": node_id,
            "adapter_id": "local_asset_runtime",
            "capability": (
                "launch_local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate"
            ),
            "execution_mode": "fixture",
            "depends_on": [],
            "approval_checkpoint_required": True,
            "inputs": {
                "cycle_contract_output_dir": Path(
                    cycle_contract_output
                ).as_posix(),
                "output_dir": Path(output_dir).as_posix(),
                "human_review_id": "graph-next-cycle-contract-review-1",
                "project_id": "cycle-test",
                "reviewer_id": "reviewer-graph",
                "operator_notes": "graph bounded review",
            },
        }

    def assert_review_artifacts_absent(self, output_dir):
        for filename in REVIEW_OUTPUTS:
            self.assertFalse((Path(output_dir) / filename).exists(), filename)

    def assert_no_scope_false(self, payload_like):
        for field_name in NO_SCOPE_FIELDS:
            self.assertFalse(payload_like[field_name], field_name)

    def test_full_chain_from_previous_helpers_creates_human_review_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cycle_contract_output, _gate_output = (
                self.build_ready_source_cycle_contract(root)
            )
            review_output = root / "next-cycle-contract-human-review"
            review_output.mkdir()

            exit_code, payload = self.run_human_review(
                cycle_contract_output,
                review_output,
            )
            artifact_index = read_json(review_output / "artifact_index.json")
            roles = {entry["artifact_role"] for entry in artifact_index["entries"]}

            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["complete"])
            for filename in REVIEW_OUTPUTS:
                self.assertTrue((review_output / filename).exists(), filename)
            self.assertEqual(roles, set(REVIEW_ROLES))

    def test_ready_source_cycle_contract_creates_required_human_review_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cycle_contract_output, _gate_output = (
                self.build_ready_source_cycle_contract(root)
            )
            review_output = root / "next-cycle-contract-human-review"
            review_output.mkdir()

            exit_code, payload = self.run_human_review(
                cycle_contract_output,
                review_output,
            )
            review = read_json(review_output / REVIEW_OUTPUTS[0])
            manifest = read_json(review_output / REVIEW_OUTPUTS[1])
            index_manifest = read_json(review_output / "artifact_index_manifest.json")

            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["complete"])
            self.assertEqual(
                review["human_review_type"],
                "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_v1",
            )
            self.assertEqual(
                review["authority"],
                "non_authority_bounded_cycle_human_review_record",
            )
            self.assertEqual(
                review["execution_capability"],
                "local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate_only",
            )
            self.assertEqual(
                review["human_review_status"],
                "next_bounded_smoke_cycle_contract_human_review_ready",
            )
            self.assertEqual(
                review["human_review_decision"],
                "approve_next_bounded_smoke_cycle_contract_for_bounded_admission",
            )
            self.assertEqual(
                review["next_allowed_action"],
                "admit_next_bounded_smoke_cycle_contract_for_later_execution_request",
            )
            self.assertTrue(review["bounded_cycle_contract_human_review_created"])
            self.assertTrue(review["bounded_cycle_admission_allowed"])
            self.assertTrue(review["source_cycle_contract_created"])
            self.assertTrue(review["source_cycle_contract_from_run_promotion_gate"])
            self.assertEqual(
                manifest["human_review_sha256"],
                sha256_file(review_output / REVIEW_OUTPUTS[0]),
            )
            self.assertEqual(
                index_manifest["artifact_index_sha256"],
                sha256_file(review_output / "artifact_index.json"),
            )

    def test_human_review_is_bounded_admission_only_not_production_approval(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cycle_contract_output, _gate_output = (
                self.build_ready_source_cycle_contract(root)
            )
            review_output = root / "next-cycle-contract-human-review"
            review_output.mkdir()

            exit_code, payload = self.run_human_review(
                cycle_contract_output,
                review_output,
            )
            review = read_json(review_output / REVIEW_OUTPUTS[0])

            self.assertEqual(exit_code, 0)
            for payload_like in (payload, review):
                self.assertTrue(payload_like["bounded_cycle_admission_allowed"])
                self.assertFalse(payload_like["production_scan_approved"])
                self.assertFalse(payload_like["production_promotion_granted"])
                self.assertFalse(payload_like["automatic_approval_performed"])
                self.assertFalse(payload_like["autonomous_execution_performed"])
                self.assertFalse(
                    payload_like["runner_execution_performed_by_human_review"]
                )
                self.assertFalse(payload_like["cycle_contract_reexecution_performed"])

    def test_human_review_does_not_touch_live_candidate_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cycle_contract_output, _gate_output = (
                self.build_ready_source_cycle_contract(root)
            )
            source_contract = read_json(cycle_contract_output / SOURCE_CONTRACT_FILE)
            candidate = Path(source_contract["requested_candidate_input_dir"])
            shutil.rmtree(candidate)
            os.symlink("/definitely/not-read-by-human-review", candidate)
            review_output = root / "next-cycle-contract-human-review"
            review_output.mkdir()

            exit_code, payload = self.run_human_review(
                cycle_contract_output,
                review_output,
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["bounded_cycle_admission_allowed"])
            self.assertFalse(payload["candidate_input_path_checked_by_human_review"])
            self.assertFalse(payload["candidate_input_path_listed_by_human_review"])
            self.assertFalse(payload["candidate_input_file_read_by_human_review"])
            self.assertFalse(
                payload["candidate_input_file_hashing_performed_by_human_review"]
            )

    def test_blocks_missing_required_source_artifacts(self):
        for filename in (
            SOURCE_CONTRACT_FILE,
            SOURCE_CONTRACT_MANIFEST_FILE,
            "artifact_index.json",
            "artifact_index_manifest.json",
        ):
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    cycle_contract_output, _gate_output = (
                        self.build_ready_source_cycle_contract(root)
                    )
                    (cycle_contract_output / filename).unlink()
                    review_output = root / "next-cycle-contract-human-review"
                    review_output.mkdir()

                    exit_code, payload = self.run_human_review(
                        cycle_contract_output,
                        review_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        payload["human_review_status"],
                        "blocked_missing_required_artifacts",
                    )

    def test_blocks_malformed_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cycle_contract_output, _gate_output = (
                self.build_ready_source_cycle_contract(root)
            )
            (cycle_contract_output / SOURCE_CONTRACT_FILE).write_text(
                "{",
                encoding="utf-8",
            )
            review_output = root / "next-cycle-contract-human-review"
            review_output.mkdir()

            exit_code, payload = self.run_human_review(
                cycle_contract_output,
                review_output,
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(payload["human_review_status"], "blocked_untrusted_artifacts")

    def test_blocks_source_symlink_artifacts(self):
        for filename in (
            SOURCE_CONTRACT_FILE,
            SOURCE_CONTRACT_MANIFEST_FILE,
            "artifact_index.json",
            "artifact_index_manifest.json",
        ):
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    cycle_contract_output, _gate_output = (
                        self.build_ready_source_cycle_contract(root)
                    )
                    (cycle_contract_output / filename).unlink()
                    os.symlink(
                        root / "target-does-not-need-to-exist",
                        cycle_contract_output / filename,
                    )
                    review_output = root / "next-cycle-contract-human-review"
                    review_output.mkdir()

                    exit_code, payload = self.run_human_review(
                        cycle_contract_output,
                        review_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        payload["human_review_status"],
                        "blocked_untrusted_artifacts",
                    )

    def test_blocks_source_type_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cycle_contract_output, _gate_output = (
                self.build_ready_source_cycle_contract(root)
            )
            contract_path = cycle_contract_output / SOURCE_CONTRACT_FILE
            source_contract = read_json(contract_path)
            source_contract["contract_type"] = "wrong_contract_type"
            write_json(contract_path, source_contract)
            self.rewrite_contract_manifest_hash(cycle_contract_output)
            review_output = root / "next-cycle-contract-human-review"
            review_output.mkdir()

            exit_code, payload = self.run_human_review(
                cycle_contract_output,
                review_output,
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(payload["human_review_status"], "blocked_untrusted_artifacts")

    def test_blocks_source_manifest_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cycle_contract_output, _gate_output = (
                self.build_ready_source_cycle_contract(root)
            )
            manifest_path = cycle_contract_output / SOURCE_CONTRACT_MANIFEST_FILE
            manifest = read_json(manifest_path)
            manifest["contract_sha256"] = "0" * 64
            write_json(manifest_path, manifest)
            review_output = root / "next-cycle-contract-human-review"
            review_output.mkdir()

            exit_code, payload = self.run_human_review(
                cycle_contract_output,
                review_output,
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(payload["human_review_status"], "blocked_untrusted_artifacts")

    def test_blocks_source_artifact_index_manifest_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cycle_contract_output, _gate_output = (
                self.build_ready_source_cycle_contract(root)
            )
            manifest_path = cycle_contract_output / "artifact_index_manifest.json"
            manifest = read_json(manifest_path)
            manifest["artifact_index_sha256"] = "0" * 64
            write_json(manifest_path, manifest)
            review_output = root / "next-cycle-contract-human-review"
            review_output.mkdir()

            exit_code, payload = self.run_human_review(
                cycle_contract_output,
                review_output,
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(payload["human_review_status"], "blocked_untrusted_artifacts")

    def test_blocks_optional_summary_or_checklist_missing_hash_binding(self):
        for hash_field in ("summary_sha256", "checklist_sha256"):
            with self.subTest(hash_field=hash_field):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    cycle_contract_output, _gate_output = (
                        self.build_ready_source_cycle_contract(root)
                    )
                    manifest_path = cycle_contract_output / SOURCE_CONTRACT_MANIFEST_FILE
                    manifest = read_json(manifest_path)
                    manifest.pop(hash_field, None)
                    write_json(manifest_path, manifest)
                    review_output = root / "next-cycle-contract-human-review"
                    review_output.mkdir()

                    exit_code, payload = self.run_human_review(
                        cycle_contract_output,
                        review_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        payload["human_review_status"],
                        "blocked_untrusted_artifacts",
                    )

    def test_blocks_source_cycle_contract_not_ready(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cycle_contract_output, _gate_output = (
                self.build_ready_source_cycle_contract(root)
            )
            contract_path = cycle_contract_output / SOURCE_CONTRACT_FILE
            source_contract = read_json(contract_path)
            source_contract["contract_status"] = "next_cycle_contract_needs_repair"
            write_json(contract_path, source_contract)
            self.rewrite_contract_manifest_hash(cycle_contract_output)
            review_output = root / "next-cycle-contract-human-review"
            review_output.mkdir()

            exit_code, payload = self.run_human_review(
                cycle_contract_output,
                review_output,
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                payload["human_review_status"],
                "blocked_source_cycle_contract_not_ready",
            )

    def test_blocks_source_decision_or_next_action_mismatch(self):
        cases = (
            ("contract_decision", "wrong_decision"),
            ("next_allowed_action", "wrong_action"),
        )
        for field_name, value in cases:
            with self.subTest(field_name=field_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    cycle_contract_output, _gate_output = (
                        self.build_ready_source_cycle_contract(root)
                    )
                    contract_path = cycle_contract_output / SOURCE_CONTRACT_FILE
                    source_contract = read_json(contract_path)
                    source_contract[field_name] = value
                    write_json(contract_path, source_contract)
                    self.rewrite_contract_manifest_hash(cycle_contract_output)
                    review_output = root / "next-cycle-contract-human-review"
                    review_output.mkdir()

                    exit_code, payload = self.run_human_review(
                        cycle_contract_output,
                        review_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        payload["human_review_status"],
                        "blocked_invalid_source_contract_record",
                    )

    def test_blocks_source_contract_contains_blockers_missing_or_untrusted(self):
        cases = (
            ("contract_blockers", [{"reason": "manual_blocker"}]),
            ("missing_required_artifacts", [{"artifact_role": "missing"}]),
            ("untrusted_artifacts", [{"artifact_role": "untrusted"}]),
        )
        for field_name, value in cases:
            with self.subTest(field_name=field_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    cycle_contract_output, _gate_output = (
                        self.build_ready_source_cycle_contract(root)
                    )
                    contract_path = cycle_contract_output / SOURCE_CONTRACT_FILE
                    source_contract = read_json(contract_path)
                    source_contract[field_name] = value
                    write_json(contract_path, source_contract)
                    self.rewrite_contract_manifest_hash(cycle_contract_output)
                    review_output = root / "next-cycle-contract-human-review"
                    review_output.mkdir()

                    exit_code, payload = self.run_human_review(
                        cycle_contract_output,
                        review_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        payload["human_review_status"],
                        "blocked_source_cycle_contract_contains_blockers",
                    )

    def test_blocks_missing_source_boundary_false_field(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cycle_contract_output, _gate_output = (
                self.build_ready_source_cycle_contract(root)
            )
            contract_path = cycle_contract_output / SOURCE_CONTRACT_FILE
            source_contract = read_json(contract_path)
            source_contract.pop("candidate_input_file_read_by_contract", None)
            write_json(contract_path, source_contract)
            self.rewrite_contract_manifest_hash(cycle_contract_output)
            review_output = root / "next-cycle-contract-human-review"
            review_output.mkdir()

            exit_code, payload = self.run_human_review(
                cycle_contract_output,
                review_output,
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                payload["human_review_status"],
                "blocked_invalid_source_contract_record",
            )

    def test_blocks_non_boolean_source_boundary_false_field(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cycle_contract_output, _gate_output = (
                self.build_ready_source_cycle_contract(root)
            )
            contract_path = cycle_contract_output / SOURCE_CONTRACT_FILE
            source_contract = read_json(contract_path)
            source_contract["candidate_input_file_read_by_contract"] = "false"
            write_json(contract_path, source_contract)
            self.rewrite_contract_manifest_hash(cycle_contract_output)
            review_output = root / "next-cycle-contract-human-review"
            review_output.mkdir()

            exit_code, payload = self.run_human_review(
                cycle_contract_output,
                review_output,
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                payload["human_review_status"],
                "blocked_invalid_source_contract_record",
            )

    def test_blocks_true_source_boundary_false_field(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cycle_contract_output, _gate_output = (
                self.build_ready_source_cycle_contract(root)
            )
            contract_path = cycle_contract_output / SOURCE_CONTRACT_FILE
            source_contract = read_json(contract_path)
            source_contract["candidate_input_file_read_by_contract"] = True
            write_json(contract_path, source_contract)
            self.rewrite_contract_manifest_hash(cycle_contract_output)
            review_output = root / "next-cycle-contract-human-review"
            review_output.mkdir()

            exit_code, payload = self.run_human_review(
                cycle_contract_output,
                review_output,
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                payload["human_review_status"],
                "blocked_source_boundary_violation",
            )

    def test_blocks_invalid_inherited_run_facts(self):
        cases = (
            ("cycle_contract_id", ""),
            ("candidate_file_count", "2"),
            ("bounded_file_records_raw_content", True),
        )
        for field_name, value in cases:
            with self.subTest(field_name=field_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    cycle_contract_output, _gate_output = (
                        self.build_ready_source_cycle_contract(root)
                    )
                    contract_path = cycle_contract_output / SOURCE_CONTRACT_FILE
                    source_contract = read_json(contract_path)
                    if field_name == "bounded_file_records_raw_content":
                        if not source_contract["bounded_file_records"]:
                            source_contract["bounded_file_records"] = [
                                {"relative_path": "asset.bin"}
                            ]
                        source_contract["bounded_file_records"][0][
                            "raw_content"
                        ] = "private"
                    else:
                        source_contract[field_name] = value
                    write_json(contract_path, source_contract)
                    self.rewrite_contract_manifest_hash(cycle_contract_output)
                    review_output = root / "next-cycle-contract-human-review"
                    review_output.mkdir()

                    exit_code, payload = self.run_human_review(
                        cycle_contract_output,
                        review_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        payload["human_review_status"],
                        "blocked_invalid_inherited_run_facts",
                    )

    def test_invalid_human_review_metadata_blocks_without_artifacts(self):
        cases = (
            {"human_review_id": ""},
            {"reviewer_id": ""},
            {"project_id": ""},
        )
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    cycle_contract_output, _gate_output = (
                        self.build_ready_source_cycle_contract(root)
                    )
                    review_output = root / "next-cycle-contract-human-review"
                    review_output.mkdir()

                    exit_code, payload = self.run_human_review(
                        cycle_contract_output,
                        review_output,
                        **kwargs,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertFalse(payload["artifacts_written"])
                    self.assertEqual(payload["human_review_status"], "blocked_unknown")
                    self.assert_review_artifacts_absent(review_output)

    def test_existing_output_files_block_with_no_overwrite(self):
        for filename in REVIEW_OUTPUTS:
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    cycle_contract_output, _gate_output = (
                        self.build_ready_source_cycle_contract(root)
                    )
                    review_output = root / "next-cycle-contract-human-review"
                    review_output.mkdir()
                    existing = review_output / filename
                    existing.write_text("existing\n", encoding="utf-8")

                    exit_code, payload = self.run_human_review(
                        cycle_contract_output,
                        review_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertFalse(payload["artifacts_written"])
                    self.assertEqual(existing.read_text(encoding="utf-8"), "existing\n")
                    for other in REVIEW_OUTPUTS:
                        if other != filename:
                            self.assertFalse((review_output / other).exists(), other)

    def test_symlink_output_collisions_block(self):
        for filename in REVIEW_OUTPUTS:
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    cycle_contract_output, _gate_output = (
                        self.build_ready_source_cycle_contract(root)
                    )
                    review_output = root / "next-cycle-contract-human-review"
                    review_output.mkdir()
                    os.symlink(
                        root / "target-does-not-need-to-exist",
                        review_output / filename,
                    )

                    exit_code, payload = self.run_human_review(
                        cycle_contract_output,
                        review_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertFalse(payload["artifacts_written"])
                    for other in REVIEW_OUTPUTS:
                        if other != filename:
                            self.assertFalse((review_output / other).exists(), other)

    def test_missing_output_dir_returns_structured_failure_and_writes_no_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cycle_contract_output, _gate_output = (
                self.build_ready_source_cycle_contract(root)
            )
            review_output = root / "missing-human-review-output"

            exit_code, payload = self.run_human_review(
                cycle_contract_output,
                review_output,
            )

            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["artifacts_written"])
            self.assertFalse(review_output.exists())

    def test_input_output_overlap_blocks_and_writes_no_artifacts(self):
        cases = (
            "output_inside_contract",
            "contract_inside_output",
            "same_dir",
        )
        for case_name in cases:
            with self.subTest(case_name=case_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    cycle_contract_output, _gate_output = (
                        self.build_ready_source_cycle_contract(root)
                    )
                    if case_name == "output_inside_contract":
                        review_output = cycle_contract_output / "human-review"
                        review_output.mkdir()
                    elif case_name == "contract_inside_output":
                        review_output = root / "next-cycle-contract-human-review"
                        review_output.mkdir()
                        copied_contract = review_output / "source-contract"
                        shutil.copytree(cycle_contract_output, copied_contract)
                        cycle_contract_output = copied_contract
                    else:
                        review_output = cycle_contract_output

                    exit_code, payload = self.run_human_review(
                        cycle_contract_output,
                        review_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertFalse(payload["artifacts_written"])
                    for filename in REVIEW_OUTPUTS[:4]:
                        self.assertFalse((review_output / filename).exists(), filename)

    def test_task_graph_node_writes_artifact_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cycle_contract_output, _gate_output = (
                self.build_ready_source_cycle_contract(root)
            )
            review_output = root / "next-cycle-contract-human-review"
            graph_output = root / "graph-output"
            review_output.mkdir()
            graph_output.mkdir()
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.human_review_node(
                        node_id="review_next_cycle_contract",
                        cycle_contract_output=cycle_contract_output,
                        output_dir=review_output,
                    )
                ],
            )

            result = run_local_task_graph_fixture(graph_path, graph_output)
            artifact_outputs = read_json(result.artifact_outputs_manifest_path)
            roles = {
                artifact["artifact_role"]
                for artifact in artifact_outputs["artifacts"]
                if artifact["node_id"] == "review_next_cycle_contract"
            }

            self.assertTrue(result.success)
            for role in REVIEW_ROLES:
                self.assertIn(role, roles)

    def test_no_scope_boundary_fields_remain_false(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cycle_contract_output, _gate_output = (
                self.build_ready_source_cycle_contract(root)
            )
            review_output = root / "next-cycle-contract-human-review"
            review_output.mkdir()

            exit_code, payload = self.run_human_review(
                cycle_contract_output,
                review_output,
            )
            review = read_json(review_output / REVIEW_OUTPUTS[0])
            manifest = read_json(review_output / REVIEW_OUTPUTS[1])
            graph_output = root / "graph-output"
            graph_review_output = root / "graph-review-output"
            graph_output.mkdir()
            graph_review_output.mkdir()
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.human_review_node(
                        node_id="review_next_cycle_contract",
                        cycle_contract_output=cycle_contract_output,
                        output_dir=graph_review_output,
                    )
                ],
            )
            graph_result = run_local_task_graph_fixture(graph_path, graph_output)
            node = read_json(graph_result.execution_manifest_path)["nodes"][0]

            self.assertEqual(exit_code, 0)
            for payload_like in (payload, review, manifest, node):
                self.assertTrue(payload_like["required_human_approval"])
                self.assertTrue(payload_like["required_human_review"])
                self.assertTrue(payload_like["deterministic_ordering"])
                self.assert_no_scope_false(payload_like)

    def test_deterministic_stable_fields(self):
        reviews = []
        checklists = []
        for index in range(2):
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                cycle_contract_output, _gate_output = (
                    self.build_ready_source_cycle_contract(root)
                )
                review_output = root / "next-cycle-contract-human-review"
                review_output.mkdir()
                exit_code, _payload = self.run_human_review(
                    cycle_contract_output,
                    review_output,
                    human_review_id="stable-review",
                    reviewer_id="stable-reviewer",
                    operator_notes="stable notes",
                )
                self.assertEqual(exit_code, 0, index)
                reviews.append(read_json(review_output / REVIEW_OUTPUTS[0]))
                checklists.append(
                    (review_output / REVIEW_OUTPUTS[3]).read_text(
                        encoding="utf-8"
                    )
                )

        for field_name in (
            "human_review_status",
            "human_review_decision",
            "next_allowed_action",
            "disallowed_actions",
        ):
            self.assertEqual(reviews[0][field_name], reviews[1][field_name])
        self.assertEqual(
            [artifact["role"] for artifact in reviews[0]["source_artifacts"]],
            [artifact["role"] for artifact in reviews[1]["source_artifacts"]],
        )
        self.assertEqual(checklists[0], checklists[1])

    def test_builder_structured_failure_writes_no_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cycle_contract_output, _gate_output = (
                self.build_ready_source_cycle_contract(root)
            )
            review_output = root / "missing-human-review-output"

            result = build_local_asset_next_bounded_smoke_cycle_contract_human_review_from_run_promotion_gate(
                cycle_contract_output,
                review_output,
                human_review_id="builder-human-review-1",
            )

            self.assertFalse(result.complete)
            self.assertFalse(result.payload["artifacts_written"])
            self.assertFalse(review_output.exists())


if __name__ == "__main__":
    unittest.main()
