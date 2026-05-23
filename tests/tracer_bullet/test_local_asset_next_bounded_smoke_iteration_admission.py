import contextlib
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


ADMISSION_OUTPUTS = (
    "local_asset_next_bounded_smoke_iteration_admission.json",
    "local_asset_next_bounded_smoke_iteration_admission_manifest.json",
    "local_asset_next_bounded_smoke_iteration_admission_summary.md",
    "local_asset_next_bounded_smoke_iteration_admission_checklist.md",
    "artifact_index.json",
    "artifact_index_manifest.json",
)
ADMISSION_ROLES = (
    "local_asset_next_bounded_smoke_iteration_admission",
    "local_asset_next_bounded_smoke_iteration_admission_manifest",
    "local_asset_next_bounded_smoke_iteration_admission_summary",
    "local_asset_next_bounded_smoke_iteration_admission_checklist",
)
BOUNDARY_FIELDS = (
    "scan_performed",
    "readiness_run_performed",
    "human_smoke_run_performed",
    "smoke_review_packet_run_performed",
    "smoke_promotion_gate_run_performed",
    "bounded_smoke_iteration_performed_by_admission",
    "iteration_review_packet_run_performed",
    "iteration_promotion_gate_run_performed",
    "cycle_contract_run_performed",
    "cycle_human_review_run_performed",
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
    "production_scan_performed",
    "production_scan_recommended",
    "production_scan_approved",
    "production_promotion_granted",
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


class LocalAssetNextBoundedSmokeIterationAdmissionTests(unittest.TestCase):
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

    def run_cli(self, args):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(args)
        return exit_code, json.loads(stdout.getvalue())

    def run_cycle_human_review(
        self,
        cycle_output,
        output_dir,
        *,
        human_decision="approve_cycle_contract_for_next_bounded_smoke_iteration",
    ):
        return self.run_cli(
            [
                "launch-local-asset-bounded-smoke-cycle-human-review",
                "--cycle-contract-output-dir",
                Path(cycle_output).as_posix(),
                "--output-dir",
                Path(output_dir).as_posix(),
                "--human-review-id",
                "cycle-review-1",
                "--human-reviewer-id",
                "reviewer-1",
                "--human-decision",
                human_decision,
                "--human-signoff-phrase",
                LOCAL_ASSET_BOUNDED_SMOKE_CYCLE_HUMAN_REVIEW_SIGNOFF_PHRASE,
                "--project-id",
                "cycle-test",
            ]
        )

    def build_ready_cycle_human_review(self, root, *, human_decision=None):
        chain = self.build_full_chain(root)
        cycle_output = Path(root) / "cycle-contract"
        cycle_output.mkdir()
        cycle_exit, _cycle_payload = self.run_cycle_contract(chain, cycle_output)
        self.assertEqual(cycle_exit, 0)
        review_output = Path(root) / "cycle-human-review"
        review_output.mkdir()
        kwargs = {}
        if human_decision is not None:
            kwargs["human_decision"] = human_decision
        review_exit, _review_payload = self.run_cycle_human_review(
            cycle_output,
            review_output,
            **kwargs,
        )
        self.assertEqual(review_exit, 0)
        return chain, cycle_output, review_output

    def run_admission(
        self,
        cycle_human_review_output,
        output_dir,
        *,
        requested_next_iteration_id="iteration-2",
        operator_notes=None,
    ):
        args = [
            "launch-local-asset-next-bounded-smoke-iteration-admission",
            "--cycle-human-review-output-dir",
            Path(cycle_human_review_output).as_posix(),
            "--output-dir",
            Path(output_dir).as_posix(),
            "--project-id",
            "cycle-test",
            "--requested-next-iteration-id",
            requested_next_iteration_id,
        ]
        if operator_notes is not None:
            args.extend(["--operator-notes", operator_notes])
        return self.run_cli(args)

    def write_graph(self, graph_path, nodes, *, graph_id="next-admission-graph"):
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

    def next_admission_node(self, *, node_id, review_output, output_dir):
        return {
            "node_id": node_id,
            "adapter_id": "local_asset_runtime",
            "capability": (
                "launch_local_asset_next_bounded_smoke_iteration_admission"
            ),
            "execution_mode": "fixture",
            "depends_on": [],
            "approval_checkpoint_required": True,
            "inputs": {
                "cycle_human_review_output_dir": Path(review_output).as_posix(),
                "output_dir": Path(output_dir).as_posix(),
                "project_id": "cycle-test",
                "requested_next_iteration_id": "iteration-2",
                "operator_notes": "prepare next iteration request only",
            },
        }

    def rewrite_review_manifest_hash(self, review_output):
        decision_path = (
            Path(review_output)
            / "local_asset_bounded_smoke_cycle_human_review_decision.json"
        )
        manifest_path = (
            Path(review_output)
            / "local_asset_bounded_smoke_cycle_human_review_manifest.json"
        )
        manifest = read_json(manifest_path)
        manifest["decision_sha256"] = sha256_file(decision_path)
        write_json(manifest_path, manifest)

    def test_full_chain_writes_admission_outputs_and_artifact_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _chain, _cycle_output, review_output = (
                self.build_ready_cycle_human_review(root)
            )
            admission_output = root / "next-admission"
            admission_output.mkdir()

            exit_code, payload = self.run_admission(review_output, admission_output)
            artifact_index = read_json(admission_output / "artifact_index.json")
            roles = {entry["artifact_role"] for entry in artifact_index["entries"]}

            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["complete"])
            for filename in ADMISSION_OUTPUTS:
                self.assertTrue((admission_output / filename).exists(), filename)
            self.assertEqual(roles, set(ADMISSION_ROLES))

    def test_approved_human_review_admits_prepare_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _chain, _cycle_output, review_output = (
                self.build_ready_cycle_human_review(root)
            )
            admission_output = root / "next-admission"
            admission_output.mkdir()

            exit_code, payload = self.run_admission(review_output, admission_output)
            admission = read_json(
                admission_output
                / "local_asset_next_bounded_smoke_iteration_admission.json"
            )

            self.assertEqual(exit_code, 0)
            for payload_like in (payload, admission):
                self.assertEqual(
                    payload_like["admission_status"],
                    "next_bounded_smoke_iteration_admission_ready",
                )
                self.assertEqual(
                    payload_like["admission_decision"],
                    "admit_prepare_next_bounded_smoke_iteration",
                )
                self.assertEqual(
                    payload_like["next_allowed_action"],
                    "create_next_bounded_smoke_iteration_execution_request",
                )
                self.assertTrue(
                    payload_like["next_bounded_smoke_iteration_prepare_admitted"]
                )
                self.assertFalse(
                    payload_like["next_bounded_smoke_iteration_execute_allowed"]
                )
                self.assertFalse(
                    payload_like["next_bounded_smoke_iteration_executed"]
                )
                self.assertFalse(payload_like["next_iteration_output_dir_created"])
                self.assertFalse(payload_like["production_scan_approved"])
                self.assertFalse(payload_like["production_promotion_granted"])

    def test_blocks_missing_required_human_review_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _chain, _cycle_output, review_output = (
                self.build_ready_cycle_human_review(root)
            )
            (
                review_output
                / "local_asset_bounded_smoke_cycle_human_review_decision.json"
            ).unlink()
            admission_output = root / "next-admission"
            admission_output.mkdir()

            exit_code, _payload = self.run_admission(review_output, admission_output)
            admission = read_json(
                admission_output
                / "local_asset_next_bounded_smoke_iteration_admission.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                admission["admission_status"],
                "blocked_missing_required_artifacts",
            )

    def test_blocks_untrusted_human_review_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _chain, _cycle_output, review_output = (
                self.build_ready_cycle_human_review(root)
            )
            manifest_path = (
                review_output
                / "local_asset_bounded_smoke_cycle_human_review_manifest.json"
            )
            manifest = read_json(manifest_path)
            manifest["decision_sha256"] = "0" * 64
            write_json(manifest_path, manifest)
            admission_output = root / "next-admission"
            admission_output.mkdir()

            exit_code, _payload = self.run_admission(review_output, admission_output)
            admission = read_json(
                admission_output
                / "local_asset_next_bounded_smoke_iteration_admission.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                admission["admission_status"],
                "blocked_untrusted_artifacts",
            )

    def test_blocks_if_human_review_not_approved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _chain, _cycle_output, review_output = (
                self.build_ready_cycle_human_review(
                    root,
                    human_decision="stop_cycle",
                )
            )
            admission_output = root / "next-admission"
            admission_output.mkdir()

            exit_code, _payload = self.run_admission(review_output, admission_output)
            admission = read_json(
                admission_output
                / "local_asset_next_bounded_smoke_iteration_admission.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                admission["admission_status"],
                "blocked_human_review_not_approved",
            )

    def test_blocks_if_prepare_not_allowed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _chain, _cycle_output, review_output = (
                self.build_ready_cycle_human_review(root)
            )
            decision_path = (
                review_output
                / "local_asset_bounded_smoke_cycle_human_review_decision.json"
            )
            decision = read_json(decision_path)
            decision["next_bounded_smoke_iteration_prepare_allowed"] = False
            write_json(decision_path, decision)
            self.rewrite_review_manifest_hash(review_output)
            admission_output = root / "next-admission"
            admission_output.mkdir()

            exit_code, _payload = self.run_admission(review_output, admission_output)
            admission = read_json(
                admission_output
                / "local_asset_next_bounded_smoke_iteration_admission.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                admission["admission_status"],
                "blocked_prepare_not_allowed",
            )

    def test_blocks_if_execute_already_allowed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _chain, _cycle_output, review_output = (
                self.build_ready_cycle_human_review(root)
            )
            decision_path = (
                review_output
                / "local_asset_bounded_smoke_cycle_human_review_decision.json"
            )
            decision = read_json(decision_path)
            decision["next_bounded_smoke_iteration_execute_allowed"] = True
            write_json(decision_path, decision)
            self.rewrite_review_manifest_hash(review_output)
            admission_output = root / "next-admission"
            admission_output.mkdir()

            exit_code, _payload = self.run_admission(review_output, admission_output)
            admission = read_json(
                admission_output
                / "local_asset_next_bounded_smoke_iteration_admission.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                admission["admission_status"],
                "blocked_execution_already_allowed",
            )
            self.assertFalse(admission["next_bounded_smoke_iteration_execute_allowed"])

    def test_blocks_production_boundary_violation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _chain, _cycle_output, review_output = (
                self.build_ready_cycle_human_review(root)
            )
            decision_path = (
                review_output
                / "local_asset_bounded_smoke_cycle_human_review_decision.json"
            )
            decision = read_json(decision_path)
            decision["production_scan_approved"] = True
            write_json(decision_path, decision)
            self.rewrite_review_manifest_hash(review_output)
            admission_output = root / "next-admission"
            admission_output.mkdir()

            exit_code, _payload = self.run_admission(review_output, admission_output)
            admission = read_json(
                admission_output
                / "local_asset_next_bounded_smoke_iteration_admission.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                admission["admission_status"],
                "blocked_production_boundary_violation",
            )

    def test_blocks_malformed_human_review_record(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _chain, _cycle_output, review_output = (
                self.build_ready_cycle_human_review(root)
            )
            decision_path = (
                review_output
                / "local_asset_bounded_smoke_cycle_human_review_decision.json"
            )
            decision = read_json(decision_path)
            decision["disallowed_actions"] = [
                action
                for action in decision["disallowed_actions"]
                if action != "production_scan"
            ]
            write_json(decision_path, decision)
            self.rewrite_review_manifest_hash(review_output)
            admission_output = root / "next-admission"
            admission_output.mkdir()

            exit_code, _payload = self.run_admission(review_output, admission_output)
            admission = read_json(
                admission_output
                / "local_asset_next_bounded_smoke_iteration_admission.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertIn(
                admission["admission_status"],
                (
                    "blocked_invalid_human_review_record",
                    "blocked_production_boundary_violation",
                ),
            )

    def test_fail_closed_on_existing_outputs(self):
        for filename in ADMISSION_OUTPUTS:
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    _chain, _cycle_output, review_output = (
                        self.build_ready_cycle_human_review(root)
                    )
                    admission_output = root / "next-admission"
                    admission_output.mkdir()
                    preexisting = admission_output / filename
                    preexisting.write_text("preexisting\n", encoding="utf-8")

                    exit_code, payload = self.run_admission(
                        review_output,
                        admission_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertFalse(payload["artifacts_written"])
                    self.assertEqual(
                        preexisting.read_text(encoding="utf-8"),
                        "preexisting\n",
                    )
                    for other_filename in ADMISSION_OUTPUTS:
                        if other_filename != filename:
                            self.assertFalse(
                                (admission_output / other_filename).exists()
                            )

    def test_missing_output_dir_structured_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _chain, _cycle_output, review_output = (
                self.build_ready_cycle_human_review(root)
            )
            admission_output = root / "missing-next-admission"

            exit_code, payload = self.run_admission(review_output, admission_output)

            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["artifacts_written"])
            self.assertFalse(admission_output.exists())

    def test_input_output_overlap_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _chain, _cycle_output, review_output = (
                self.build_ready_cycle_human_review(root)
            )
            cases = [
                (review_output, review_output),
                (review_output, review_output / "nested-next-admission"),
            ]
            cases[1][1].mkdir()
            parent_output = root / "parent-next-admission"
            parent_output.mkdir()
            nested_review = parent_output / "nested-cycle-human-review"
            nested_review.mkdir()
            cases.append((nested_review, parent_output))

            for input_dir, admission_output in cases:
                with self.subTest(admission_output=admission_output):
                    exit_code, payload = self.run_admission(
                        input_dir,
                        admission_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertFalse(payload["artifacts_written"])
                    self.assertFalse(
                        (
                            admission_output
                            / "local_asset_next_bounded_smoke_iteration_admission.json"
                        ).exists()
                    )

    def test_task_graph_node_writes_artifact_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _chain, _cycle_output, review_output = (
                self.build_ready_cycle_human_review(root)
            )
            admission_output = root / "next-admission"
            admission_output.mkdir()
            graph_output = root / "graph-output"
            graph_output.mkdir()
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.next_admission_node(
                        node_id="next-admission",
                        review_output=review_output,
                        output_dir=admission_output,
                    )
                ],
            )

            result = run_local_task_graph_fixture(graph_path, graph_output)
            artifact_outputs = read_json(result.artifact_outputs_manifest_path)
            roles = {
                artifact["artifact_role"]
                for artifact in artifact_outputs["artifacts"]
                if artifact["node_id"] == "next-admission"
            }

            self.assertTrue(result.success)
            for role in ADMISSION_ROLES:
                self.assertIn(role, roles)

    def test_no_scope_boundaries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _chain, _cycle_output, review_output = (
                self.build_ready_cycle_human_review(root)
            )
            admission_output = root / "next-admission"
            admission_output.mkdir()

            exit_code, payload = self.run_admission(review_output, admission_output)
            admission = read_json(
                admission_output
                / "local_asset_next_bounded_smoke_iteration_admission.json"
            )
            manifest = read_json(
                admission_output
                / "local_asset_next_bounded_smoke_iteration_admission_manifest.json"
            )
            graph_output = root / "graph-output"
            graph_output.mkdir()
            graph_path = root / "graph.json"
            graph_admission_output = root / "graph-next-admission"
            graph_admission_output.mkdir()
            self.write_graph(
                graph_path,
                [
                    self.next_admission_node(
                        node_id="next-admission",
                        review_output=review_output,
                        output_dir=graph_admission_output,
                    )
                ],
            )
            graph_result = run_local_task_graph_fixture(graph_path, graph_output)
            execution = read_json(graph_result.execution_manifest_path)
            node = execution["nodes"][0]

            self.assertEqual(exit_code, 0)
            for payload_like in (payload, admission, manifest, node):
                self.assertTrue(payload_like["required_human_approval"])
                self.assertTrue(payload_like["required_human_review"])
                self.assertFalse(
                    payload_like["next_bounded_smoke_iteration_execute_allowed"]
                )
                self.assertFalse(
                    payload_like["next_bounded_smoke_iteration_executed"]
                )
                self.assertFalse(payload_like["next_iteration_output_dir_created"])
                for field in BOUNDARY_FIELDS:
                    self.assertFalse(payload_like[field], field)

    def test_deterministic_stable_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _chain, _cycle_output, review_output = (
                self.build_ready_cycle_human_review(root)
            )
            first_output = root / "next-admission-1"
            second_output = root / "next-admission-2"
            first_output.mkdir()
            second_output.mkdir()

            first_exit, _first_payload = self.run_admission(
                review_output,
                first_output,
                requested_next_iteration_id="same-next",
            )
            second_exit, _second_payload = self.run_admission(
                review_output,
                second_output,
                requested_next_iteration_id="same-next",
            )
            first_admission = read_json(
                first_output
                / "local_asset_next_bounded_smoke_iteration_admission.json"
            )
            second_admission = read_json(
                second_output
                / "local_asset_next_bounded_smoke_iteration_admission.json"
            )

            self.assertEqual(first_exit, 0)
            self.assertEqual(second_exit, 0)
            for field in (
                "admission_status",
                "admission_decision",
                "next_allowed_action",
                "disallowed_actions",
            ):
                self.assertEqual(first_admission[field], second_admission[field])
            self.assertEqual(
                [
                    item["artifact_role"]
                    for item in first_admission["source_artifacts"]
                ],
                [
                    item["artifact_role"]
                    for item in second_admission["source_artifacts"]
                ],
            )
            self.assertEqual(
                first_admission["admission_checklist"],
                second_admission["admission_checklist"],
            )


if __name__ == "__main__":
    unittest.main()
