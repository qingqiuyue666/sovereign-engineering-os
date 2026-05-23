import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.task_graph import run_local_task_graph_fixture
from tests.tracer_bullet import (
    test_local_asset_next_bounded_smoke_iteration_admission as admission_helpers,
)
from tests.tracer_bullet import test_local_asset_bounded_smoke_cycle_contract as cycle_helpers


REQUEST_OUTPUTS = (
    "local_asset_next_bounded_smoke_iteration_execution_request.json",
    "local_asset_next_bounded_smoke_iteration_execution_request_manifest.json",
    "local_asset_next_bounded_smoke_iteration_execution_request_summary.md",
    "local_asset_next_bounded_smoke_iteration_execution_request_checklist.md",
    "artifact_index.json",
    "artifact_index_manifest.json",
)
REQUEST_ROLES = (
    "local_asset_next_bounded_smoke_iteration_execution_request",
    "local_asset_next_bounded_smoke_iteration_execution_request_manifest",
    "local_asset_next_bounded_smoke_iteration_execution_request_summary",
    "local_asset_next_bounded_smoke_iteration_execution_request_checklist",
)
BOUNDARY_FIELDS = (
    "scan_performed",
    "readiness_run_performed",
    "human_smoke_run_performed",
    "smoke_review_packet_run_performed",
    "smoke_promotion_gate_run_performed",
    "bounded_smoke_iteration_performed_by_request",
    "iteration_review_packet_run_performed",
    "iteration_promotion_gate_run_performed",
    "cycle_contract_run_performed",
    "cycle_human_review_run_performed",
    "next_admission_run_performed",
    "raw_candidate_content_read",
    "candidate_file_hashing_performed",
    "candidate_path_validation_performed",
    "candidate_path_listing_performed",
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
    "next_bounded_smoke_iteration_execute_allowed",
    "next_bounded_smoke_iteration_executed",
    "next_iteration_output_dir_created",
    "requested_next_iteration_output_dir_created",
    "candidate_input_path_checked",
    "candidate_input_path_listed",
    "candidate_input_file_read",
    "candidate_input_file_hashing_performed",
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


class LocalAssetNextBoundedSmokeIterationExecutionRequestTests(unittest.TestCase):
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
    run_cycle_human_review = (
        admission_helpers.LocalAssetNextBoundedSmokeIterationAdmissionTests.run_cycle_human_review
    )
    build_ready_cycle_human_review = (
        admission_helpers.LocalAssetNextBoundedSmokeIterationAdmissionTests.build_ready_cycle_human_review
    )
    run_admission = (
        admission_helpers.LocalAssetNextBoundedSmokeIterationAdmissionTests.run_admission
    )

    def run_cli(self, args):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(args)
        return exit_code, json.loads(stdout.getvalue())

    def build_ready_admission(self, root):
        _chain, _cycle_output, review_output = self.build_ready_cycle_human_review(root)
        admission_output = Path(root) / "next-admission"
        admission_output.mkdir()
        admission_exit, _admission_payload = self.run_admission(
            review_output,
            admission_output,
        )
        self.assertEqual(admission_exit, 0)
        return admission_output

    def build_non_ready_admission(self, root):
        _chain, _cycle_output, review_output = self.build_ready_cycle_human_review(
            root,
            human_decision="stop_cycle",
        )
        admission_output = Path(root) / "next-admission"
        admission_output.mkdir()
        admission_exit, _admission_payload = self.run_admission(
            review_output,
            admission_output,
        )
        self.assertEqual(admission_exit, 1)
        return admission_output

    def run_execution_request(
        self,
        next_admission_output,
        output_dir,
        *,
        requested_next_iteration_id="iteration-2",
        requested_candidate_input_dir=None,
        requested_next_iteration_output_dir=None,
        requested_max_files=5,
        requested_max_total_bytes=4096,
        requested_max_depth=2,
        request_id="request-1",
        operator_id="operator-1",
    ):
        candidate_input_dir = (
            requested_candidate_input_dir
            if requested_candidate_input_dir is not None
            else (Path(output_dir).parent / "future-candidate").as_posix()
        )
        next_iteration_output_dir = (
            requested_next_iteration_output_dir
            if requested_next_iteration_output_dir is not None
            else (Path(output_dir).parent / "future-iteration-output").as_posix()
        )
        return self.run_cli(
            [
                "launch-local-asset-next-bounded-smoke-iteration-execution-request",
                "--next-admission-output-dir",
                Path(next_admission_output).as_posix(),
                "--output-dir",
                Path(output_dir).as_posix(),
                "--requested-next-iteration-id",
                requested_next_iteration_id,
                "--requested-candidate-input-dir",
                candidate_input_dir,
                "--requested-next-iteration-output-dir",
                next_iteration_output_dir,
                "--requested-max-files",
                str(requested_max_files),
                "--requested-max-total-bytes",
                str(requested_max_total_bytes),
                "--requested-max-depth",
                str(requested_max_depth),
                "--project-id",
                "cycle-test",
                "--request-id",
                request_id,
                "--operator-id",
                operator_id,
                "--operator-notes",
                "request future iteration only",
                "--requested-compare-previous-scan-manifest-path",
                (Path(output_dir).parent / "previous-manifest.json").as_posix(),
                "--requested-previous-iteration-artifact-index-path",
                (Path(output_dir).parent / "previous-index.json").as_posix(),
            ]
        )

    def rewrite_admission_manifest_hash(self, admission_output):
        admission_path = (
            Path(admission_output)
            / "local_asset_next_bounded_smoke_iteration_admission.json"
        )
        manifest_path = (
            Path(admission_output)
            / "local_asset_next_bounded_smoke_iteration_admission_manifest.json"
        )
        manifest = read_json(manifest_path)
        manifest["admission_sha256"] = sha256_file(admission_path)
        write_json(manifest_path, manifest)

    def write_graph(self, graph_path, nodes, *, graph_id="execution-request-graph"):
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

    def execution_request_node(self, *, node_id, admission_output, output_dir):
        return {
            "node_id": node_id,
            "adapter_id": "local_asset_runtime",
            "capability": (
                "launch_local_asset_next_bounded_smoke_iteration_execution_request"
            ),
            "execution_mode": "fixture",
            "depends_on": [],
            "approval_checkpoint_required": True,
            "inputs": {
                "next_admission_output_dir": Path(admission_output).as_posix(),
                "output_dir": Path(output_dir).as_posix(),
                "project_id": "cycle-test",
                "request_id": "graph-request-1",
                "operator_id": "operator-1",
                "operator_notes": "request future iteration only",
                "requested_next_iteration_id": "iteration-2",
                "requested_candidate_input_dir": (
                    Path(output_dir).parent / "future-candidate"
                ).as_posix(),
                "requested_next_iteration_output_dir": (
                    Path(output_dir).parent / "future-iteration-output"
                ).as_posix(),
                "requested_max_files": 5,
                "requested_max_total_bytes": 4096,
                "requested_max_depth": 2,
                "requested_compare_previous_scan_manifest_path": (
                    Path(output_dir).parent / "previous-manifest.json"
                ).as_posix(),
                "requested_previous_iteration_artifact_index_path": (
                    Path(output_dir).parent / "previous-index.json"
                ).as_posix(),
            },
        }

    def test_full_chain_writes_request_outputs_and_artifact_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            admission_output = self.build_ready_admission(root)
            request_output = root / "execution-request"
            request_output.mkdir()

            exit_code, payload = self.run_execution_request(
                admission_output,
                request_output,
            )
            artifact_index = read_json(request_output / "artifact_index.json")
            roles = {entry["artifact_role"] for entry in artifact_index["entries"]}

            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["complete"])
            for filename in REQUEST_OUTPUTS:
                self.assertTrue((request_output / filename).exists(), filename)
            self.assertEqual(roles, set(REQUEST_ROLES))

    def test_ready_admission_creates_request_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            admission_output = self.build_ready_admission(root)
            request_output = root / "execution-request"
            request_output.mkdir()

            exit_code, payload = self.run_execution_request(
                admission_output,
                request_output,
            )
            request = read_json(
                request_output
                / "local_asset_next_bounded_smoke_iteration_execution_request.json"
            )

            self.assertEqual(exit_code, 0)
            for payload_like in (payload, request):
                self.assertEqual(
                    payload_like["request_status"],
                    "next_bounded_smoke_iteration_execution_request_ready",
                )
                self.assertEqual(
                    payload_like["request_decision"],
                    "create_future_bounded_smoke_iteration_execution_request",
                )
                self.assertEqual(
                    payload_like["next_allowed_action"],
                    "await_separate_bounded_smoke_iteration_runner",
                )
                self.assertTrue(payload_like["future_execution_request_created"])
                self.assertFalse(
                    payload_like["next_bounded_smoke_iteration_execute_allowed"]
                )
                self.assertFalse(
                    payload_like["next_bounded_smoke_iteration_executed"]
                )
                self.assertFalse(payload_like["next_iteration_output_dir_created"])
                self.assertFalse(
                    payload_like["requested_next_iteration_output_dir_created"]
                )
                self.assertFalse(payload_like["candidate_input_path_checked"])
                self.assertFalse(payload_like["candidate_input_path_listed"])
                self.assertFalse(payload_like["candidate_input_file_read"])
                self.assertFalse(
                    payload_like["candidate_input_file_hashing_performed"]
                )
                self.assertFalse(payload_like["production_scan_approved"])
                self.assertFalse(payload_like["production_promotion_granted"])

    def test_requested_path_metadata_not_touched(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            admission_output = self.build_ready_admission(root)
            request_output = root / "execution-request"
            request_output.mkdir()
            missing_candidate = root / "missing-candidate"
            missing_future_output = root / "missing-future-output"

            exit_code, _payload = self.run_execution_request(
                admission_output,
                request_output,
                requested_candidate_input_dir=missing_candidate.as_posix(),
                requested_next_iteration_output_dir=missing_future_output.as_posix(),
            )
            request = read_json(
                request_output
                / "local_asset_next_bounded_smoke_iteration_execution_request.json"
            )

            self.assertEqual(exit_code, 0)
            self.assertFalse(missing_candidate.exists())
            self.assertFalse(missing_future_output.exists())
            self.assertFalse(request["candidate_input_path_checked"])
            self.assertFalse(request["candidate_input_path_listed"])
            self.assertFalse(request["candidate_input_file_read"])
            self.assertFalse(request["candidate_input_file_hashing_performed"])
            self.assertEqual(
                request["requested_candidate_input_dir"],
                missing_candidate.as_posix(),
            )
            self.assertEqual(
                request["requested_next_iteration_output_dir"],
                missing_future_output.as_posix(),
            )

    def test_blocks_missing_required_admission_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            admission_output = self.build_ready_admission(root)
            (
                admission_output
                / "local_asset_next_bounded_smoke_iteration_admission.json"
            ).unlink()
            request_output = root / "execution-request"
            request_output.mkdir()

            exit_code, _payload = self.run_execution_request(
                admission_output,
                request_output,
            )
            request = read_json(
                request_output
                / "local_asset_next_bounded_smoke_iteration_execution_request.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                request["request_status"],
                "blocked_missing_required_artifacts",
            )

    def test_blocks_untrusted_admission_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            admission_output = self.build_ready_admission(root)
            manifest_path = (
                admission_output
                / "local_asset_next_bounded_smoke_iteration_admission_manifest.json"
            )
            manifest = read_json(manifest_path)
            manifest["admission_sha256"] = "0" * 64
            write_json(manifest_path, manifest)
            request_output = root / "execution-request"
            request_output.mkdir()

            exit_code, _payload = self.run_execution_request(
                admission_output,
                request_output,
            )
            request = read_json(
                request_output
                / "local_asset_next_bounded_smoke_iteration_execution_request.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(request["request_status"], "blocked_untrusted_artifacts")

    def test_blocks_if_admission_not_ready(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            admission_output = self.build_non_ready_admission(root)
            request_output = root / "execution-request"
            request_output.mkdir()

            exit_code, _payload = self.run_execution_request(
                admission_output,
                request_output,
            )
            request = read_json(
                request_output
                / "local_asset_next_bounded_smoke_iteration_execution_request.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(request["request_status"], "blocked_admission_not_ready")

    def test_blocks_if_prepare_not_admitted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            admission_output = self.build_ready_admission(root)
            admission_path = (
                admission_output
                / "local_asset_next_bounded_smoke_iteration_admission.json"
            )
            admission = read_json(admission_path)
            admission["next_bounded_smoke_iteration_prepare_admitted"] = False
            write_json(admission_path, admission)
            self.rewrite_admission_manifest_hash(admission_output)
            request_output = root / "execution-request"
            request_output.mkdir()

            exit_code, _payload = self.run_execution_request(
                admission_output,
                request_output,
            )
            request = read_json(
                request_output
                / "local_asset_next_bounded_smoke_iteration_execution_request.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(request["request_status"], "blocked_prepare_not_admitted")

    def test_blocks_if_execute_already_allowed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            admission_output = self.build_ready_admission(root)
            admission_path = (
                admission_output
                / "local_asset_next_bounded_smoke_iteration_admission.json"
            )
            admission = read_json(admission_path)
            admission["next_bounded_smoke_iteration_execute_allowed"] = True
            write_json(admission_path, admission)
            self.rewrite_admission_manifest_hash(admission_output)
            request_output = root / "execution-request"
            request_output.mkdir()

            exit_code, _payload = self.run_execution_request(
                admission_output,
                request_output,
            )
            request = read_json(
                request_output
                / "local_asset_next_bounded_smoke_iteration_execution_request.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                request["request_status"],
                "blocked_execution_already_allowed",
            )

    def test_blocks_if_iteration_already_executed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            admission_output = self.build_ready_admission(root)
            admission_path = (
                admission_output
                / "local_asset_next_bounded_smoke_iteration_admission.json"
            )
            admission = read_json(admission_path)
            admission["next_bounded_smoke_iteration_executed"] = True
            write_json(admission_path, admission)
            self.rewrite_admission_manifest_hash(admission_output)
            request_output = root / "execution-request"
            request_output.mkdir()

            exit_code, _payload = self.run_execution_request(
                admission_output,
                request_output,
            )
            request = read_json(
                request_output
                / "local_asset_next_bounded_smoke_iteration_execution_request.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                request["request_status"],
                "blocked_iteration_already_executed",
            )

    def test_blocks_if_next_iteration_output_already_created(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            admission_output = self.build_ready_admission(root)
            admission_path = (
                admission_output
                / "local_asset_next_bounded_smoke_iteration_admission.json"
            )
            admission = read_json(admission_path)
            admission["next_iteration_output_dir_created"] = True
            write_json(admission_path, admission)
            self.rewrite_admission_manifest_hash(admission_output)
            request_output = root / "execution-request"
            request_output.mkdir()

            exit_code, _payload = self.run_execution_request(
                admission_output,
                request_output,
            )
            request = read_json(
                request_output
                / "local_asset_next_bounded_smoke_iteration_execution_request.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                request["request_status"],
                "blocked_next_iteration_output_already_created",
            )

    def test_blocks_production_boundary_violation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            admission_output = self.build_ready_admission(root)
            admission_path = (
                admission_output
                / "local_asset_next_bounded_smoke_iteration_admission.json"
            )
            admission = read_json(admission_path)
            admission["production_scan_approved"] = True
            write_json(admission_path, admission)
            self.rewrite_admission_manifest_hash(admission_output)
            request_output = root / "execution-request"
            request_output.mkdir()

            exit_code, _payload = self.run_execution_request(
                admission_output,
                request_output,
            )
            request = read_json(
                request_output
                / "local_asset_next_bounded_smoke_iteration_execution_request.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                request["request_status"],
                "blocked_production_boundary_violation",
            )

    def test_blocks_invalid_requested_limits(self):
        invalid_cases = (
            ("requested_max_files", {"requested_max_files": 0}),
            ("requested_max_total_bytes", {"requested_max_total_bytes": 0}),
            ("requested_max_depth", {"requested_max_depth": -1}),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            admission_output = self.build_ready_admission(root)
            for label, kwargs in invalid_cases:
                with self.subTest(label=label):
                    request_output = root / ("execution-request-" + label)
                    request_output.mkdir()
                    exit_code, _payload = self.run_execution_request(
                        admission_output,
                        request_output,
                        **kwargs,
                    )
                    request = read_json(
                        request_output
                        / "local_asset_next_bounded_smoke_iteration_execution_request.json"
                    )
                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        request["request_status"],
                        "blocked_invalid_requested_limits",
                    )

    def test_blocks_invalid_requested_metadata(self):
        invalid_cases = (
            (
                "requested_next_iteration_id",
                {"requested_next_iteration_id": ""},
            ),
            (
                "requested_candidate_input_dir",
                {"requested_candidate_input_dir": ""},
            ),
            (
                "requested_next_iteration_output_dir",
                {"requested_next_iteration_output_dir": ""},
            ),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            admission_output = self.build_ready_admission(root)
            for label, kwargs in invalid_cases:
                with self.subTest(label=label):
                    request_output = root / ("execution-request-" + label)
                    request_output.mkdir()
                    exit_code, _payload = self.run_execution_request(
                        admission_output,
                        request_output,
                        **kwargs,
                    )
                    request = read_json(
                        request_output
                        / "local_asset_next_bounded_smoke_iteration_execution_request.json"
                    )
                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        request["request_status"],
                        "blocked_invalid_requested_metadata",
                    )

    def test_blocks_malformed_admission_record(self):
        cases = ("wrong_next_allowed_action", "missing_disallowed_action")
        for case in cases:
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    admission_output = self.build_ready_admission(root)
                    admission_path = (
                        admission_output
                        / "local_asset_next_bounded_smoke_iteration_admission.json"
                    )
                    admission = read_json(admission_path)
                    if case == "wrong_next_allowed_action":
                        admission["next_allowed_action"] = "execute_now"
                    else:
                        admission["disallowed_actions"] = [
                            action
                            for action in admission["disallowed_actions"]
                            if action != "production_scan"
                        ]
                    write_json(admission_path, admission)
                    self.rewrite_admission_manifest_hash(admission_output)
                    request_output = root / "execution-request"
                    request_output.mkdir()

                    exit_code, _payload = self.run_execution_request(
                        admission_output,
                        request_output,
                    )
                    request = read_json(
                        request_output
                        / "local_asset_next_bounded_smoke_iteration_execution_request.json"
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertIn(
                        request["request_status"],
                        (
                            "blocked_invalid_admission_record",
                            "blocked_production_boundary_violation",
                        ),
                    )

    def test_fail_closed_on_existing_outputs(self):
        for filename in REQUEST_OUTPUTS:
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    admission_output = self.build_ready_admission(root)
                    request_output = root / "execution-request"
                    request_output.mkdir()
                    preexisting = request_output / filename
                    preexisting.write_text("preexisting\n", encoding="utf-8")

                    exit_code, payload = self.run_execution_request(
                        admission_output,
                        request_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertFalse(payload["artifacts_written"])
                    self.assertEqual(
                        preexisting.read_text(encoding="utf-8"),
                        "preexisting\n",
                    )
                    for other_filename in REQUEST_OUTPUTS:
                        if other_filename != filename:
                            self.assertFalse(
                                (request_output / other_filename).exists()
                            )

    def test_missing_output_dir_structured_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            admission_output = self.build_ready_admission(root)
            request_output = root / "missing-execution-request"

            exit_code, payload = self.run_execution_request(
                admission_output,
                request_output,
            )

            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["artifacts_written"])
            self.assertFalse(request_output.exists())

    def test_input_output_overlap_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            admission_output = self.build_ready_admission(root)
            cases = [
                (admission_output, admission_output),
                (admission_output, admission_output / "nested-execution-request"),
            ]
            cases[1][1].mkdir()
            parent_output = root / "parent-execution-request"
            parent_output.mkdir()
            nested_admission = parent_output / "nested-next-admission"
            nested_admission.mkdir()
            cases.append((nested_admission, parent_output))

            for input_dir, request_output in cases:
                with self.subTest(request_output=request_output):
                    exit_code, payload = self.run_execution_request(
                        input_dir,
                        request_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertFalse(payload["artifacts_written"])
                    self.assertFalse(
                        (
                            request_output
                            / "local_asset_next_bounded_smoke_iteration_execution_request.json"
                        ).exists()
                    )

    def test_task_graph_node_writes_artifact_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            admission_output = self.build_ready_admission(root)
            request_output = root / "execution-request"
            request_output.mkdir()
            graph_output = root / "graph-output"
            graph_output.mkdir()
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.execution_request_node(
                        node_id="execution-request",
                        admission_output=admission_output,
                        output_dir=request_output,
                    )
                ],
            )

            result = run_local_task_graph_fixture(graph_path, graph_output)
            artifact_outputs = read_json(result.artifact_outputs_manifest_path)
            roles = {
                artifact["artifact_role"]
                for artifact in artifact_outputs["artifacts"]
                if artifact["node_id"] == "execution-request"
            }

            self.assertTrue(result.success)
            for role in REQUEST_ROLES:
                self.assertIn(role, roles)

    def test_no_scope_boundaries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            admission_output = self.build_ready_admission(root)
            request_output = root / "execution-request"
            request_output.mkdir()

            exit_code, payload = self.run_execution_request(
                admission_output,
                request_output,
            )
            request = read_json(
                request_output
                / "local_asset_next_bounded_smoke_iteration_execution_request.json"
            )
            manifest = read_json(
                request_output
                / "local_asset_next_bounded_smoke_iteration_execution_request_manifest.json"
            )
            graph_output = root / "graph-output"
            graph_output.mkdir()
            graph_path = root / "graph.json"
            graph_request_output = root / "graph-execution-request"
            graph_request_output.mkdir()
            self.write_graph(
                graph_path,
                [
                    self.execution_request_node(
                        node_id="execution-request",
                        admission_output=admission_output,
                        output_dir=graph_request_output,
                    )
                ],
            )
            graph_result = run_local_task_graph_fixture(graph_path, graph_output)
            execution = read_json(graph_result.execution_manifest_path)
            node = execution["nodes"][0]

            self.assertEqual(exit_code, 0)
            for payload_like in (payload, request, manifest, node):
                self.assertTrue(payload_like["required_human_approval"])
                self.assertTrue(payload_like["required_human_review"])
                for field in BOUNDARY_FIELDS:
                    self.assertFalse(payload_like[field], field)

    def test_deterministic_stable_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            admission_output = self.build_ready_admission(root)
            first_output = root / "execution-request-1"
            second_output = root / "execution-request-2"
            first_output.mkdir()
            second_output.mkdir()

            first_exit, _first_payload = self.run_execution_request(
                admission_output,
                first_output,
                requested_next_iteration_id="same-next",
            )
            second_exit, _second_payload = self.run_execution_request(
                admission_output,
                second_output,
                requested_next_iteration_id="same-next",
            )
            first_request = read_json(
                first_output
                / "local_asset_next_bounded_smoke_iteration_execution_request.json"
            )
            second_request = read_json(
                second_output
                / "local_asset_next_bounded_smoke_iteration_execution_request.json"
            )

            self.assertEqual(first_exit, 0)
            self.assertEqual(second_exit, 0)
            for field in (
                "request_status",
                "request_decision",
                "next_allowed_action",
                "disallowed_actions",
                "requested_limits",
            ):
                self.assertEqual(first_request[field], second_request[field])
            self.assertEqual(
                [
                    item["artifact_role"]
                    for item in first_request["source_artifacts"]
                ],
                [
                    item["artifact_role"]
                    for item in second_request["source_artifacts"]
                ],
            )
            self.assertEqual(
                first_request["request_checklist"],
                second_request["request_checklist"],
            )


if __name__ == "__main__":
    unittest.main()
