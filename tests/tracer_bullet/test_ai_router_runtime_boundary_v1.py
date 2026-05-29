"""Tests for AI router runtime boundary V1."""

from __future__ import annotations

import ast
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from kernel.runtime.ai_router_runtime_boundary import (
    ZERO_HASH,
    FileBackedAIRouterRuntimeBoundary,
    compute_ai_router_runtime_boundary_receipt_hash,
)
from kernel.runtime.durable_job_queue import DurableJobQueue
from kernel.stores.artifact_store_persistence import FileBackedArtifactStore
from kernel.stores.real_wal_storage import FileBackedRealWalStorage


ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = ROOT / "kernel" / "runtime" / "ai_router_runtime_boundary.py"
TASK_ID = "task-522"
RUN_ID = "run-522"
OBSERVED_AT = "2026-05-29T00:02:20+00:00"


def _hash(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def _queue(root: Path) -> DurableJobQueue:
    return DurableJobQueue(
        path=root / "review-queue" / "jobs.jsonl",
        queue_id="ai-router-boundary-test-queue",
    )


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "blocked_worker_ids": (),
        "declared_effects": ("patch_candidate_emitted",),
        "human_invoked": True,
        "idempotency_key": "ai-router-idempotency-522",
        "input_artifact_hash": _hash("input-artifact-522"),
        "output_candidate_hash": _hash("output-candidate-522"),
        "output_kind": "patch_candidate",
        "prompt_artifact_hash": _hash("prompt-artifact-522"),
        "proposal_body_hash": _hash("proposal-body-522"),
        "requested_action": "emit_patch_candidate",
        "requested_by": "operator-522",
        "required_capabilities": ("code_editing", "test_authoring"),
        "review_packet_hash": _hash("review-packet-522"),
        "risk_level": "medium",
        "route_id": "route-522",
        "run_id": RUN_ID,
        "task_class": "code_change",
        "task_id": TASK_ID,
    }
    payload.update(overrides)
    return payload


def _artifact_payload_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            keys.add(str(key))
            keys.update(_artifact_payload_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.update(_artifact_payload_keys(item))
    return keys


class AIRouterRuntimeBoundaryV1Tests(unittest.TestCase):
    def test_proposal_route_binds_model_receipt_artifact_wal_and_review_queue(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            queue = _queue(root)
            runtime = FileBackedAIRouterRuntimeBoundary(runtime_root=root)

            receipt = runtime.route_proposal(
                _payload(),
                queue,
                observed_at=OBSERVED_AT,
            )
            wal_records = FileBackedRealWalStorage(
                root / "ai-router-runtime" / "ai-router.real-wal.jsonl"
            ).read_records()
            artifact_store = FileBackedArtifactStore(
                root / "ai-router-runtime" / "artifacts",
                store_id="ai-router-runtime-artifacts-v1",
            )
            artifact_records = artifact_store.read_records()
            artifact_payload = json.loads(
                artifact_store.artifact_path(artifact_records[0].manifest).read_text(
                    encoding="utf-8"
                )
            )
            queue_state = queue.get_job_state(receipt.review_queue_job_id)
            receipt_path = (
                root
                / "ai-router-runtime"
                / "receipts"
                / (receipt.receipt_hash.removeprefix("sha256:") + ".json")
            )
            receipt_path_exists = receipt_path.is_file()

        self.assertTrue(receipt.accepted, receipt.failures)
        self.assertEqual(receipt.selected_worker_id, "codex")
        self.assertEqual(receipt.provider_family, "openai")
        self.assertTrue(receipt.review_required)
        self.assertTrue(receipt.approval_required)
        self.assertFalse(receipt.provider_execution_performed)
        self.assertFalse(receipt.tool_execution_performed)
        self.assertFalse(receipt.runtime_state_mutated)
        self.assertFalse(receipt.automatic_merge_performed)
        self.assertFalse(receipt.automatic_push_performed)
        self.assertNotEqual(receipt.route_plan_hash, ZERO_HASH)
        self.assertNotEqual(receipt.model_routing_receipt_hash, ZERO_HASH)
        self.assertNotEqual(receipt.artifact_record_hash, ZERO_HASH)
        self.assertNotEqual(receipt.artifact_manifest_hash, ZERO_HASH)
        self.assertNotEqual(receipt.queue_record_hash, ZERO_HASH)
        self.assertNotEqual(receipt.ai_router_wal_record_hash, ZERO_HASH)
        self.assertEqual(
            receipt.receipt_hash,
            compute_ai_router_runtime_boundary_receipt_hash(receipt),
        )
        self.assertEqual(queue_state.state, "queued")
        self.assertEqual(queue_state.last_event_hash, receipt.queue_record_hash)
        self.assertTrue(receipt_path_exists)
        self.assertEqual(len(wal_records), 1)
        self.assertEqual(wal_records[0].record_type, "AI_ROUTER_EVENT")
        self.assertEqual(wal_records[0].record_hash, receipt.ai_router_wal_record_hash)
        self.assertEqual(len(artifact_records), 1)
        self.assertEqual(artifact_records[0].manifest.artifact_type, "audit_json")
        self.assertFalse(
            _artifact_payload_keys(artifact_payload).intersection(
                {
                    "argv",
                    "command",
                    "content",
                    "credential",
                    "cwd",
                    "env",
                    "path",
                    "raw",
                    "raw_response",
                    "secret",
                    "stderr",
                    "stdout",
                    "token",
                    "tool",
                }
            )
        )

    def test_unsafe_tool_unsupported_mutation_and_secret_requests_fail_closed(self) -> None:
        cases = (
            (
                {"tool_request_hash": _hash("tool-request-522")},
                "unsafe_ai_router_field:tool_request_hash",
            ),
            (
                {
                    "requested_action": "publish_summary",
                    "declared_effects": ("proposal_emitted",),
                    "output_kind": "proposal",
                },
                "unsupported_action",
            ),
            (
                {
                    "requested_action": "merge_to_main",
                    "declared_effects": ("patch_candidate_emitted",),
                },
                "runtime_mutation_action_forbidden",
            ),
            (
                {
                    "declared_effects": (
                        "patch_candidate_emitted",
                        "provider_called",
                    )
                },
                "hallucinated_action_forbidden:provider_called",
            ),
            (
                {"api_key": "sk-" + ("x" * 24)},
                "unsafe_ai_router_field:api_key",
            ),
        )

        for overrides, expected_failure in cases:
            with self.subTest(expected_failure=expected_failure):
                with tempfile.TemporaryDirectory() as tempdir:
                    root = Path(tempdir)
                    queue = _queue(root)
                    runtime = FileBackedAIRouterRuntimeBoundary(runtime_root=root)

                    receipt = runtime.route_proposal(
                        _payload(**overrides),
                        queue,
                        observed_at=OBSERVED_AT,
                    )

                    self.assertFalse(receipt.accepted)
                    self.assertIn(expected_failure, receipt.failures)
                    self.assertEqual(queue.records, ())
                    self.assertEqual(receipt.artifact_record_hash, ZERO_HASH)
                    self.assertEqual(receipt.queue_record_hash, ZERO_HASH)
                    self.assertEqual(receipt.ai_router_wal_record_hash, ZERO_HASH)
                    self.assertFalse((root / "ai-router-runtime").exists())

    def test_action_output_kind_mismatch_and_missing_review_queue_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            runtime = FileBackedAIRouterRuntimeBoundary(runtime_root=root)

            mismatch = runtime.route_proposal(
                _payload(output_kind="plan"),
                _queue(root),
                observed_at=OBSERVED_AT,
            )
            missing_queue = runtime.route_proposal(
                _payload(),
                object(),  # type: ignore[arg-type]
                observed_at=OBSERVED_AT,
            )

        self.assertFalse(mismatch.accepted)
        self.assertIn("action_output_kind_mismatch", mismatch.failures)
        self.assertFalse(missing_queue.accepted)
        self.assertIn("review_queue_required", missing_queue.failures)

    def test_source_has_no_provider_tool_browser_network_or_main_mutation_surface(self) -> None:
        source = SOURCE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".", 1)[0])

        forbidden_imports = {
            "argparse",
            "asyncio",
            "httpx",
            "mcp",
            "openai",
            "playwright",
            "requests",
            "selenium",
            "socket",
            "subprocess",
            "threading",
            "urllib",
            "webbrowser",
        }
        self.assertFalse(imports.intersection(forbidden_imports))
        for marker in (
            "git merge",
            "git push",
            "os.environ",
            "Popen",
            "shell=True",
            "while True",
        ):
            self.assertNotIn(marker, source)


if __name__ == "__main__":
    unittest.main()
