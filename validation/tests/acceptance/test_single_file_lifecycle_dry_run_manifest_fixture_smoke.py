import json
import unittest

from examples.single_file_lifecycle_dry_run_manifest_fixture import (
    run_single_file_lifecycle_dry_run_manifest_fixture,
)


_TOP_LEVEL_KEYS = (
    "ok",
    "fixture_id",
    "fixture_version",
    "mode",
    "status",
    "description",
    "manifest",
    "authority",
    "forbidden_operations",
    "proves",
    "does_not_prove",
    "bounded_summary",
)

_MANIFEST_KEYS = (
    "manifest_id",
    "manifest_version",
    "lifecycle_line",
    "intended_operation",
    "target_scope",
    "execution_mode",
    "planned_inputs",
    "planned_outputs",
    "planned_verification",
    "json_safe",
    "bounded",
)

_PLANNED_INPUTS_KEYS = (
    "proposal_id",
    "patch_id",
    "target_path",
    "expected_preimage_identity",
    "validation_profile",
    "approval_mapping_required",
)

_PLANNED_OUTPUTS_KEYS = (
    "would_create_proposal_record",
    "would_create_patch_body_record",
    "would_create_preimage_record",
    "would_create_validation_result_record",
    "would_create_final_seal_record",
    "would_create_replay_summary",
)

_PLANNED_VERIFICATION_KEYS = (
    "would_require_existing_lifecycle",
    "would_require_existing_replay_verifier",
    "would_require_explicit_approval_mapping",
    "would_require_validation_callable",
    "would_require_bounded_json_safe_output",
)

_AUTHORITY_KEYS = (
    "adapter_implementation_authorized",
    "adapter_runtime_authorized",
    "runtime_authorized",
    "service_calls_authorized",
    "db_repository_uow_authorized",
    "evidence_audit_append_authorized",
    "executor_dispatch_authorized",
    "restore_service_authorized",
    "cli_authorized",
    "subprocess_authorized",
    "network_authorized",
    "tool_execution_authorized",
    "multi_file_lifecycle_authorized",
    "broad_physical_io_authorized",
    "durable_writes_authorized",
    "irreversible_actions_authorized",
    "autonomous_agent_runtime_authorized",
    "production_automation_platform_authorized",
    "business_delivery_os_authorized",
    "personal_ai_execution_os_authorized",
    "creative_production_os_authorized",
    "research_decision_os_authorized",
    "new_governance_boundary_family_authorized",
)

_FORBIDDEN_OPERATIONS = [
    "adapter implementation",
    "adapter runtime",
    "service calls",
    "DB/repository/UoW",
    "evidence/audit append",
    "executor dispatch",
    "restore service",
    "CLI integration",
    "subprocess",
    "network",
    "tool execution",
    "multi-file lifecycle",
    "broad physical I/O",
    "durable writes",
    "irreversible actions",
    "autonomous agent runtime",
    "production automation platform",
    "Business Delivery OS",
    "Personal AI Execution OS",
    "Creative Production OS",
    "Research Decision OS",
    "new governance boundary family",
]

_PROVES = [
    "bounded manifest shape",
    "hard-false authority posture",
    "non-execution claim",
    "JSON-safe fixture output",
    "dry-run manifest wording",
]

_DOES_NOT_PROVE = [
    "adapter implementation readiness",
    "adapter runtime readiness",
    "general runtime readiness",
    "service runtime readiness",
    "DB/repository/UoW readiness",
    "executor runtime readiness",
    "evidence/audit append readiness",
    "multi-file lifecycle readiness",
    "broad physical I/O readiness",
    "autonomous agent runtime readiness",
    "production automation platform readiness",
    "Business Delivery OS readiness",
    "Personal AI Execution OS readiness",
    "Creative Production OS readiness",
    "Research Decision OS readiness",
]

_BOUNDED_SUMMARY_KEYS = (
    "summary",
    "stop_rule",
    "next_step_boundary",
)

_FORBIDDEN_POSITIVE_WORDING = (
    "adapter implementation",
    "adapter runtime",
    "general runtime",
    "autonomous executor",
    "production automation platform",
    "full AI execution OS",
    "multi-file patch system",
)


class SingleFileLifecycleDryRunManifestFixtureSmokeTest(unittest.TestCase):
    def test_fixture_returns_exact_bounded_manifest(self):
        result = run_single_file_lifecycle_dry_run_manifest_fixture()

        self.assertIs(result["ok"], True)
        self.assertEqual(tuple(result), _TOP_LEVEL_KEYS)
        self.assertEqual(
            result["fixture_id"],
            "single-file-lifecycle-dry-run-manifest-fixture-v1",
        )
        self.assertEqual(result["fixture_version"], "v1")
        self.assertEqual(result["mode"], "dry_run_manifest_only")
        self.assertEqual(result["status"], "non_executing")
        self.assertEqual(
            result["description"],
            "a bounded non-executing dry-run manifest fixture for the controlled "
            "single-file lifecycle line",
        )

        manifest = result["manifest"]
        self.assertEqual(tuple(manifest), _MANIFEST_KEYS)
        self.assertEqual(
            manifest["manifest_id"],
            "single-file-lifecycle-dry-run-manifest-v1",
        )
        self.assertEqual(manifest["manifest_version"], "v1")
        self.assertEqual(
            manifest["lifecycle_line"],
            "controlled_single_file_lifecycle",
        )
        self.assertEqual(manifest["intended_operation"], "dry_run_planning_only")
        self.assertEqual(manifest["target_scope"], "repo_contained_single_text_file")
        self.assertEqual(manifest["execution_mode"], "non_executing_manifest_only")
        self.assertIs(manifest["json_safe"], True)
        self.assertIs(manifest["bounded"], True)

        self.assertEqual(tuple(manifest["planned_inputs"]), _PLANNED_INPUTS_KEYS)
        for value in manifest["planned_inputs"].values():
            self.assertIsInstance(value, str)
            self.assertTrue(value)

        self.assertEqual(tuple(manifest["planned_outputs"]), _PLANNED_OUTPUTS_KEYS)
        for value in manifest["planned_outputs"].values():
            self.assertIs(type(value), bool)

        self.assertEqual(
            tuple(manifest["planned_verification"]),
            _PLANNED_VERIFICATION_KEYS,
        )
        for value in manifest["planned_verification"].values():
            self.assertIs(value, True)

        authority = result["authority"]
        self.assertEqual(tuple(authority), _AUTHORITY_KEYS)
        self.assertEqual(set(authority), set(_AUTHORITY_KEYS))
        for value in authority.values():
            self.assertIs(type(value), bool)
            self.assertIs(value, False)

        self.assertEqual(result["forbidden_operations"], _FORBIDDEN_OPERATIONS)
        self.assertEqual(result["proves"], _PROVES)
        self.assertEqual(result["does_not_prove"], _DOES_NOT_PROVE)

        bounded_summary = result["bounded_summary"]
        self.assertEqual(tuple(bounded_summary), _BOUNDED_SUMMARY_KEYS)
        self.assertEqual(
            bounded_summary,
            {
                "summary": "bounded non-executing dry-run manifest fixture only",
                "stop_rule": "STOP_BEFORE_ADAPTER_IMPLEMENTATION",
                "next_step_boundary": (
                    "no adapter implementation without later explicit decision audit"
                ),
            },
        )
        self.assertEqual(
            bounded_summary["stop_rule"],
            "STOP_BEFORE_ADAPTER_IMPLEMENTATION",
        )

        encoded = json.dumps(result, sort_keys=True, allow_nan=False)
        self.assertEqual(json.loads(encoded), result)
        self._assert_json_safe(result)
        self._assert_no_positive_forbidden_wording(result)

    def test_repeated_calls_return_independent_dict_objects(self):
        first = run_single_file_lifecycle_dry_run_manifest_fixture()
        second = run_single_file_lifecycle_dry_run_manifest_fixture()

        self.assertIsNot(first, second)
        self.assertIsNot(first["manifest"], second["manifest"])
        self.assertIsNot(
            first["manifest"]["planned_inputs"],
            second["manifest"]["planned_inputs"],
        )
        self.assertIsNot(first["authority"], second["authority"])
        self.assertIsNot(first["forbidden_operations"], second["forbidden_operations"])

        first["manifest"]["planned_inputs"]["proposal_id"] = "mutated"
        first["authority"]["runtime_authorized"] = True
        first["forbidden_operations"].append("mutated")

        fresh = run_single_file_lifecycle_dry_run_manifest_fixture()
        self.assertEqual(
            fresh["manifest"]["planned_inputs"]["proposal_id"],
            "placeholder-proposal-id",
        )
        self.assertIs(fresh["authority"]["runtime_authorized"], False)
        self.assertEqual(fresh["forbidden_operations"], _FORBIDDEN_OPERATIONS)

    def _assert_json_safe(self, value):
        if value is None:
            return
        if type(value) is bool:
            return
        if isinstance(value, str):
            return
        if isinstance(value, int):
            return
        if isinstance(value, float):
            self.assertEqual(value, value)
            self.assertNotEqual(value, float("inf"))
            self.assertNotEqual(value, float("-inf"))
            return
        if isinstance(value, list):
            for item in value:
                self._assert_json_safe(item)
            return
        if isinstance(value, dict):
            for key, item in value.items():
                self.assertIsInstance(key, str)
                self._assert_json_safe(item)
            return
        self.fail(f"non-JSON-safe value leaked: {type(value).__name__}")

    def _assert_no_positive_forbidden_wording(self, result):
        for path, text in self._string_values(result):
            lowered = text.lower()
            for wording in _FORBIDDEN_POSITIVE_WORDING:
                if wording.lower() not in lowered:
                    continue
                if self._allowed_denial_path(path, lowered):
                    continue
                self.fail(f"positive forbidden wording at {path}: {wording}")

    def _string_values(self, value, path="result"):
        if isinstance(value, str):
            yield path, value
            return
        if isinstance(value, list):
            for index, item in enumerate(value):
                yield from self._string_values(item, f"{path}[{index}]")
            return
        if isinstance(value, dict):
            for key, item in value.items():
                yield from self._string_values(item, f"{path}.{key}")

    def _allowed_denial_path(self, path, lowered):
        return (
            ".forbidden_operations[" in path
            or ".does_not_prove[" in path
            or lowered.startswith("no ")
        )


if __name__ == "__main__":
    unittest.main()
