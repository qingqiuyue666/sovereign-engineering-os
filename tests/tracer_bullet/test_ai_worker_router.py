"""Tracer-bullet tests for the non-executing AI worker router."""

from __future__ import annotations

from pathlib import Path
import json
import unittest

from kernel.audit.hashchain import digest_payload
from kernel.runtime.ai_worker_router import (
    DEFAULT_AI_WORKER_DECLARATIONS,
    AIWorkerDeclaration,
    route_ai_worker_task,
    render_ai_worker_route_plan_json,
)


def route_material(**overrides: object) -> dict[str, object]:
    material: dict[str, object] = {
        "route_id": "route-001",
        "task_id": "task-001",
        "task_class": "code_change",
        "risk_level": "medium",
        "required_capabilities": ["code_editing", "test_authoring"],
    }
    material.update(overrides)
    return material


class AIWorkerRouterTests(unittest.TestCase):
    def test_code_change_routes_to_codex_without_dispatch_or_provider_call(self) -> None:
        plan = route_ai_worker_task(route_material())

        self.assertEqual(plan.route_status, "ready_for_handoff")
        self.assertEqual(plan.selected_worker_id, "codex")
        self.assertIn("codex", plan.candidate_worker_ids)
        self.assertTrue(plan.handoff_packet_required)
        self.assertTrue(plan.human_review_required)
        self.assertFalse(plan.provider_execution_permitted)
        self.assertFalse(plan.worker_dispatch_performed)
        self.assertFalse(plan.credential_accessed)
        self.assertFalse(plan.tool_execution_performed)
        self.assertFalse(plan.network_accessed)
        self.assertFalse(plan.production_autonomy_enabled)
        self.assertEqual(plan.content_hash, digest_payload(plan.deterministic_material()))

    def test_local_validation_prefers_local_python(self) -> None:
        plan = route_ai_worker_task(
            route_material(
                task_class="deterministic_validation",
                risk_level="low",
                required_capabilities=["local_validation"],
            )
        )

        self.assertEqual(plan.selected_worker_id, "local_python")
        self.assertFalse(plan.human_review_required)

    def test_requested_worker_and_blocked_worker_are_deterministic(self) -> None:
        requested = route_ai_worker_task(
            route_material(
                task_class="implementation_review",
                required_capabilities=["code_reasoning"],
                requested_worker_id="deepseek",
            )
        )
        blocked = route_ai_worker_task(
            route_material(
                task_class="implementation_review",
                required_capabilities=["code_reasoning"],
                requested_worker_id="deepseek",
                blocked_worker_ids=["deepseek"],
            )
        )

        self.assertEqual(requested.selected_worker_id, "deepseek")
        self.assertEqual(blocked.route_status, "blocked_no_candidate")
        self.assertIn("worker_explicitly_blocked", blocked.rejected_worker_reasons["deepseek"])

    def test_no_candidate_records_rejections(self) -> None:
        plan = route_ai_worker_task(
            route_material(
                task_class="financial_execution",
                required_capabilities=["brokerage_api"],
            )
        )

        self.assertEqual(plan.route_status, "blocked_no_candidate")
        self.assertEqual(plan.selected_worker_id, "")
        self.assertFalse(plan.candidate_worker_ids)
        self.assertTrue(plan.rejected_worker_reasons)

    def test_forbidden_raw_prompt_and_secret_fields_fail_closed(self) -> None:
        for field in ("raw_prompt", "secret", "api_key", "env"):
            with self.subTest(field=field):
                material = route_material()
                material[field] = "blocked"
                with self.assertRaises(ValueError):
                    route_ai_worker_task(material)

    def test_live_provider_or_tool_enabled_declaration_is_rejected(self) -> None:
        unsafe = AIWorkerDeclaration(
            worker_id="unsafe",
            display_name="Unsafe",
            provider_family="unsafe",
            task_classes=("code_change",),
            capabilities=("code_editing",),
            timeout_seconds=60,
            budget_policy_ref="budget-policy:unsafe",
            evidence_requirements=("final_report",),
            hallucination_boundary="unsafe",
            human_review_required=True,
            live_provider_call_allowed=True,
        )

        plan = route_ai_worker_task(
            route_material(required_capabilities=["code_editing"]),
            declarations=(unsafe,),
        )

        self.assertEqual(plan.route_status, "blocked_no_candidate")
        self.assertIn("live_provider_call_not_allowed", plan.rejected_worker_reasons["unsafe"])

    def test_rendering_is_json_and_deterministic(self) -> None:
        first = route_ai_worker_task(route_material())
        second = route_ai_worker_task(route_material())

        self.assertEqual(first.content_hash, second.content_hash)
        payload = json.loads(render_ai_worker_route_plan_json(first))
        self.assertEqual(payload["selected_worker_id"], "codex")

    def test_default_registry_declares_required_workers(self) -> None:
        worker_ids = {declaration.worker_id for declaration in DEFAULT_AI_WORKER_DECLARATIONS}
        self.assertTrue({"codex", "claude", "gemini", "gpt", "deepseek", "local_python"}.issubset(worker_ids))

    def test_source_safety_checks_pass(self) -> None:
        source = Path("kernel/runtime/ai_worker_router.py").read_text(encoding="utf-8")
        for marker in (
            "import subprocess",
            "import socket",
            "import requests",
            "import httpx",
            "import sqlite3",
            "os.environ",
            "os.getenv",
            "load_dotenv",
        ):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
