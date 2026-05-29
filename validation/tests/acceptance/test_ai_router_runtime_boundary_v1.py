"""Acceptance tests for AI router runtime boundary V1."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from kernel.runtime.ai_router_runtime_boundary import (
    ZERO_HASH,
    FileBackedAIRouterRuntimeBoundary,
)
from kernel.runtime.durable_job_queue import DurableJobQueue
from kernel.stores.artifact_store_persistence import FileBackedArtifactStore
from kernel.stores.real_wal_storage import FileBackedRealWalStorage


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


class AIRouterRuntimeBoundaryAcceptanceV1Tests(unittest.TestCase):
    def test_ai_router_outputs_review_queued_proposal_without_execution_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            queue = DurableJobQueue(
                path=root / "review-queue" / "jobs.jsonl",
                queue_id="ai-router-acceptance-review-queue",
            )
            runtime = FileBackedAIRouterRuntimeBoundary(runtime_root=root)

            receipt = runtime.route_proposal(
                {
                    "blocked_worker_ids": (),
                    "declared_effects": ("plan_emitted",),
                    "human_invoked": True,
                    "idempotency_key": "acceptance-idempotency-522",
                    "input_artifact_hash": _hash("acceptance-input"),
                    "output_candidate_hash": _hash("acceptance-output"),
                    "output_kind": "plan",
                    "prompt_artifact_hash": _hash("acceptance-prompt"),
                    "proposal_body_hash": _hash("acceptance-proposal"),
                    "requested_action": "emit_plan",
                    "requested_by": "acceptance-operator",
                    "required_capabilities": ("planning",),
                    "review_packet_hash": _hash("acceptance-review-packet"),
                    "risk_level": "high",
                    "route_id": "route-acceptance-522",
                    "run_id": "run-acceptance-522",
                    "task_class": "planning",
                    "task_id": "task-acceptance-522",
                },
                queue,
                observed_at="2026-05-29T00:02:20+00:00",
            )
            queued_state = queue.get_job_state(receipt.review_queue_job_id)
            wal_records = FileBackedRealWalStorage(
                root / "ai-router-runtime" / "ai-router.real-wal.jsonl"
            ).read_records()
            artifact_records = FileBackedArtifactStore(
                root / "ai-router-runtime" / "artifacts",
                store_id="ai-router-runtime-artifacts-v1",
            ).read_records()

        self.assertTrue(receipt.accepted, receipt.failures)
        self.assertEqual(receipt.requested_action, "emit_plan")
        self.assertEqual(receipt.output_kind, "plan")
        self.assertEqual(queued_state.state, "queued")
        self.assertEqual(queued_state.last_event_hash, receipt.queue_record_hash)
        self.assertNotEqual(receipt.model_routing_receipt_hash, ZERO_HASH)
        self.assertNotEqual(receipt.artifact_manifest_hash, ZERO_HASH)
        self.assertNotEqual(receipt.ai_router_wal_record_hash, ZERO_HASH)
        self.assertEqual(wal_records[0].record_type, "AI_ROUTER_EVENT")
        self.assertEqual(artifact_records[0].manifest.artifact_type, "audit_json")
        self.assertFalse(receipt.provider_execution_performed)
        self.assertFalse(receipt.tool_execution_performed)
        self.assertFalse(receipt.runtime_state_mutated)
        self.assertFalse(receipt.automatic_merge_performed)
        self.assertFalse(receipt.automatic_push_performed)


if __name__ == "__main__":
    unittest.main()
