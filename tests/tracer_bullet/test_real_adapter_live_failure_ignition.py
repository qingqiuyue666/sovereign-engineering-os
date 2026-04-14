"""
Live (opt-in) real-model **failure** ignition tracer.

Constitutional anchors:
- v11 §22.9 (inter-plane interface discipline)
- v11 §23.5 InferenceArtifact (no artifact persisted on failure)
- v11 §23.15 FailureBundle linkage on API failure
- foundation §4.2 ModelIntegrationContract

Sibling of `test_real_adapter_live_ignition.py`. Where that file proves
the *happy* path against the real provider, this file proves that the
existing real Anthropic provider path remains **fail-closed** and
**audit-honest** for two normalized failure classes when the failure
is produced by the real provider, not by a fake transport:

- `auth_error`      — invalid API key -> Anthropic returns HTTP 401
                      with `error.type = "authentication_error"`. The
                      adapter normalizes this to
                      `InferenceFailure("auth_error: ...")`.
- `quota_exhausted` — operator-supplied rate-limited key -> Anthropic
                      returns HTTP 429 with
                      `error.type in {"rate_limit_error",
                      "overloaded_error"}`. The adapter normalizes this
                      to `InferenceFailure("quota_exhausted: ...")`.

For each enabled live failure class this test asserts:
- `InferenceService.run_inference` raises `InferenceFailure` whose
  string starts with the expected normalized class prefix.
- ZERO rows in `inference_artifacts` for the task (fail-closed: no
  artifact may be persisted on a real-failure path).
- Exactly one `audit_records` row with
  `record_type = 'inference_failure'`.
- Its payload reports `failure_class = "model_api_failure"`, `detail`
  carrying the normalized class prefix, and `root_revision_id`.
- ZERO `inference_artifact_created` audit rows for the task (no
  honest-success leak on a failure path).

OPT-IN ONLY. Default CI / test runs MUST NOT perform network IO.

- The `auth_error` test runs only when
  `SOS_RUN_LIVE_ANTHROPIC_AUTH_FAIL=1`. The test supplies its own
  obviously-invalid API key; no real key is consumed and no real
  user data is sent. Internet access to `api.anthropic.com` is
  required.

- The `quota_exhausted` test runs only when
  `SOS_RUN_LIVE_ANTHROPIC_QUOTA_FAIL=1` AND `ANTHROPIC_API_KEY` is
  set to a key the operator knows is currently rate-limited /
  quota-exhausted. There is no honest way to fabricate a real 429
  in unattended CI; this test is therefore a real-failure probe to
  be run by an operator who has staged the conditions.

This is the **smallest** honest real-failure evidence tracer for the
existing real Anthropic provider path. It does not introduce a second
provider, does not redesign the classifier, does not redesign the
replay taxonomy, does not silently downgrade, and does not change the
success-path behavior. Adapter and service code are unchanged; the
normalization of `auth_error` / `quota_exhausted` and the failure-bundle
emission already exist and are unit-tested with a fake transport in
`tests/tracer_bullet/test_real_adapter_ignition.py`. This file proves
the same invariants under **live** adapter conditions.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from datetime import datetime, timezone
from uuid import uuid4

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)

from kernel.adapters.anthropic_adapter import AnthropicMessagesAdapter
from kernel.evidence.append_only_ledger import AppendOnlyLedger
from kernel.lifecycle.signable_path_orchestrator import IntentCausalAnchor
from kernel.services.context_service import ContextService
from kernel.services.inference_service import (
    InferenceFailure,
    InferencePolicy,
    InferenceService,
)
from kernel.stores.sqlite.repositories import (
    AuditRepository,
    ContextArtifactRepository,
    InferenceArtifactRepository,
)
from kernel.stores.sqlite.wal_recovery import apply_migrations, open_connection


# ---------------------------------------------------------------------------
# Opt-in flags
# ---------------------------------------------------------------------------

_AUTH_FAIL_ENABLED = os.environ.get("SOS_RUN_LIVE_ANTHROPIC_AUTH_FAIL") == "1"
_AUTH_FAIL_SKIP_REASON = (
    "live Anthropic auth_error tracer disabled: set "
    "SOS_RUN_LIVE_ANTHROPIC_AUTH_FAIL=1 to run one real invocation with a "
    "deliberately invalid API key (no real key required; internet access "
    "to api.anthropic.com required)."
)

_QUOTA_FAIL_ENABLED = (
    os.environ.get("SOS_RUN_LIVE_ANTHROPIC_QUOTA_FAIL") == "1"
    and bool(os.environ.get("ANTHROPIC_API_KEY"))
)
_QUOTA_FAIL_SKIP_REASON = (
    "live Anthropic quota_exhausted tracer disabled: set "
    "SOS_RUN_LIVE_ANTHROPIC_QUOTA_FAIL=1 and ANTHROPIC_API_KEY to a key "
    "the operator knows is currently rate-limited or quota-exhausted. "
    "Real 429 cannot be honestly fabricated in unattended CI."
)


# Deliberately invalid key for the auth_error probe. This must NEVER
# match a real key shape that could collide with a live credential.
# Anthropic returns HTTP 401 + error.type='authentication_error' for any
# key the API does not recognize.
_INVALID_API_KEY = "sk-ant-invalid-sovereign-os-failure-tracer-deadbeef"


# ---------------------------------------------------------------------------
# Common harness
# ---------------------------------------------------------------------------


class _LiveFailureHarness(unittest.TestCase):
    """Wires the real adapter into the real InferenceService boundary.

    Subclasses opt into a specific live failure class.
    """

    # Subclasses set this so assertions can name the expected normalized
    # failure prefix in the audit detail.
    expected_class_prefix: str = ""

    def setUp(self) -> None:
        self.conn = open_connection(":memory:")
        apply_migrations(self.conn)
        self.audit_repo = AuditRepository(self.conn)
        self.ctx_repo = ContextArtifactRepository(self.conn)
        self.inf_repo = InferenceArtifactRepository(self.conn)
        self.audit = AppendOnlyLedger(
            repository=self.audit_repo, actor_identity="live_failure_tracer"
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
                "candidate_file_ids": ["src/tracer.py"],
                "symbol_frontier_ids": ["main"],
                "packing_policy_version": "phase1_budget_policy_v1",
                "actual_tokens": 100,
            },
        )

    def _build_service(self, *, api_key: str) -> tuple[InferenceService, str]:
        # Narrow opt-in policy. No retries. Tight budget.
        policy = InferencePolicy(
            max_output_tokens=64,
            timeout_seconds=30.0,
            max_retries=0,
        )
        adapter = AnthropicMessagesAdapter(api_key=api_key)
        svc = InferenceService(
            repository=self.inf_repo,
            audit_ledger=self.audit,
            context_reader=self.ctx_repo,
            adapter=adapter,
            policy=policy,
        )
        return svc, adapter._model_route_id

    # ------------------------------------------------------------------
    # invariant assertions shared across every live failure class
    # ------------------------------------------------------------------

    def _assert_failclosed_and_audit_honest(
        self, *, task_id: str, raised_message: str
    ) -> None:
        # 1. Adapter-normalized class prefix is present in the raised
        #    InferenceFailure message.
        self.assertTrue(
            raised_message.startswith(self.expected_class_prefix),
            f"expected raised message to start with "
            f"{self.expected_class_prefix!r}; got {raised_message!r}",
        )

        # 2. Fail-closed: no InferenceArtifact persisted for this task.
        count = self.conn.execute(
            "SELECT COUNT(*) AS c FROM inference_artifacts "
            "WHERE task_id = ?;",
            (task_id,),
        ).fetchone()["c"]
        self.assertEqual(
            count,
            0,
            "no InferenceArtifact may be persisted on a live failure path",
        )

        # 3. No honest-success leak: zero inference_artifact_created
        #    audit rows for this task.
        success_rows = self.conn.execute(
            "SELECT COUNT(*) AS c FROM audit_records "
            "WHERE record_type = 'inference_artifact_created' "
            "AND task_id = ?;",
            (task_id,),
        ).fetchone()["c"]
        self.assertEqual(
            success_rows,
            0,
            "no inference_artifact_created audit record may be emitted "
            "on a live failure path",
        )

        # 4. Exactly one normalized failure-bundle audit record for this
        #    task, with the stable shape downstream replay relies on.
        fail_rows = self.conn.execute(
            "SELECT payload_json FROM audit_records "
            "WHERE record_type = 'inference_failure' "
            "AND task_id = ?;",
            (task_id,),
        ).fetchall()
        self.assertEqual(
            len(fail_rows),
            1,
            "live failure must produce exactly one inference_failure "
            "audit record",
        )
        payload = json.loads(fail_rows[0]["payload_json"])
        self.assertEqual(
            payload["failure_class"],
            "model_api_failure",
            "service must classify adapter failures as model_api_failure",
        )
        self.assertTrue(
            payload["detail"].startswith(self.expected_class_prefix),
            f"failure detail must carry the normalized adapter class "
            f"prefix {self.expected_class_prefix!r}; got "
            f"{payload['detail']!r}",
        )
        self.assertIn(
            "root_revision_id",
            payload,
            "failure-bundle audit payload must record root_revision_id "
            "for forensic reconstructability",
        )


# ---------------------------------------------------------------------------
# auth_error  (invalid API key)
# ---------------------------------------------------------------------------


@unittest.skipUnless(_AUTH_FAIL_ENABLED, _AUTH_FAIL_SKIP_REASON)
class TestLiveAnthropicAuthErrorTracer(_LiveFailureHarness):
    """Single real invocation with an invalid API key. Opt-in only."""

    expected_class_prefix = "auth_error:"

    def test_live_auth_error_is_failclosed_and_audit_honest(self) -> None:
        task_id = f"task-auth-{uuid4().hex[:8]}"
        ctx_id = self._make_context(task_id, "rev-live-auth-000")

        svc, model_route_id = self._build_service(api_key=_INVALID_API_KEY)

        with self.assertRaises(InferenceFailure) as exc_ctx:
            svc.run_inference(
                task_id=task_id,
                context_artifact_id=ctx_id,
                worker_profile="live_failure_tracer",
                model_route_id=model_route_id,
            )

        self._assert_failclosed_and_audit_honest(
            task_id=task_id, raised_message=str(exc_ctx.exception)
        )


# ---------------------------------------------------------------------------
# quota_exhausted  (operator-staged rate limit)
# ---------------------------------------------------------------------------


@unittest.skipUnless(_QUOTA_FAIL_ENABLED, _QUOTA_FAIL_SKIP_REASON)
class TestLiveAnthropicQuotaExhaustedTracer(_LiveFailureHarness):
    """Single real invocation with a rate-limited key. Opt-in only.

    The operator is responsible for supplying a key whose current
    rate-limit / quota state will produce HTTP 429 on a single small
    request. There is no honest way to fabricate this in CI.
    """

    expected_class_prefix = "quota_exhausted:"

    def test_live_quota_exhausted_is_failclosed_and_audit_honest(self) -> None:
        api_key = os.environ.get("ANTHROPIC_API_KEY") or ""
        # Defense-in-depth: the skip predicate already enforces this.
        self.assertTrue(api_key, "ANTHROPIC_API_KEY must be set for this probe")

        task_id = f"task-quota-{uuid4().hex[:8]}"
        ctx_id = self._make_context(task_id, "rev-live-quota-000")

        svc, model_route_id = self._build_service(api_key=api_key)

        with self.assertRaises(InferenceFailure) as exc_ctx:
            svc.run_inference(
                task_id=task_id,
                context_artifact_id=ctx_id,
                worker_profile="live_failure_tracer",
                model_route_id=model_route_id,
            )

        self._assert_failclosed_and_audit_honest(
            task_id=task_id, raised_message=str(exc_ctx.exception)
        )


if __name__ == "__main__":
    unittest.main()
