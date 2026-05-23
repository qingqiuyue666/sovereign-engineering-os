"""Product health report for the Personal AI Execution OS."""

from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path

from kernel.personal_ai.adapters.adapter_registry import (
    DEFAULT_ADAPTER_REGISTRY,
    validate_adapter_registry_entry,
)
from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.markdown_utils import write_markdown_atomically
from kernel.personal_ai.runtime_admission_gate import build_runtime_class_policies

__all__ = [
    "ProductHealthCheckResult",
    "build_product_health_report",
    "write_product_health_check",
]

_REPORT_FILE = "product_health_report.json"
_SUMMARY_FILE = "product_health_summary.md"
_LAUNCHER_WORKFLOW_CALLABLES = (
    ("local_asset_scan_workflow", "run_local_asset_scan_launcher"),
    (
        "local_asset_smoke_readiness_workflow",
        "run_local_asset_smoke_readiness_launcher",
    ),
    (
        "local_asset_human_smoke_run_workflow",
        "run_local_asset_human_smoke_launcher",
    ),
    (
        "local_asset_bounded_smoke_iteration_workflow",
        "run_local_asset_bounded_smoke_iteration_launcher",
    ),
    (
        "local_asset_smoke_review_packet_workflow",
        "run_local_asset_smoke_review_packet_launcher",
    ),
    (
        "local_asset_smoke_iteration_review_packet_workflow",
        "run_local_asset_smoke_iteration_review_packet_launcher",
    ),
    (
        "local_asset_smoke_promotion_gate_workflow",
        "run_local_asset_smoke_promotion_gate_launcher",
    ),
    (
        "local_asset_iteration_promotion_gate_workflow",
        "run_local_asset_iteration_promotion_gate_launcher",
    ),
    (
        "local_asset_bounded_smoke_cycle_contract_workflow",
        "run_local_asset_bounded_smoke_cycle_contract_launcher",
    ),
    (
        "local_asset_bounded_smoke_cycle_human_review_workflow",
        "run_local_asset_bounded_smoke_cycle_human_review_launcher",
    ),
    (
        "local_asset_next_bounded_smoke_iteration_admission_workflow",
        "run_local_asset_next_bounded_smoke_iteration_admission_launcher",
    ),
    (
        "local_asset_next_bounded_smoke_iteration_execution_request_workflow",
        "run_local_asset_next_bounded_smoke_iteration_execution_request_launcher",
    ),
    ("local_office_workflow", "run_local_office_launcher"),
    ("model_fixture_workflow", "run_model_fixture_launcher"),
    ("model_provider_dry_run_workflow", "run_model_provider_dry_run_launcher"),
    ("browser_fixture_workflow", "run_browser_fixture_launcher"),
    ("browser_runtime_dry_run_workflow", "run_browser_runtime_dry_run_launcher"),
    ("comfyui_dry_run_workflow", "run_comfyui_dry_run_launcher"),
    ("blender_dry_run_workflow", "run_blender_dry_run_launcher"),
    ("creative_handoff_workflow", "run_creative_handoff_launcher"),
    ("task_graph_workflow", "run_task_graph_launcher"),
    ("runtime_delivery_validation_workflow", "run_runtime_delivery_validation_launcher"),
    ("product_health_check_workflow", "run_product_health_check_launcher"),
)
_LAUNCHER_WORKFLOWS = tuple(
    workflow for workflow, _callable_name in _LAUNCHER_WORKFLOW_CALLABLES
)
_REQUIRED_CLI_SUBCOMMANDS = (
    "launch-local-asset-scan",
    "launch-local-asset-smoke-readiness",
    "launch-local-asset-human-smoke-run",
    "launch-local-asset-bounded-smoke-iteration",
    "launch-local-asset-smoke-review-packet",
    "launch-local-asset-smoke-iteration-review-packet",
    "launch-local-asset-smoke-promotion-gate",
    "launch-local-asset-iteration-promotion-gate",
    "launch-local-asset-bounded-smoke-cycle-contract",
    "launch-local-asset-bounded-smoke-cycle-human-review",
    "launch-local-asset-next-bounded-smoke-iteration-admission",
    "launch-office-workflow",
    "launch-model-fixture",
    "launch-model-provider-dry-run",
    "launch-browser-fixture",
    "launch-browser-dry-run",
    "launch-comfyui-dry-run",
    "launch-blender-dry-run",
    "launch-creative-handoff",
    "launch-task-graph",
    "launch-runtime-delivery-validation",
    "launch-product-health-check",
)
_CORE_DOCS = (
    "README.md",
    "docs/current_phase.md",
    "docs/decisions/main_health_verification_after_full_landing_v1.md",
)
_FINAL_DOCS = (
    "docs/decisions/personal_ai_execution_os_final_product_completion_decision_audit_v1.md",
    "docs/decisions/personal_ai_execution_os_final_product_completion_merge_readiness_audit_v1.md",
    "docs/roadmap/personal_ai_execution_os_post_completion_roadmap_v1.md",
    "docs/usage/personal_ai_execution_os_product_usage_v1.md",
)
_REQUIRED_RUNTIME_CLASSES = (
    "live_model_provider",
    "external_browser",
    "comfyui_endpoint",
    "blender_runtime",
    "creative_external_tool",
)


@dataclass(frozen=True)
class ProductHealthCheckResult:
    output_dir: Path
    product_health_report_path: Path
    product_health_summary_path: Path
    complete: bool
    required_human_approval: bool


def build_product_health_report(repo_root: Path | None = None) -> dict[str, object]:
    root = Path.cwd() if repo_root is None else Path(repo_root)
    dependencies = _dependency_state()
    adapter_entries = _adapter_entries()
    runtime_defaults = _runtime_admission_defaults()
    docs = _docs_state(root)
    tests = _tests_state(root)
    launcher_static_checks = _launcher_static_state(root)
    adapter_registry_valid = all(
        not entry["validation_failures"] for entry in adapter_entries
    )
    runtime_defaults_fail_closed = all(
        not runtime_defaults[runtime_class]["activation_allowed_by_default"]
        for runtime_class in _REQUIRED_RUNTIME_CLASSES
    )
    launcher_workflows_complete = bool(
        launcher_static_checks["launcher_workflows_declared_complete"]
    )
    cli_subcommands_complete = bool(
        launcher_static_checks["required_cli_subcommands_declared_complete"]
    )
    core_docs_present = all(docs["core_docs"].values())
    tests_metadata_available = tests["personal_ai_test_files_count"] > 0
    structural_complete = all(
        (
            dependencies["openpyxl"]["available"],
            adapter_registry_valid,
            runtime_defaults_fail_closed,
            launcher_workflows_complete,
            cli_subcommands_complete,
            core_docs_present,
            tests_metadata_available,
        )
    )
    runtime_workflow_smoke_verified = False
    final_product_health_complete = (
        structural_complete and runtime_workflow_smoke_verified
    )
    return {
        "health_type": "personal_ai_execution_os_product_health_v1",
        "complete": structural_complete,
        "structural_complete": structural_complete,
        "runtime_workflow_smoke_verified": runtime_workflow_smoke_verified,
        "final_product_health_complete": final_product_health_complete,
        "completion_scope": "static_structural_health_only",
        "authority": "non_authority",
        "repo_root": root.as_posix(),
        "dependencies": dependencies,
        "adapter_registry_valid": adapter_registry_valid,
        "adapter_count": len(adapter_entries),
        "adapters": adapter_entries,
        "runtime_admission_defaults_fail_closed": runtime_defaults_fail_closed,
        "runtime_admission_defaults": runtime_defaults,
        "runtime_activation_performed": False,
        "does_not_execute_launcher_workflows": True,
        "does_not_execute_real_runtime": True,
        "human_review_required_before_final_product_claim": True,
        "deferred_real_runtimes": list(_REQUIRED_RUNTIME_CLASSES),
        "launcher_workflows": list(_LAUNCHER_WORKFLOWS),
        "launcher_workflows_complete": launcher_workflows_complete,
        "required_cli_subcommands": list(_REQUIRED_CLI_SUBCOMMANDS),
        "cli_subcommands_complete": cli_subcommands_complete,
        "launcher_static_checks": launcher_static_checks,
        "docs": docs,
        "tests": tests,
        "network_runtime_allowed_by_default": False,
        "subprocess_runtime_allowed_by_default": False,
        "browser_runtime_allowed_by_default": False,
        "model_api_runtime_allowed_by_default": False,
        "creative_runtime_allowed_by_default": False,
        "required_human_approval": True,
        "next_allowed_action": "human_review_product_health_report",
    }


def write_product_health_check(
    output_dir: Path,
    *,
    repo_root: Path | None = None,
    report_file_name: str = _REPORT_FILE,
    summary_file_name: str = _SUMMARY_FILE,
) -> ProductHealthCheckResult:
    output_path = Path(output_dir)
    if not output_path.exists() or not output_path.is_dir():
        raise ValueError("output_dir is missing")
    report_path = output_path / report_file_name
    summary_path = output_path / summary_file_name
    _require_no_overwrite(report_path)
    _require_no_overwrite(summary_path)
    report = build_product_health_report(repo_root)
    write_json_atomically(report_path, report)
    write_markdown_atomically(summary_path, _render_summary(report))
    return ProductHealthCheckResult(
        output_dir=output_path,
        product_health_report_path=report_path,
        product_health_summary_path=summary_path,
        complete=bool(report["complete"]),
        required_human_approval=True,
    )


def _dependency_state() -> dict[str, dict[str, object]]:
    return {
        "python_stdlib_json": {"available": True, "required": True},
        "python_stdlib_unittest": {"available": True, "required": True},
        "openpyxl": {
            "available": find_spec("openpyxl") is not None,
            "required": True,
        },
        "playwright": {
            "available": find_spec("playwright") is not None,
            "required": False,
            "disabled_by_default": True,
        },
    }


def _adapter_entries() -> list[dict[str, object]]:
    return [
        {
            "adapter_id": entry.adapter_id,
            "mode": entry.mode.value,
            "risk_class": entry.risk_class.value,
            "admission_status": entry.admission_status.value,
            "capabilities": list(entry.capabilities),
            "validation_failures": list(validate_adapter_registry_entry(entry)),
        }
        for entry in DEFAULT_ADAPTER_REGISTRY
    ]


def _runtime_admission_defaults() -> dict[str, dict[str, object]]:
    return {
        policy.runtime_class: policy.to_dict()
        for policy in build_runtime_class_policies()
    }


def _docs_state(root: Path) -> dict[str, object]:
    core_docs = {path: (root / path).is_file() for path in _CORE_DOCS}
    final_docs = {path: (root / path).is_file() for path in _FINAL_DOCS}
    return {
        "core_docs": core_docs,
        "final_freeze_docs": final_docs,
        "core_docs_complete": all(core_docs.values()),
        "final_freeze_docs_complete": all(final_docs.values()),
    }


def _tests_state(root: Path) -> dict[str, object]:
    tests_dir = root / "tests" / "personal_ai"
    test_files = sorted(
        path.name for path in tests_dir.glob("test_*.py")
    ) if tests_dir.is_dir() else []
    return {
        "tests_dir": tests_dir.as_posix(),
        "personal_ai_test_files_count": len(test_files),
        "final_product_e2e_battery_present": (
            "test_final_product_e2e_battery.py" in test_files
        ),
    }


def _launcher_static_state(root: Path) -> dict[str, object]:
    launcher_path = root / "kernel" / "personal_ai" / "local_launcher.py"
    cli_path = root / "kernel" / "personal_ai" / "local_mvp_cli.py"
    launcher_text = _read_text_if_present(launcher_path)
    cli_text = _read_text_if_present(cli_path)
    workflow_names_declared = {
        workflow: workflow in launcher_text
        for workflow in _LAUNCHER_WORKFLOWS
    }
    workflow_callables_declared = {
        workflow: callable_name in launcher_text
        for workflow, callable_name in _LAUNCHER_WORKFLOW_CALLABLES
    }
    launcher_workflows_declared = {
        workflow: (
            workflow_names_declared[workflow]
            and workflow_callables_declared[workflow]
        )
        for workflow in _LAUNCHER_WORKFLOWS
    }
    cli_subcommands_declared = {
        subcommand: '"' + subcommand + '"' in cli_text
        for subcommand in _REQUIRED_CLI_SUBCOMMANDS
    }
    return {
        "launcher_source_path": launcher_path.as_posix(),
        "cli_source_path": cli_path.as_posix(),
        "launcher_source_present": bool(launcher_text),
        "cli_source_present": bool(cli_text),
        "workflow_names_declared": workflow_names_declared,
        "workflow_callables_declared": workflow_callables_declared,
        "launcher_workflows_declared": launcher_workflows_declared,
        "launcher_workflows_declared_complete": all(
            launcher_workflows_declared.values()
        ),
        "required_cli_subcommands_declared": cli_subcommands_declared,
        "required_cli_subcommands_declared_complete": all(
            cli_subcommands_declared.values()
        ),
        "workflows_executed": False,
    }


def _read_text_if_present(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _render_summary(report: dict[str, object]) -> str:
    docs = report["docs"]
    tests = report["tests"]
    lines = [
        "# Product Health Check",
        "",
        "Status: static structural complete"
        if report["complete"]
        else "Status: static structural incomplete",
        "Completion scope: " + str(report["completion_scope"]),
        "Structural complete: "
        + str(report["structural_complete"]).lower(),
        "Runtime workflow smoke verified: "
        + str(report["runtime_workflow_smoke_verified"]).lower(),
        "Final product health complete: "
        + str(report["final_product_health_complete"]).lower(),
        "Launcher workflows executed: false",
        "Runtime activation performed: false",
        "Real runtime executed: false",
        "Adapter registry valid: "
        + str(report["adapter_registry_valid"]).lower(),
        "Runtime defaults fail closed: "
        + str(report["runtime_admission_defaults_fail_closed"]).lower(),
        "Core docs complete: "
        + str(docs["core_docs_complete"]).lower(),
        "Final freeze docs complete: "
        + str(docs["final_freeze_docs_complete"]).lower(),
        "Personal AI test files: "
        + str(tests["personal_ai_test_files_count"]),
        "Next action: human review of product health report",
        "",
        "Boundary: static structural health inspection only; full runtime "
        "correctness is supported by tests, not this report alone.",
    ]
    return "\n".join(lines)


def _require_no_overwrite(path: Path) -> None:
    if path.exists():
        raise ValueError("product health check output already exists")
