import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from kernel.assets.local_asset_bounded_smoke_iteration import (
    BOUNDED_SMOKE_ITERATION_SIGNOFF_PHRASE,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.task_graph import run_local_task_graph_fixture


SMOKE_APPROVAL_PHRASE = "I_APPROVE_LOCAL_ASSET_SMOKE_RUN"
CYCLE_OUTPUTS = (
    "local_asset_bounded_smoke_cycle_contract.json",
    "local_asset_bounded_smoke_cycle_contract_manifest.json",
    "local_asset_bounded_smoke_cycle_summary.md",
    "local_asset_bounded_smoke_cycle_human_review_checklist.md",
    "artifact_index.json",
    "artifact_index_manifest.json",
)
CYCLE_ROLES = (
    "local_asset_bounded_smoke_cycle_contract",
    "local_asset_bounded_smoke_cycle_contract_manifest",
    "local_asset_bounded_smoke_cycle_summary",
    "local_asset_bounded_smoke_cycle_human_review_checklist",
)
BOUNDARY_FIELDS = (
    "scan_performed",
    "readiness_run_performed",
    "human_smoke_run_performed",
    "smoke_review_packet_run_performed",
    "smoke_promotion_gate_run_performed",
    "bounded_smoke_iteration_performed_by_contract",
    "iteration_review_packet_run_performed",
    "iteration_promotion_gate_run_performed",
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


class LocalAssetBoundedSmokeCycleContractTests(unittest.TestCase):
    def run_cli(self, args):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(args)
        return exit_code, json.loads(stdout.getvalue())

    def make_candidate(self, root):
        candidate = Path(root) / "candidate"
        nested = candidate / "nested"
        nested.mkdir(parents=True)
        (candidate / "plate.png").write_bytes(b"plate")
        (nested / "clip.mov").write_bytes(b"clip")
        return candidate

    def run_readiness(self, candidate, output_dir, *, project_id="cycle-test"):
        return self.run_cli(
            [
                "launch-local-asset-smoke-readiness",
                "--candidate-input-dir",
                Path(candidate).as_posix(),
                "--output-dir",
                Path(output_dir).as_posix(),
                "--recursive",
                "--project-id",
                project_id,
            ]
        )

    def run_human_smoke(
        self,
        candidate,
        output_dir,
        readiness_report,
        *,
        project_id="cycle-test",
    ):
        return self.run_cli(
            [
                "launch-local-asset-human-smoke-run",
                "--candidate-input-dir",
                Path(candidate).as_posix(),
                "--output-dir",
                Path(output_dir).as_posix(),
                "--readiness-report",
                Path(readiness_report).as_posix(),
                "--human-approval-id",
                "cycle-smoke-approval",
                "--human-approval-phrase",
                SMOKE_APPROVAL_PHRASE,
                "--recursive",
                "--project-id",
                project_id,
                "--max-smoke-files",
                "10",
                "--max-smoke-bytes",
                "2000",
                "--max-smoke-depth",
                "4",
            ]
        )

    def run_smoke_review(self, smoke_output_dir, output_dir):
        return self.run_cli(
            [
                "launch-local-asset-smoke-review-packet",
                "--smoke-output-dir",
                Path(smoke_output_dir).as_posix(),
                "--output-dir",
                Path(output_dir).as_posix(),
                "--project-id",
                "cycle-test",
            ]
        )

    def run_smoke_promotion(self, review_output_dir, output_dir):
        return self.run_cli(
            [
                "launch-local-asset-smoke-promotion-gate",
                "--review-output-dir",
                Path(review_output_dir).as_posix(),
                "--output-dir",
                Path(output_dir).as_posix(),
                "--project-id",
                "cycle-test",
            ]
        )

    def run_iteration(self, promotion_output_dir, candidate, readiness_report, output_dir):
        return self.run_cli(
            [
                "launch-local-asset-bounded-smoke-iteration",
                "--promotion-output-dir",
                Path(promotion_output_dir).as_posix(),
                "--candidate-input-dir",
                Path(candidate).as_posix(),
                "--readiness-report",
                Path(readiness_report).as_posix(),
                "--output-dir",
                Path(output_dir).as_posix(),
                "--human-signoff-id",
                "cycle-iteration-signoff",
                "--human-signoff-phrase",
                BOUNDED_SMOKE_ITERATION_SIGNOFF_PHRASE,
                "--recursive",
                "--project-id",
                "cycle-test",
                "--max-smoke-files",
                "10",
                "--max-smoke-bytes",
                "2000",
                "--max-smoke-depth",
                "4",
            ]
        )

    def run_iteration_review(self, iteration_output_dir, output_dir):
        return self.run_cli(
            [
                "launch-local-asset-smoke-iteration-review-packet",
                "--iteration-output-dir",
                Path(iteration_output_dir).as_posix(),
                "--output-dir",
                Path(output_dir).as_posix(),
                "--project-id",
                "cycle-test",
            ]
        )

    def run_iteration_promotion(self, iteration_review_output_dir, output_dir):
        return self.run_cli(
            [
                "launch-local-asset-iteration-promotion-gate",
                "--iteration-review-output-dir",
                Path(iteration_review_output_dir).as_posix(),
                "--output-dir",
                Path(output_dir).as_posix(),
                "--project-id",
                "cycle-test",
            ]
        )

    def run_cycle_contract(self, chain, output_dir):
        return self.run_cli(
            [
                "launch-local-asset-bounded-smoke-cycle-contract",
                "--readiness-output-dir",
                Path(chain["readiness_output"]).as_posix(),
                "--smoke-output-dir",
                Path(chain["smoke_output"]).as_posix(),
                "--smoke-review-output-dir",
                Path(chain["smoke_review_output"]).as_posix(),
                "--smoke-promotion-output-dir",
                Path(chain["smoke_promotion_output"]).as_posix(),
                "--iteration-output-dir",
                Path(chain["iteration_output"]).as_posix(),
                "--iteration-review-output-dir",
                Path(chain["iteration_review_output"]).as_posix(),
                "--iteration-promotion-output-dir",
                Path(chain["iteration_promotion_output"]).as_posix(),
                "--output-dir",
                Path(output_dir).as_posix(),
                "--project-id",
                "cycle-test",
            ]
        )

    def build_full_chain(self, root):
        candidate = self.make_candidate(root)
        dirs = {
            "readiness_output": Path(root) / "readiness",
            "smoke_output": Path(root) / "smoke-0",
            "smoke_review_output": Path(root) / "smoke-review",
            "smoke_promotion_output": Path(root) / "smoke-promotion",
            "iteration_output": Path(root) / "iteration",
            "iteration_review_output": Path(root) / "iteration-review",
            "iteration_promotion_output": Path(root) / "iteration-promotion",
        }
        for path in dirs.values():
            path.mkdir()

        readiness_code, readiness_payload = self.run_readiness(
            candidate,
            dirs["readiness_output"],
        )
        self.assertEqual(readiness_code, 0)
        smoke_code, _smoke_payload = self.run_human_smoke(
            candidate,
            dirs["smoke_output"],
            readiness_payload["local_asset_smoke_readiness_report_path"],
        )
        self.assertEqual(smoke_code, 0)
        review_code, _review_payload = self.run_smoke_review(
            dirs["smoke_output"],
            dirs["smoke_review_output"],
        )
        self.assertEqual(review_code, 0)
        promotion_code, _promotion_payload = self.run_smoke_promotion(
            dirs["smoke_review_output"],
            dirs["smoke_promotion_output"],
        )
        self.assertEqual(promotion_code, 0)
        iteration_code, _iteration_payload = self.run_iteration(
            dirs["smoke_promotion_output"],
            candidate,
            readiness_payload["local_asset_smoke_readiness_report_path"],
            dirs["iteration_output"],
        )
        self.assertEqual(iteration_code, 0)
        iteration_review_code, _iteration_review_payload = self.run_iteration_review(
            dirs["iteration_output"],
            dirs["iteration_review_output"],
        )
        self.assertEqual(iteration_review_code, 0)
        iteration_promotion_code, _iteration_promotion_payload = (
            self.run_iteration_promotion(
                dirs["iteration_review_output"],
                dirs["iteration_promotion_output"],
            )
        )
        self.assertEqual(iteration_promotion_code, 0)
        dirs["candidate"] = candidate
        return dirs

    def write_graph(self, graph_path, nodes, *, graph_id="cycle-contract-graph"):
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

    def cycle_contract_node(self, *, node_id, chain, output_dir):
        return {
            "node_id": node_id,
            "adapter_id": "local_asset_runtime",
            "capability": "launch_local_asset_bounded_smoke_cycle_contract",
            "execution_mode": "fixture",
            "depends_on": [],
            "approval_checkpoint_required": True,
            "inputs": {
                "readiness_output_dir": Path(
                    chain["readiness_output"]
                ).as_posix(),
                "smoke_output_dir": Path(chain["smoke_output"]).as_posix(),
                "smoke_review_output_dir": Path(
                    chain["smoke_review_output"]
                ).as_posix(),
                "smoke_promotion_output_dir": Path(
                    chain["smoke_promotion_output"]
                ).as_posix(),
                "iteration_output_dir": Path(
                    chain["iteration_output"]
                ).as_posix(),
                "iteration_review_output_dir": Path(
                    chain["iteration_review_output"]
                ).as_posix(),
                "iteration_promotion_output_dir": Path(
                    chain["iteration_promotion_output"]
                ).as_posix(),
                "output_dir": Path(output_dir).as_posix(),
                "project_id": "cycle-test",
            },
        }

    def rewrite_manifest_hash(self, manifest_path, field_name, target_path):
        manifest = read_json(manifest_path)
        manifest[field_name] = sha256_file(target_path)
        write_json(manifest_path, manifest)

    def test_full_chain_writes_contract_manifest_summary_checklist_and_artifact_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_full_chain(root)
            cycle_output = root / "cycle-contract"
            cycle_output.mkdir()

            exit_code, payload = self.run_cycle_contract(chain, cycle_output)
            artifact_index = read_json(cycle_output / "artifact_index.json")
            roles = {entry["artifact_role"] for entry in artifact_index["entries"]}

            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["complete"])
            for filename in CYCLE_OUTPUTS:
                self.assertTrue((cycle_output / filename).exists(), filename)
            self.assertEqual(roles, set(CYCLE_ROLES))

    def test_clean_chain_contract_ready(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_full_chain(root)
            cycle_output = root / "cycle-contract"
            cycle_output.mkdir()

            exit_code, payload = self.run_cycle_contract(chain, cycle_output)
            contract = read_json(
                cycle_output / "local_asset_bounded_smoke_cycle_contract.json"
            )

            self.assertEqual(exit_code, 0)
            self.assertEqual(contract["cycle_contract_status"], "cycle_contract_ready")
            self.assertEqual(
                contract["cycle_contract_decision"],
                "bind_completed_bounded_smoke_cycle",
            )
            self.assertEqual(
                contract["next_allowed_action"],
                "human_review_bounded_smoke_cycle_contract",
            )
            for payload_like in (payload, contract):
                for field in BOUNDARY_FIELDS:
                    self.assertFalse(payload_like[field], field)

    def test_blocks_missing_required_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_full_chain(root)
            (
                chain["iteration_promotion_output"]
                / "local_asset_iteration_promotion_decision.json"
            ).unlink()
            cycle_output = root / "cycle-contract"
            cycle_output.mkdir()

            exit_code, _payload = self.run_cycle_contract(chain, cycle_output)
            contract = read_json(
                cycle_output / "local_asset_bounded_smoke_cycle_contract.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                contract["cycle_contract_status"],
                "blocked_missing_required_artifacts",
            )
            self.assertNotIn(
                contract["cycle_contract_status"],
                ("cycle_contract_ready", "cycle_contract_ready_with_warnings"),
            )

    def test_blocks_untrusted_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_full_chain(root)
            manifest_path = (
                chain["iteration_promotion_output"]
                / "local_asset_iteration_promotion_gate_manifest.json"
            )
            manifest = read_json(manifest_path)
            manifest["decision_sha256"] = "0" * 64
            write_json(manifest_path, manifest)
            cycle_output = root / "cycle-contract"
            cycle_output.mkdir()

            exit_code, _payload = self.run_cycle_contract(chain, cycle_output)
            contract = read_json(
                cycle_output / "local_asset_bounded_smoke_cycle_contract.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                contract["cycle_contract_status"],
                "blocked_untrusted_artifacts",
            )

    def test_blocks_incomplete_cycle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_full_chain(root)
            decision_path = (
                chain["iteration_promotion_output"]
                / "local_asset_iteration_promotion_decision.json"
            )
            decision = read_json(decision_path)
            decision["iteration_promotion_gate_status"] = "blocked_incomplete_cycle"
            decision["iteration_promotion_decision"] = "repair_cycle"
            decision["next_bounded_smoke_iteration_allowed"] = False
            write_json(decision_path, decision)
            self.rewrite_manifest_hash(
                chain["iteration_promotion_output"]
                / "local_asset_iteration_promotion_gate_manifest.json",
                "decision_sha256",
                decision_path,
            )
            cycle_output = root / "cycle-contract"
            cycle_output.mkdir()

            exit_code, _payload = self.run_cycle_contract(chain, cycle_output)
            contract = read_json(
                cycle_output / "local_asset_bounded_smoke_cycle_contract.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                contract["cycle_contract_status"],
                "blocked_incomplete_cycle",
            )

    def test_blocks_quarantine(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_full_chain(root)
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
            cycle_output = root / "cycle-contract"
            cycle_output.mkdir()

            exit_code, _payload = self.run_cycle_contract(chain, cycle_output)
            contract = read_json(
                cycle_output / "local_asset_bounded_smoke_cycle_contract.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(contract["cycle_contract_status"], "blocked_quarantine")
            self.assertEqual(contract["cycle_contract_decision"], "inspect_quarantine")

    def test_blocks_duplicates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_full_chain(root)
            packet_path = (
                chain["iteration_review_output"]
                / "local_asset_smoke_iteration_review_packet.json"
            )
            packet = read_json(packet_path)
            packet["duplicate_summary"]["duplicate_group_count"] = 1
            packet["duplicate_group_count"] = 1
            write_json(packet_path, packet)
            self.rewrite_manifest_hash(
                chain["iteration_review_output"]
                / "local_asset_smoke_iteration_review_packet_manifest.json",
                "packet_sha256",
                packet_path,
            )
            cycle_output = root / "cycle-contract"
            cycle_output.mkdir()

            exit_code, _payload = self.run_cycle_contract(chain, cycle_output)
            contract = read_json(
                cycle_output / "local_asset_bounded_smoke_cycle_contract.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(contract["cycle_contract_status"], "blocked_duplicates")
            self.assertEqual(contract["cycle_contract_decision"], "inspect_duplicates")

    def test_blocks_incremental_changes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_full_chain(root)
            plan_path = (
                chain["iteration_output"]
                / "smoke"
                / "scan"
                / "local_asset_incremental_scan_plan.json"
            )
            plan = read_json(plan_path)
            plan["plan_mode"] = "compare_previous_scan"
            plan["changed_asset_count"] = 1
            plan["suspicious_change_count"] = 1
            write_json(plan_path, plan)
            cycle_output = root / "cycle-contract"
            cycle_output.mkdir()

            exit_code, _payload = self.run_cycle_contract(chain, cycle_output)
            contract = read_json(
                cycle_output / "local_asset_bounded_smoke_cycle_contract.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                contract["cycle_contract_status"],
                "blocked_incremental_changes",
            )
            self.assertEqual(
                contract["cycle_contract_decision"],
                "inspect_incremental_changes",
            )

    def test_blocks_production_boundary_violation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_full_chain(root)
            decision_path = (
                chain["smoke_promotion_output"]
                / "local_asset_smoke_promotion_decision.json"
            )
            decision = read_json(decision_path)
            decision["production_scan_approved"] = True
            write_json(decision_path, decision)
            self.rewrite_manifest_hash(
                chain["smoke_promotion_output"]
                / "local_asset_smoke_promotion_gate_manifest.json",
                "decision_sha256",
                decision_path,
            )
            cycle_output = root / "cycle-contract"
            cycle_output.mkdir()

            exit_code, _payload = self.run_cycle_contract(chain, cycle_output)
            contract = read_json(
                cycle_output / "local_asset_bounded_smoke_cycle_contract.json"
            )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                contract["cycle_contract_status"],
                "blocked_production_boundary_violation",
            )
            self.assertEqual(
                contract["cycle_contract_decision"],
                "reject_boundary_violation",
            )

    def test_fail_closed_on_existing_outputs(self):
        for filename in CYCLE_OUTPUTS:
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    chain = self.build_full_chain(root)
                    cycle_output = root / "cycle-contract"
                    cycle_output.mkdir()
                    preexisting = cycle_output / filename
                    preexisting.write_text("preexisting\n", encoding="utf-8")

                    exit_code, payload = self.run_cycle_contract(chain, cycle_output)

                    self.assertEqual(exit_code, 1)
                    self.assertEqual(
                        preexisting.read_text(encoding="utf-8"),
                        "preexisting\n",
                    )
                    self.assertFalse(payload["artifacts_written"])

    def test_missing_output_dir_structured_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_full_chain(root)
            cycle_output = root / "missing-cycle-contract"

            exit_code, payload = self.run_cycle_contract(chain, cycle_output)

            self.assertEqual(exit_code, 1)
            self.assertFalse(cycle_output.exists())
            self.assertFalse(payload["artifacts_written"])

    def test_input_output_overlap_rejected(self):
        cases = (
            ("same_readiness_dir", lambda root, chain: chain["readiness_output"]),
            (
                "output_inside_readiness",
                lambda root, chain: chain["readiness_output"] / "cycle",
            ),
            (
                "output_inside_smoke",
                lambda root, chain: chain["smoke_output"] / "cycle",
            ),
            (
                "output_inside_iteration",
                lambda root, chain: chain["iteration_output"] / "cycle",
            ),
            ("upstream_inside_output", lambda root, chain: root),
            (
                "ambiguous_initial_smoke_inside_iteration",
                lambda root, chain: root / "cycle-contract",
            ),
        )
        for case_name, output_factory in cases:
            with self.subTest(case_name=case_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    chain = self.build_full_chain(root)
                    output_dir = output_factory(root, chain)
                    output_dir.mkdir(parents=True, exist_ok=True)
                    if case_name == "ambiguous_initial_smoke_inside_iteration":
                        chain = dict(chain)
                        chain["smoke_output"] = chain["iteration_output"] / "smoke"
                    before = sorted(
                        path.relative_to(output_dir).as_posix()
                        for path in output_dir.rglob("*")
                    )

                    exit_code, payload = self.run_cycle_contract(chain, output_dir)
                    after = sorted(
                        path.relative_to(output_dir).as_posix()
                        for path in output_dir.rglob("*")
                    )

                    self.assertEqual(exit_code, 1)
                    self.assertFalse(payload["artifacts_written"])
                    self.assertEqual(before, after)

    def test_task_graph_node_writes_artifact_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_full_chain(root)
            cycle_output = root / "cycle-contract"
            graph_output = root / "graph-output"
            cycle_output.mkdir()
            graph_output.mkdir()
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.cycle_contract_node(
                        node_id="cycle_contract",
                        chain=chain,
                        output_dir=cycle_output,
                    )
                ],
            )

            result = run_local_task_graph_fixture(graph_path, graph_output)
            artifact_outputs = read_json(result.artifact_outputs_manifest_path)
            roles = {
                artifact["artifact_role"]
                for artifact in artifact_outputs["artifacts"]
                if artifact["node_id"] == "cycle_contract"
            }

            self.assertTrue(result.success)
            for role in CYCLE_ROLES:
                self.assertIn(role, roles)

    def test_no_scope_boundaries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            chain = self.build_full_chain(root)
            cycle_output = root / "cycle-contract"
            graph_cycle_output = root / "graph-cycle-contract"
            graph_output = root / "graph-output"
            cycle_output.mkdir()
            graph_cycle_output.mkdir()
            graph_output.mkdir()

            exit_code, payload = self.run_cycle_contract(chain, cycle_output)
            contract = read_json(
                cycle_output / "local_asset_bounded_smoke_cycle_contract.json"
            )
            manifest = read_json(
                cycle_output
                / "local_asset_bounded_smoke_cycle_contract_manifest.json"
            )
            graph_path = root / "graph.json"
            self.write_graph(
                graph_path,
                [
                    self.cycle_contract_node(
                        node_id="cycle_contract",
                        chain=chain,
                        output_dir=graph_cycle_output,
                    )
                ],
                graph_id="cycle-contract-boundaries-graph",
            )
            graph_result = run_local_task_graph_fixture(graph_path, graph_output)
            node = read_json(graph_result.execution_manifest_path)["nodes"][0]

            self.assertEqual(exit_code, 0)
            for payload_like in (payload, contract, manifest, node):
                for field in BOUNDARY_FIELDS:
                    self.assertFalse(payload_like[field], field)
                self.assertTrue(payload_like["required_human_approval"])
                self.assertTrue(payload_like["required_human_review"])

    def test_deterministic_stable_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first_chain = self.build_full_chain(root / "first")
            second_chain = self.build_full_chain(root / "second")
            first_output = root / "first-cycle-contract"
            second_output = root / "second-cycle-contract"
            first_output.mkdir()
            second_output.mkdir()

            first_code, _first_payload = self.run_cycle_contract(
                first_chain,
                first_output,
            )
            second_code, _second_payload = self.run_cycle_contract(
                second_chain,
                second_output,
            )
            first_contract = read_json(
                first_output / "local_asset_bounded_smoke_cycle_contract.json"
            )
            second_contract = read_json(
                second_output / "local_asset_bounded_smoke_cycle_contract.json"
            )

            self.assertEqual(first_code, 0)
            self.assertEqual(second_code, 0)
            for field in (
                "cycle_contract_status",
                "cycle_contract_decision",
                "disallowed_actions",
            ):
                self.assertEqual(first_contract[field], second_contract[field])
            self.assertEqual(
                first_contract["blocker_summary"]["blocker_roles"],
                second_contract["blocker_summary"]["blocker_roles"],
            )
            self.assertEqual(
                [
                    artifact["artifact_role"]
                    for artifact in first_contract["source_artifacts"]
                ],
                [
                    artifact["artifact_role"]
                    for artifact in second_contract["source_artifacts"]
                ],
            )
            self.assertEqual(
                first_contract["human_review_checklist"]["decision_options"],
                second_contract["human_review_checklist"]["decision_options"],
            )


if __name__ == "__main__":
    unittest.main()
