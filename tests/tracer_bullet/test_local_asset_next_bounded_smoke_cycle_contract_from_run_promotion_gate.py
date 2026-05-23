import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from kernel.assets.local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate import (
    build_local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.task_graph import run_local_task_graph_fixture
from tests.tracer_bullet import (
    test_local_asset_next_bounded_smoke_iteration_run_promotion_gate as gate_helpers,
)


CONTRACT_OUTPUTS = (
    "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate.json",
    "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_manifest.json",
    "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_summary.md",
    "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_checklist.md",
    "artifact_index.json",
    "artifact_index_manifest.json",
)
CONTRACT_ROLES = (
    "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate",
    "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_manifest",
    "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_summary",
    "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_checklist",
)
NO_SCOPE_FIELDS = (
    "production_scan_approved",
    "production_promotion_granted",
    "automatic_approval_performed",
    "autonomous_execution_performed",
    "runner_execution_performed_by_contract",
    "review_packet_generation_performed_by_contract",
    "run_promotion_gate_reexecution_performed",
    "candidate_input_path_checked_by_contract",
    "candidate_input_path_listed_by_contract",
    "candidate_input_file_read_by_contract",
    "candidate_input_file_hashing_performed_by_contract",
    "raw_candidate_content_read_by_contract",
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
)
SOURCE_GATE_FILE = "local_asset_next_bounded_smoke_iteration_run_promotion_gate.json"
SOURCE_GATE_MANIFEST_FILE = (
    "local_asset_next_bounded_smoke_iteration_run_promotion_gate_manifest.json"
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    Path(path).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class LocalAssetNextBoundedSmokeCycleContractFromRunPromotionGateTests(
    unittest.TestCase
):
    def helper(self):
        return gate_helpers.LocalAssetNextBoundedSmokeIterationRunPromotionGateTests(
            methodName="test_full_chain_writes_promotion_gate_artifacts"
        )

    def run_cli(self, args):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(args)
        return exit_code, json.loads(stdout.getvalue())

    def build_ready_promotion_gate(self, root):
        helper = self.helper()
        review, runner_output, actual = helper.build_ready_review_packet(root)
        gate_output = Path(root) / "run-promotion-gate"
        gate_output.mkdir()
        exit_code, payload = helper.run_promotion_gate(
            review,
            gate_output,
            promotion_gate_id="ready-run-promotion-gate-1",
        )
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["complete"])
        return gate_output, review, runner_output, actual

    def run_contract(
        self,
        gate_output,
        output_dir,
        *,
        cycle_contract_id="next-cycle-contract-1",
        project_id="cycle-test",
        reviewer_id="cycle-reviewer-1",
        operator_notes="package approved run into next cycle contract",
    ):
        args = [
            "launch-local-asset-next-bounded-smoke-cycle-contract-from-run-promotion-gate",
            "--run-promotion-gate-output-dir",
            Path(gate_output).as_posix(),
            "--output-dir",
            Path(output_dir).as_posix(),
            "--cycle-contract-id",
            cycle_contract_id,
        ]
        if project_id is not None:
            args.extend(["--project-id", project_id])
        if reviewer_id is not None:
            args.extend(["--reviewer-id", reviewer_id])
        if operator_notes is not None:
            args.extend(["--operator-notes", operator_notes])
        return self.run_cli(args)

    def rewrite_gate_manifest_hash(self, gate_output):
        gate_output = Path(gate_output)
        gate_path = gate_output / SOURCE_GATE_FILE
        manifest_path = gate_output / SOURCE_GATE_MANIFEST_FILE
        manifest = read_json(manifest_path)
        manifest["gate_sha256"] = sha256_file(gate_path)
        write_json(manifest_path, manifest)

    def rewrite_index_manifest_hash(self, gate_output):
        gate_output = Path(gate_output)
        index_path = gate_output / "artifact_index.json"
        manifest_path = gate_output / "artifact_index_manifest.json"
        manifest = read_json(manifest_path)
        manifest["artifact_index_sha256"] = sha256_file(index_path)
        write_json(manifest_path, manifest)

    def contract_node(self, *, node_id, gate_output, output_dir):
        return {
            "node_id": node_id,
            "adapter_id": "local_asset_runtime",
            "capability": (
                "launch_local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate"
            ),
            "execution_mode": "fixture",
            "depends_on": [],
            "approval_checkpoint_required": True,
            "inputs": {
                "run_promotion_gate_output_dir": Path(gate_output).as_posix(),
                "output_dir": Path(output_dir).as_posix(),
                "cycle_contract_id": "graph-next-cycle-contract-1",
                "project_id": "cycle-test",
                "reviewer_id": "cycle-reviewer-1",
                "operator_notes": "graph packages approved run promotion gate",
            },
        }

    def write_graph(self, graph_path, nodes):
        write_json_atomically(
            graph_path,
            {
                "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
                "graph_id": "cycle-contract-from-run-gate-graph",
                "execution_mode": "fixture_execution",
                "authority": "non_authority",
                "required_human_approval": True,
                "nodes": nodes,
            },
        )

    def assert_contract_artifacts_absent(self, output_dir):
        for filename in CONTRACT_OUTPUTS:
            self.assertFalse((Path(output_dir) / filename).exists(), filename)

    def assert_no_scope_false(self, payload_like):
        for field_name in NO_SCOPE_FIELDS:
            self.assertFalse(payload_like[field_name], field_name)

    def test_full_chain_from_run_promotion_gate_creates_contract_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            gate_output, _review, _runner_output, _actual = (
                self.build_ready_promotion_gate(root)
            )
            contract_output = root / "next-cycle-contract"
            contract_output.mkdir()

            exit_code, payload = self.run_contract(gate_output, contract_output)
            index = read_json(contract_output / "artifact_index.json")
            roles = {entry["artifact_role"] for entry in index["entries"]}

            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["complete"])
            for filename in CONTRACT_OUTPUTS:
                self.assertTrue((contract_output / filename).exists(), filename)
            self.assertEqual(roles, set(CONTRACT_ROLES))

    def test_ready_source_gate_creates_required_contract_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            gate_output, _review, _runner_output, _actual = (
                self.build_ready_promotion_gate(root)
            )
            contract_output = root / "next-cycle-contract"
            contract_output.mkdir()

            exit_code, payload = self.run_contract(gate_output, contract_output)
            contract = read_json(
                contract_output
                / "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate.json"
            )
            manifest = read_json(
                contract_output
                / "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_manifest.json"
            )
            index_manifest = read_json(
                contract_output / "artifact_index_manifest.json"
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["complete"])
            self.assertEqual(
                contract["contract_type"],
                "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_v1",
            )
            self.assertEqual(
                contract["authority"],
                "non_authority_bounded_cycle_contract_record",
            )
            self.assertEqual(
                contract["execution_capability"],
                "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_only",
            )
            self.assertEqual(
                contract["contract_status"],
                "next_bounded_smoke_cycle_contract_ready",
            )
            self.assertEqual(
                contract["contract_decision"],
                "create_bounded_smoke_cycle_contract_from_approved_run",
            )
            self.assertEqual(
                contract["next_allowed_action"],
                "submit_next_bounded_smoke_cycle_contract_for_human_review",
            )
            self.assertTrue(contract["cycle_contract_created"])
            self.assertTrue(contract["cycle_contract_from_run_promotion_gate"])
            self.assertEqual(
                manifest["contract_sha256"],
                sha256_file(
                    contract_output
                    / "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate.json"
                ),
            )
            self.assertEqual(
                index_manifest["artifact_index_sha256"],
                sha256_file(contract_output / "artifact_index.json"),
            )

    def test_contract_is_cycle_contract_only_not_production_approval(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            gate_output, _review, _runner_output, _actual = (
                self.build_ready_promotion_gate(root)
            )
            contract_output = root / "next-cycle-contract"
            contract_output.mkdir()

            exit_code, payload = self.run_contract(gate_output, contract_output)
            contract = read_json(
                contract_output
                / "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate.json"
            )

            self.assertEqual(exit_code, 0)
            for payload_like in (payload, contract):
                self.assertFalse(payload_like["production_scan_approved"])
                self.assertFalse(payload_like["production_promotion_granted"])
                self.assertFalse(payload_like["automatic_approval_performed"])
                self.assertFalse(payload_like["autonomous_execution_performed"])
                self.assertFalse(
                    payload_like["runner_execution_performed_by_contract"]
                )
                self.assertFalse(
                    payload_like["review_packet_generation_performed_by_contract"]
                )
                self.assertEqual(
                    payload_like["next_allowed_action"],
                    "submit_next_bounded_smoke_cycle_contract_for_human_review",
                )

    def test_contract_does_not_touch_live_candidate_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            gate_output, _review, _runner_output, _actual = (
                self.build_ready_promotion_gate(root)
            )
            gate = read_json(gate_output / SOURCE_GATE_FILE)
            candidate = Path(gate["requested_candidate_input_dir"])
            shutil.rmtree(candidate)
            os.symlink("/definitely/not-read-by-cycle-contract", candidate)
            contract_output = root / "next-cycle-contract"
            contract_output.mkdir()

            exit_code, payload = self.run_contract(gate_output, contract_output)

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                payload["contract_status"],
                "next_bounded_smoke_cycle_contract_ready",
            )
            self.assertFalse(payload["candidate_input_path_checked_by_contract"])
            self.assertFalse(payload["candidate_input_path_listed_by_contract"])
            self.assertFalse(payload["candidate_input_file_read_by_contract"])
            self.assertFalse(
                payload["candidate_input_file_hashing_performed_by_contract"]
            )

    def test_blocks_missing_required_source_artifacts(self):
        for filename in (
            SOURCE_GATE_FILE,
            SOURCE_GATE_MANIFEST_FILE,
            "artifact_index.json",
            "artifact_index_manifest.json",
        ):
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    gate_output, _review, _runner_output, _actual = (
                        self.build_ready_promotion_gate(root)
                    )
                    (gate_output / filename).unlink()
                    contract_output = root / "next-cycle-contract"
                    contract_output.mkdir()

                    exit_code, payload = self.run_contract(
                        gate_output,
                        contract_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        payload["contract_status"],
                        "blocked_missing_required_artifacts",
                    )

    def test_blocks_malformed_source_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            gate_output, _review, _runner_output, _actual = (
                self.build_ready_promotion_gate(root)
            )
            (gate_output / SOURCE_GATE_FILE).write_text("{", encoding="utf-8")
            contract_output = root / "next-cycle-contract"
            contract_output.mkdir()

            exit_code, payload = self.run_contract(gate_output, contract_output)

            self.assertEqual(exit_code, 1)
            self.assertEqual(payload["contract_status"], "blocked_untrusted_artifacts")

    def test_blocks_source_symlink_artifacts(self):
        for filename in (
            SOURCE_GATE_FILE,
            SOURCE_GATE_MANIFEST_FILE,
            "artifact_index.json",
            "artifact_index_manifest.json",
        ):
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    gate_output, _review, _runner_output, _actual = (
                        self.build_ready_promotion_gate(root)
                    )
                    (gate_output / filename).unlink()
                    os.symlink(root / "target-does-not-need-to-exist", gate_output / filename)
                    contract_output = root / "next-cycle-contract"
                    contract_output.mkdir()

                    exit_code, payload = self.run_contract(
                        gate_output,
                        contract_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        payload["contract_status"],
                        "blocked_untrusted_artifacts",
                    )

    def test_blocks_source_type_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            gate_output, _review, _runner_output, _actual = (
                self.build_ready_promotion_gate(root)
            )
            gate_path = gate_output / SOURCE_GATE_FILE
            gate = read_json(gate_path)
            gate["gate_type"] = "wrong_gate_type"
            write_json(gate_path, gate)
            self.rewrite_gate_manifest_hash(gate_output)
            contract_output = root / "next-cycle-contract"
            contract_output.mkdir()

            exit_code, payload = self.run_contract(gate_output, contract_output)

            self.assertEqual(exit_code, 1)
            self.assertEqual(payload["contract_status"], "blocked_untrusted_artifacts")

    def test_blocks_source_manifest_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            gate_output, _review, _runner_output, _actual = (
                self.build_ready_promotion_gate(root)
            )
            manifest_path = gate_output / SOURCE_GATE_MANIFEST_FILE
            manifest = read_json(manifest_path)
            manifest["gate_sha256"] = "0" * 64
            write_json(manifest_path, manifest)
            contract_output = root / "next-cycle-contract"
            contract_output.mkdir()

            exit_code, payload = self.run_contract(gate_output, contract_output)

            self.assertEqual(exit_code, 1)
            self.assertEqual(payload["contract_status"], "blocked_untrusted_artifacts")

    def test_blocks_source_artifact_index_manifest_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            gate_output, _review, _runner_output, _actual = (
                self.build_ready_promotion_gate(root)
            )
            manifest_path = gate_output / "artifact_index_manifest.json"
            manifest = read_json(manifest_path)
            manifest["artifact_index_sha256"] = "0" * 64
            write_json(manifest_path, manifest)
            contract_output = root / "next-cycle-contract"
            contract_output.mkdir()

            exit_code, payload = self.run_contract(gate_output, contract_output)

            self.assertEqual(exit_code, 1)
            self.assertEqual(payload["contract_status"], "blocked_untrusted_artifacts")

    def test_blocks_optional_source_artifacts_missing_hash_bindings(self):
        cases = (
            ("summary_sha256", "summary"),
            ("checklist_sha256", "checklist"),
        )
        for hash_field, artifact_name in cases:
            with self.subTest(hash_field=hash_field):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    gate_output, _review, _runner_output, _actual = (
                        self.build_ready_promotion_gate(root)
                    )
                    manifest_path = gate_output / SOURCE_GATE_MANIFEST_FILE
                    manifest = read_json(manifest_path)
                    manifest.pop(hash_field, None)
                    write_json(manifest_path, manifest)
                    contract_output = root / "next-cycle-contract"
                    contract_output.mkdir()

                    exit_code, payload = self.run_contract(
                        gate_output,
                        contract_output,
                    )

                    self.assertEqual(exit_code, 1, artifact_name)
                    self.assertEqual(
                        payload["contract_status"],
                        "blocked_untrusted_artifacts",
                    )

    def test_blocks_source_gate_not_ready(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            gate_output, _review, _runner_output, _actual = (
                self.build_ready_promotion_gate(root)
            )
            gate_path = gate_output / SOURCE_GATE_FILE
            gate = read_json(gate_path)
            gate["gate_status"] = "next_bounded_smoke_iteration_gate_still_under_repair"
            write_json(gate_path, gate)
            self.rewrite_gate_manifest_hash(gate_output)
            contract_output = root / "next-cycle-contract"
            contract_output.mkdir()

            exit_code, payload = self.run_contract(gate_output, contract_output)

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                payload["contract_status"],
                "blocked_source_gate_not_ready",
            )

    def test_blocks_source_gate_decision_or_next_action_mismatch(self):
        cases = (
            ("gate_decision", "wrong_decision"),
            ("next_allowed_action", "wrong_action"),
        )
        for field_name, value in cases:
            with self.subTest(field_name=field_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    gate_output, _review, _runner_output, _actual = (
                        self.build_ready_promotion_gate(root)
                    )
                    gate_path = gate_output / SOURCE_GATE_FILE
                    gate = read_json(gate_path)
                    gate[field_name] = value
                    write_json(gate_path, gate)
                    self.rewrite_gate_manifest_hash(gate_output)
                    contract_output = root / "next-cycle-contract"
                    contract_output.mkdir()

                    exit_code, payload = self.run_contract(
                        gate_output,
                        contract_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        payload["contract_status"],
                        "blocked_invalid_source_gate_record",
                    )

    def test_blocks_source_gate_contains_blocking_fields(self):
        cases = (
            ("gate_blockers", [{"reason": "manual_blocker"}]),
            ("missing_required_artifacts", [{"artifact_role": "missing"}]),
            ("untrusted_artifacts", [{"artifact_role": "untrusted"}]),
        )
        for field_name, value in cases:
            with self.subTest(field_name=field_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    gate_output, _review, _runner_output, _actual = (
                        self.build_ready_promotion_gate(root)
                    )
                    gate_path = gate_output / SOURCE_GATE_FILE
                    gate = read_json(gate_path)
                    gate[field_name] = value
                    write_json(gate_path, gate)
                    self.rewrite_gate_manifest_hash(gate_output)
                    contract_output = root / "next-cycle-contract"
                    contract_output.mkdir()

                    exit_code, payload = self.run_contract(
                        gate_output,
                        contract_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        payload["contract_status"],
                        "blocked_source_gate_contains_blockers",
                    )

    def test_blocks_missing_source_boundary_false_field(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            gate_output, _review, _runner_output, _actual = (
                self.build_ready_promotion_gate(root)
            )
            gate_path = gate_output / SOURCE_GATE_FILE
            gate = read_json(gate_path)
            gate.pop("candidate_input_file_read_by_gate", None)
            write_json(gate_path, gate)
            self.rewrite_gate_manifest_hash(gate_output)
            contract_output = root / "next-cycle-contract"
            contract_output.mkdir()

            exit_code, payload = self.run_contract(gate_output, contract_output)

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                payload["contract_status"],
                "blocked_invalid_source_gate_record",
            )

    def test_blocks_non_boolean_source_boundary_false_field(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            gate_output, _review, _runner_output, _actual = (
                self.build_ready_promotion_gate(root)
            )
            gate_path = gate_output / SOURCE_GATE_FILE
            gate = read_json(gate_path)
            gate["candidate_input_file_read_by_gate"] = "false"
            write_json(gate_path, gate)
            self.rewrite_gate_manifest_hash(gate_output)
            contract_output = root / "next-cycle-contract"
            contract_output.mkdir()

            exit_code, payload = self.run_contract(gate_output, contract_output)

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                payload["contract_status"],
                "blocked_invalid_source_gate_record",
            )

    def test_blocks_true_source_boundary_false_field(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            gate_output, _review, _runner_output, _actual = (
                self.build_ready_promotion_gate(root)
            )
            gate_path = gate_output / SOURCE_GATE_FILE
            gate = read_json(gate_path)
            gate["candidate_input_file_read_by_gate"] = True
            write_json(gate_path, gate)
            self.rewrite_gate_manifest_hash(gate_output)
            contract_output = root / "next-cycle-contract"
            contract_output.mkdir()

            exit_code, payload = self.run_contract(gate_output, contract_output)

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                payload["contract_status"],
                "blocked_source_boundary_violation",
            )

    def test_blocks_invalid_inherited_run_facts(self):
        cases = (
            ("review_packet_id", ""),
            ("candidate_file_count", "2"),
            ("bounded_file_records_raw_content", True),
        )
        for field_name, value in cases:
            with self.subTest(field_name=field_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    gate_output, _review, _runner_output, _actual = (
                        self.build_ready_promotion_gate(root)
                    )
                    gate_path = gate_output / SOURCE_GATE_FILE
                    gate = read_json(gate_path)
                    if field_name == "bounded_file_records_raw_content":
                        gate["bounded_file_records"][0]["raw_content"] = "private"
                    else:
                        gate[field_name] = value
                    write_json(gate_path, gate)
                    self.rewrite_gate_manifest_hash(gate_output)
                    contract_output = root / "next-cycle-contract"
                    contract_output.mkdir()

                    exit_code, payload = self.run_contract(
                        gate_output,
                        contract_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        payload["contract_status"],
                        "blocked_invalid_inherited_run_facts",
                    )

    def test_blocks_invalid_cycle_contract_metadata(self):
        cases = (
            {"cycle_contract_id": ""},
            {"reviewer_id": ""},
        )
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    gate_output, _review, _runner_output, _actual = (
                        self.build_ready_promotion_gate(root)
                    )
                    contract_output = root / "next-cycle-contract"
                    contract_output.mkdir()

                    exit_code, payload = self.run_contract(
                        gate_output,
                        contract_output,
                        **kwargs,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        payload["contract_status"],
                        "blocked_invalid_cycle_contract_metadata",
                    )

    def test_fails_closed_on_existing_contract_outputs(self):
        for filename in CONTRACT_OUTPUTS:
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    gate_output, _review, _runner_output, _actual = (
                        self.build_ready_promotion_gate(root)
                    )
                    contract_output = root / "next-cycle-contract"
                    contract_output.mkdir()
                    existing = contract_output / filename
                    existing.write_text("existing\n", encoding="utf-8")

                    exit_code, payload = self.run_contract(
                        gate_output,
                        contract_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertFalse(payload["artifacts_written"])
                    self.assertEqual(existing.read_text(encoding="utf-8"), "existing\n")
                    for other in CONTRACT_OUTPUTS:
                        if other != filename:
                            self.assertFalse((contract_output / other).exists(), other)

    def test_fails_closed_on_symlink_contract_output_collisions(self):
        for filename in CONTRACT_OUTPUTS:
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    gate_output, _review, _runner_output, _actual = (
                        self.build_ready_promotion_gate(root)
                    )
                    contract_output = root / "next-cycle-contract"
                    contract_output.mkdir()
                    os.symlink(
                        root / "target-does-not-need-to-exist",
                        contract_output / filename,
                    )

                    exit_code, payload = self.run_contract(
                        gate_output,
                        contract_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertFalse(payload["artifacts_written"])
                    for other in CONTRACT_OUTPUTS:
                        if other != filename:
                            self.assertFalse((contract_output / other).exists(), other)

    def test_missing_output_dir_returns_structured_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            gate_output, _review, _runner_output, _actual = (
                self.build_ready_promotion_gate(root)
            )
            contract_output = root / "missing-cycle-contract"

            exit_code, payload = self.run_contract(gate_output, contract_output)

            self.assertEqual(exit_code, 1)
            self.assertFalse(payload["artifacts_written"])
            self.assertFalse(contract_output.exists())

    def test_input_output_overlap_rejected_without_artifacts(self):
        cases = (
            "output_inside_gate",
            "gate_inside_output",
            "same_dir",
        )
        for case_name in cases:
            with self.subTest(case_name=case_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    gate_output, _review, _runner_output, _actual = (
                        self.build_ready_promotion_gate(root)
                    )
                    if case_name == "output_inside_gate":
                        contract_output = gate_output / "cycle-contract"
                        contract_output.mkdir()
                    elif case_name == "gate_inside_output":
                        contract_output = root / "next-cycle-contract"
                        contract_output.mkdir()
                        copied_gate = contract_output / "gate"
                        shutil.copytree(gate_output, copied_gate)
                        gate_output = copied_gate
                    else:
                        contract_output = gate_output

                    exit_code, payload = self.run_contract(
                        gate_output,
                        contract_output,
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertFalse(payload["artifacts_written"])
                    if case_name == "same_dir":
                        for filename in CONTRACT_OUTPUTS[:4]:
                            self.assertFalse(
                                (contract_output / filename).exists(),
                                filename,
                            )
                    else:
                        self.assert_contract_artifacts_absent(contract_output)

    def test_task_graph_node_writes_artifact_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            gate_output, _review, _runner_output, _actual = (
                self.build_ready_promotion_gate(root)
            )
            contract_output = root / "next-cycle-contract"
            contract_output.mkdir()
            graph_output = root / "graph-output"
            graph_output.mkdir()
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.contract_node(
                        node_id="contract_from_gate",
                        gate_output=gate_output,
                        output_dir=contract_output,
                    )
                ],
            )

            result = run_local_task_graph_fixture(graph_path, graph_output)
            artifact_outputs = read_json(result.artifact_outputs_manifest_path)
            roles = {
                artifact["artifact_role"]
                for artifact in artifact_outputs["artifacts"]
                if artifact["node_id"] == "contract_from_gate"
            }

            self.assertTrue(result.success)
            for role in CONTRACT_ROLES:
                self.assertIn(role, roles)

    def test_no_scope_boundaries_remain_false(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            gate_output, _review, _runner_output, _actual = (
                self.build_ready_promotion_gate(root)
            )
            contract_output = root / "next-cycle-contract"
            contract_output.mkdir()

            exit_code, payload = self.run_contract(gate_output, contract_output)
            contract = read_json(
                contract_output
                / "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate.json"
            )
            manifest = read_json(
                contract_output
                / "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_manifest.json"
            )
            graph_output = root / "graph-output"
            graph_output.mkdir()
            graph_path = root / "graph.json"
            graph_contract_output = root / "graph-next-cycle-contract"
            graph_contract_output.mkdir()
            self.write_graph(
                graph_path,
                [
                    self.contract_node(
                        node_id="contract_from_gate",
                        gate_output=gate_output,
                        output_dir=graph_contract_output,
                    )
                ],
            )
            graph_result = run_local_task_graph_fixture(graph_path, graph_output)
            node = read_json(graph_result.execution_manifest_path)["nodes"][0]

            self.assertEqual(exit_code, 0)
            for payload_like in (payload, contract, manifest, node):
                self.assert_no_scope_false(payload_like)

    def test_deterministic_stable_fields(self):
        contracts = []
        checklists = []
        for index in range(2):
            with tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                gate_output, _review, _runner_output, _actual = (
                    self.build_ready_promotion_gate(root)
                )
                contract_output = root / "next-cycle-contract"
                contract_output.mkdir()
                exit_code, _payload = self.run_contract(
                    gate_output,
                    contract_output,
                    cycle_contract_id="stable-cycle-contract-" + str(index),
                )
                self.assertEqual(exit_code, 0)
                contracts.append(
                    read_json(
                        contract_output
                        / "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate.json"
                    )
                )
                checklists.append(
                    (
                        contract_output
                        / "local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate_checklist.md"
                    ).read_text(encoding="utf-8")
                )

        self.assertEqual(
            contracts[0]["contract_status"],
            contracts[1]["contract_status"],
        )
        self.assertEqual(
            contracts[0]["contract_decision"],
            contracts[1]["contract_decision"],
        )
        self.assertEqual(
            contracts[0]["next_allowed_action"],
            contracts[1]["next_allowed_action"],
        )
        self.assertEqual(
            contracts[0]["disallowed_actions"],
            contracts[1]["disallowed_actions"],
        )
        self.assertEqual(
            [artifact["role"] for artifact in contracts[0]["source_artifacts"]],
            [artifact["role"] for artifact in contracts[1]["source_artifacts"]],
        )
        self.assertEqual(checklists[0], checklists[1])

    def test_builder_structured_failure_writes_no_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            gate_output, _review, _runner_output, _actual = (
                self.build_ready_promotion_gate(root)
            )
            contract_output = root / "missing-cycle-contract"

            result = build_local_asset_next_bounded_smoke_cycle_contract_from_run_promotion_gate(
                gate_output,
                contract_output,
                cycle_contract_id="builder-cycle-contract-1",
            )

            self.assertFalse(result.complete)
            self.assertFalse(result.payload["artifacts_written"])
            self.assertFalse(contract_output.exists())


if __name__ == "__main__":
    unittest.main()
