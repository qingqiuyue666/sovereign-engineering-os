"""Tracer-bullet tests for the H1 human approval readiness CI consumer."""

from __future__ import annotations

import copy
import inspect
import json
import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)

from kernel.lifecycle import human_approval_readiness_ci as ci_module
from kernel.lifecycle.human_approval_readiness_ci import (
    consume_human_approval_readiness_ci,
    human_approval_readiness_ci_manifest,
)


EXPECTED_MANIFEST = {
    "surface": "human_approval_readiness_ci",
    "version": 1,
    "input_shape": "rendered_human_approval_readiness",
    "depends_on": {
        "human_approval_readiness": "human-approval-readiness-v1",
        "restore_dry_run_read_only_stack": "restore-dry-run-read-only-stack-v1",
        "restore_dry_run_aggregate_summary": "restore-dry-run-aggregate-summary-v1",
        "restore_dry_run_plan_ci": "restore-dry-run-plan-ci-v1",
        "restore_dry_run_plan_renderer": "restore-dry-run-plan-renderer-v1",
        "restore_dry_run_readiness_ci": "restore-dry-run-readiness-ci-v1",
        "restore_dry_run_readiness": "restore-dry-run-readiness-v1",
        "write_side_recovery_spec_only": "write-side-recovery-spec-only-v1",
        "write_side_precondition_ci": "write-side-precondition-ci-v1",
        "write_side_precondition_checker": "write-side-precondition-checker-v1",
        "read_only_governance_layer": "read-only-governance-layer-v1",
    },
    "restore_authorized": False,
    "write_side_recovery_authorized": False,
    "cli_execution_authorized": False,
    "schema_migration_authorized": False,
    "daemon_server_queue_authorized": False,
    "db_repair_authorized": False,
    "durable_writes": False,
    "executes_plan": False,
    "runtime_dependencies": [],
    "json_safe": True,
    "reason_codes": ["invalid_ci_payload", "not_ready", "ready"],
    "failure_values": [
        "payload_not_mapping",
        "payload_shape_mismatch",
        "payload_failures_invalid",
        "human_approval_invalid",
        "human_approval_shape_mismatch",
        "human_approval_surface_invalid",
        "human_approval_version_invalid",
        "human_approval_field_invalid",
        "human_approval_field_missing",
        "human_approval_not_ready",
        "authorization_flag_invalid",
        "authorization_flag_true",
        "execution_flag_invalid",
        "execution_flag_true",
        "json_safe_invalid",
        "source_human_approval_not_ready",
    ],
}


EXPECTED_OUTPUT_KEYS = [
    "ci_ok",
    "reason_code",
    "failures",
    "surface",
    "version",
    "human_approval_ready",
    "human_approval_reason_code",
    "approval_ref",
    "actor_identity",
    "approval_scope",
    "approval_reason",
    "created_at",
    "expires_at",
    "freshness_seconds",
    "target_task_id",
    "operation_kind",
    "idempotency_key",
    "projected_action",
    "projected_evidence_ref",
    "aggregate_summary_ref",
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "durable_writes",
    "executes_plan",
    "json_safe",
]


AUTHORIZATION_FLAGS = (
    "restore_authorized",
    "write_side_recovery_authorized",
    "cli_execution_authorized",
    "schema_migration_authorized",
    "daemon_server_queue_authorized",
    "db_repair_authorized",
    "durable_writes",
)


REPR_MARKERS = (
    "HumanApprovalReadiness(",
    " object at 0x",
    "<sqlite3.",
)


FORBIDDEN_SOURCE_MARKERS = (
    "sqlite",
    "open_connection",
    "Repository",
    "UnitOfWork",
    "KernelUnitOfWork",
    "approval_service",
    "review_service",
    "revision_seal_service",
    "evidence_service",
    "append_audit",
    "append_evidence",
    "subprocess",
    "os.environ",
    "argparse",
    "click",
    "socket",
    "queue",
    "threading",
    "asyncio",
    "datetime.now",
    "time.time",
    "restore_task",
    "restore_if_allowed",
    "restore_task_from_snapshot",
    "recovery_session_host",
    "signable_path_orchestrator",
    "apply_migrations",
    "open(",
    "Path(",
    "audit",
    "evidence append",
    "evaluate_human_approval_readiness",
    "render_human_approval_readiness",
    "human_approval_readiness_manifest",
    "summarize_restore_dry_run_readiness",
    "restore_dry_run_aggregate_summary_manifest",
    "governance_readiness_aggregator",
)


ALLOWED_SOURCE_FIELD_STRINGS = (
    "human_approval_readiness_ci",
    "human_approval_readiness",
    "human-approval-readiness-v1",
    "restore-dry-run-read-only-stack-v1",
    "projected_evidence_ref",
    "projected_action",
    "daemon_server_queue_authorized",
)


def _valid_human_approval(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "surface": "human_approval_readiness",
        "version": 1,
        "aggregate_summary_ready": True,
        "approval_present": True,
        "approval_ref": "AR-1",
        "actor_identity": "alice@org",
        "approval_scope": "restore:T-1",
        "approval_reason": "recover from incident",
        "created_at": "2024-01-01T00:00:00Z",
        "expires_at": "2024-01-02T00:00:00Z",
        "freshness_seconds": 3600,
        "target_task_id": "T-1",
        "operation_kind": "op-recover",
        "idempotency_key": "idem-1",
        "projected_action": "projected.restore",
        "projected_evidence_ref": "ev/ref/1",
        "aggregate_summary_ref": "agg-ref-1",
        "restore_authorized": False,
        "write_side_recovery_authorized": False,
        "cli_execution_authorized": False,
        "schema_migration_authorized": False,
        "daemon_server_queue_authorized": False,
        "db_repair_authorized": False,
        "durable_writes": False,
        "executes_plan": False,
        "json_safe": True,
    }
    base.update(overrides)
    return base


def _valid_payload(**overrides: object) -> dict[str, object]:
    human_approval = overrides.pop("human_approval", _valid_human_approval())
    base: dict[str, object] = {
        "human_approval_ready": True,
        "reason_code": "ready",
        "failures": [],
        "human_approval": human_approval,
    }
    base.update(overrides)
    return base


def _recursive_values(payload: object) -> list[object]:
    values = [payload]
    if isinstance(payload, dict):
        for key, value in payload.items():
            values.extend(_recursive_values(key))
            values.extend(_recursive_values(value))
    elif isinstance(payload, list):
        for value in payload:
            values.extend(_recursive_values(value))
    return values


def _assert_json_safe(payload: object) -> None:
    encoded = json.dumps(payload, sort_keys=True)
    decoded = json.loads(encoded)
    if decoded != payload:
        raise AssertionError("payload did not round-trip through JSON")
    for value in _recursive_values(payload):
        if isinstance(value, (set, frozenset, tuple)):
            raise AssertionError(
                f"payload leaked runtime collection {type(value).__name__}"
            )


def _assert_no_runtime_repr(payload: object) -> None:
    encoded = json.dumps(payload, sort_keys=True)
    for marker in REPR_MARKERS:
        if marker in encoded:
            raise AssertionError(f"runtime repr marker leaked: {marker}")


def _scrubbed_source() -> str:
    source = inspect.getsource(ci_module)
    for allowed in ALLOWED_SOURCE_FIELD_STRINGS:
        source = source.replace(allowed, "")
    return source


class HappyPathTests(unittest.TestCase):
    def test_valid_payload_returns_ci_ok_true(self) -> None:
        result = consume_human_approval_readiness_ci(_valid_payload())

        self.assertEqual(list(result.keys()), EXPECTED_OUTPUT_KEYS)
        self.assertIs(result["ci_ok"], True)
        self.assertEqual(result["reason_code"], "ready")
        self.assertEqual(result["failures"], [])

    def test_metadata_copied_deterministically(self) -> None:
        result = consume_human_approval_readiness_ci(_valid_payload())

        self.assertEqual(result["surface"], "human_approval_readiness")
        self.assertEqual(result["version"], 1)
        self.assertIs(result["human_approval_ready"], True)
        self.assertEqual(result["human_approval_reason_code"], "ready")
        self.assertEqual(result["approval_ref"], "AR-1")
        self.assertEqual(result["actor_identity"], "alice@org")
        self.assertEqual(result["approval_scope"], "restore:T-1")
        self.assertEqual(result["approval_reason"], "recover from incident")
        self.assertEqual(result["created_at"], "2024-01-01T00:00:00Z")
        self.assertEqual(result["expires_at"], "2024-01-02T00:00:00Z")
        self.assertEqual(result["freshness_seconds"], 3600)
        self.assertEqual(result["target_task_id"], "T-1")
        self.assertEqual(result["operation_kind"], "op-recover")
        self.assertEqual(result["idempotency_key"], "idem-1")
        self.assertEqual(result["projected_action"], "projected.restore")
        self.assertEqual(result["projected_evidence_ref"], "ev/ref/1")
        self.assertEqual(result["aggregate_summary_ref"], "agg-ref-1")

    def test_authorization_flags_remain_false(self) -> None:
        result = consume_human_approval_readiness_ci(_valid_payload())

        self.assertIs(result["ci_ok"], True)
        for flag in AUTHORIZATION_FLAGS:
            self.assertIs(result[flag], False, flag)
        self.assertIs(result["executes_plan"], False)
        self.assertIs(result["json_safe"], True)

    def test_ci_ok_does_not_authorize_restore_or_write_side(self) -> None:
        result = consume_human_approval_readiness_ci(_valid_payload())

        self.assertIs(result["ci_ok"], True)
        self.assertIs(result["restore_authorized"], False)
        self.assertIs(result["write_side_recovery_authorized"], False)
        self.assertIs(result["cli_execution_authorized"], False)
        self.assertIs(result["schema_migration_authorized"], False)
        self.assertIs(result["daemon_server_queue_authorized"], False)
        self.assertIs(result["db_repair_authorized"], False)
        self.assertIs(result["durable_writes"], False)
        self.assertIs(result["executes_plan"], False)


class PayloadValidationTests(unittest.TestCase):
    def test_non_mapping_input_rejected(self) -> None:
        for payload in (None, 1, "x", [1, 2], (1, 2)):
            with self.subTest(payload=payload):
                result = consume_human_approval_readiness_ci(payload)

                self.assertIs(result["ci_ok"], False)
                self.assertEqual(result["reason_code"], "invalid_ci_payload")
                self.assertEqual(result["failures"], ["payload_not_mapping"])
                self.assertIsNone(result["surface"])
                self.assertIsNone(result["version"])

    def test_top_level_missing_key_rejected(self) -> None:
        payload = _valid_payload()
        del payload["human_approval_ready"]

        result = consume_human_approval_readiness_ci(payload)

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["payload_shape_mismatch"])

    def test_top_level_unknown_key_rejected(self) -> None:
        payload = _valid_payload()
        payload["extra"] = True

        result = consume_human_approval_readiness_ci(payload)

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["payload_shape_mismatch"])

    def test_human_approval_ready_not_bool_rejected(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(human_approval_ready=1)
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["payload_shape_mismatch"])
        self.assertIs(result["human_approval_ready"], False)

    def test_reason_code_not_str_rejected(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(reason_code=1)
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["payload_shape_mismatch"])
        self.assertEqual(
            result["human_approval_reason_code"], "invalid_ci_payload"
        )

    def test_failures_not_list_rejected(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(failures=("x",))
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["payload_failures_invalid"])

    def test_failures_list_with_non_string_rejected(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(failures=["x", 1])
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["payload_failures_invalid"])

    def test_human_approval_not_mapping_rejected(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(human_approval=[])
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["human_approval_invalid"])
        self.assertIsNone(result["surface"])
        self.assertIsNone(result["version"])


class HumanApprovalSubshapeTests(unittest.TestCase):
    def test_missing_human_approval_subkey_rejected(self) -> None:
        human_approval = _valid_human_approval()
        del human_approval["json_safe"]

        result = consume_human_approval_readiness_ci(
            _valid_payload(human_approval=human_approval)
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(
            result["failures"], ["human_approval_shape_mismatch"]
        )

    def test_unknown_human_approval_subkey_rejected(self) -> None:
        human_approval = _valid_human_approval(extra=True)

        result = consume_human_approval_readiness_ci(
            _valid_payload(human_approval=human_approval)
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(
            result["failures"], ["human_approval_shape_mismatch"]
        )

    def test_wrong_surface_rejected(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(human_approval=_valid_human_approval(surface="x"))
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(
            result["failures"], ["human_approval_surface_invalid"]
        )

    def test_wrong_version_rejected(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(human_approval=_valid_human_approval(version=2))
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(
            result["failures"], ["human_approval_version_invalid"]
        )

    def test_bool_as_int_version_rejected(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(human_approval=_valid_human_approval(version=True))
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(
            result["failures"], ["human_approval_version_invalid"]
        )

    def test_aggregate_summary_ready_false_returns_not_ready(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(
                human_approval=_valid_human_approval(
                    aggregate_summary_ready=False
                )
            )
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["human_approval_not_ready"])

    def test_aggregate_summary_ready_non_bool_rejected(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(
                human_approval=_valid_human_approval(
                    aggregate_summary_ready="yes"
                )
            )
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["human_approval_field_invalid"])

    def test_approval_present_false_returns_not_ready(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(
                human_approval=_valid_human_approval(approval_present=False)
            )
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["human_approval_not_ready"])

    def test_approval_ref_non_string_rejected(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(
                human_approval=_valid_human_approval(approval_ref=1)
            )
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["human_approval_field_invalid"])
        self.assertIsNone(result["approval_ref"])

    def test_approval_ref_empty_rejected(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(
                human_approval=_valid_human_approval(approval_ref="")
            )
        )

        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["human_approval_field_missing"])

    def test_actor_identity_non_string_rejected(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(
                human_approval=_valid_human_approval(actor_identity=1)
            )
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["human_approval_field_invalid"])

    def test_actor_identity_empty_rejected(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(
                human_approval=_valid_human_approval(actor_identity="")
            )
        )

        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["human_approval_field_missing"])

    def test_approval_scope_invalid_rejected(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(
                human_approval=_valid_human_approval(approval_scope=1)
            )
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["human_approval_field_invalid"])

    def test_approval_reason_invalid_rejected(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(
                human_approval=_valid_human_approval(approval_reason="")
            )
        )

        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["human_approval_field_missing"])

    def test_created_at_invalid_rejected(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(
                human_approval=_valid_human_approval(created_at=1)
            )
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["human_approval_field_invalid"])

    def test_expires_at_non_string_non_none_rejected(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(
                human_approval=_valid_human_approval(expires_at=42)
            )
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["human_approval_field_invalid"])

    def test_expires_at_none_with_freshness_seconds_present_ok(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(
                human_approval=_valid_human_approval(expires_at=None)
            )
        )

        self.assertIs(result["ci_ok"], True)
        self.assertIsNone(result["expires_at"])
        self.assertEqual(result["freshness_seconds"], 3600)

    def test_freshness_seconds_invalid_rejected(self) -> None:
        for value in ("3600", -1, 0, True, False):
            with self.subTest(value=value):
                result = consume_human_approval_readiness_ci(
                    _valid_payload(
                        human_approval=_valid_human_approval(
                            freshness_seconds=value
                        )
                    )
                )

                self.assertEqual(result["reason_code"], "invalid_ci_payload")
                self.assertEqual(
                    result["failures"], ["human_approval_field_invalid"]
                )

    def test_both_freshness_mechanisms_absent_rejected(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(
                human_approval=_valid_human_approval(
                    expires_at=None, freshness_seconds=None
                )
            )
        )

        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["human_approval_field_missing"])

    def test_target_task_id_invalid_rejected(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(
                human_approval=_valid_human_approval(target_task_id=1)
            )
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["human_approval_field_invalid"])

    def test_operation_kind_invalid_rejected(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(
                human_approval=_valid_human_approval(operation_kind="")
            )
        )

        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["human_approval_field_missing"])

    def test_idempotency_key_invalid_rejected(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(
                human_approval=_valid_human_approval(idempotency_key=1)
            )
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["human_approval_field_invalid"])

    def test_projected_action_invalid_rejected(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(
                human_approval=_valid_human_approval(projected_action="")
            )
        )

        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["human_approval_field_missing"])

    def test_projected_evidence_ref_invalid_rejected(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(
                human_approval=_valid_human_approval(projected_evidence_ref=1)
            )
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["human_approval_field_invalid"])

    def test_aggregate_summary_ref_invalid_rejected(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(
                human_approval=_valid_human_approval(aggregate_summary_ref="")
            )
        )

        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["human_approval_field_missing"])

    def test_authorization_flag_non_bool_rejected(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(
                human_approval=_valid_human_approval(restore_authorized="no")
            )
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["authorization_flag_invalid"])
        self.assertIsNone(result["restore_authorized"])

    def test_authorization_flag_true_returns_not_ready(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(
                human_approval=_valid_human_approval(restore_authorized=True)
            )
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["authorization_flag_true"])
        self.assertIs(result["restore_authorized"], True)

    def test_durable_writes_true_returns_not_ready(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(
                human_approval=_valid_human_approval(durable_writes=True)
            )
        )

        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["authorization_flag_true"])
        self.assertIs(result["durable_writes"], True)

    def test_executes_plan_non_bool_rejected(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(
                human_approval=_valid_human_approval(executes_plan="yes")
            )
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["execution_flag_invalid"])
        self.assertIsNone(result["executes_plan"])

    def test_executes_plan_true_returns_not_ready(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(
                human_approval=_valid_human_approval(executes_plan=True)
            )
        )

        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["execution_flag_true"])
        self.assertIs(result["executes_plan"], True)

    def test_json_safe_false_returns_not_ready(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(
                human_approval=_valid_human_approval(json_safe=False)
            )
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["json_safe_invalid"])
        self.assertIs(result["json_safe"], False)

    def test_json_safe_non_bool_rejected(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(
                human_approval=_valid_human_approval(json_safe="yes")
            )
        )

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["json_safe_invalid"])
        self.assertIsNone(result["json_safe"])


class SourceSemanticsTests(unittest.TestCase):
    def test_human_approval_ready_false_returns_not_ready(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(human_approval_ready=False)
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(
            result["failures"], ["source_human_approval_not_ready"]
        )
        self.assertIs(result["human_approval_ready"], False)

    def test_reason_code_not_ready_returns_not_ready(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(reason_code="not_ready")
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(
            result["failures"], ["source_human_approval_not_ready"]
        )
        self.assertEqual(result["human_approval_reason_code"], "not_ready")

    def test_failures_non_empty_returns_not_ready(self) -> None:
        result = consume_human_approval_readiness_ci(
            _valid_payload(failures=["upstream_detail"])
        )

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertEqual(
            result["failures"], ["source_human_approval_not_ready"]
        )

    def test_combined_failures_use_deterministic_order(self) -> None:
        human_approval = _valid_human_approval(
            surface="wrong",
            version=True,
            aggregate_summary_ready="bad",
            approval_present=False,
            restore_authorized="bad",
            write_side_recovery_authorized=True,
            executes_plan=True,
            json_safe=False,
        )
        payload = _valid_payload(
            human_approval_ready=False,
            reason_code="not_ready",
            failures=["upstream_detail"],
            human_approval=human_approval,
        )
        payload["extra"] = True

        result = consume_human_approval_readiness_ci(payload)

        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(
            result["failures"],
            [
                "payload_shape_mismatch",
                "human_approval_surface_invalid",
                "human_approval_version_invalid",
                "human_approval_field_invalid",
                "human_approval_not_ready",
                "authorization_flag_invalid",
                "authorization_flag_true",
                "execution_flag_true",
                "json_safe_invalid",
                "source_human_approval_not_ready",
            ],
        )


class SafetyAndApiTests(unittest.TestCase):
    def test_manifest_exact_shape(self) -> None:
        manifest = human_approval_readiness_ci_manifest()

        self.assertEqual(list(manifest.keys()), list(EXPECTED_MANIFEST.keys()))
        self.assertEqual(manifest, EXPECTED_MANIFEST)

    def test_manifest_defensive_copy(self) -> None:
        manifest = human_approval_readiness_ci_manifest()
        manifest["surface"] = "tampered"
        manifest["failure_values"].append("injected")  # type: ignore[union-attr]
        manifest["depends_on"]["human_approval_readiness"] = "broken"  # type: ignore[index]

        self.assertEqual(
            human_approval_readiness_ci_manifest(),
            EXPECTED_MANIFEST,
        )

    def test_manifest_authorization_flags_false(self) -> None:
        manifest = human_approval_readiness_ci_manifest()

        for flag in AUTHORIZATION_FLAGS:
            self.assertIs(manifest[flag], False, flag)
        self.assertIs(manifest["executes_plan"], False)

    def test_output_json_safe(self) -> None:
        result = consume_human_approval_readiness_ci(_valid_payload())

        _assert_json_safe(result)

    def test_no_runtime_repr_leakage(self) -> None:
        result = consume_human_approval_readiness_ci(_valid_payload())

        _assert_no_runtime_repr(result)

    def test_input_not_mutated(self) -> None:
        payload = _valid_payload()
        snapshot = copy.deepcopy(payload)

        consume_human_approval_readiness_ci(payload)

        self.assertEqual(payload, snapshot)

    def test_public_api_exact(self) -> None:
        public = sorted(
            name for name in dir(ci_module) if not name.startswith("_")
        )

        self.assertEqual(
            public,
            [
                "consume_human_approval_readiness_ci",
                "human_approval_readiness_ci_manifest",
            ],
        )
        self.assertEqual(
            sorted(ci_module.__all__),
            [
                "consume_human_approval_readiness_ci",
                "human_approval_readiness_ci_manifest",
            ],
        )

    def test_source_boundary_has_no_forbidden_symbols(self) -> None:
        source = _scrubbed_source()

        for marker in FORBIDDEN_SOURCE_MARKERS:
            self.assertNotIn(marker, source, marker)

    def test_no_wall_clock_dependency(self) -> None:
        source = inspect.getsource(ci_module)

        self.assertNotIn("datetime", source)
        self.assertNotIn("time.time", source)
        self.assertNotIn("time.monotonic", source)


if __name__ == "__main__":
    unittest.main()
