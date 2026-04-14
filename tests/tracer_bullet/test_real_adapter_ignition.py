"""
Tracer-bullet test: real-model adapter ignition.

Proves that the one real adapter wired into the narrow signable path
(`kernel.adapters.anthropic_adapter.AnthropicMessagesAdapter`) routes
provider output honestly through the existing governed boundary and
normalizes every declared failure class to `InferenceFailure` so that
`InferenceService._emit_failure_bundle` records it.

No live network. A fake transport callable is injected into the adapter,
which lets the test exercise each failure class AND the happy path
without ever touching the network. The `live` ignition test that calls
the real provider is in `test_real_adapter_live_ignition.py` and is
opt-in via env.

Scope:
- failure classes: timeout, network_error, quota_exhausted, auth_error,
  server_error, malformed_response (multiple shapes), refusal.
- happy path: well-formed Messages API response -> valid typed dict
  matching InferenceService._parse_response's required keys.
- InferenceService records the adapter's replay_ceiling ("semantic")
  on the `inference_artifact_created` audit payload.
- Fail-closed on failure: no InferenceArtifact row is persisted.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping
from uuid import uuid4

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)

from kernel.adapters.anthropic_adapter import (
    AnthropicMessagesAdapter,
    REPLAY_CEILING,
    _TransportResponse,
)
from kernel.services.inference_service import (
    InferenceFailure,
    InferencePolicy,
    InferenceService,
)
from kernel.evidence.append_only_ledger import AppendOnlyLedger
from kernel.lifecycle.signable_path_orchestrator import IntentCausalAnchor
from kernel.services.context_service import ContextService
from kernel.stores.sqlite.repositories import (
    AuditRepository,
    ContextArtifactRepository,
    InferenceArtifactRepository,
)
from kernel.stores.sqlite.wal_recovery import apply_migrations, open_connection


# ---------------------------------------------------------------------------
# Fake transports: one per failure class + one happy-path transport.
# ---------------------------------------------------------------------------


def _json_bytes(obj: Any) -> bytes:
    return json.dumps(obj).encode("utf-8")


def _happy_body(model: str = "claude-sonnet-4-5") -> bytes:
    return _json_bytes(
        {
            "id": "msg_tracer_01",
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": [
                {"type": "text", "text": "tracer ignition acknowledged"},
            ],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 12, "output_tokens": 7},
        }
    )


# ---------------------------------------------------------------------------
# Unit tests: adapter failure-class normalization + happy path.
# ---------------------------------------------------------------------------


class TestAdapterFailureClassNormalization(unittest.TestCase):
    """Every failure class raises InferenceFailure with a class-tagged detail."""

    envelope: Mapping[str, Any] = {
        "context_artifact_id": "ctx-1",
        "root_revision_id": "rev-1",
        "candidate_file_ids": ["a.py"],
        "symbol_frontier_ids": [],
        "content_hash": "sha256:abc",
        "packing_policy_version": "p1",
        "taint_set": [],
        "phase": "phase1",
    }
    policy = InferencePolicy(max_output_tokens=64, timeout_seconds=5.0)

    def _invoke(self, transport, api_key: str = "sk-test"):
        adapter = AnthropicMessagesAdapter(
            api_key=api_key, transport=transport
        )
        return adapter.invoke(prompt_envelope=self.envelope, policy=self.policy)

    def test_missing_api_key_raises_auth_error(self) -> None:
        adapter = AnthropicMessagesAdapter(api_key="", transport=lambda *a, **k: None)
        with self.assertRaises(InferenceFailure) as ctx:
            adapter.invoke(prompt_envelope=self.envelope, policy=self.policy)
        self.assertTrue(str(ctx.exception).startswith("auth_error:"))

    def test_timeout_is_normalized(self) -> None:
        def t(*_a, **_k):
            raise socket.timeout("read timed out")

        with self.assertRaises(InferenceFailure) as ctx:
            self._invoke(t)
        self.assertTrue(str(ctx.exception).startswith("timeout:"))

    def test_builtin_timeouterror_is_normalized(self) -> None:
        def t(*_a, **_k):
            raise TimeoutError("deadline exceeded")

        with self.assertRaises(InferenceFailure) as ctx:
            self._invoke(t)
        self.assertTrue(str(ctx.exception).startswith("timeout:"))

    def test_urlerror_wrapping_timeout_is_normalized_as_timeout(self) -> None:
        def t(*_a, **_k):
            raise urllib.error.URLError(socket.timeout("slow"))

        with self.assertRaises(InferenceFailure) as ctx:
            self._invoke(t)
        self.assertTrue(str(ctx.exception).startswith("timeout:"))

    def test_network_error_is_normalized(self) -> None:
        def t(*_a, **_k):
            raise urllib.error.URLError("Name or service not known")

        with self.assertRaises(InferenceFailure) as ctx:
            self._invoke(t)
        self.assertTrue(str(ctx.exception).startswith("network_error:"))

    def test_oserror_is_normalized_as_network_error(self) -> None:
        def t(*_a, **_k):
            raise OSError("connection reset by peer")

        with self.assertRaises(InferenceFailure) as ctx:
            self._invoke(t)
        self.assertTrue(str(ctx.exception).startswith("network_error:"))

    def test_unexpected_transport_exception_is_network_error(self) -> None:
        def t(*_a, **_k):
            raise RuntimeError("bad TLS handshake")

        with self.assertRaises(InferenceFailure) as ctx:
            self._invoke(t)
        self.assertTrue(str(ctx.exception).startswith("network_error:"))

    def test_http_429_is_quota_exhausted(self) -> None:
        def t(*_a, **_k):
            return _TransportResponse(
                429,
                _json_bytes(
                    {"error": {"type": "rate_limit_error", "message": "slow down"}}
                ),
            )

        with self.assertRaises(InferenceFailure) as ctx:
            self._invoke(t)
        self.assertTrue(str(ctx.exception).startswith("quota_exhausted:"))

    def test_overloaded_error_is_quota_exhausted(self) -> None:
        def t(*_a, **_k):
            return _TransportResponse(
                529,
                _json_bytes(
                    {"error": {"type": "overloaded_error", "message": "overloaded"}}
                ),
            )

        with self.assertRaises(InferenceFailure) as ctx:
            self._invoke(t)
        self.assertTrue(str(ctx.exception).startswith("quota_exhausted:"))

    def test_http_401_is_auth_error(self) -> None:
        def t(*_a, **_k):
            return _TransportResponse(
                401,
                _json_bytes(
                    {"error": {"type": "authentication_error", "message": "bad key"}}
                ),
            )

        with self.assertRaises(InferenceFailure) as ctx:
            self._invoke(t)
        self.assertTrue(str(ctx.exception).startswith("auth_error:"))

    def test_http_403_is_auth_error(self) -> None:
        def t(*_a, **_k):
            return _TransportResponse(
                403,
                _json_bytes(
                    {"error": {"type": "permission_error", "message": "forbidden"}}
                ),
            )

        with self.assertRaises(InferenceFailure) as ctx:
            self._invoke(t)
        self.assertTrue(str(ctx.exception).startswith("auth_error:"))

    def test_http_5xx_is_server_error(self) -> None:
        def t(*_a, **_k):
            return _TransportResponse(
                500, _json_bytes({"error": {"type": "api_error", "message": "boom"}})
            )

        with self.assertRaises(InferenceFailure) as ctx:
            self._invoke(t)
        self.assertTrue(str(ctx.exception).startswith("server_error:"))

    def test_non_json_body_is_malformed(self) -> None:
        def t(*_a, **_k):
            return _TransportResponse(200, b"<html>not json</html>")

        with self.assertRaises(InferenceFailure) as ctx:
            self._invoke(t)
        self.assertTrue(str(ctx.exception).startswith("malformed_response:"))

    def test_missing_usage_is_malformed(self) -> None:
        def t(*_a, **_k):
            return _TransportResponse(
                200,
                _json_bytes(
                    {
                        "content": [{"type": "text", "text": "hello"}],
                        "stop_reason": "end_turn",
                        "model": "claude-sonnet-4-5",
                    }
                ),
            )

        with self.assertRaises(InferenceFailure) as ctx:
            self._invoke(t)
        self.assertTrue(str(ctx.exception).startswith("malformed_response:"))

    def test_content_not_list_is_malformed(self) -> None:
        def t(*_a, **_k):
            return _TransportResponse(
                200,
                _json_bytes(
                    {
                        "content": "not a list",
                        "stop_reason": "end_turn",
                        "usage": {"input_tokens": 1, "output_tokens": 1},
                        "model": "claude-sonnet-4-5",
                    }
                ),
            )

        with self.assertRaises(InferenceFailure) as ctx:
            self._invoke(t)
        self.assertTrue(str(ctx.exception).startswith("malformed_response:"))

    def test_non_object_body_is_malformed(self) -> None:
        def t(*_a, **_k):
            return _TransportResponse(200, _json_bytes([1, 2, 3]))

        with self.assertRaises(InferenceFailure) as ctx:
            self._invoke(t)
        self.assertTrue(str(ctx.exception).startswith("malformed_response:"))

    def test_explicit_refusal_stop_reason(self) -> None:
        def t(*_a, **_k):
            return _TransportResponse(
                200,
                _json_bytes(
                    {
                        "content": [{"type": "text", "text": "I cannot help."}],
                        "stop_reason": "refusal",
                        "usage": {"input_tokens": 10, "output_tokens": 5},
                        "model": "claude-sonnet-4-5",
                    }
                ),
            )

        with self.assertRaises(InferenceFailure) as ctx:
            self._invoke(t)
        self.assertTrue(str(ctx.exception).startswith("refusal:"))

    def test_empty_content_is_refusal(self) -> None:
        def t(*_a, **_k):
            return _TransportResponse(
                200,
                _json_bytes(
                    {
                        "content": [],
                        "stop_reason": "end_turn",
                        "usage": {"input_tokens": 3, "output_tokens": 0},
                        "model": "claude-sonnet-4-5",
                    }
                ),
            )

        with self.assertRaises(InferenceFailure) as ctx:
            self._invoke(t)
        self.assertTrue(str(ctx.exception).startswith("refusal:"))

    def test_happy_path_returns_typed_response(self) -> None:
        seen: dict[str, Any] = {}

        def t(url, body, headers, timeout):
            seen["url"] = url
            seen["timeout"] = timeout
            seen["headers"] = dict(headers)
            seen["body"] = json.loads(body.decode("utf-8"))
            return _TransportResponse(200, _happy_body())

        result = self._invoke(t)
        # Typed response contract.
        self.assertEqual(result["output_text"], "tracer ignition acknowledged")
        self.assertEqual(result["token_usage"], {"input": 12, "output": 7})
        self.assertIsInstance(result["latency_ms"], int)
        self.assertGreaterEqual(result["latency_ms"], 0)
        self.assertEqual(result["model_route_id"], "claude-sonnet-4-5")

        # Transport was called with governed headers and a typed body.
        self.assertEqual(seen["url"], "https://api.anthropic.com/v1/messages")
        self.assertEqual(seen["timeout"], 5.0)
        self.assertEqual(seen["headers"]["x-api-key"], "sk-test")
        self.assertEqual(seen["headers"]["anthropic-version"], "2023-06-01")
        self.assertEqual(seen["headers"]["content-type"], "application/json")
        # The user content carries the governed envelope verbatim.
        msg = seen["body"]["messages"][0]["content"]
        self.assertIn("ctx-1", msg)
        self.assertIn("rev-1", msg)
        self.assertIn("packing_policy_version", msg)

    def test_adapter_declares_semantic_replay_ceiling(self) -> None:
        adapter = AnthropicMessagesAdapter(api_key="sk-x")
        self.assertEqual(adapter.replay_ceiling, "semantic")
        self.assertEqual(REPLAY_CEILING, "semantic")


# ---------------------------------------------------------------------------
# Integration test: adapter wired into real InferenceService.
# ---------------------------------------------------------------------------


class TestRealAdapterThroughInferenceService(unittest.TestCase):
    """Prove the real adapter routes through the governed boundary honestly."""

    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)

        self.audit_repo = AuditRepository(self.conn)
        self.ctx_repo = ContextArtifactRepository(self.conn)
        self.inf_repo = InferenceArtifactRepository(self.conn)

        self.audit = AppendOnlyLedger(
            repository=self.audit_repo, actor_identity="real_adapter_test"
        )
        self.ctx_svc = ContextService(
            repository=self.ctx_repo, audit_ledger=self.audit
        )

    def tearDown(self) -> None:
        self.conn.close()

    def _make_context(self, task_id: str, root_rev_id: str) -> str:
        intent_anchor = IntentCausalAnchor(
            intent_id=f"intent-{task_id}",
            task_id=task_id,
            state="admitted",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        return self.ctx_svc.build_context_artifact(
            task_id=task_id,
            root_revision_id=root_rev_id,
            intent_anchor=intent_anchor,
            request={
                "repo_graph_version": "1.0",
                "symbol_index_version": "1.0",
                "candidate_file_ids": ["src/a.py"],
                "symbol_frontier_ids": ["main"],
                "packing_policy_version": "phase1_budget_policy_v1",
                "actual_tokens": 100,
            },
        )

    def test_happy_path_persists_artifact_and_records_ceiling(self) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        ctx_id = self._make_context(task_id, "rev-genesis-000")

        def t(*_a, **_k):
            return _TransportResponse(200, _happy_body())

        adapter = AnthropicMessagesAdapter(api_key="sk-test", transport=t)
        svc = InferenceService(
            repository=self.inf_repo,
            audit_ledger=self.audit,
            context_reader=self.ctx_repo,
            adapter=adapter,
            policy=InferencePolicy(),
        )
        inf_id = svc.run_inference(
            task_id=task_id,
            context_artifact_id=ctx_id,
            worker_profile="real_adapter_tracer",
            model_route_id="claude-sonnet-4-5",
        )
        self.assertTrue(inf_id.startswith("inf-"))

        # Artifact persisted with governed fields.
        row = self.conn.execute(
            "SELECT * FROM inference_artifacts WHERE inference_artifact_id = ?;",
            (inf_id,),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["task_id"], task_id)
        self.assertEqual(row["model_route_id"], "claude-sonnet-4-5")
        self.assertTrue(row["output_hash"].startswith("sha256:"))

        # Audit carries the honest replay ceiling.
        audit_rows = self.conn.execute(
            "SELECT record_type, payload_json FROM audit_records "
            "WHERE record_type = 'inference_artifact_created';"
        ).fetchall()
        self.assertEqual(len(audit_rows), 1)
        payload = json.loads(audit_rows[0]["payload_json"])
        self.assertEqual(payload.get("replay_ceiling"), "semantic")

    def test_failure_emits_failure_bundle_and_no_artifact(self) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        ctx_id = self._make_context(task_id, "rev-genesis-000")

        def t(*_a, **_k):
            return _TransportResponse(
                429,
                _json_bytes(
                    {"error": {"type": "rate_limit_error", "message": "slow"}}
                ),
            )

        adapter = AnthropicMessagesAdapter(api_key="sk-test", transport=t)
        svc = InferenceService(
            repository=self.inf_repo,
            audit_ledger=self.audit,
            context_reader=self.ctx_repo,
            adapter=adapter,
            policy=InferencePolicy(),
        )
        with self.assertRaises(InferenceFailure) as ctx:
            svc.run_inference(
                task_id=task_id,
                context_artifact_id=ctx_id,
                worker_profile="real_adapter_tracer",
                model_route_id="claude-sonnet-4-5",
            )
        self.assertTrue(str(ctx.exception).startswith("quota_exhausted:"))

        # No InferenceArtifact persisted (fail-closed).
        count = self.conn.execute(
            "SELECT COUNT(*) AS c FROM inference_artifacts WHERE task_id = ?;",
            (task_id,),
        ).fetchone()["c"]
        self.assertEqual(count, 0)

        # Failure bundle audit record emitted with model_api_failure class
        # and detail carrying the adapter-normalized class tag.
        fail_rows = self.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE record_type = 'inference_failure';"
        ).fetchall()
        self.assertEqual(len(fail_rows), 1)
        payload = json.loads(fail_rows[0]["payload_json"])
        self.assertEqual(payload["failure_class"], "model_api_failure")
        self.assertIn("quota_exhausted", payload["detail"])

    def test_timeout_failure_routes_through_failure_bundle(self) -> None:
        task_id = f"task-{uuid4().hex[:8]}"
        ctx_id = self._make_context(task_id, "rev-genesis-000")

        def t(*_a, **_k):
            raise socket.timeout("provider timed out")

        adapter = AnthropicMessagesAdapter(api_key="sk-test", transport=t)
        svc = InferenceService(
            repository=self.inf_repo,
            audit_ledger=self.audit,
            context_reader=self.ctx_repo,
            adapter=adapter,
            policy=InferencePolicy(timeout_seconds=1.0),
        )
        with self.assertRaises(InferenceFailure) as ctx:
            svc.run_inference(
                task_id=task_id,
                context_artifact_id=ctx_id,
                worker_profile="real_adapter_tracer",
                model_route_id="claude-sonnet-4-5",
            )
        self.assertTrue(str(ctx.exception).startswith("timeout:"))

        fail_rows = self.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE record_type = 'inference_failure';"
        ).fetchall()
        self.assertEqual(len(fail_rows), 1)
        payload = json.loads(fail_rows[0]["payload_json"])
        self.assertEqual(payload["failure_class"], "model_api_failure")
        self.assertIn("timeout", payload["detail"])


if __name__ == "__main__":
    unittest.main()
