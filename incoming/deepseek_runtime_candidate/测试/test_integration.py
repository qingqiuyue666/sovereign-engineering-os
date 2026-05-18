"""Tests: CLI dispatch, task manifest, task contracts, health plan.

Run:   python -m pytest 测试/test_integration.py -v
Expect: 12 tests pass — CLI commands return correct exit codes and JSON,
        task manifest validates correctly, task contracts create valid envelopes,
        health plan returns expected checks.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
import pytest

from kernel.cli.commands import dispatch
from kernel.tasks.task_manifest import validate_task_manifest
from kernel.tasks.task_contracts import create_operator_task_envelope
from kernel.status.health_plan import ordered_health_plan, run_health_checks, register_health_check


# ── CLI dispatch tests ─────────────────────────────────────────

def test_cli_no_args():
    """Dispatch with no args returns version info."""
    result = dispatch([])
    assert result == 0


def test_cli_version():
    result = dispatch(["version"])
    assert result == 0


def test_cli_status():
    result = dispatch(["status"])
    assert result == 0


def test_cli_explain_gates():
    result = dispatch(["explain-gates"])
    assert result == 0


def test_cli_health_plan():
    result = dispatch(["health-plan"])
    assert result == 0


def test_cli_unknown_command():
    result = dispatch(["nonexistent_command_xyz"])
    assert result == 2


# ── Task manifest validation tests ─────────────────────────────

def test_validate_valid_manifest():
    result = validate_task_manifest({
        "task_id": "task-abc123",
        "objective": "Test task",
        "classification": "PUBLIC",
    })
    assert result.accepted is True
    assert len(result.failures) == 0


def test_validate_missing_keys():
    result = validate_task_manifest({})
    assert result.accepted is False
    assert len(result.failures) > 0


def test_validate_invalid_classification():
    result = validate_task_manifest({
        "task_id": "task-xyz",
        "objective": "Bad classification",
        "classification": "TOP_SECRET",
    })
    assert result.accepted is False
    assert any("classification" in f for f in result.failures)


def test_validate_non_dict_payload():
    result = validate_task_manifest("not_a_dict")
    assert result.accepted is False


# ── Task contract tests ────────────────────────────────────────

def test_create_operator_task_envelope_valid():
    result = create_operator_task_envelope({
        "objective": "Dry run test",
        "requested_capabilities": ["local_validation"],
        "classification": "PUBLIC",
        "policy_version": "v12",
        "code_version": "test",
        "descriptor": {"descriptor_type": "text", "content_digest": "sha256:test"},
    })
    assert result.accepted is True
    assert result.envelope.get("task_id", "").startswith("task-")
    assert result.envelope.get("envelope_version") == "v12"


def test_create_operator_task_envelope_invalid_classification():
    result = create_operator_task_envelope({
        "objective": "Test",
        "classification": "INVALID",
        "policy_version": "v12",
    })
    assert result.accepted is False


# ── Health plan tests ──────────────────────────────────────────

def test_health_plan_returns_list():
    plan = ordered_health_plan()
    assert isinstance(plan, list)
    assert "pid1-alive" in plan
    assert "filesystem-root" in plan


def test_run_health_checks():
    results = run_health_checks()
    assert len(results) >= 2
    for r in results:
        assert "check" in r
        assert "ok" in r


def test_register_custom_health_check():
    called = [False]

    def custom_check():
        called[0] = True
        return {"ok": True, "component": "custom"}

    register_health_check("custom-check", custom_check)
    results = run_health_checks()
    assert called[0] is True
    assert any(r.get("check") == "custom-check" for r in results)


# ── Operator CLI (apps layer) tests ────────────────────────────

def test_operator_cli_main_imports():
    """Verify operator_cli main can be imported and called."""
    from apps.operator_cli.main import main
    result = main([])
    assert result == 0


def test_operator_cli_health_command():
    """Verify 'health' subcommand."""
    from apps.operator_cli.main import main
    result = main(["health"])
    assert result == 0


def test_operator_cli_audit_summary():
    """Verify 'audit summary' subcommand."""
    from apps.operator_cli.main import main
    result = main(["audit", "summary"])
    assert result == 0


def test_operator_cli_run_ledger_dry_run():
    """Verify 'run-ledger create --dry-run' subcommand."""
    from apps.operator_cli.main import main
    result = main(["run-ledger", "create", "--dry-run"])
    assert result == 0


def test_operator_cli_task_validate_with_tempfile():
    """Validate a task manifest from a temp file."""
    from apps.operator_cli.main import main

    manifest = {
        "task_id": "task-test001",
        "objective": "Integration test task",
        "classification": "PUBLIC",
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(manifest, f)
        tmp_path = f.name

    try:
        result = main(["task", "validate", tmp_path])
        assert result == 0
    finally:
        Path(tmp_path).unlink()
