"""
AI Worker Router V1 acceptance.

Routing must produce a deterministic handoff plan only. It must not dispatch a
worker, call a provider, read credentials, access networks, or execute tools.
"""

from __future__ import annotations

import unittest

from kernel.runtime.ai_worker_router import route_ai_worker_task


class AIWorkerRouterAcceptanceTests(unittest.TestCase):
    def test_code_change_route_is_handoff_only_and_hash_bound(self) -> None:
        plan = route_ai_worker_task(
            {
                "route_id": "route-acceptance-001",
                "task_id": "task-acceptance-001",
                "task_class": "code_change",
                "risk_level": "high",
                "required_capabilities": ["code_editing", "test_authoring"],
            }
        )

        self.assertEqual(plan.route_status, "ready_for_handoff")
        self.assertEqual(plan.selected_worker_id, "codex")
        self.assertTrue(plan.handoff_packet_required)
        self.assertTrue(plan.human_review_required)
        self.assertTrue(plan.content_hash.startswith("sha256:"))
        self.assertFalse(plan.provider_execution_permitted)
        self.assertFalse(plan.worker_dispatch_performed)
        self.assertFalse(plan.credential_accessed)
        self.assertFalse(plan.tool_execution_performed)
        self.assertFalse(plan.network_accessed)
        self.assertFalse(plan.production_autonomy_enabled)

    def test_forbidden_prompt_material_is_rejected_before_route_plan(self) -> None:
        with self.assertRaises(ValueError):
            route_ai_worker_task(
                {
                    "route_id": "route-acceptance-002",
                    "task_id": "task-acceptance-002",
                    "task_class": "code_change",
                    "risk_level": "medium",
                    "required_capabilities": ["code_editing"],
                    "raw_prompt": "must not be routed",
                }
            )


if __name__ == "__main__":
    unittest.main()
