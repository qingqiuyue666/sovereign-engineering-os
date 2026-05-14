import unittest

from kernel.personal_ai.adapters.adapter_contract import (
    AdapterAdmissionDecision,
    AdapterAdmissionStatus,
    AdapterCapabilityRequest,
    AdapterExecutionBoundary,
    AdapterMode,
    AdapterResultManifest,
    AdapterRiskClass,
)


class AdapterContractTests(unittest.TestCase):
    def test_default_execution_boundary_is_fail_closed(self):
        boundary = AdapterExecutionBoundary()

        self.assertFalse(boundary.network_allowed)
        self.assertFalse(boundary.subprocess_allowed)
        self.assertFalse(boundary.external_tool_control_allowed)
        self.assertFalse(boundary.input_mutation_allowed)
        self.assertFalse(boundary.overwrite_existing_allowed)
        self.assertFalse(boundary.raw_value_copy_allowed)
        self.assertFalse(boundary.output_write_allowed)
        self.assertTrue(boundary.requires_human_approval)
        self.assertTrue(boundary.requires_capability_token)
        self.assertTrue(boundary.requires_manifest)
        self.assertTrue(boundary.requires_evidence_capture)
        self.assertTrue(boundary.requires_quarantine)
        self.assertTrue(boundary.requires_output_hashing)

    def test_helper_methods_reject_unsafe_runtime_surfaces(self):
        boundary = AdapterExecutionBoundary()

        self.assertTrue(boundary.is_runtime_safe_for_current_branch())
        self.assertFalse(boundary.requires_explicit_future_admission())
        self.assertTrue(boundary.rejects_unapproved_external_control())
        self.assertTrue(boundary.rejects_raw_value_leakage())
        self.assertTrue(boundary.rejects_input_mutation())
        self.assertTrue(boundary.rejects_unapproved_output_write())
        self.assertTrue(boundary.rejects_network_runtime())
        self.assertTrue(boundary.rejects_subprocess_runtime())
        self.assertTrue(boundary.requires_hash_bound_outputs())

    def test_network_and_subprocess_boundaries_require_future_admission(self):
        boundary = AdapterExecutionBoundary(
            network_allowed=True,
            subprocess_allowed=True,
        )

        self.assertFalse(boundary.is_runtime_safe_for_current_branch())
        self.assertTrue(boundary.requires_explicit_future_admission())
        self.assertFalse(boundary.rejects_network_runtime())
        self.assertFalse(boundary.rejects_subprocess_runtime())

    def test_output_write_can_be_safe_only_with_required_controls(self):
        boundary = AdapterExecutionBoundary(output_write_allowed=True)

        self.assertTrue(boundary.is_runtime_safe_for_current_branch())
        self.assertTrue(boundary.rejects_unapproved_output_write())

        unsafe_boundary = AdapterExecutionBoundary(
            output_write_allowed=True,
            requires_human_approval=False,
        )
        self.assertFalse(unsafe_boundary.is_runtime_safe_for_current_branch())
        self.assertFalse(unsafe_boundary.rejects_unapproved_output_write())

    def test_admission_decision_must_be_admitted_and_safe(self):
        decision = AdapterAdmissionDecision(
            adapter_id="xlsx_readonly_runtime",
            capability="inspect_local_xlsx_metadata",
            admission_status=AdapterAdmissionStatus.ADMITTED,
            admitted=True,
            reason_codes=(),
        )

        self.assertTrue(decision.is_runtime_safe_for_current_branch())

        rejected = AdapterAdmissionDecision(
            adapter_id="network_runtime",
            capability="fetch_url",
            admission_status=AdapterAdmissionStatus.REJECTED,
            admitted=False,
            reason_codes=("adapter_not_admitted",),
            boundary=AdapterExecutionBoundary(network_allowed=True),
        )
        self.assertFalse(rejected.is_runtime_safe_for_current_branch())

    def test_capability_request_preserves_typed_mode_and_risk(self):
        request = AdapterCapabilityRequest(
            adapter_id="xlsx_readonly_runtime",
            capability="inspect_local_xlsx_metadata",
            mode=AdapterMode.READONLY,
            risk_class=AdapterRiskClass.LOCAL_READONLY,
        )

        self.assertEqual(request.mode, AdapterMode.READONLY)
        self.assertEqual(request.risk_class, AdapterRiskClass.LOCAL_READONLY)
        self.assertTrue(request.boundary.is_runtime_safe_for_current_branch())

    def test_result_manifest_is_deterministic_and_non_authority(self):
        manifest = AdapterResultManifest(
            adapter_id="adapter",
            capability="capability",
            manifest_type="test_manifest",
            artifact_paths=("b.json", "a.json"),
            artifact_hashes={"b": "2", "a": "1"},
        )

        payload = manifest.to_dict()

        self.assertEqual(payload["authority"], "non_authority")
        self.assertFalse(payload["input_mutation_performed"])
        self.assertFalse(payload["overwrite_performed"])
        self.assertFalse(payload["raw_value_copy_performed"])
        self.assertEqual(list(payload["artifact_hashes"]), ["a", "b"])


if __name__ == "__main__":
    unittest.main()
