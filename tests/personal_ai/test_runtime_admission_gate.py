import json
import tempfile
import unittest
from pathlib import Path

from kernel.personal_ai.hash_utils import sha256_file
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.runtime_admission_gate import (
    RuntimeAdmissionRequest,
    evaluate_runtime_admission,
    runtime_policy_for_class,
    write_runtime_admission_decision,
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class RuntimeAdmissionGateTests(unittest.TestCase):
    def make_root(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def write_artifacts(
        self,
        root,
        *,
        adapter_id="live_model_provider_boundary",
        capability="call_typed_schema_provider",
        runtime_class="live_model_provider",
        dry_run=True,
        approved=True,
        human_reviewed=True,
        real_runtime_enabled=False,
        manifest_config_hash_override=None,
        approval_config_hash_override=None,
        approval_manifest_hash_override=None,
        config_extra=None,
        approval_extra=None,
        manifest_extra=None,
    ):
        config_path = root / "runtime_config.json"
        manifest_path = root / "runtime_manifest.json"
        approval_path = root / "runtime_approval.json"
        policy = runtime_policy_for_class(runtime_class).to_dict()
        config = {
            "config_type": "personal_ai_runtime_config_v1",
            "adapter_id": adapter_id,
            "capability": capability,
            "runtime_class": runtime_class,
            "dry_run": dry_run,
            "real_runtime_enabled": real_runtime_enabled,
            "runtime_class_policy": policy,
            "required_human_approval": True,
        }
        if config_extra:
            config.update(config_extra)
        write_json_atomically(config_path, config)
        config_hash = sha256_file(config_path)
        manifest = {
            "manifest_type": "personal_ai_runtime_manifest_v1",
            "adapter_id": adapter_id,
            "capability": capability,
            "runtime_class": runtime_class,
            "dry_run": dry_run,
            "config_sha256": manifest_config_hash_override or config_hash,
            "required_human_approval": True,
        }
        if manifest_extra:
            manifest.update(manifest_extra)
        write_json_atomically(manifest_path, manifest)
        manifest_hash = sha256_file(manifest_path)
        approval = {
            "approval_type": "personal_ai_runtime_human_approval_v1",
            "adapter_id": adapter_id,
            "capability": capability,
            "runtime_class": runtime_class,
            "approved_action": "admit_runtime_execution",
            "approved": approved,
            "human_reviewed": human_reviewed,
            "config_sha256": approval_config_hash_override or config_hash,
            "manifest_sha256": approval_manifest_hash_override or manifest_hash,
            "required_human_approval": True,
        }
        if approval_extra:
            approval.update(approval_extra)
        write_json_atomically(approval_path, approval)
        return config_path, approval_path, manifest_path

    def request_for(
        self,
        config_path,
        approval_path,
        manifest_path,
        *,
        adapter_id="live_model_provider_boundary",
        capability="call_typed_schema_provider",
        runtime_class="live_model_provider",
        dry_run=True,
        activation_sources=("human_approval_artifact",),
    ):
        return RuntimeAdmissionRequest(
            adapter_id=adapter_id,
            capability=capability,
            runtime_class=runtime_class,
            config_artifact_path=config_path,
            human_approval_artifact_path=approval_path,
            manifest_artifact_path=manifest_path,
            dry_run=dry_run,
            activation_sources=activation_sources,
        )

    def test_default_request_is_denied_fail_closed(self):
        decision = evaluate_runtime_admission(RuntimeAdmissionRequest())

        self.assertFalse(decision.admitted)
        self.assertFalse(decision.activation_allowed)
        self.assertIn("adapter_id_required", decision.reason_codes)
        self.assertIn("capability_required", decision.reason_codes)
        self.assertIn("config_artifact_required", decision.reason_codes)
        self.assertIn("human_approval_artifact_required", decision.reason_codes)
        self.assertIn("manifest_artifact_required", decision.reason_codes)

    def test_valid_external_runtime_dry_run_writes_decision_artifact(self):
        root = self.make_root()
        config_path, approval_path, manifest_path = self.write_artifacts(root)
        decision_path = root / "runtime_decision.json"

        decision = write_runtime_admission_decision(
            self.request_for(config_path, approval_path, manifest_path),
            decision_path,
        )
        decision_payload = read_json(decision_path)

        self.assertTrue(decision.admitted)
        self.assertFalse(decision.activation_allowed)
        self.assertTrue(decision.dry_run)
        self.assertEqual(decision.reason_codes, ())
        self.assertTrue(decision.manifest_hash_bound)
        self.assertEqual(
            decision_payload["artifact_hashes"]["config_sha256"],
            sha256_file(config_path),
        )
        self.assertFalse(decision_payload["model_output_can_activate_runtime"])
        self.assertFalse(decision_payload["task_graph_can_activate_runtime"])
        self.assertFalse(decision_payload["cli_flag_can_activate_runtime"])

    def test_local_fixture_activation_can_be_admitted_with_artifacts(self):
        root = self.make_root()
        config_path, approval_path, manifest_path = self.write_artifacts(
            root,
            adapter_id="browser_fixture_runtime",
            capability="open_local_fixture",
            runtime_class="local_fixture",
            dry_run=False,
        )

        decision = evaluate_runtime_admission(
            self.request_for(
                config_path,
                approval_path,
                manifest_path,
                adapter_id="browser_fixture_runtime",
                capability="open_local_fixture",
                runtime_class="local_fixture",
                dry_run=False,
            )
        )

        self.assertTrue(decision.admitted)
        self.assertTrue(decision.activation_allowed)
        self.assertEqual(decision.reason_codes, ())

    def test_real_runtime_activation_is_deferred_even_with_valid_artifacts(self):
        root = self.make_root()
        config_path, approval_path, manifest_path = self.write_artifacts(
            root,
            dry_run=False,
        )

        decision = evaluate_runtime_admission(
            self.request_for(
                config_path,
                approval_path,
                manifest_path,
                dry_run=False,
            )
        )

        self.assertFalse(decision.admitted)
        self.assertFalse(decision.activation_allowed)
        self.assertIn(
            "runtime_class_not_activation_admitted",
            decision.reason_codes,
        )

    def test_activation_from_model_task_graph_or_cli_alone_is_denied(self):
        for source in ("model_output", "task_graph", "cli_flag"):
            with self.subTest(source=source):
                root = self.make_root()
                config_path, approval_path, manifest_path = self.write_artifacts(
                    root
                )
                decision = evaluate_runtime_admission(
                    self.request_for(
                        config_path,
                        approval_path,
                        manifest_path,
                        activation_sources=(source,),
                    )
                )

                self.assertFalse(decision.admitted)
                self.assertFalse(decision.activation_allowed)
                self.assertIn(
                    "activation_source_lacks_human_approval",
                    decision.reason_codes,
                )
                self.assertIn(
                    "model_task_cli_sources_are_not_authority",
                    decision.reason_codes,
                )

    def test_rejects_manifest_and_approval_hash_mismatch(self):
        root = self.make_root()
        config_path, approval_path, manifest_path = self.write_artifacts(
            root,
            manifest_config_hash_override="wrong-config-hash",
            approval_manifest_hash_override="wrong-manifest-hash",
        )

        decision = evaluate_runtime_admission(
            self.request_for(config_path, approval_path, manifest_path)
        )

        self.assertFalse(decision.admitted)
        self.assertFalse(decision.manifest_hash_bound)
        self.assertIn("manifest_config_hash_mismatch", decision.reason_codes)
        self.assertIn(
            "human_approval_manifest_hash_mismatch",
            decision.reason_codes,
        )

    def test_rejects_secret_material_in_admission_artifacts(self):
        root = self.make_root()
        config_path, approval_path, manifest_path = self.write_artifacts(
            root,
            config_extra={"api_key": "SHOULD_NOT_BE_STORED"},
        )

        decision = evaluate_runtime_admission(
            self.request_for(config_path, approval_path, manifest_path)
        )

        self.assertFalse(decision.admitted)
        self.assertIn("config_contains_secret_material", decision.reason_codes)

    def test_real_runtime_enabled_flag_is_not_current_admission(self):
        root = self.make_root()
        config_path, approval_path, manifest_path = self.write_artifacts(
            root,
            real_runtime_enabled=True,
        )

        decision = evaluate_runtime_admission(
            self.request_for(config_path, approval_path, manifest_path)
        )

        self.assertFalse(decision.admitted)
        self.assertIn("real_runtime_activation_deferred", decision.reason_codes)


if __name__ == "__main__":
    unittest.main()
