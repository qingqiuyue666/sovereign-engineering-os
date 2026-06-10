"""Tracer-bullet tests for Domain Adapter Foundation V1."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import unittest

from kernel.domain.domain_adapter_foundation import (
    AdapterAdmissionRules,
    AssetHashBinding,
    DomainAdapterFamily,
    DomainOperationClass,
    OperationPlanDescriptor,
    OutputManifestContract,
    ReplayPolicy,
    build_default_domain_adapter_contracts,
    build_domain_adapter_contract,
    validate_asset_hash_binding,
    validate_domain_adapter_contract,
)


class DomainAdapterFoundationV1Tests(unittest.TestCase):
    def test_all_required_adapter_families_are_contract_only_candidates(self):
        contracts = build_default_domain_adapter_contracts()

        self.assertEqual(
            tuple(contract.adapter_family for contract in contracts),
            DomainAdapterFamily.all(),
        )
        self.assertIn("comfyui", DomainAdapterFamily.all())
        self.assertIn("houdini", DomainAdapterFamily.all())
        self.assertIn("blender", DomainAdapterFamily.all())
        self.assertIn("unreal", DomainAdapterFamily.all())
        self.assertIn("davinci_resolve", DomainAdapterFamily.all())
        self.assertIn("after_effects", DomainAdapterFamily.all())

        for contract in contracts:
            self.assertEqual(validate_domain_adapter_contract(contract), ())
            self.assertFalse(contract.admission_rules.runtime_admitted)
            self.assertFalse(contract.admission_rules.live_dcc_execution_allowed)
            self.assertEqual(contract.admission_rules.admission_status, "candidate")

    def test_descriptors_bind_state_operation_assets_outputs_provenance_and_replay(self):
        contract = build_domain_adapter_contract(DomainAdapterFamily.BLENDER)
        payload = contract.to_dict()

        self.assertEqual(payload["adapter_family"], "blender")
        self.assertIn("state_proxy", payload)
        self.assertIn("operation_plan", payload)
        self.assertIn("output_manifest", payload)
        self.assertIn("provenance_policy", payload)
        self.assertIn("replay_policy", payload)
        self.assertTrue(payload["operation_plan"]["content_hash"].startswith("sha256:"))
        self.assertTrue(payload["output_manifest"]["output_hashing_required"])
        self.assertTrue(payload["provenance_policy"]["operation_plan_hash_required"])
        self.assertTrue(payload["replay_policy"]["environment_digest_required"])
        self.assertFalse(payload["replay_policy"]["automatic_reexecution_allowed"])

    def test_validation_rejects_live_dcc_runtime_and_uncontrolled_authority(self):
        contract = build_domain_adapter_contract(DomainAdapterFamily.HOUDINI)
        unsafe = replace(
            contract,
            operation_plan=replace(
                contract.operation_plan,
                live_execution_allowed=True,
                process_launch_allowed=True,
                network_access_allowed=True,
                source_asset_overwrite_allowed=True,
                arbitrary_command_allowed=True,
                arbitrary_python_allowed=True,
            ),
            admission_rules=AdapterAdmissionRules(
                runtime_admitted=True,
                live_dcc_execution_allowed=True,
                process_launch_allowed=True,
                network_access_allowed=True,
                source_asset_overwrite_allowed=True,
                explicit_future_admission_required=False,
            ),
            replay_policy=ReplayPolicy(automatic_reexecution_allowed=True),
        )

        failures = validate_domain_adapter_contract(unsafe)

        self.assertIn("live_execution_forbidden", failures)
        self.assertIn("process_launch_forbidden", failures)
        self.assertIn("operation_network_forbidden", failures)
        self.assertIn("source_asset_overwrite_forbidden", failures)
        self.assertIn("arbitrary_command_forbidden", failures)
        self.assertIn("arbitrary_python_forbidden", failures)
        self.assertIn("runtime_admitted_forbidden", failures)
        self.assertIn("live_dcc_execution_allowed_forbidden", failures)
        self.assertIn("automatic_reexecution_forbidden", failures)

    def test_asset_and_output_manifest_contracts_reject_overwrite_and_bad_digest(self):
        bad_binding = AssetHashBinding(
            asset_id="source",
            asset_role="source",
            digest="not-a-digest",
            source_mutation_allowed=True,
            source_overwrite_allowed=True,
        )

        binding_failures = validate_asset_hash_binding(bad_binding)
        self.assertIn("asset_digest_must_be_sha256", binding_failures)
        self.assertIn("source_mutation_forbidden", binding_failures)
        self.assertIn("source_overwrite_forbidden", binding_failures)

        contract = build_domain_adapter_contract(DomainAdapterFamily.COMFYUI)
        unsafe_manifest = replace(
            contract,
            output_manifest=OutputManifestContract(
                manifest_id="manifest",
                plan_id=contract.operation_plan.plan_id,
                output_asset_bindings=(bad_binding,),
                output_directory_policy="source_directory",
                output_hashing_required=False,
                source_asset_overwrite_allowed=True,
                existing_output_overwrite_allowed=True,
                raw_payload_storage_allowed=True,
            ),
        )

        manifest_failures = validate_domain_adapter_contract(unsafe_manifest)
        self.assertIn(
            "output_directory_policy_must_be_new_artifact_directory_only",
            manifest_failures,
        )
        self.assertIn("output_hashing_required", manifest_failures)
        self.assertIn("output_overwrite_forbidden", manifest_failures)
        self.assertIn("raw_payload_storage_forbidden", manifest_failures)

    def test_operation_classes_are_declarative_only(self):
        plan = OperationPlanDescriptor(
            plan_id="plan",
            adapter_family=DomainAdapterFamily.DAVINCI_RESOLVE,
            operation_class=DomainOperationClass.PREPARE_REPLAY,
            operation_name="prepare_descriptor_only_replay",
            input_asset_bindings=(
                AssetHashBinding(
                    asset_id="timeline",
                    asset_role="source",
                    digest="sha256:" + ("1" * 64),
                ),
            ),
            planned_output_refs=("artifact:manifest",),
            operation_steps=("compare descriptor hashes",),
        )

        self.assertTrue(plan.content_hash().startswith("sha256:"))
        self.assertFalse(plan.to_dict()["live_execution_allowed"])
        self.assertIn(DomainOperationClass.PREPARE_REPLAY, DomainOperationClass.all())

    def test_governance_descriptor_and_docs_record_forbidden_surfaces(self):
        descriptor = json.loads(
            Path("governance/domain/domain_adapter_foundation_v1.json").read_text(
                encoding="utf-8"
            )
        )
        docs = Path("docs/operator/domain_adapter_foundation_v1.md").read_text(
            encoding="utf-8"
        ).lower()

        self.assertTrue(descriptor["contract_only"])
        self.assertFalse(descriptor["runtime_admitted"])
        self.assertFalse(descriptor["live_dcc_execution_allowed"])
        self.assertFalse(descriptor["process_launch_allowed"])
        self.assertFalse(descriptor["network_access_allowed"])
        self.assertFalse(descriptor["source_asset_overwrite_allowed"])
        self.assertTrue(descriptor["future_runtime_admission_required"])
        self.assertIn("state_proxy_descriptor", descriptor["required_descriptors"])
        self.assertIn("operation_plan_descriptor", descriptor["required_descriptors"])
        self.assertIn("no live dcc execution", docs)
        self.assertIn("source overwrite", docs)

    def test_source_has_no_live_execution_imports_or_runtime_launch_surface(self):
        source = Path("kernel/domain/domain_adapter_foundation.py").read_text(
            encoding="utf-8"
        )

        for marker in (
            "subprocess",
            "socket",
            "requests",
            "httpx",
            "urllib",
            "webbrowser",
            "playwright",
            "selenium",
            "os.system",
            "Popen",
            "shell=True",
            "exec(",
            "eval(",
        ):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
