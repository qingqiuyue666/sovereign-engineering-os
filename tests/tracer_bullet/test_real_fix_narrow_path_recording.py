"""
Tracer-bullet test: real-fix tracer narrow-path recording.

Proves that when a ``RealFixNarrowPathRecorder`` is injected into
``RealFixTracer``, a verified real-provider fix is persisted as exactly
one ``InferenceArtifact`` row on the authority-bearing narrow-path
surface, with an honest ``replay_ceiling == "semantic"`` audit record,
and that every non-verified outcome class leaves the narrow-path
surface untouched (fail-closed by outcome class).

Scope:
- Exercises the existing ``AnthropicMessagesAdapter`` with a fake
  transport — no network.
- Uses the canonical ``make_add_fix_task`` single-file fix task.
- Uses the real ``InferenceArtifactRepository`` + schema validator.
- Asserts no ``replay_claim_exact`` ever appears, including on the
  narrow-path audit record.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import unittest
import urllib.error
from typing import Any
from uuid import uuid4

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)

from kernel.adapters.anthropic_adapter import (
    AnthropicMessagesAdapter,
    _TransportResponse,
)
from kernel.evidence.append_only_ledger import AppendOnlyLedger
from kernel.lifecycle.real_fix_recorder import (
    RealFixNarrowPathRecorder,
    RealFixRecorderRejected,
)
from kernel.stores.sqlite.repositories import (
    AuditRepository,
    InferenceArtifactRepository,
)
from kernel.stores.sqlite.wal_recovery import apply_migrations, open_connection
from kernel.tracers.real_fix_tracer import (
    RealFixTracer,
    RealFixResult,
    make_add_fix_task,
)


def _json_bytes(obj: Any) -> bytes:
    return json.dumps(obj).encode("utf-8")


def _messages_body(text: str, model: str = "claude-sonnet-4-5") -> bytes:
    return _json_bytes(
        {
            "id": "msg_fix_tracer_narrow",
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": [{"type": "text", "text": text}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 12, "output_tokens": 24},
        }
    )


CORRECT_ADD_BLOCK = (
    "```python\n"
    "def add(a, b):\n"
    "    return a + b\n"
    "```\n"
)

WRONG_ADD_BLOCK = (
    "```python\n"
    "def add(a, b):\n"
    "    return a + b + 1\n"
    "```\n"
)

NO_FENCE_RESPONSE = "I cannot produce a code block. Returning prose only."

MISSING_SYMBOL_BLOCK = (
    "```python\n"
    "def subtract(a, b):\n"
    "    return a - b\n"
    "```\n"
)


class _AuditCapture:
    """Wrap the ledger and record appended events for assertions."""

    def __init__(self, ledger: AppendOnlyLedger) -> None:
        self._ledger = ledger
        self.records: list[dict[str, Any]] = []

    def append(
        self,
        *,
        record_type: str,
        task_id: str,
        artifact_refs,
        payload,
    ) -> None:
        self.records.append(
            {
                "record_type": record_type,
                "task_id": task_id,
                "artifact_refs": list(artifact_refs),
                "payload": dict(payload),
            }
        )
        self._ledger.append(
            record_type=record_type,
            task_id=task_id,
            artifact_refs=artifact_refs,
            payload=payload,
        )


class RealFixNarrowPathRecordingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)
        self.audit_repo = AuditRepository(self.conn)
        self.inference_repo = InferenceArtifactRepository(self.conn)
        self.ledger = AppendOnlyLedger(
            repository=self.audit_repo,
            actor_identity="real_fix_tracer_narrow_path_test",
        )
        self.audit = _AuditCapture(self.ledger)
        self.recorder = RealFixNarrowPathRecorder(
            repository=self.inference_repo,
            audit_ledger=self.audit,
        )

    def tearDown(self) -> None:
        self.conn.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _tracer_with_transport(
        self,
        transport,
        *,
        with_recorder: bool = True,
    ) -> RealFixTracer:
        adapter = AnthropicMessagesAdapter(
            api_key="sk-test", transport=transport
        )
        return RealFixTracer(
            adapter=adapter,
            audit_ledger=self.audit,
            narrow_path_recorder=self.recorder if with_recorder else None,
        )

    def _count_inference_rows(self) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM inference_artifacts;"
        ).fetchone()[0]

    def _records_of(self, record_type: str) -> list[dict[str, Any]]:
        return [r for r in self.audit.records if r["record_type"] == record_type]

    def _assert_no_exact_replay_claim_anywhere(self) -> None:
        for rec in self.audit.records:
            # Every tracer-emitted record (including the narrow-path
            # inference_artifact_created when a recorder is wired) must
            # carry the honest semantic ceiling and must never assert an
            # exact-replay claim.
            self.assertEqual(
                rec["payload"].get("replay_ceiling"),
                "semantic",
                f"record {rec['record_type']} must carry replay_ceiling=semantic",
            )
            self.assertNotIn("replay_claim_exact", rec["payload"])

    # ------------------------------------------------------------------
    # Success: verified pass writes ONE authority-bearing row
    # ------------------------------------------------------------------

    def test_verified_pass_persists_one_inference_artifact_row(self) -> None:
        def t(*_a, **_k):
            return _TransportResponse(200, _messages_body(CORRECT_ADD_BLOCK))

        task = make_add_fix_task(task_id=f"fix-{uuid4().hex[:8]}")
        tracer = self._tracer_with_transport(t)

        result = tracer.run(task)

        # Honest verified-pass result carrying the narrow-path id.
        self.assertIsInstance(result, RealFixResult)
        self.assertTrue(result.verified)
        self.assertEqual(result.outcome, "real_fix_verified_pass")
        self.assertEqual(result.replay_ceiling, "semantic")
        self.assertTrue(
            result.inference_artifact_id.startswith("inf-"),
            f"expected surfaced inference_artifact_id, got {result.inference_artifact_id!r}",
        )

        # Exactly one row exists on the narrow-path surface.
        self.assertEqual(self._count_inference_rows(), 1)
        row = self.inference_repo.fetch(result.inference_artifact_id)
        self.assertIsNotNone(row)
        self.assertEqual(row["task_id"], task.task_id)
        self.assertEqual(row["output_hash"], result.output_hash)
        # Synthetic, tracer-scoped ids are used, clearly labeled for
        # reviewability. Nothing claims a ContextArtifact actually
        # exists upstream.
        self.assertEqual(
            row["context_artifact_id"], f"real-fix::context::{task.task_id}"
        )
        self.assertEqual(
            row["root_revision_id"], f"real-fix::root::{task.task_id}"
        )

        # The narrow-path audit event is present and cross-referenced
        # from the tracer's own verified_pass record.
        narrow_recs = self._records_of("inference_artifact_created")
        self.assertEqual(len(narrow_recs), 1)
        self.assertEqual(narrow_recs[0]["payload"]["source"], "real_fix_tracer")
        self.assertEqual(
            narrow_recs[0]["payload"]["replay_ceiling"], "semantic"
        )
        self.assertIn(
            result.inference_artifact_id, narrow_recs[0]["artifact_refs"]
        )

        pass_recs = self._records_of("real_fix_verified_pass")
        self.assertEqual(len(pass_recs), 1)
        self.assertEqual(
            pass_recs[0]["payload"].get("inference_artifact_id"),
            result.inference_artifact_id,
        )

        # Audit event ordering: tracer started -> narrow-path row
        # created -> tracer verified_pass. This is the minimum causal
        # shape a reviewer can walk.
        types = [r["record_type"] for r in self.audit.records]
        self.assertEqual(
            types,
            [
                "real_fix_attempt_started",
                "inference_artifact_created",
                "real_fix_verified_pass",
            ],
        )
        self._assert_no_exact_replay_claim_anywhere()

    # ------------------------------------------------------------------
    # Without a recorder: legacy audit-only behavior preserved bit-for-bit
    # ------------------------------------------------------------------

    def test_no_recorder_preserves_audit_only_behavior(self) -> None:
        def t(*_a, **_k):
            return _TransportResponse(200, _messages_body(CORRECT_ADD_BLOCK))

        task = make_add_fix_task(task_id=f"fix-{uuid4().hex[:8]}")
        tracer = self._tracer_with_transport(t, with_recorder=False)

        result = tracer.run(task)

        self.assertTrue(result.verified)
        self.assertEqual(result.inference_artifact_id, "")
        self.assertEqual(self._count_inference_rows(), 0)
        self.assertEqual(self._records_of("inference_artifact_created"), [])
        # The legacy audit chain is unchanged when no recorder is wired.
        types = [r["record_type"] for r in self.audit.records]
        self.assertEqual(
            types, ["real_fix_attempt_started", "real_fix_verified_pass"]
        )

    # ------------------------------------------------------------------
    # Failure classes: no narrow-path row is ever created
    # ------------------------------------------------------------------

    def test_verified_fail_does_not_write_narrow_path_row(self) -> None:
        def t(*_a, **_k):
            return _TransportResponse(200, _messages_body(WRONG_ADD_BLOCK))

        task = make_add_fix_task(task_id=f"fix-{uuid4().hex[:8]}")
        tracer = self._tracer_with_transport(t)

        result = tracer.run(task)

        self.assertFalse(result.verified)
        self.assertEqual(result.outcome, "real_fix_verified_fail")
        self.assertEqual(result.inference_artifact_id, "")
        self.assertEqual(self._count_inference_rows(), 0)
        self.assertEqual(self._records_of("inference_artifact_created"), [])
        self.assertEqual(len(self._records_of("real_fix_verified_fail")), 1)

    def test_unparseable_does_not_write_narrow_path_row(self) -> None:
        def t(*_a, **_k):
            return _TransportResponse(200, _messages_body(NO_FENCE_RESPONSE))

        task = make_add_fix_task(task_id=f"fix-{uuid4().hex[:8]}")
        tracer = self._tracer_with_transport(t)

        result = tracer.run(task)

        self.assertEqual(result.outcome, "real_fix_unparseable")
        self.assertEqual(result.inference_artifact_id, "")
        self.assertEqual(self._count_inference_rows(), 0)
        self.assertEqual(self._records_of("inference_artifact_created"), [])

    def test_exec_error_does_not_write_narrow_path_row(self) -> None:
        def t(*_a, **_k):
            return _TransportResponse(200, _messages_body(MISSING_SYMBOL_BLOCK))

        task = make_add_fix_task(task_id=f"fix-{uuid4().hex[:8]}")
        tracer = self._tracer_with_transport(t)

        result = tracer.run(task)

        self.assertEqual(result.outcome, "real_fix_exec_error")
        self.assertEqual(result.inference_artifact_id, "")
        self.assertEqual(self._count_inference_rows(), 0)
        self.assertEqual(self._records_of("inference_artifact_created"), [])

    def test_adapter_failure_does_not_write_narrow_path_row(self) -> None:
        def t(*_a, **_k):
            raise socket.timeout("read timeout")

        task = make_add_fix_task(task_id=f"fix-{uuid4().hex[:8]}")
        tracer = self._tracer_with_transport(t)

        result = tracer.run(task)

        self.assertEqual(result.outcome, "real_fix_adapter_failure")
        self.assertEqual(result.failure_class, "timeout")
        self.assertEqual(result.inference_artifact_id, "")
        self.assertEqual(self._count_inference_rows(), 0)
        self.assertEqual(self._records_of("inference_artifact_created"), [])

    def test_adapter_network_error_does_not_write_narrow_path_row(self) -> None:
        def t(*_a, **_k):
            raise urllib.error.URLError("Name or service not known")

        task = make_add_fix_task(task_id=f"fix-{uuid4().hex[:8]}")
        tracer = self._tracer_with_transport(t)

        result = tracer.run(task)

        self.assertEqual(result.outcome, "real_fix_adapter_failure")
        self.assertEqual(result.inference_artifact_id, "")
        self.assertEqual(self._count_inference_rows(), 0)

    # ------------------------------------------------------------------
    # Recorder admission is fail-closed: non-verified results rejected
    # ------------------------------------------------------------------

    def test_recorder_refuses_unverified_result(self) -> None:
        task = make_add_fix_task(task_id="fix-direct-reject")
        unverified = RealFixResult(
            verified=False,
            outcome="real_fix_verified_fail",
            fixed_source="def add(a, b):\n    return 0\n",
            output_hash="sha256:" + "0" * 64,
            failure_class="verification_failed",
            failure_detail="deliberate",
            latency_ms=0,
            replay_ceiling="semantic",
        )

        with self.assertRaises(RealFixRecorderRejected):
            self.recorder.record(
                task=task,
                result=unverified,
                worker_profile="test",
                model_route_id="anthropic:test",
            )

        # Fail-closed: the rejected call must not have persisted a row
        # nor appended an audit event.
        self.assertEqual(self._count_inference_rows(), 0)
        self.assertEqual(self._records_of("inference_artifact_created"), [])


if __name__ == "__main__":
    unittest.main()
