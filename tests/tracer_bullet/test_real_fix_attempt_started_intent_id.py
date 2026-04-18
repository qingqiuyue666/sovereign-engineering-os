"""
Tracer-bullet test: AUDIT-003 / §22.1 parity for the
``real_fix_attempt_started`` audit record emitted by
``RealFixTracer.run`` via the shared ``_emit`` helper.

When the caller threads the durable
``intent_anchor_records.intent_id`` into ``RealFixTracer.run`` (as
``SignablePathOrchestrator.run_real_fix_chain`` does), the shared
``_emit`` helper forwards the id so the ``real_fix_attempt_started``
audit record names it in both ``artifact_refs`` and ``payload`` — the
tracer's causally-first emission, which fires on every chain entry
independent of downstream outcome.

Authoritative fail-closed verification of ``intent_id`` against
``intent_anchor_records`` remains the responsibility of
``RevisionSealService`` downstream; this tracer performs no
independent verification. Absent / empty ``intent_id`` preserves the
prior audit shape exactly on the attempt-started record.

Other outcome classes (``real_fix_adapter_failure``,
``real_fix_unparseable``, ``real_fix_exec_error``,
``real_fix_verified_fail``) are intentionally out of scope for this
increment; their emissions preserve the prior audit shape byte-for-byte.
The ``real_fix_verified_pass`` sibling landed in the prior increment
and is not re-asserted here. Driving this through the live tracer is
direct: feed a fake transport that returns any response and call
``RealFixTracer.run`` with the test's ``intent_id``; the
``real_fix_attempt_started`` record fires before the transport is
invoked.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
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
from kernel.stores.sqlite.repositories import AuditRepository
from kernel.stores.sqlite.wal_recovery import apply_migrations, open_connection
from kernel.tracers.real_fix_tracer import RealFixTracer, make_add_fix_task


def _messages_body(text: str) -> bytes:
    return json.dumps(
        {
            "id": "msg_fix_tracer",
            "type": "message",
            "role": "assistant",
            "model": "claude-sonnet-4-5",
            "content": [{"type": "text", "text": text}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }
    ).encode("utf-8")


CORRECT_ADD_BLOCK = (
    "Here is the fix:\n\n"
    "```python\n"
    "def add(a, b):\n"
    "    return a + b\n"
    "```\n"
)


class TestRealFixAttemptStartedNamesIntentId(unittest.TestCase):
    """AUDIT-003 / §22.1 parity for ``real_fix_attempt_started``."""

    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)
        self.audit_repo = AuditRepository(self.conn)
        self.audit = AppendOnlyLedger(
            repository=self.audit_repo,
            actor_identity="test_real_fix_attempt_started_intent_id",
        )

    def tearDown(self) -> None:
        self.conn.close()

    def _tracer(self) -> RealFixTracer:
        def transport(url, body, headers, timeout):
            return _TransportResponse(200, _messages_body(CORRECT_ADD_BLOCK))

        adapter = AnthropicMessagesAdapter(
            api_key="sk-test", transport=transport
        )
        return RealFixTracer(adapter=adapter, audit_ledger=self.audit)

    def _fetch_attempt_started_row(self, task_id: str) -> Any:
        return self.conn.execute(
            "SELECT payload_json, artifact_refs FROM audit_records "
            "WHERE task_id = ? "
            "AND record_type = 'real_fix_attempt_started' "
            "ORDER BY sequence ASC LIMIT 1;",
            (task_id,),
        ).fetchone()

    def test_attempt_started_names_intent_id_when_threaded(self) -> None:
        """A ``run`` call carrying ``intent_id`` must emit a
        ``real_fix_attempt_started`` audit row whose ``payload`` and
        ``artifact_refs`` both name the threaded ``intent_id`` while
        preserving the prior ``function_name`` / ``instruction`` /
        ``broken_source_hash`` / ``policy`` payload fields and the
        prior ``[real-fix::<task_id>]`` refs contribution."""
        intent_id = f"intent-{uuid4().hex[:8]}"
        task = make_add_fix_task(task_id=f"fix-{uuid4().hex[:8]}")

        self._tracer().run(task, intent_id=intent_id)

        row = self._fetch_attempt_started_row(task.task_id)
        self.assertIsNotNone(row)
        payload = json.loads(row["payload_json"])
        refs = json.loads(row["artifact_refs"])
        self.assertEqual(payload["intent_id"], intent_id)
        self.assertIn(intent_id, refs)
        # Prior fields preserved.
        self.assertEqual(payload["function_name"], task.function_name)
        self.assertEqual(payload["instruction"], task.instruction)
        self.assertIn("broken_source_hash", payload)
        self.assertIn("policy", payload)
        self.assertEqual(payload["replay_ceiling"], "semantic")
        self.assertIn(f"real-fix::{task.task_id}", refs)

    def test_absent_intent_id_preserves_prior_audit_shape(self) -> None:
        """A ``run`` call without ``intent_id`` must emit a
        ``real_fix_attempt_started`` audit row with the prior shape
        exactly: no ``intent_id`` field on ``payload`` and refs equal
        to ``[real-fix::<task_id>]``."""
        task = make_add_fix_task(task_id=f"fix-{uuid4().hex[:8]}")

        self._tracer().run(task)

        row = self._fetch_attempt_started_row(task.task_id)
        self.assertIsNotNone(row)
        payload = json.loads(row["payload_json"])
        refs = json.loads(row["artifact_refs"])
        self.assertNotIn("intent_id", payload)
        self.assertEqual(refs, [f"real-fix::{task.task_id}"])


if __name__ == "__main__":
    unittest.main()
