"""
Tracer-bullet test: real-model real-fix tracer (fake transport).

Proves that ``kernel.tracers.real_fix_tracer.RealFixTracer`` routes one
adapter invocation through
``kernel.adapters.anthropic_adapter.AnthropicMessagesAdapter`` and
produces an honest verified/failed result for the canonical ``add`` fix
task. No network. A fake transport is injected.

Every outcome class is exercised:
- verified pass     : fenced block with a correct ``add`` implementation
- verified fail     : fenced block with a semantically-wrong ``add``
- unparseable       : response has no fenced Python block
- exec error        : fenced block has invalid Python / missing symbol
- adapter failure   : transport raises -> adapter maps to InferenceFailure

Every audit record is checked for:
- ``replay_ceiling == "semantic"``
- matching ``record_type`` for the outcome
- presence of the task id on the record
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
from kernel.stores.sqlite.repositories import AuditRepository
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
            "id": "msg_fix_tracer",
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": [{"type": "text", "text": text}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }
    )


# Canonical correct fix wrapped in a fenced Python block.
CORRECT_ADD_BLOCK = (
    "Here is the fix:\n\n"
    "```python\n"
    "def add(a, b):\n"
    "    return a + b\n"
    "```\n"
    "That changes the operator from - to +.\n"
)

# Semantically-wrong fix: passes syntax but fails verification.
WRONG_ADD_BLOCK = (
    "```python\n"
    "def add(a, b):\n"
    "    return a + b + 1\n"
    "```\n"
)

# No fenced block — unparseable.
NO_FENCE_RESPONSE = "I cannot produce a code block. Returning prose only."

# Fenced block that defines the wrong symbol (no ``add``).
MISSING_SYMBOL_BLOCK = (
    "```python\n"
    "def subtract(a, b):\n"
    "    return a - b\n"
    "```\n"
)

# Fenced block with invalid Python.
SYNTAX_ERROR_BLOCK = (
    "```python\n"
    "def add(a, b)\n"
    "    return a + b\n"
    "```\n"
)


class _AuditCapture:
    """Wrap the ledger and remember appended records for assertions."""

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


class RealFixTracerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)
        self.audit_repo = AuditRepository(self.conn)
        self.ledger = AppendOnlyLedger(
            repository=self.audit_repo, actor_identity="real_fix_tracer_test"
        )
        self.audit = _AuditCapture(self.ledger)

    def tearDown(self) -> None:
        self.conn.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _tracer_with_transport(self, transport) -> RealFixTracer:
        adapter = AnthropicMessagesAdapter(
            api_key="sk-test", transport=transport
        )
        return RealFixTracer(adapter=adapter, audit_ledger=self.audit)

    def _record_types(self) -> list[str]:
        return [r["record_type"] for r in self.audit.records]

    def _records_of(self, record_type: str) -> list[dict[str, Any]]:
        return [r for r in self.audit.records if r["record_type"] == record_type]

    def _assert_semantic_ceiling_on_every_record(self) -> None:
        for rec in self.audit.records:
            self.assertEqual(
                rec["payload"].get("replay_ceiling"),
                "semantic",
                f"record {rec['record_type']} did not carry honest replay ceiling",
            )

    # ------------------------------------------------------------------
    # Happy path: verified pass
    # ------------------------------------------------------------------

    def test_happy_path_produces_verified_pass(self) -> None:
        seen: dict[str, Any] = {}

        def t(url, body, headers, timeout):
            seen["body"] = json.loads(body.decode("utf-8"))
            return _TransportResponse(200, _messages_body(CORRECT_ADD_BLOCK))

        task = make_add_fix_task(task_id=f"fix-{uuid4().hex[:8]}")
        tracer = self._tracer_with_transport(t)
        result = tracer.run(task)

        self.assertIsInstance(result, RealFixResult)
        self.assertTrue(result.verified)
        self.assertEqual(result.outcome, "real_fix_verified_pass")
        self.assertEqual(result.replay_ceiling, "semantic")
        self.assertTrue(result.output_hash.startswith("sha256:"))
        self.assertIn("return a + b", result.fixed_source)

        # The adapter's fix-task prompt mode fired: the broken source
        # must be embedded in the user content verbatim.
        msg = seen["body"]["messages"][0]["content"]
        self.assertIn("real-fix tracer", msg)
        self.assertIn("return a - b", msg)
        self.assertIn("def add(a, b)", msg)

        # Audit chain: started -> verified_pass, with honest ceiling.
        self.assertEqual(
            self._record_types(),
            ["real_fix_attempt_started", "real_fix_verified_pass"],
        )
        self._assert_semantic_ceiling_on_every_record()
        pass_rec = self._records_of("real_fix_verified_pass")[0]
        self.assertEqual(pass_rec["task_id"], task.task_id)
        self.assertEqual(
            pass_rec["payload"]["cases_passed"],
            len(task.verification_cases),
        )

    # ------------------------------------------------------------------
    # Semantic failure
    # ------------------------------------------------------------------

    def test_semantic_wrong_fix_produces_verified_fail(self) -> None:
        def t(*_a, **_k):
            return _TransportResponse(200, _messages_body(WRONG_ADD_BLOCK))

        task = make_add_fix_task(task_id=f"fix-{uuid4().hex[:8]}")
        tracer = self._tracer_with_transport(t)
        result = tracer.run(task)

        self.assertFalse(result.verified)
        self.assertEqual(result.outcome, "real_fix_verified_fail")
        self.assertEqual(result.failure_class, "verification_failed")
        # First case is add(2, 3) == 5; wrong impl returns 6.
        self.assertEqual(result.first_failing_case_index, 0)

        fail_recs = self._records_of("real_fix_verified_fail")
        self.assertEqual(len(fail_recs), 1)
        payload = fail_recs[0]["payload"]
        self.assertEqual(payload["case_index"], 0)
        self.assertEqual(payload["expected"], 5)
        self.assertEqual(payload["actual"], 6)
        self._assert_semantic_ceiling_on_every_record()

    # ------------------------------------------------------------------
    # Unparseable response
    # ------------------------------------------------------------------

    def test_no_code_block_produces_unparseable(self) -> None:
        def t(*_a, **_k):
            return _TransportResponse(200, _messages_body(NO_FENCE_RESPONSE))

        task = make_add_fix_task(task_id=f"fix-{uuid4().hex[:8]}")
        tracer = self._tracer_with_transport(t)
        result = tracer.run(task)

        self.assertFalse(result.verified)
        self.assertEqual(result.outcome, "real_fix_unparseable")
        self.assertEqual(result.fixed_source, "")

        self.assertIn("real_fix_unparseable", self._record_types())
        self._assert_semantic_ceiling_on_every_record()

    # ------------------------------------------------------------------
    # Exec errors: missing symbol and syntax error
    # ------------------------------------------------------------------

    def test_missing_function_produces_exec_error(self) -> None:
        def t(*_a, **_k):
            return _TransportResponse(
                200, _messages_body(MISSING_SYMBOL_BLOCK)
            )

        task = make_add_fix_task(task_id=f"fix-{uuid4().hex[:8]}")
        tracer = self._tracer_with_transport(t)
        result = tracer.run(task)

        self.assertFalse(result.verified)
        self.assertEqual(result.outcome, "real_fix_exec_error")
        self.assertEqual(result.first_failing_case_index, 0)
        self.assertIn("add", result.failure_detail)

        exec_recs = self._records_of("real_fix_exec_error")
        self.assertEqual(len(exec_recs), 1)
        self._assert_semantic_ceiling_on_every_record()

    def test_syntax_error_produces_exec_error(self) -> None:
        def t(*_a, **_k):
            return _TransportResponse(
                200, _messages_body(SYNTAX_ERROR_BLOCK)
            )

        task = make_add_fix_task(task_id=f"fix-{uuid4().hex[:8]}")
        tracer = self._tracer_with_transport(t)
        result = tracer.run(task)

        self.assertFalse(result.verified)
        self.assertEqual(result.outcome, "real_fix_exec_error")
        self.assertEqual(result.failure_class, "SyntaxError")
        self._assert_semantic_ceiling_on_every_record()

    # ------------------------------------------------------------------
    # Adapter failures: timeout, quota, auth, refusal
    # ------------------------------------------------------------------

    def test_adapter_timeout_is_normalized_failure(self) -> None:
        def t(*_a, **_k):
            raise socket.timeout("read timeout")

        task = make_add_fix_task(task_id=f"fix-{uuid4().hex[:8]}")
        tracer = self._tracer_with_transport(t)
        result = tracer.run(task)

        self.assertFalse(result.verified)
        self.assertEqual(result.outcome, "real_fix_adapter_failure")
        self.assertEqual(result.failure_class, "timeout")
        recs = self._records_of("real_fix_adapter_failure")
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["payload"]["failure_class"], "timeout")
        self._assert_semantic_ceiling_on_every_record()

    def test_adapter_quota_is_normalized_failure(self) -> None:
        def t(*_a, **_k):
            return _TransportResponse(
                429,
                _json_bytes(
                    {"error": {"type": "rate_limit_error", "message": "slow"}}
                ),
            )

        task = make_add_fix_task(task_id=f"fix-{uuid4().hex[:8]}")
        tracer = self._tracer_with_transport(t)
        result = tracer.run(task)

        self.assertFalse(result.verified)
        self.assertEqual(result.outcome, "real_fix_adapter_failure")
        self.assertEqual(result.failure_class, "quota_exhausted")
        self._assert_semantic_ceiling_on_every_record()

    def test_adapter_auth_is_normalized_failure(self) -> None:
        def t(*_a, **_k):
            return _TransportResponse(
                401,
                _json_bytes(
                    {
                        "error": {
                            "type": "authentication_error",
                            "message": "bad key",
                        }
                    }
                ),
            )

        task = make_add_fix_task(task_id=f"fix-{uuid4().hex[:8]}")
        tracer = self._tracer_with_transport(t)
        result = tracer.run(task)

        self.assertFalse(result.verified)
        self.assertEqual(result.outcome, "real_fix_adapter_failure")
        self.assertEqual(result.failure_class, "auth_error")
        self._assert_semantic_ceiling_on_every_record()

    def test_adapter_refusal_is_normalized_failure(self) -> None:
        def t(*_a, **_k):
            return _TransportResponse(
                200,
                _json_bytes(
                    {
                        "content": [{"type": "text", "text": "no"}],
                        "stop_reason": "refusal",
                        "usage": {"input_tokens": 5, "output_tokens": 1},
                        "model": "claude-sonnet-4-5",
                    }
                ),
            )

        task = make_add_fix_task(task_id=f"fix-{uuid4().hex[:8]}")
        tracer = self._tracer_with_transport(t)
        result = tracer.run(task)

        self.assertFalse(result.verified)
        self.assertEqual(result.outcome, "real_fix_adapter_failure")
        self.assertEqual(result.failure_class, "refusal")
        self._assert_semantic_ceiling_on_every_record()

    def test_network_error_is_normalized_failure(self) -> None:
        def t(*_a, **_k):
            raise urllib.error.URLError("Name or service not known")

        task = make_add_fix_task(task_id=f"fix-{uuid4().hex[:8]}")
        tracer = self._tracer_with_transport(t)
        result = tracer.run(task)

        self.assertFalse(result.verified)
        self.assertEqual(result.outcome, "real_fix_adapter_failure")
        self.assertEqual(result.failure_class, "network_error")
        self._assert_semantic_ceiling_on_every_record()

    # ------------------------------------------------------------------
    # No-silent-downgrade: tracer never claims verified on real-model
    # output without the ceiling recorded.
    # ------------------------------------------------------------------

    def test_no_exact_replay_claim_is_ever_emitted(self) -> None:
        def t(*_a, **_k):
            return _TransportResponse(200, _messages_body(CORRECT_ADD_BLOCK))

        task = make_add_fix_task(task_id=f"fix-{uuid4().hex[:8]}")
        tracer = self._tracer_with_transport(t)
        result = tracer.run(task)

        self.assertTrue(result.verified)
        for rec in self.audit.records:
            ceiling = rec["payload"].get("replay_ceiling")
            self.assertEqual(
                ceiling,
                "semantic",
                "real-model output must never claim exact replay fidelity",
            )
            self.assertNotIn("replay_claim_exact", rec["payload"])


if __name__ == "__main__":
    unittest.main()
