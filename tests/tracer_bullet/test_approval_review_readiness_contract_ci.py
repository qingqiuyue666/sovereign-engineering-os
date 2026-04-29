"""P3-01 approval/review readiness envelope, contract, and CI tests."""

from __future__ import annotations

import ast
import copy
import inspect
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
)

from kernel.lifecycle import approval_review_readiness as envelope_module
from kernel.lifecycle import approval_review_readiness_ci as ci_module
from kernel.lifecycle import (
    approval_review_readiness_contract as contract_module,
)
from kernel.lifecycle.approval_review_readiness import (
    ApprovalReviewReadinessEnvelope,
    approval_review_readiness_manifest,
    build_approval_review_readiness_envelope,
    render_approval_review_readiness_envelope,
)
from kernel.lifecycle.approval_review_readiness_ci import (
    approval_review_readiness_ci_manifest,
    consume_approval_review_readiness_ci,
)
from kernel.lifecycle.approval_review_readiness_contract import (
    ApprovalReviewReadinessContractCheck,
    approval_review_readiness_contract_manifest,
    check_approval_review_readiness_contract,
    render_approval_review_readiness_contract_check,
)
from kernel.stores.sqlite.repositories import (
    ApprovalArtifactRepository,
    RevisionRepository,
    ReviewArtifactRepository,
)
from kernel.stores.sqlite.wal_recovery import apply_migrations, open_connection


EXPECTED_ENVELOPE_MANIFEST = {
    "surface": "approval_review_readiness",
    "version": 1,
    "input_shape": (
        "rendered approval_artifacts/review_artifacts/revisions rows: "
        "task_id, record_type, approval_state, review_state, revision_id, "
        "seal_id, actor_identity, created_at"
    ),
    "restore_supported": False,
    "durable_writes": False,
    "cli_commands": [],
    "runtime_dependencies": [],
    "json_safe": True,
    "reason_codes": ["invalid_approval_review", "not_ready", "ready"],
    "failure_values": [
        "items_not_sequence",
        "items_empty",
        "item_invalid_type",
        "item_shape_invalid",
        "task_id_invalid",
        "record_type_invalid",
        "approval_state_invalid",
        "review_state_invalid",
        "revision_id_invalid",
        "seal_id_invalid",
        "actor_identity_invalid",
        "created_at_invalid",
        "missing_review_state",
        "missing_revision_or_seal",
        "mixed_task_ids",
        "conflicting_terminal_states",
    ],
}

EXPECTED_CONTRACT_MANIFEST = {
    "surface": "approval_review_readiness_contract",
    "version": 1,
    "input_shape": "rendered_approval_review_readiness_envelope",
    "restore_supported": False,
    "durable_writes": False,
    "cli_commands": [],
    "runtime_dependencies": [],
    "json_safe": True,
    "reason_codes": ["invalid_approval_review_envelope", "not_ready", "ready"],
    "failure_values": [
        "payload_not_mapping",
        "payload_shape_mismatch",
        "payload_failures_invalid",
        "envelope_invalid",
        "envelope_shape_mismatch",
        "envelope_counter_invalid",
        "envelope_bool_invalid",
        "envelope_list_invalid",
        "envelope_mapping_invalid",
        "status_inconsistent",
        "safety_inconsistent",
        "operator_not_safe",
    ],
}

EXPECTED_CI_OUTPUT_KEYS = [
    "ci_ok",
    "reason_code",
    "failures",
    "surface",
    "version",
    "contract_ready",
    "contract_reason_code",
    "restore_supported",
    "durable_writes",
    "cli_command_count",
    "runtime_dependency_count",
    "json_safe",
]

REPR_MARKERS = (
    "ApprovalReviewReadinessEnvelope(",
    "ApprovalReviewReadinessContractCheck(",
    " object at 0x",
    "<sqlite3.",
)

FORBIDDEN_SOURCE_MARKERS = (
    "sqlite",
    "open_connection",
    "AuditRepository",
    "AppendOnlyLedger",
    "UnitOfWork",
    "KernelUnitOfWork",
    "subprocess",
    "os.environ",
    "argparse",
    "click",
    "socket",
    "queue",
    "threading",
    "asyncio",
    "restore_task",
    "restore_if_allowed",
    "restore_task_from_snapshot",
    "recovery_session_host",
    "task_lifecycle_journal_snapshot",
    "evidence_replay_readiness",
    "apply_migrations",
)


def _item(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "task_id": "task-001",
        "record_type": "approval_artifact",
        "approval_state": "approved",
        "review_state": "created",
        "revision_id": "rev-001",
        "seal_id": "snap-001",
        "actor_identity": "phase1_approver",
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    base.update(overrides)
    return base


def _rendered_envelope(items: object | None = None) -> dict[str, object]:
    envelope = build_approval_review_readiness_envelope(
        items if items is not None else [_item()]
    )
    return render_approval_review_readiness_envelope(envelope)


def _rendered_contract_payload(
    rendered_envelope: dict[str, object] | None = None,
) -> dict[str, object]:
    check = check_approval_review_readiness_contract(
        rendered_envelope if rendered_envelope is not None else _rendered_envelope()
    )
    return render_approval_review_readiness_contract_check(check)


def _recursive_values(payload: object) -> list[object]:
    values: list[object] = [payload]
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
    text = json.dumps(payload, sort_keys=True)
    for marker in REPR_MARKERS:
        if marker in text:
            raise AssertionError(f"runtime repr marker leaked: {marker}")


def _assert_no_source_creep(module: object) -> None:
    source = inspect.getsource(module)
    for marker in FORBIDDEN_SOURCE_MARKERS:
        if marker in source:
            raise AssertionError(f"source marker leaked: {marker}")


def _imported_modules(module: object) -> set[str]:
    tree = ast.parse(inspect.getsource(module))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)
    return imported


def _quote_sql_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _table_row_counts(db_path: Path) -> dict[str, int]:
    conn = sqlite3.connect(str(db_path))
    try:
        table_names = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name;"
            )
        ]
        return {
            table_name: conn.execute(
                f"SELECT COUNT(*) FROM {_quote_sql_identifier(table_name)};"
            ).fetchone()[0]
            for table_name in table_names
        }
    finally:
        conn.close()


class TestApprovalReviewReadinessEnvelope(unittest.TestCase):
    def test_valid_rendered_approval_review_item_sequence_ready(self) -> None:
        result = build_approval_review_readiness_envelope(
            [
                _item(record_type="review_artifact", approval_state=None),
                _item(record_type="approval_artifact", seal_id=None),
            ]
        )

        self.assertIsInstance(result, ApprovalReviewReadinessEnvelope)
        self.assertTrue(result.ready)
        self.assertEqual(result.reason_code, "ready")
        self.assertEqual(result.failures, ())
        self.assertEqual(result.envelope["item_count"], 2)
        self.assertEqual(result.envelope["unique_task_count"], 1)
        self.assertEqual(result.envelope["task_ids"], ["task-001"])
        self.assertTrue(result.envelope["operator_safe"])

    def test_non_sequence_rejected(self) -> None:
        for payload in ({"task_id": "x"}, "not-items"):
            with self.subTest(payload=payload):
                result = build_approval_review_readiness_envelope(payload)

                self.assertFalse(result.ready)
                self.assertEqual(result.reason_code, "invalid_approval_review")
                self.assertEqual(result.failures, ("items_not_sequence",))

    def test_empty_sequence_rejected(self) -> None:
        result = build_approval_review_readiness_envelope([])

        self.assertFalse(result.ready)
        self.assertEqual(result.reason_code, "invalid_approval_review")
        self.assertEqual(result.failures, ("items_empty",))
        self.assertEqual(result.envelope["item_count"], 0)

    def test_malformed_item_rejected(self) -> None:
        result = build_approval_review_readiness_envelope([{"task_id": "x"}])

        self.assertFalse(result.ready)
        self.assertEqual(result.reason_code, "invalid_approval_review")
        self.assertEqual(result.failures, ("item_shape_invalid",))

    def test_invalid_item_type_rejected(self) -> None:
        result = build_approval_review_readiness_envelope([object()])

        self.assertFalse(result.ready)
        self.assertEqual(result.failures, ("item_invalid_type",))

    def test_invalid_task_id_rejected(self) -> None:
        result = build_approval_review_readiness_envelope([_item(task_id="")])

        self.assertFalse(result.ready)
        self.assertEqual(result.failures, ("task_id_invalid",))

    def test_invalid_record_type_rejected(self) -> None:
        result = build_approval_review_readiness_envelope(
            [_item(record_type="")]
        )

        self.assertFalse(result.ready)
        self.assertEqual(result.failures, ("record_type_invalid",))

    def test_invalid_approval_state_rejected(self) -> None:
        result = build_approval_review_readiness_envelope(
            [_item(approval_state=object())]
        )

        self.assertFalse(result.ready)
        self.assertEqual(result.failures, ("approval_state_invalid",))

    def test_invalid_review_state_rejected(self) -> None:
        result = build_approval_review_readiness_envelope(
            [_item(review_state="")]
        )

        self.assertFalse(result.ready)
        self.assertEqual(result.failures, ("review_state_invalid",))

    def test_invalid_revision_id_rejected(self) -> None:
        result = build_approval_review_readiness_envelope(
            [_item(revision_id="")]
        )

        self.assertFalse(result.ready)
        self.assertEqual(result.failures, ("revision_id_invalid",))

    def test_invalid_seal_id_rejected(self) -> None:
        result = build_approval_review_readiness_envelope([_item(seal_id="")])

        self.assertFalse(result.ready)
        self.assertEqual(result.failures, ("seal_id_invalid",))

    def test_invalid_actor_identity_rejected(self) -> None:
        result = build_approval_review_readiness_envelope(
            [_item(actor_identity="")]
        )

        self.assertFalse(result.ready)
        self.assertEqual(result.failures, ("actor_identity_invalid",))

    def test_invalid_created_at_rejected(self) -> None:
        result = build_approval_review_readiness_envelope(
            [_item(created_at=object())]
        )

        self.assertFalse(result.ready)
        self.assertEqual(result.failures, ("created_at_invalid",))

    def test_missing_review_state_counted_and_not_ready(self) -> None:
        result = build_approval_review_readiness_envelope(
            [_item(review_state=None)]
        )

        self.assertFalse(result.ready)
        self.assertEqual(result.reason_code, "not_ready")
        self.assertEqual(result.failures, ("missing_review_state",))
        self.assertEqual(result.envelope["missing_review_state_count"], 1)

    def test_missing_revision_or_seal_counted_and_not_ready(self) -> None:
        result = build_approval_review_readiness_envelope(
            [_item(revision_id=None, seal_id=None)]
        )

        self.assertFalse(result.ready)
        self.assertEqual(result.reason_code, "not_ready")
        self.assertEqual(result.failures, ("missing_revision_or_seal",))
        self.assertEqual(result.envelope["missing_revision_or_seal_count"], 1)

    def test_mixed_task_ids_detected(self) -> None:
        result = build_approval_review_readiness_envelope(
            [_item(), _item(task_id="task-002", revision_id="rev-002")]
        )

        self.assertFalse(result.ready)
        self.assertEqual(result.reason_code, "not_ready")
        self.assertEqual(result.failures, ("mixed_task_ids",))
        self.assertEqual(result.envelope["task_ids"], ["task-001", "task-002"])

    def test_conflicting_terminal_states_detected(self) -> None:
        result = build_approval_review_readiness_envelope(
            [_item(), _item(approval_state="rejected", revision_id="rev-002")]
        )

        self.assertFalse(result.ready)
        self.assertEqual(result.reason_code, "not_ready")
        self.assertEqual(result.failures, ("conflicting_terminal_states",))

    def test_record_type_counts_deterministic(self) -> None:
        result = build_approval_review_readiness_envelope(
            [
                _item(record_type="revision", revision_id="rev-003"),
                _item(record_type="approval_artifact", revision_id="rev-002"),
                _item(record_type="revision", revision_id="rev-004"),
            ]
        )

        self.assertTrue(result.ready)
        self.assertEqual(
            result.envelope["record_type_counts"],
            {"approval_artifact": 1, "revision": 2},
        )

    def test_approval_state_counts_deterministic(self) -> None:
        result = build_approval_review_readiness_envelope(
            [
                _item(approval_state="pending", revision_id="rev-003"),
                _item(approval_state="approved", revision_id="rev-002"),
                _item(approval_state=None, revision_id="rev-004"),
            ]
        )

        self.assertTrue(result.ready)
        self.assertEqual(
            result.envelope["approval_state_counts"],
            {"approved": 1, "pending": 1},
        )

    def test_review_state_counts_deterministic(self) -> None:
        result = build_approval_review_readiness_envelope(
            [
                _item(review_state="rendered", revision_id="rev-003"),
                _item(review_state="created", revision_id="rev-002"),
                _item(review_state="rendered", revision_id="rev-004"),
            ]
        )

        self.assertTrue(result.ready)
        self.assertEqual(
            result.envelope["review_state_counts"],
            {"created": 1, "rendered": 2},
        )

    def test_manifest_exact_shape(self) -> None:
        self.assertEqual(
            approval_review_readiness_manifest(),
            EXPECTED_ENVELOPE_MANIFEST,
        )

    def test_manifest_defensive_copy(self) -> None:
        manifest = approval_review_readiness_manifest()
        manifest["failure_values"].append("INJECTED")  # type: ignore[union-attr]
        manifest["surface"] = "tampered"

        self.assertEqual(
            approval_review_readiness_manifest(),
            EXPECTED_ENVELOPE_MANIFEST,
        )

    def test_renderer_exact_shape(self) -> None:
        envelope = build_approval_review_readiness_envelope([_item()])
        rendered = render_approval_review_readiness_envelope(envelope)

        self.assertEqual(
            set(rendered.keys()), {"ready", "reason_code", "failures", "envelope"}
        )
        self.assertEqual(rendered["ready"], True)
        self.assertEqual(rendered["reason_code"], "ready")
        self.assertEqual(rendered["failures"], [])
        self.assertEqual(rendered["envelope"]["surface"], "approval_review_readiness")

    def test_renderer_defensive_copy(self) -> None:
        envelope = build_approval_review_readiness_envelope([_item()])
        rendered = render_approval_review_readiness_envelope(envelope)
        rendered["envelope"]["surface"] = "tampered"  # type: ignore[index]

        rendered_again = render_approval_review_readiness_envelope(envelope)

        self.assertEqual(
            rendered_again["envelope"]["surface"], "approval_review_readiness"
        )

    def test_input_not_mutated(self) -> None:
        items = [_item()]
        original = copy.deepcopy(items)

        build_approval_review_readiness_envelope(items)

        self.assertEqual(items, original)

    def test_output_json_safe(self) -> None:
        rendered = _rendered_envelope()
        _assert_json_safe(rendered)

    def test_no_runtime_repr_leakage(self) -> None:
        rendered = _rendered_envelope()
        _assert_no_runtime_repr(rendered)

    def test_public_api_exact(self) -> None:
        self.assertEqual(
            sorted(envelope_module.__all__),
            sorted(
                [
                    "ApprovalReviewReadinessEnvelope",
                    "approval_review_readiness_manifest",
                    "build_approval_review_readiness_envelope",
                    "render_approval_review_readiness_envelope",
                ]
            ),
        )
        envelope = build_approval_review_readiness_envelope([_item()])
        with self.assertRaises(Exception):
            envelope.ready = False  # type: ignore[misc]

    def test_no_restore_cli_db_or_source_creep(self) -> None:
        _assert_no_source_creep(envelope_module)


class TestApprovalReviewReadinessContract(unittest.TestCase):
    def test_accepts_valid_rendered_envelope(self) -> None:
        check = check_approval_review_readiness_contract(_rendered_envelope())

        self.assertIsInstance(check, ApprovalReviewReadinessContractCheck)
        self.assertIs(check.ready, True)
        self.assertEqual(check.reason_code, "ready")
        self.assertEqual(check.failures, ())
        self.assertEqual(
            check.contract["surface"], "approval_review_readiness_contract"
        )

    def test_rejects_non_mapping(self) -> None:
        check = check_approval_review_readiness_contract("bad")

        self.assertIs(check.ready, False)
        self.assertEqual(check.reason_code, "invalid_approval_review_envelope")
        self.assertEqual(check.failures, ("payload_not_mapping",))

    def test_rejects_top_level_shape_mismatch(self) -> None:
        payload = _rendered_envelope()
        payload["extra"] = True

        check = check_approval_review_readiness_contract(payload)

        self.assertEqual(check.reason_code, "invalid_approval_review_envelope")
        self.assertIn("payload_shape_mismatch", check.failures)

    def test_rejects_invalid_failures(self) -> None:
        payload = _rendered_envelope()
        payload["failures"] = ["ok", 1]

        check = check_approval_review_readiness_contract(payload)

        self.assertEqual(check.reason_code, "invalid_approval_review_envelope")
        self.assertIn("payload_failures_invalid", check.failures)

    def test_rejects_invalid_envelope_object(self) -> None:
        payload = _rendered_envelope()
        payload["envelope"] = []

        check = check_approval_review_readiness_contract(payload)

        self.assertEqual(check.failures, ("envelope_invalid",))

    def test_rejects_missing_envelope_keys(self) -> None:
        payload = _rendered_envelope()
        envelope = payload["envelope"]
        assert isinstance(envelope, dict)
        envelope.pop("item_count")

        check = check_approval_review_readiness_contract(payload)

        self.assertEqual(check.reason_code, "invalid_approval_review_envelope")
        self.assertIn("envelope_shape_mismatch", check.failures)

    def test_rejects_invalid_counters_bool_list_mapping_fields(self) -> None:
        counter_fields = (
            "version",
            "item_count",
            "unique_task_count",
            "revision_id_count",
            "seal_id_count",
            "missing_review_state_count",
            "missing_revision_or_seal_count",
            "cli_command_count",
            "runtime_dependency_count",
        )
        for field in counter_fields:
            with self.subTest(field=field):
                payload = _rendered_envelope()
                envelope = payload["envelope"]
                assert isinstance(envelope, dict)
                envelope[field] = True

                check = check_approval_review_readiness_contract(payload)

                self.assertIn("envelope_counter_invalid", check.failures)

        for field in ("operator_safe", "restore_supported", "durable_writes", "json_safe"):
            with self.subTest(field=field):
                payload = _rendered_envelope()
                envelope = payload["envelope"]
                assert isinstance(envelope, dict)
                envelope[field] = "bad"

                check = check_approval_review_readiness_contract(payload)

                self.assertIn("envelope_bool_invalid", check.failures)

        payload = _rendered_envelope()
        envelope = payload["envelope"]
        assert isinstance(envelope, dict)
        envelope["task_ids"] = ["ok", 1]
        check = check_approval_review_readiness_contract(payload)
        self.assertIn("envelope_list_invalid", check.failures)

        for field, value in (
            ("record_type_counts", {"x": True}),
            ("approval_state_counts", {"x": -1}),
            ("review_state_counts", []),
        ):
            with self.subTest(field=field):
                payload = _rendered_envelope()
                envelope = payload["envelope"]
                assert isinstance(envelope, dict)
                envelope[field] = value

                check = check_approval_review_readiness_contract(payload)

                self.assertIn("envelope_mapping_invalid", check.failures)

    def test_detects_status_inconsistency(self) -> None:
        payload = _rendered_envelope()
        payload["reason_code"] = "not_ready"

        check = check_approval_review_readiness_contract(payload)

        self.assertIn("status_inconsistent", check.failures)

    def test_detects_safety_inconsistency(self) -> None:
        payload = _rendered_envelope()
        envelope = payload["envelope"]
        assert isinstance(envelope, dict)
        envelope["restore_supported"] = True

        check = check_approval_review_readiness_contract(payload)

        self.assertEqual(check.reason_code, "invalid_approval_review_envelope")
        self.assertIn("safety_inconsistent", check.failures)

    def test_marks_operator_safe_false_envelope_as_not_ready(self) -> None:
        rendered = _rendered_envelope([_item(review_state=None)])
        self.assertIs(rendered["ready"], False)
        self.assertEqual(rendered["reason_code"], "not_ready")

        check = check_approval_review_readiness_contract(rendered)

        self.assertIs(check.ready, False)
        self.assertEqual(check.reason_code, "not_ready")
        self.assertEqual(check.failures, ("operator_not_safe",))

    def test_manifest_exact_shape(self) -> None:
        self.assertEqual(
            approval_review_readiness_contract_manifest(),
            EXPECTED_CONTRACT_MANIFEST,
        )

    def test_manifest_defensive_copy(self) -> None:
        manifest = approval_review_readiness_contract_manifest()
        manifest["failure_values"].append("INJECTED")  # type: ignore[union-attr]
        manifest["surface"] = "tampered"

        self.assertEqual(
            approval_review_readiness_contract_manifest(),
            EXPECTED_CONTRACT_MANIFEST,
        )

    def test_renderer_defensive_copy(self) -> None:
        check = check_approval_review_readiness_contract(_rendered_envelope())
        rendered = render_approval_review_readiness_contract_check(check)
        rendered["contract"]["surface"] = "tampered"  # type: ignore[index]
        rendered["contract"]["failure_values"].append(  # type: ignore[index]
            "INJECTED"
        )

        rendered_again = render_approval_review_readiness_contract_check(check)

        self.assertEqual(rendered_again["contract"], EXPECTED_CONTRACT_MANIFEST)

    def test_output_json_safe(self) -> None:
        _assert_json_safe(_rendered_contract_payload())

    def test_no_runtime_repr_leakage(self) -> None:
        _assert_no_runtime_repr(_rendered_contract_payload())

    def test_public_api_exact(self) -> None:
        self.assertEqual(
            sorted(contract_module.__all__),
            sorted(
                [
                    "ApprovalReviewReadinessContractCheck",
                    "approval_review_readiness_contract_manifest",
                    "check_approval_review_readiness_contract",
                    "render_approval_review_readiness_contract_check",
                ]
            ),
        )
        check = check_approval_review_readiness_contract(_rendered_envelope())
        with self.assertRaises(Exception):
            check.ready = False  # type: ignore[misc]

    def test_no_source_creep(self) -> None:
        _assert_no_source_creep(contract_module)


class TestApprovalReviewReadinessCiConsumer(unittest.TestCase):
    def test_ready_contract_payload_ci_ok_true(self) -> None:
        result = consume_approval_review_readiness_ci(_rendered_contract_payload())

        self.assertIs(result["ci_ok"], True)
        self.assertEqual(result["reason_code"], "ready")
        self.assertEqual(result["failures"], [])
        self.assertEqual(result["surface"], "approval_review_readiness_contract")
        self.assertEqual(result["version"], 1)
        self.assertIs(result["contract_ready"], True)
        self.assertEqual(result["contract_reason_code"], "ready")
        self.assertIs(result["restore_supported"], False)
        self.assertIs(result["durable_writes"], False)
        self.assertEqual(result["cli_command_count"], 0)
        self.assertEqual(result["runtime_dependency_count"], 0)
        self.assertIs(result["json_safe"], True)

    def test_invalid_payload_invalid_ci_payload(self) -> None:
        result = consume_approval_review_readiness_ci(None)

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "invalid_ci_payload")
        self.assertEqual(result["failures"], ["invalid_ci_payload"])
        self.assertIs(result["contract_ready"], False)
        self.assertEqual(result["contract_reason_code"], "invalid_ci_payload")
        self.assertIsNone(result["surface"])
        self.assertIsNone(result["version"])

    def test_not_ready_payload_ci_ok_false(self) -> None:
        rendered = _rendered_envelope([_item(review_state=None)])
        payload = _rendered_contract_payload(rendered)

        result = consume_approval_review_readiness_ci(payload)

        self.assertIs(result["ci_ok"], False)
        self.assertEqual(result["reason_code"], "not_ready")
        self.assertIs(result["contract_ready"], False)
        self.assertEqual(result["contract_reason_code"], "not_ready")
        self.assertEqual(result["failures"], ["operator_not_safe"])

    def test_restore_durable_cli_runtime_json_safe_hazards(self) -> None:
        hazard_cases = [
            ("restore_supported", True, "restore_supported"),
            ("durable_writes", True, "durable_writes"),
            ("cli_commands", ["approve"], "has_cli_commands"),
            ("runtime_dependencies", ["approval-service"], "has_runtime_dependencies"),
            ("json_safe", False, "not_json_safe"),
        ]
        for field, value, expected_failure in hazard_cases:
            with self.subTest(field=field):
                payload = _rendered_contract_payload()
                contract = payload["contract"]
                assert isinstance(contract, dict)
                contract[field] = value

                result = consume_approval_review_readiness_ci(payload)

                self.assertIs(result["ci_ok"], False)
                self.assertEqual(result["reason_code"], "not_ready")
                self.assertIn(expected_failure, result["failures"])

    def test_output_exact_shape(self) -> None:
        result = consume_approval_review_readiness_ci(_rendered_contract_payload())

        self.assertEqual(list(result.keys()), EXPECTED_CI_OUTPUT_KEYS)

    def test_manifest_defensive_copy(self) -> None:
        manifest = approval_review_readiness_ci_manifest()
        manifest["failure_values"].append("INJECTED")  # type: ignore[union-attr]
        manifest["surface"] = "tampered"
        manifest_again = approval_review_readiness_ci_manifest()

        self.assertEqual(manifest_again["surface"], "approval_review_readiness_ci")
        self.assertNotIn("INJECTED", manifest_again["failure_values"])
        _assert_json_safe(manifest_again)

    def test_output_json_safe(self) -> None:
        _assert_json_safe(consume_approval_review_readiness_ci(_rendered_contract_payload()))

    def test_no_upstream_calls(self) -> None:
        payload = _rendered_contract_payload()
        with mock.patch(
            "kernel.lifecycle.approval_review_readiness_contract"
            ".check_approval_review_readiness_contract"
        ) as check_call, mock.patch(
            "kernel.lifecycle.approval_review_readiness_contract"
            ".render_approval_review_readiness_contract_check"
        ) as render_call, mock.patch(
            "kernel.lifecycle.approval_review_readiness"
            ".build_approval_review_readiness_envelope"
        ) as build_call:
            consume_approval_review_readiness_ci(payload)
            self.assertEqual(check_call.call_count, 0)
            self.assertEqual(render_call.call_count, 0)
            self.assertEqual(build_call.call_count, 0)

    def test_no_source_creep(self) -> None:
        _assert_no_source_creep(ci_module)


class TestApprovalReviewReadinessEndToEnd(unittest.TestCase):
    def test_real_approval_review_revision_rows_pipeline_to_ci_ok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "approval-review-readiness.db"
            conn = open_connection(db_path)
            try:
                apply_migrations(conn)
                review_repo = ReviewArtifactRepository(conn)
                approval_repo = ApprovalArtifactRepository(conn)
                revision_repo = RevisionRepository(conn)
                created_at = "2026-01-01T00:00:00+00:00"

                review_repo.insert(
                    {
                        "review_artifact_id": "rv-real",
                        "task_id": "task-real",
                        "root_revision_id": "root-real",
                        "patch_proposal_id": "pp-real",
                        "diff_hash": "sha256:review-real",
                        "semantic_impact_hash": "sha256:semantic-real",
                        "risk_class": "low",
                        "rendering_provenance": {
                            "renderer_id": "p3_01_test",
                            "renderer_version": "phase1-slice1",
                            "self_summary_flag": False,
                        },
                        "taint_set": [],
                        "created_at": created_at,
                        "version_tuple_hash": "vt-real",
                    }
                )
                approval_repo.insert(
                    {
                        "approval_id": "ap-real",
                        "task_id": "task-real",
                        "originating_root_revision_id": "root-real",
                        "reviewed_patch_hash": "patch-real",
                        "reviewed_context_artifact_id": "ctx-real",
                        "required_receipt_ids": ["vr-real"],
                        "approval_scope": "phase1",
                        "approver_identity": "p3_01_test",
                        "approval_state": "approved",
                        "policy_version": "phase1-slice1",
                        "created_at": created_at,
                        "expires_at": "2026-01-02T00:00:00+00:00",
                        "version_tuple_hash": "vt-real",
                    }
                )
                revision_repo.insert_pending(
                    {
                        "revision_id": "rev-real",
                        "parent_revision_id": None,
                        "project_id": "project-real",
                        "task_id": "task-real",
                        "root_hash": "root-hash-real",
                        "snapshot_root_id": "snap-real",
                        "intent_id": "intent-real",
                        "originating_context_artifact_id": "ctx-real",
                        "approval_id": "ap-real",
                        "logical_sequence_at_seal": None,
                        "version_tuple_hash": "vt-real",
                        "taint_set": [],
                        "created_at": created_at,
                    }
                )
                revision_repo.transition_to_sealed(
                    revision_id="rev-real",
                    sealed_at="2026-01-01T00:01:00+00:00",
                    logical_sequence_at_seal=1,
                    approval_id="ap-real",
                )
                conn.commit()

                review = review_repo.fetch("rv-real")
                approval = approval_repo.fetch("ap-real")
                revision = revision_repo.fetch("rev-real")
                self.assertIsNotNone(review)
                self.assertIsNotNone(approval)
                self.assertIsNotNone(revision)
                rendered_items = [
                    {
                        "task_id": review["task_id"],
                        "record_type": "review_artifact",
                        "approval_state": None,
                        "review_state": "created",
                        "revision_id": review["root_revision_id"],
                        "seal_id": None,
                        "actor_identity": None,
                        "created_at": review["created_at"],
                    },
                    {
                        "task_id": approval["task_id"],
                        "record_type": "approval_artifact",
                        "approval_state": approval["approval_state"],
                        "review_state": "created",
                        "revision_id": approval["originating_root_revision_id"],
                        "seal_id": None,
                        "actor_identity": approval["approver_identity"],
                        "created_at": approval["created_at"],
                    },
                    {
                        "task_id": revision["task_id"],
                        "record_type": "revision",
                        "approval_state": "approved",
                        "review_state": "created",
                        "revision_id": revision["revision_id"],
                        "seal_id": revision["snapshot_root_id"],
                        "actor_identity": None,
                        "created_at": revision["created_at"],
                    },
                ]
            finally:
                conn.close()

            before_counts = _table_row_counts(db_path)
            envelope = build_approval_review_readiness_envelope(rendered_items)
            rendered_envelope = render_approval_review_readiness_envelope(envelope)
            contract_check = check_approval_review_readiness_contract(
                rendered_envelope
            )
            rendered_contract = render_approval_review_readiness_contract_check(
                contract_check
            )
            ci_result = consume_approval_review_readiness_ci(rendered_contract)
            after_counts = _table_row_counts(db_path)

        self.assertEqual(before_counts, after_counts)
        self.assertIs(ci_result["ci_ok"], True)
        self.assertEqual(ci_result["reason_code"], "ready")
        self.assertEqual(ci_result["failures"], [])
        self.assertEqual(ci_result["surface"], "approval_review_readiness_contract")
        _assert_json_safe(ci_result)


class TestApprovalReviewReadinessSourceBoundaries(unittest.TestCase):
    def test_layering_imports_are_one_way_rendered_payload_only(self) -> None:
        envelope_imports = _imported_modules(envelope_module)
        contract_imports = _imported_modules(contract_module)
        ci_imports = _imported_modules(ci_module)

        self.assertNotIn(
            "kernel.lifecycle.approval_review_readiness_contract",
            envelope_imports,
        )
        self.assertNotIn(
            "kernel.lifecycle.approval_review_readiness_ci",
            envelope_imports,
        )
        self.assertNotIn(
            "kernel.lifecycle.approval_review_readiness",
            contract_imports,
        )
        self.assertNotIn(
            "kernel.lifecycle.approval_review_readiness_contract",
            ci_imports,
        )

    def test_all_new_modules_have_no_source_boundary_creep(self) -> None:
        for module in (envelope_module, contract_module, ci_module):
            with self.subTest(module=module.__name__):
                _assert_no_source_creep(module)


if __name__ == "__main__":
    unittest.main()
