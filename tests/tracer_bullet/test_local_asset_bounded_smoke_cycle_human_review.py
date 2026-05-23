import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from kernel.assets.local_asset_bounded_smoke_cycle_human_review import (
    LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_SIGNOFF_PHRASE,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.task_graph import run_local_task_graph_fixture
from tests.tracer_bullet import test_local_asset_bounded_smoke_cycle_contract as cycle_helpers


REVIEW_OUTPUTS = (
    "local_asset_bounded_smoke_cycle_human_review_decision.json",
    "local_asset_bounded_smoke_cycle_human_review_manifest.json",
    "local_asset_bounded_smoke_cycle_human_review_summary.md",
    "local_asset_bounded_smoke_cycle_human_review_checklist.md",
    "artifact_index.json",
    "artifact_index_manifest.json",
)
REVIEW_ROLES = (
    "local_asset_bounded_smoke_cycle_human_review_decision",
    "local_asset_bounded_smoke_cycle_human_review_manifest",
    "local_asset_bounded_smoke_cycle_human_review_summary",
    "local_asset_bounded_smoke_cycle_human_review_checklist",
)
BOUNDARY_FIELDS = (
    "scan_performed",
    "readiness_run_performed",
    "human_smoke_run_performed",
    "smoke_review_packet_run_performed",
    "smoke_promotion_gate_run_performed",
    "bounded_smoke_iteration_performed_by_review",
    "iteration_review_packet_run_performed",
    "iteration_promotion_gate_run_performed",
    "cycle_contract_run_performed",
    "raw_candidate_content_read",
    "candidate_file_hashing_performed",
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
    "production_promotion_granted",
    "production_scan_approved",
    "production_scan_performed",
    "production_scan_recommended",
    "automatic_approval_performed",
    "autonomous_execution_performed",
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    Path(path).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class LocalAssetBoundedSmokeCycleHumanReviewTests(unittest.TestCase):
    run_cli = cycle_helpers.LocalAssetBoundedSmokeCycleContractTests.run_cli
    make_candidate = cycle_helpers.LocalAssetBoundedSmokeCycleContractTests.make_candidate
    run_readiness = cycle_helpers.LocalAssetBoundedSmokeCycleContractTests.run_readiness
    run_human_smoke = (
        cycle_helpers.LocalAssetBoundedSmokeCycleContractTests.run_human_smoke
    )
    run_smoke_review = (
        cycle_helpers.LocalAssetBoundedSmokeCycleContractTests.run_smoke_review
    )
    run_smoke_promotion = (
        cycle_helpers.LocalAssetBoundedSmokeCycleContractTests.run_smoke_promotion
    )
    run_iteration = cycle_helpers.LocalAssetBoundedSmokeCycleContractTests.run_iteration
    run_iteration_review = (
        cycle_helpers.LocalAssetBoundedSmokeCycleContractTests.run_iteration_review
    )
    run_iteration_promotion = (
        cycle_helpers.LocalAssetBoundedSmokeCycleContractTests.run_iteration_promotion
    )
    run_cycle_contract = (
        cycle_helpers.LocalAssetBoundedSmokeCycleContractTests.run_cycle_contract
    )
    build_full_chain = (
        cycle_helpers.LocalAssetBoundedSmokeCycleContractTests.build_full_chain
    )
    rewrite_manifest_hash = (
        cycle_helpers.LocalAssetBoundedSmokeCycleContractTests.rewrite_manifest_hash
    )

    def run_cli(self, args):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(args)
        return exit_code, json.loads(stdout.getvalue())

    def build_ready_cycle_contract(self, root):
        chain = self.build_full_chain(root)
        cycle_output = Path(root) / "cycle-contract"
        cycle_output.mkdir()
        exit_code, _payload = self.run_cycle_contract(chain, cycle_output)
        self.assertEqual(exit_code, 0)
        return chain, cycle_output

    def run_cycle_human_review(
        self,
        cycle_output,
        output_dir,
        *,
        human_decision="approve_cycle_contract_for_next_bounded_smoke_iteration",
        human_signoff_phrase=LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_SIGNOFF_PHRASE,
        human_review_id="cycle-review-1",
        human_reviewer_id="reviewer-1",
        human_review_notes=None,
    ):
        args = [
            "launch-local-asset-bounded-smoke-cycle-human-review",
            "--cycle-contract-output-dir",
            Path(cycle_output).as_posix(),
            "--output-dir",
            Path(output_dir).as_posix(),
            "--human-review-id",
            human_review_id,
            "--human-reviewer-id",
            human_reviewer_id,
            "--human-decision",
            human_decision,
            "--human-signoff-phrase",
            human_signoff_phrase,
            "--project-id",
            "cycle-test",
        ]
        if human_review_notes is not None:
            args.extend(["--human-review-notes", human_review_notes])
        return self.run_cli(args)

    def write_graph(self, graph_path, nodes, *, graph_id="cycle-human-review-graph"):
        write_json_atomically(
            graph_path,
            {
                "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
                "graph_id": graph_id,
                "execution_mode": "fixture_execution",
                "authority": "non_authority",
                "required_human_approval": True,
                "nodes": nodes,
            },
        )

    def cycle_human_review_node(self, *, node_id, cycle_output, output_dir):
        return {
            "node_id": node_id,
            "adapter_id": "local_asset_runtime",
            "capability": "launch_local_asset_bounded_smoke_cycle_human_review",
            "execution_mode": "fixture",
            "depends_on": [],
            "approval_checkpoint_required": True,
            "inputs": {
                "cycle_contract_output_dir": Path(cycle_output).as_posix(),
                "output_dir": Path(output_dir).as_posix(),
                "human_review_id": "cycle-review-graph",
                "human_reviewer_id": "reviewer-graph",
                "human_decision": (
                    "approve_cycle_contract_for_next_bounded_smoke_iteration"
                ),
                "human_signoff_phrase": (
                    LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_SIGNOFF_PHRASE
                ),
                "project_id": "cycle-test",
                "human_review_notes": "graph review",
            },
        }

    def corrupt_contract_for_quarantine(self, chain):
        packet_path = (
            chain["smoke_review_output"] / "local_asset_smoke_review_packet.json"
        )
        packet = read_json(packet_path)
        packet["quarantine_summary"]["quarantined_path_count"] = 1
        packet["quarantined_path_count"] = 1
        write_json(packet_path, packet)
        self.rewrite_manifest_hash(
            chain["smoke_review_output"]
            / "local_asset_smoke_review_packet_manifest.json",
            "packet_sha256",
            packet_path,
        )

    def rewrite_cycle_contract_manifest_hash(self, cycle_output):
        contract_path = (
            Path(cycle_output) / "local_asset_bounded_smoke_cycle_contract.json"
        )
        manifest_path = (
            Path(cycle_output)
            / "local_asset_bounded_smoke_cycle_contract_manifest.json"
        )
        manifest = read_json(manifest_path)
        manifest["contract_sha256"] = sha256_file(contract_path)
        write_json(manifest_path, manifest)

    def test_full_chain_writes_human_review_outputs_and_artifact_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _chain, cycle_output = self.build_ready_cycle_contract(root)
            review_output = root / "cycle-human-review"
            review_output.mkdir()

            exit_code, payload = self.run_cycle_human_review(
                cycle_output,
                review_output,
            )
            artifact_index = read_json(review_output / "artifact_index.json")
            roles = {entry["artifact_role"] for entry in artifact_index["entries"]}

            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["complete"])
            for filename in REVIEW_OUTPUTS:
                self.assertTrue((review_output / filename).exists(), filename)
            self.assertEqual(roles, set(REVIEW_ROLES))

    def test_approved_ready_contract_allows_prepare_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _chain, cycle_output = self.build_ready_cycle_contract(root)
            review_output = root / "cycle-human-review"
            review_output.mkdir()

            exit_code, _payload = self.run_cycle_human_review(
                cycle_output,
                review_output,
            )
            decision = read_json(
                review_output
                / "local_asset_bounded_smoke_cycle_human_review_decision.json"
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                decision["human_review_status"],
                "human_review_approved_next_bounded_smoke_iteration",
            )
            self.assertEqual(
                decision["human_review_decision"],
                "allow_prepare_next_bounded_smoke_iteration",
            )
            self.assertTrue(decision["next_bounded_smoke_iteration_prepare_allowed"])
            self.assertFalse(decision["next_bounded_smoke_iteration_execute_allowed"])
            self.assertFalse(decision["production_scan_approved"])
            self.assertFalse(decision["production_promotion_granted"])

    def test_plaintext_signoff_never_persists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _chain, cycle_output = self.build_ready_cycle_contract(root)
            review_output = root / "cycle-human-review"
            review_output.mkdir()

            exit_code, _payload = self.run_cycle_human_review(
                cycle_output,
                review_output,
            )
            expected_hash = hashlib.sha256(
                LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_SIGNOFF_PHRASE.encode(
                    "utf-8"
                )
            ).hexdigest()

            self.assertEqual(exit_code, 0)
            for filename in REVIEW_OUTPUTS:
                content = (review_output / filename).read_text(encoding="utf-8")
                self.assertNotIn(
                    LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_SIGNOFF_PHRASE,
                    content,
                )
            decision = read_json(
                review_output
                / "local_asset_bounded_smoke_cycle_human_review_decision.json"
            )
            self.assertEqual(decision["human_signoff_phrase_sha256"], expected_hash)
            self.assertFalse(decision["human_signoff_phrase_persisted"])

    def test_invalid_signoff_blocks_and_writes_artifacts_when_output_safe(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _chain, cycle_output = self.build_ready_cycle_contract(root)
            review_output = root / "cycle-human-review"
            review_output.mkdir()

            exit_code, payload = self.run_cycle_human_review(
                cycle_output,
                review_output,
                human_signoff_phrase="WRONG",
            )
            decision = read_json(
                review_output
                / "local_asset_bounded_smoke_cycle_human_review_decision.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["complete"])
            self.assertEqual(
                decision["human_review_status"],
                "blocked_invalid_human_signoff",
            )
            self.assertFalse(decision["next_bounded_smoke_iteration_prepare_allowed"])

    def test_invalid_human_decision_blocks(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _chain, cycle_output = self.build_ready_cycle_contract(root)
            review_output = root / "cycle-human-review"
            review_output.mkdir()

            exit_code, _payload = self.run_cycle_human_review(
                cycle_output,
                review_output,
                human_decision="approve_production",
            )
            decision = read_json(
                review_output
                / "local_asset_bounded_smoke_cycle_human_review_decision.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                decision["human_review_status"],
                "blocked_invalid_human_decision",
            )
            self.assertFalse(decision["next_bounded_smoke_iteration_prepare_allowed"])

    def assert_decision_maps(self, human_decision, expected_status, expected_action):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _chain, cycle_output = self.build_ready_cycle_contract(root)
            review_output = root / "cycle-human-review"
            review_output.mkdir()

            exit_code, _payload = self.run_cycle_human_review(
                cycle_output,
                review_output,
                human_decision=human_decision,
            )
            decision = read_json(
                review_output
                / "local_asset_bounded_smoke_cycle_human_review_decision.json"
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(decision["human_review_status"], expected_status)
            self.assertEqual(decision["human_review_decision"], expected_action)
            self.assertEqual(decision["next_allowed_action"], expected_action)
            self.assertFalse(decision["next_bounded_smoke_iteration_prepare_allowed"])

    def test_stop_cycle_maps_correctly(self):
        self.assert_decision_maps(
            "stop_cycle",
            "human_review_stopped_cycle",
            "stop_cycle",
        )

    def test_repair_artifacts_maps_correctly(self):
        self.assert_decision_maps(
            "repair_artifacts",
            "human_review_requires_artifact_repair",
            "repair_artifacts",
        )

    def test_repair_cycle_maps_correctly(self):
        self.assert_decision_maps(
            "repair_cycle",
            "human_review_requires_cycle_repair",
            "repair_cycle",
        )

    def test_inspect_quarantine_maps_correctly(self):
        self.assert_decision_maps(
            "inspect_quarantine",
            "human_review_requires_quarantine_inspection",
            "inspect_quarantine",
        )

    def test_inspect_duplicates_maps_correctly(self):
        self.assert_decision_maps(
            "inspect_duplicates",
            "human_review_requires_duplicate_inspection",
            "inspect_duplicates",
        )

    def test_inspect_incremental_changes_maps_correctly(self):
        self.assert_decision_maps(
            "inspect_incremental_changes",
            "human_review_requires_incremental_inspection",
            "inspect_incremental_changes",
        )

    def test_reject_boundary_violation_maps_correctly(self):
        self.assert_decision_maps(
            "reject_boundary_violation",
            "human_review_rejected_boundary_violation",
            "reject_boundary_violation",
        )

    def test_blocks_if_cycle_contract_missing_required_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _chain, cycle_output = self.build_ready_cycle_contract(root)
            (
                cycle_output / "local_asset_bounded_smoke_cycle_contract.json"
            ).unlink()
            review_output = root / "cycle-human-review"
            review_output.mkdir()

            exit_code, _payload = self.run_cycle_human_review(
                cycle_output,
                review_output,
            )
            decision = read_json(
                review_output
                / "local_asset_bounded_smoke_cycle_human_review_decision.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                decision["human_review_status"],
                "blocked_missing_required_artifacts",
            )

    def test_blocks_if_cycle_contract_untrusted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _chain, cycle_output = self.build_ready_cycle_contract(root)
            manifest_path = (
                cycle_output
                / "local_asset_bounded_smoke_cycle_contract_manifest.json"
            )
            manifest = read_json(manifest_path)
            manifest["contract_sha256"] = "0" * 64
            write_json(manifest_path, manifest)
            review_output = root / "cycle-human-review"
            review_output.mkdir()

            exit_code, _payload = self.run_cycle_human_review(
                cycle_output,
                review_output,
            )
            decision = read_json(
                review_output
                / "local_asset_bounded_smoke_cycle_human_review_decision.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                decision["human_review_status"],
                "blocked_untrusted_artifacts",
            )

    def test_blocks_if_cycle_contract_not_ready_and_human_tries_approve(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_full_chain(root)
            self.corrupt_contract_for_quarantine(chain)
            cycle_output = root / "cycle-contract"
            cycle_output.mkdir()
            cycle_exit, _cycle_payload = self.run_cycle_contract(chain, cycle_output)
            self.assertEqual(cycle_exit, 1)
            review_output = root / "cycle-human-review"
            review_output.mkdir()

            exit_code, _payload = self.run_cycle_human_review(
                cycle_output,
                review_output,
            )
            decision = read_json(
                review_output
                / "local_asset_bounded_smoke_cycle_human_review_decision.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                decision["human_review_status"],
                "blocked_cycle_contract_not_ready",
            )
            self.assertFalse(decision["next_bounded_smoke_iteration_prepare_allowed"])

    def test_blocks_on_cycle_boundary_violation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _chain, cycle_output = self.build_ready_cycle_contract(root)
            contract_path = (
                cycle_output / "local_asset_bounded_smoke_cycle_contract.json"
            )
            contract = read_json(contract_path)
            contract["production_scan_approved"] = True
            write_json(contract_path, contract)
            self.rewrite_cycle_contract_manifest_hash(cycle_output)
            review_output = root / "cycle-human-review"
            review_output.mkdir()

            exit_code, _payload = self.run_cycle_human_review(
                cycle_output,
                review_output,
            )
            decision = read_json(
                review_output
                / "local_asset_bounded_smoke_cycle_human_review_decision.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                decision["human_review_status"],
                "blocked_cycle_contract_boundary_violation",
            )

    def test_fail_closed_on_existing_outputs(self):
        for filename in REVIEW_OUTPUTS:
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    _chain, cycle_output = self.build_ready_cycle_contract(root)
                    review_output = root / "cycle-human-review"
                    review_output.mkdir()
                    preexisting = review_output / filename
                    preexisting.write_text("preexisting\n", encoding="utf-8")

                    exit_code, payload = self.run_cycle_human_review(
                        cycle_output,
                        review_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertFalse(payload["artifacts_written"])
                    self.assertEqual(
                        preexisting.read_text(encoding="utf-8"),
                        "preexisting\n",
                    )

    def test_missing_output_dir_structured_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _chain, cycle_output = self.build_ready_cycle_contract(root)
            review_output = root / "missing-review-output"

            exit_code, payload = self.run_cycle_human_review(
                cycle_output,
                review_output,
            )

            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["artifacts_written"])
            self.assertFalse(review_output.exists())

    def test_input_output_overlap_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _chain, cycle_output = self.build_ready_cycle_contract(root)
            cases = [
                cycle_output / "nested-review-output",
                cycle_output,
            ]
            parent_output = root / "parent-review-output"
            parent_output.mkdir()
            nested_cycle = parent_output / "nested-cycle-contract"
            nested_cycle.mkdir()
            cases.append(parent_output)

            for review_output in cases:
                with self.subTest(review_output=review_output):
                    if review_output != cycle_output and not review_output.exists():
                        review_output.mkdir()
                    input_dir = nested_cycle if review_output == parent_output else cycle_output

                    exit_code, payload = self.run_cycle_human_review(
                        input_dir,
                        review_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertFalse(payload["artifacts_written"])
                    self.assertFalse(
                        (
                            review_output
                            / "local_asset_bounded_smoke_cycle_human_review_decision.json"
                        ).exists()
                    )

    def test_task_graph_node_writes_artifact_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _chain, cycle_output = self.build_ready_cycle_contract(root)
            review_output = root / "cycle-human-review"
            review_output.mkdir()
            graph_output = root / "graph-output"
            graph_output.mkdir()
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.cycle_human_review_node(
                        node_id="cycle-review",
                        cycle_output=cycle_output,
                        output_dir=review_output,
                    )
                ],
            )

            result = run_local_task_graph_fixture(graph_path, graph_output)
            artifact_outputs = read_json(result.artifact_outputs_manifest_path)
            roles = {
                artifact["artifact_role"]
                for artifact in artifact_outputs["artifacts"]
                if artifact["node_id"] == "cycle-review"
            }

            self.assertTrue(result.success)
            for role in REVIEW_ROLES:
                self.assertIn(role, roles)

    def test_no_scope_boundaries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _chain, cycle_output = self.build_ready_cycle_contract(root)
            review_output = root / "cycle-human-review"
            review_output.mkdir()

            exit_code, payload = self.run_cycle_human_review(
                cycle_output,
                review_output,
            )
            decision = read_json(
                review_output
                / "local_asset_bounded_smoke_cycle_human_review_decision.json"
            )
            manifest = read_json(
                review_output
                / "local_asset_bounded_smoke_cycle_human_review_manifest.json"
            )
            graph_output = root / "graph-output"
            graph_output.mkdir()
            graph_path = root / "graph.json"
            graph_review_output = root / "graph-cycle-human-review"
            graph_review_output.mkdir()
            self.write_graph(
                graph_path,
                [
                    self.cycle_human_review_node(
                        node_id="cycle-review",
                        cycle_output=cycle_output,
                        output_dir=graph_review_output,
                    )
                ],
            )
            graph_result = run_local_task_graph_fixture(graph_path, graph_output)
            execution = read_json(graph_result.execution_manifest_path)
            node = execution["nodes"][0]

            self.assertEqual(exit_code, 0)
            for payload_like in (payload, decision, manifest, node):
                self.assertTrue(payload_like["required_human_approval"])
                self.assertTrue(payload_like["required_human_review"])
                for field in BOUNDARY_FIELDS:
                    self.assertFalse(payload_like[field], field)

    def test_deterministic_stable_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _chain, cycle_output = self.build_ready_cycle_contract(root)
            first_output = root / "cycle-human-review-1"
            second_output = root / "cycle-human-review-2"
            first_output.mkdir()
            second_output.mkdir()

            first_exit, _first_payload = self.run_cycle_human_review(
                cycle_output,
                first_output,
                human_review_id="same-review",
                human_reviewer_id="same-reviewer",
            )
            second_exit, _second_payload = self.run_cycle_human_review(
                cycle_output,
                second_output,
                human_review_id="same-review",
                human_reviewer_id="same-reviewer",
            )
            first_decision = read_json(
                first_output
                / "local_asset_bounded_smoke_cycle_human_review_decision.json"
            )
            second_decision = read_json(
                second_output
                / "local_asset_bounded_smoke_cycle_human_review_decision.json"
            )

            self.assertEqual(first_exit, 0)
            self.assertEqual(second_exit, 0)
            for field in (
                "human_review_status",
                "human_review_decision",
                "next_allowed_action",
                "disallowed_actions",
            ):
                self.assertEqual(first_decision[field], second_decision[field])
            self.assertEqual(
                [item["artifact_role"] for item in first_decision["source_artifacts"]],
                [item["artifact_role"] for item in second_decision["source_artifacts"]],
            )
            self.assertEqual(
                first_decision["human_review_checklist"],
                second_decision["human_review_checklist"],
            )
