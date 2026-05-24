import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from kernel.capabilities.admission_gated_local_adapter_registry_promotion import (
    ADMISSION_GATED_LOCAL_ADAPTER_REGISTRY_PROMOTION_DENIED_SCOPE,
)
from kernel.capabilities.local_fixture_adapter_usage_receipt import (
    LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_DENIED_ADMISSION_FIELDS,
    LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_FORBIDDEN_PERFORMED_FIELDS,
    LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_REVIEW_ATTESTATION,
    run_local_fixture_adapter_usage_receipt,
)
from kernel.personal_ai.adapters.adapter_contract import (
    AdapterAdmissionStatus,
    AdapterCapabilityRequest,
    AdapterMode,
    AdapterRiskClass,
)
from kernel.personal_ai.adapters.adapter_registry import (
    admit_adapter_capability,
    find_adapter_entry,
)
from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.local_launcher import (
    run_local_fixture_adapter_usage_receipt_launcher,
)
from kernel.personal_ai.local_mvp_cli import main
from kernel.personal_ai.product_health_check import build_product_health_report
from kernel.personal_ai.task_graph import run_local_task_graph_fixture


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = (
    REPO_ROOT
    / "kernel"
    / "capabilities"
    / "local_fixture_adapter_usage_receipt.py"
)
DECISION_DOC = REPO_ROOT / "docs" / "decisions" / "local_fixture_adapter_usage_receipt_v1.md"
_DEFAULT_LOCAL_FIXTURE_REFERENCE = object()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    Path(path).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class LocalFixtureAdapterUsageReceiptTests(unittest.TestCase):
    def make_workspace(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        promotion_dir = root / "promotion-output"
        promotion_dir.mkdir()
        output_dir = root / "usage-output"
        output_dir.mkdir()
        fixture_path = output_dir / "fixture.html"
        fixture_path.write_text("<!doctype html><title>fixture</title>\n", encoding="utf-8")
        promotion_path = (
            promotion_dir
            / "admission_gated_local_adapter_registry_promotion_result.json"
        )
        write_json_atomically(promotion_path, self.valid_promotion_result())
        return root, promotion_path, output_dir, fixture_path

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
        payload["registry_record"] = self.valid_registry_record()
        return payload

    def run_receipt(
        self,
        promotion_path,
        output_dir,
        fixture_path,
        *,
        registry_entry=None,
        review_attestation=LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_REVIEW_ATTESTATION,
        local_fixture_reference=_DEFAULT_LOCAL_FIXTURE_REFERENCE,
    ):
        reference = (
            fixture_path.as_posix()
            if local_fixture_reference is _DEFAULT_LOCAL_FIXTURE_REFERENCE
            else local_fixture_reference
        )
        return run_local_fixture_adapter_usage_receipt(
            promotion_path,
            output_dir,
            "usage-001",
            review_attestation=review_attestation,
            local_fixture_reference=reference,
            project_id="project-001",
            reviewer_id="reviewer-001",
            operator_notes="reviewed #428 promotion for one local fixture use",
            registry_entry=registry_entry,
        )

    def assert_rejects_promotion_mutation(self, mutator, reason):
        _root, promotion_path, output_dir, fixture_path = self.make_workspace()
        payload = read_json(promotion_path)
        mutator(payload)
        write_json(promotion_path, payload)

        result = self.run_receipt(promotion_path, output_dir, fixture_path)

        self.assertFalse(result.complete)
        self.assertIn(reason, result.rejection_reasons)
        self.assertTrue(result.result_path.exists())
        self.assertIn(reason, read_json(result.result_path)["rejection_reasons"])

    def test_valid_promotion_result_plus_fixture_writes_local_only_usage_receipt(self):
        _root, promotion_path, output_dir, fixture_path = self.make_workspace()

        result = self.run_receipt(promotion_path, output_dir, fixture_path)
        payload = read_json(result.result_path)

        self.assertTrue(result.complete)
        self.assertEqual(payload["receipt_type"], "local_fixture_adapter_usage_receipt_v1")
        self.assertEqual(payload["usage_receipt_id"], "usage-001")
        self.assertEqual(payload["adapter_id"], "bounded_playwright_worker_adapter_draft")
        self.assertEqual(payload["candidate_id"], "github-candidate-microsoft-playwright-v1")
        self.assertEqual(payload["repo_full_name"], "microsoft/playwright")
        self.assertEqual(payload["promotion_result_path"], promotion_path.as_posix())
        self.assertEqual(payload["promotion_result_sha256"], sha256_file(promotion_path))
        self.assertTrue(payload["promotion_validated"])
        self.assertFalse(payload["registry_entry_validated"])
        self.assertTrue(payload["aggregation_bound"])
        self.assertTrue(payload["regression_bound"])
        self.assertTrue(payload["local_fixture_only"])
        self.assertTrue(payload["one_usage_receipt_only"])
        self.assertEqual(payload["local_fixture_reference_scheme"], "file")
        self.assertEqual(payload["local_fixture_sha256"], sha256_file(fixture_path))
        self.assertTrue(payload["local_fixture_exists"])
        self.assertTrue(payload["local_fixture_regular_file"])
        self.assertFalse(payload["local_fixture_symlink_detected"])
        self.assertTrue(payload["local_fixture_under_allowed_root"])
        self.assertTrue(payload["usage_receipt_granted"])
        self.assertFalse(payload["production_promotion_granted"])
        self.assertEqual(
            payload["next_allowed_action"],
            "human_review_local_fixture_usage_receipt_before_any_execution",
        )
        for field_name in (
            "production_admission_granted",
            "live_website_admission_granted",
            "general_browser_automation_admission_granted",
            "autonomous_execution_admission_granted",
            "autonomous_execution_performed",
        ):
            self.assertIn(field_name, payload)
            self.assertFalse(payload[field_name], field_name)
        for field_name in (
            "adapter_execution_performed",
            "playwright_execution_performed",
            "browser_open_performed",
            "network_probe_performed",
            "fixture_content_execution_performed",
        ):
            self.assertIn(field_name, payload)
            self.assertFalse(payload[field_name], field_name)

    def test_missing_promotion_result_rejects(self):
        root, _promotion_path, output_dir, fixture_path = self.make_workspace()
        result = self.run_receipt(root / "missing-result.json", output_dir, fixture_path)

        self.assertFalse(result.complete)
        self.assertIn("promotion_result_path_missing", result.rejection_reasons)

    def test_symlink_promotion_result_rejects(self):
        root, promotion_path, output_dir, fixture_path = self.make_workspace()
        symlink_path = root / "promotion-link.json"
        symlink_path.symlink_to(promotion_path)

        result = self.run_receipt(symlink_path, output_dir, fixture_path)

        self.assertFalse(result.complete)
        self.assertIn("promotion_result_path_is_symlink", result.rejection_reasons)

    def test_invalid_json_promotion_result_rejects(self):
        _root, promotion_path, output_dir, fixture_path = self.make_workspace()
        promotion_path.write_text("{", encoding="utf-8")

        result = self.run_receipt(promotion_path, output_dir, fixture_path)

        self.assertFalse(result.complete)
        self.assertIn("promotion_result_not_json_object", result.rejection_reasons)

    def test_required_promotion_fields_reject_fail_closed(self):
        cases = (
            (
                lambda payload: payload.update({"promotion_type": "wrong"}),
                "promotion_type_mismatch",
            ),
            (
                lambda payload: payload.update({"promotion_status": "not-completed"}),
                "promotion_status_not_completed",
            ),
            (
                lambda payload: payload.update({"promotion_decision": "wrong"}),
                "promotion_decision_mismatch",
            ),
            (
                lambda payload: payload.update({"registry_promotion_granted": False}),
                "registry_promotion_not_granted",
            ),
            (
                lambda payload: payload.update({"production_promotion_granted": True}),
                "production_promotion_claimed",
            ),
            (
                lambda payload: payload.update({"source_gate_passed": False}),
                "source_gate_not_passed",
            ),
            (
                lambda payload: payload.update({"source_gate_decision_type": "wrong"}),
                "source_gate_decision_type_mismatch",
            ),
            (
                lambda payload: payload.update({"source_gate_decision_sha256": ""}),
                "source_gate_decision_sha_missing",
            ),
            (
                lambda payload: payload.update({"adapter_id": "wrong-adapter"}),
                "source_adapter_id_mismatch",
            ),
            (
                lambda payload: payload.update({"candidate_id": "wrong-candidate"}),
                "source_candidate_id_mismatch",
            ),
            (
                lambda payload: payload.update({"repo_full_name": "wrong/repo"}),
                "source_repo_full_name_mismatch",
            ),
            (
                lambda payload: payload.update({"aggregation_bound": False}),
                "aggregation_not_bound",
            ),
            (
                lambda payload: payload.update({"regression_bound": False}),
                "regression_not_bound",
            ),
            (
                lambda payload: payload.update({"local_fixture_only": False}),
                "local_fixture_only_not_true",
            ),
            (
                lambda payload: payload.update({"human_review_required": False}),
                "human_review_not_required",
            ),
            (
                lambda payload: payload.update({"required_human_approval": False}),
                "human_approval_not_required",
            ),
            (
                lambda payload: payload.update({"non_production": False}),
                "non_production_not_true",
            ),
            (
                lambda payload: payload.update({"production_adapter": True}),
                "production_adapter_claimed",
            ),
            (
                lambda payload: payload.update(
                    {"arbitrary_url_navigation_admission_granted": True}
                ),
                "forbidden_admission_claimed",
            ),
            (
                lambda payload: payload.update({"external_network_performed": True}),
                "performed_forbidden_action",
            ),
        )
        for mutator, reason in cases:
            with self.subTest(reason=reason):
                self.assert_rejects_promotion_mutation(mutator, reason)

    def test_embedded_registry_record_missing_or_invalid_rejects(self):
        cases = (
            lambda payload: payload.pop("registry_record"),
            lambda payload: payload["registry_record"].update({"allowed_scope": "production"}),
        )
        for mutator in cases:
            with self.subTest(mutator=mutator):
                self.assert_rejects_promotion_mutation(
                    mutator,
                    "registry_record_missing_or_invalid",
                )

    def test_registry_entry_artifact_rejections_are_deterministic(self):
        cases = (
            (
                "registry_entry_path_is_symlink",
                lambda root, promotion_path, registry_entry: self._make_registry_symlink(
                    root,
                    promotion_path,
                    registry_entry,
                ),
            ),
            (
                "registry_entry_not_json_object",
                lambda _root, _promotion_path, registry_entry: registry_entry.write_text(
                    "{",
                    encoding="utf-8",
                ),
            ),
            (
                "registry_entry_identity_mismatch",
                lambda _root, _promotion_path, registry_entry: write_json(
                    registry_entry,
                    {
                        **self.valid_registry_record(),
                        "adapter_id": "wrong-adapter",
                    },
                ),
            ),
            (
                "registry_entry_denied_scope_incomplete",
                lambda _root, _promotion_path, registry_entry: write_json(
                    registry_entry,
                    {
                        **self.valid_registry_record(),
                        "denied_scope": ["production"],
                    },
                ),
            ),
        )
        for reason, writer in cases:
            with self.subTest(reason=reason):
                root, promotion_path, output_dir, fixture_path = self.make_workspace()
                registry_entry = promotion_path.parent / "local_registry_entry.json"
                writer(root, promotion_path, registry_entry)

                result = self.run_receipt(
                    promotion_path,
                    output_dir,
                    fixture_path,
                    registry_entry=registry_entry,
                )

                self.assertFalse(result.complete)
                self.assertIn(reason, result.rejection_reasons)

    def _make_registry_symlink(self, root, _promotion_path, registry_entry):
        target = root / "registry-target.json"
        write_json(target, self.valid_registry_record())
        registry_entry.symlink_to(target)

    def test_local_fixture_reference_rejections_are_deterministic(self):
        forbidden_references = (
            "http://example.test/fixture",
            "https://example.test/fixture",
            "ws://example.test/socket",
            "wss://example.test/socket",
            "ftp://example.test/fixture",
            "data:text/plain,fixture",
            "javascript:alert(1)",
            "about:blank",
            "chrome://version",
        )
        for reference in forbidden_references:
            with self.subTest(reference=reference):
                _root, promotion_path, output_dir, fixture_path = self.make_workspace()
                result = self.run_receipt(
                    promotion_path,
                    output_dir,
                    fixture_path,
                    local_fixture_reference=reference,
                )
                self.assertFalse(result.complete)
                self.assertIn(
                    "local_fixture_reference_forbidden_scheme",
                    result.rejection_reasons,
                )

        local_cases = (
            (None, "local_fixture_reference_missing"),
            ("missing.html", "local_fixture_path_missing"),
        )
        for reference, reason in local_cases:
            with self.subTest(reason=reason):
                _root, promotion_path, output_dir, fixture_path = self.make_workspace()
                result = self.run_receipt(
                    promotion_path,
                    output_dir,
                    fixture_path,
                    local_fixture_reference=reference,
                )
                self.assertFalse(result.complete)
                self.assertIn(reason, result.rejection_reasons)

    def test_local_fixture_path_shape_rejections_are_deterministic(self):
        root, promotion_path, output_dir, fixture_path = self.make_workspace()
        symlink_fixture = output_dir / "fixture-link.html"
        symlink_fixture.symlink_to(fixture_path)
        result = self.run_receipt(
            promotion_path,
            output_dir,
            fixture_path,
            local_fixture_reference=symlink_fixture.as_posix(),
        )
        self.assertFalse(result.complete)
        self.assertIn("local_fixture_path_is_symlink", result.rejection_reasons)

        root, promotion_path, output_dir, fixture_path = self.make_workspace()
        fixture_dir = output_dir / "fixture-dir"
        fixture_dir.mkdir()
        result = self.run_receipt(
            promotion_path,
            output_dir,
            fixture_path,
            local_fixture_reference=fixture_dir.as_posix(),
        )
        self.assertFalse(result.complete)
        self.assertIn("local_fixture_path_not_regular_file", result.rejection_reasons)

        root, promotion_path, output_dir, fixture_path = self.make_workspace()
        outside_fixture = root / "outside.html"
        outside_fixture.write_text("<!doctype html>\n", encoding="utf-8")
        result = self.run_receipt(
            promotion_path,
            output_dir,
            fixture_path,
            local_fixture_reference=outside_fixture.as_posix(),
        )
        self.assertFalse(result.complete)
        self.assertIn(
            "local_fixture_path_outside_allowed_root",
            result.rejection_reasons,
        )

        root, promotion_path, output_dir, fixture_path = self.make_workspace()
        target_dir = root / "target-dir"
        target_dir.mkdir()
        linked_fixture = target_dir / "fixture.html"
        linked_fixture.write_text("<!doctype html>\n", encoding="utf-8")
        link_dir = output_dir / "link-dir"
        link_dir.symlink_to(target_dir)
        result = self.run_receipt(
            promotion_path,
            output_dir,
            fixture_path,
            local_fixture_reference=(link_dir / "fixture.html").as_posix(),
        )
        self.assertFalse(result.complete)
        self.assertIn(
            "local_fixture_path_has_symlink_component",
            result.rejection_reasons,
        )

    def test_output_collision_rejects_without_overwrite(self):
        _root, promotion_path, output_dir, fixture_path = self.make_workspace()
        (output_dir / "local_fixture_adapter_usage_receipt_result.json").write_text(
            "{}\n",
            encoding="utf-8",
        )

        result = self.run_receipt(promotion_path, output_dir, fixture_path)

        self.assertFalse(result.complete)
        self.assertIn("output_collision", result.rejection_reasons)
        self.assertIsNone(result.result_path)

    def test_cli_accepts_required_args_and_emits_usage_receipt(self):
        _root, promotion_path, output_dir, fixture_path = self.make_workspace()
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            exit_code = main(
                [
                    "launch-local-fixture-adapter-usage-receipt",
                    "--promotion-result",
                    promotion_path.as_posix(),
                    "--output-dir",
                    output_dir.as_posix(),
                    "--usage-receipt-id",
                    "usage-cli",
                    "--review-attestation",
                    LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_REVIEW_ATTESTATION,
                    "--local-fixture-reference",
                    fixture_path.as_posix(),
                ]
            )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["complete"])
        self.assertTrue(
            Path(payload["local_fixture_adapter_usage_receipt_result_path"]).exists()
        )

    def test_launcher_accepts_required_args_and_emits_usage_receipt(self):
        _root, promotion_path, output_dir, fixture_path = self.make_workspace()

        result = run_local_fixture_adapter_usage_receipt_launcher(
            promotion_path,
            output_dir,
            "usage-launcher",
            review_attestation=LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_REVIEW_ATTESTATION,
            local_fixture_reference=fixture_path.as_posix(),
        )

        self.assertTrue(result.complete)
        self.assertTrue(
            Path(result.payload["local_fixture_adapter_usage_receipt_result_path"]).exists()
        )

    def test_task_graph_accepts_usage_receipt_node_and_writes_artifact_outputs(self):
        root, promotion_path, output_dir, fixture_path = self.make_workspace()
        graph_path = root / "graph.json"
        graph_output = root / "graph-output"
        graph_output.mkdir()
        write_json_atomically(
            graph_path,
            {
                "graph_type": "personal_ai_execution_os_unified_task_graph_v1",
                "graph_id": "usage-receipt-graph",
                "execution_mode": "fixture_execution",
                "authority": "non_authority",
                "required_human_approval": True,
                "nodes": [
                    {
                        "node_id": "record_usage",
                        "adapter_id": "local_fixture_adapter_usage_receipt",
                        "capability": "launch_local_fixture_adapter_usage_receipt",
                        "execution_mode": "fixture",
                        "depends_on": [],
                        "approval_checkpoint_required": True,
                        "inputs": {
                            "promotion_result": promotion_path.as_posix(),
                            "output_dir": output_dir.as_posix(),
                            "usage_receipt_id": "usage-graph",
                            "review_attestation": LOCAL_FIXTURE_ADAPTER_USAGE_RECEIPT_REVIEW_ATTESTATION,
                            "local_fixture_reference": fixture_path.as_posix(),
                        },
                    }
                ],
            },
        )

        result = run_local_task_graph_fixture(graph_path, graph_output)
        execution_manifest = read_json(result.execution_manifest_path)
        artifact_outputs = read_json(result.artifact_outputs_manifest_path)

        self.assertTrue(result.success)
        node = execution_manifest["nodes"][0]
        self.assertTrue(node["local_fixture_adapter_usage_receipt_complete"])
        roles = {
            artifact["artifact_role"]
            for artifact in artifact_outputs["artifacts"]
            if artifact["node_id"] == "record_usage"
        }
        self.assertIn("local_fixture_adapter_usage_receipt_result", roles)
        self.assertIn("artifact_index", roles)
        self.assertIn("artifact_index_manifest", roles)

    def test_adapter_registry_includes_usage_receipt_candidate_local_fixture(self):
        entry = find_adapter_entry("local_fixture_adapter_usage_receipt")

        self.assertEqual(entry.admission_status, AdapterAdmissionStatus.CANDIDATE)
        self.assertEqual(entry.mode, AdapterMode.LOCAL_FIXTURE)
        self.assertEqual(entry.risk_class, AdapterRiskClass.LOCAL_READONLY)
        self.assertIn("launch_local_fixture_adapter_usage_receipt", entry.capabilities)
        decision = admit_adapter_capability(
            AdapterCapabilityRequest(
                adapter_id=entry.adapter_id,
                capability="launch_local_fixture_adapter_usage_receipt",
                mode=entry.mode,
                risk_class=entry.risk_class,
            )
        )
        self.assertFalse(decision.admitted)
        self.assertIn("adapter_not_admitted", decision.reason_codes)
        self.assertFalse(entry.boundary.network_allowed)

    def test_product_health_check_includes_usage_receipt_without_live_admission(self):
        report = build_product_health_report(Path.cwd())

        self.assertIn(
            "local_fixture_adapter_usage_receipt_workflow",
            report["launcher_workflows"],
        )
        self.assertIn(
            "launch-local-fixture-adapter-usage-receipt",
            report["required_cli_subcommands"],
        )
        self.assertTrue(report["launcher_workflows_complete"])
        self.assertTrue(report["cli_subcommands_complete"])
        self.assertTrue(report["runtime_admission_defaults_fail_closed"])
        self.assertFalse(report["network_runtime_allowed_by_default"])
        self.assertFalse(report["browser_runtime_allowed_by_default"])

    def test_review_attestation_missing_and_mismatch_reject(self):
        cases = (
            (None, "review_attestation_missing"),
            ("wrong-attestation", "review_attestation_mismatch"),
        )
        for attestation, reason in cases:
            with self.subTest(reason=reason):
                _root, promotion_path, output_dir, fixture_path = self.make_workspace()
                result = self.run_receipt(
                    promotion_path,
                    output_dir,
                    fixture_path,
                    review_attestation=attestation,
                )
                self.assertFalse(result.complete)
                self.assertIn(reason, result.rejection_reasons)

    def test_module_source_contains_no_forbidden_execution_or_cli_tokens(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        forbidden_tokens = (
            "import subprocess",
            "subprocess.run",
            "os.system",
            "os.popen",
            "import socket",
            "create_connection",
            "git clone",
            "fetch(",
            "--target-url",
            "--url",
            "--website",
            "--account",
            "--credential",
            "--cookie",
            "--scrape",
            "--bypass",
            "--captcha",
        )

        for token in forbidden_tokens:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_decision_doc_exists_and_states_non_production_local_only_boundary(self):
        self.assertTrue(DECISION_DOC.exists())
        text = DECISION_DOC.read_text(encoding="utf-8")

        for phrase in (
            "records only one local-fixture-only usage receipt after the #428",
            "does not execute the adapter",
            "does not execute Playwright",
            "does not execute #422",
            "does not execute #424",
            "does not execute #425",
            "does not execute #426",
            "does not execute #427",
            "does not execute candidate repository code",
            "does not enable production",
            "does not enable live websites",
            "does not enable general browser automation",
            "does not enable arbitrary URLs",
            "does not enable account/login/registration flows",
            "does not enable scraping",
            "does not enable bypass/captcha",
            "does not access secrets/cookies",
            "does not run npm/npx/install/browser download",
            "does not grant autonomy",
            "local_fixture_only",
            "one_usage_receipt_only",
            "human_review_required",
            "aggregation_bound",
            "regression_bound",
            "non_production",
            "separate policy, legal, network, credential, and human-approval gates",
        ):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
