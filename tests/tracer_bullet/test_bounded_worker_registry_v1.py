"""Tests for bounded worker registry declarations."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from kernel.workers.bounded_worker_registry import (
    REQUIRED_WORKER_IDS,
    BoundedWorkerDeclaration,
    build_default_bounded_worker_registry,
    build_worker_routing_plan,
    registry_as_payload,
    validate_bounded_worker_registry,
)


GOVERNANCE_PATH = Path("governance/workers/bounded_worker_registry_v1.json")


class BoundedWorkerRegistryV1Tests(unittest.TestCase):
    def test_default_registry_contains_required_workers_without_live_authority(self) -> None:
        registry = build_default_bounded_worker_registry()
        by_id = {declaration.worker_id: declaration for declaration in registry}

        self.assertEqual(set(by_id), set(REQUIRED_WORKER_IDS))
        self.assertEqual(validate_bounded_worker_registry(registry), ())
        for declaration in registry:
            self.assertFalse(declaration.live_provider_calls_enabled)
            self.assertFalse(declaration.credential_storage_enabled)
            self.assertFalse(declaration.tool_execution_enabled)
            self.assertFalse(declaration.production_autonomy_enabled)
            self.assertGreater(declaration.timeout_seconds, 0)
            self.assertGreater(declaration.budget_units, 0)
            self.assertTrue(declaration.input_contract)
            self.assertTrue(declaration.output_contract)
            self.assertIn("must not invent validation results", declaration.hallucination_boundary)

    def test_registry_payload_is_contract_only(self) -> None:
        payload = registry_as_payload()

        self.assertEqual(payload["registry_type"], "bounded_worker_registry_v1")
        self.assertTrue(payload["valid"])
        self.assertFalse(payload["live_provider_calls_enabled"])
        self.assertFalse(payload["credential_storage_enabled"])
        self.assertFalse(payload["tool_execution_enabled"])
        self.assertFalse(payload["production_autonomy_enabled"])
        self.assertTrue(payload["routing_plan_only"])

    def test_invalid_live_provider_or_missing_contract_fails_closed(self) -> None:
        invalid = BoundedWorkerDeclaration(
            worker_id="codex",
            display_name="Codex",
            provider_family="openai_codex",
            task_classes=(),
            input_contract=(),
            output_contract=(),
            timeout_seconds=0,
            budget_units=0,
            evidence_requirements=(),
            hallucination_boundary=(),
            live_provider_calls_enabled=True,
            credential_storage_enabled=True,
            tool_execution_enabled=True,
            production_autonomy_enabled=True,
        )

        failures = validate_bounded_worker_registry((invalid,))

        self.assertIn("live_provider_enabled:codex", failures)
        self.assertIn("credential_storage_enabled:codex", failures)
        self.assertIn("tool_execution_enabled:codex", failures)
        self.assertIn("production_autonomy_enabled:codex", failures)
        self.assertIn("task_classes_missing:codex", failures)
        self.assertIn("required_worker_missing:claude", failures)

    def test_routing_plan_is_non_executing_and_deterministic(self) -> None:
        first = build_worker_routing_plan("code_review").as_dict()
        second = build_worker_routing_plan("code_review").as_dict()

        self.assertEqual(first, second)
        self.assertIn("codex", first["candidate_worker_ids"])
        self.assertNotIn("local_deterministic_python", first["candidate_worker_ids"])
        self.assertTrue(first["provider_execution_disabled"])
        self.assertTrue(first["tool_execution_disabled"])
        self.assertTrue(first["production_autonomy_disabled"])
        self.assertFalse(first["dispatch_performed"])
        self.assertFalse(first["provider_call_performed"])
        self.assertFalse(first["credential_access_performed"])
        self.assertFalse(first["tool_execution_performed"])

    def test_local_deterministic_python_routes_only_to_static_classes(self) -> None:
        plan = build_worker_routing_plan("static_contract_check").as_dict()

        self.assertEqual(plan["candidate_worker_ids"], ["local_deterministic_python"])

    def test_governance_contract_names_required_workers_and_boundaries(self) -> None:
        payload = json.loads(GOVERNANCE_PATH.read_text(encoding="utf-8"))

        self.assertEqual(set(payload["required_worker_ids"]), set(REQUIRED_WORKER_IDS))
        self.assertFalse(payload["live_provider_calls_enabled"])
        self.assertFalse(payload["credential_storage_enabled"])
        self.assertFalse(payload["tool_execution_enabled"])
        self.assertFalse(payload["production_autonomy_enabled"])
        for field in (
            "input_contract",
            "output_contract",
            "timeout_seconds",
            "budget_units",
            "evidence_requirements",
            "hallucination_boundary",
        ):
            self.assertIn(field, payload["required_contract_fields"])

    def test_source_has_no_provider_network_credential_or_tool_execution_surface(self) -> None:
        source = Path("kernel/workers/bounded_worker_registry.py").read_text(encoding="utf-8")

        for marker in (
            "requests.",
            "urllib.",
            "socket",
            "subprocess",
            "webbrowser",
            "api_key =",
            "os.environ",
            "load_dotenv",
            "openai.",
            "anthropic.",
            "google.",
        ):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
