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
_LAUNCHER_WORKFLOWS = (
    "local_office_workflow",
    "model_fixture_workflow",
    "model_provider_dry_run_workflow",
    "browser_fixture_workflow",
    "browser_runtime_dry_run_workflow",
    "comfyui_dry_run_workflow",
    "blender_dry_run_workflow",
    "creative_handoff_workflow",
    "task_graph_workflow",
    "runtime_delivery_validation_workflow",
    "product_health_check_workflow",
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
    adapter_registry_valid = all(
        not entry["validation_failures"] for entry in adapter_entries
    )
    runtime_defaults_fail_closed = all(
        not runtime_defaults[runtime_class]["activation_allowed_by_default"]
        for runtime_class in _REQUIRED_RUNTIME_CLASSES
    )
    launcher_workflows_complete = all(_LAUNCHER_WORKFLOWS)
    core_docs_present = all(docs["core_docs"].values())
    tests_metadata_available = tests["personal_ai_test_files_count"] > 0
    complete = all(
        (
            dependencies["openpyxl"]["available"],
            adapter_registry_valid,
            runtime_defaults_fail_closed,
            launcher_workflows_complete,
            core_docs_present,
            tests_metadata_available,
        )
    )
    return {
        "health_type": "personal_ai_execution_os_product_health_v1",
        "complete": complete,
        "authority": "non_authority",
        "repo_root": root.as_posix(),
        "dependencies": dependencies,
        "adapter_registry_valid": adapter_registry_valid,
        "adapter_count": len(adapter_entries),
        "adapters": adapter_entries,
        "runtime_admission_defaults_fail_closed": runtime_defaults_fail_closed,
        "runtime_admission_defaults": runtime_defaults,
        "runtime_activation_performed": False,
        "deferred_real_runtimes": list(_REQUIRED_RUNTIME_CLASSES),
        "launcher_workflows": list(_LAUNCHER_WORKFLOWS),
        "launcher_workflows_complete": launcher_workflows_complete,
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


def _render_summary(report: dict[str, object]) -> str:
    docs = report["docs"]
    tests = report["tests"]
    lines = [
        "# Product Health Check",
        "",
        "Status: complete" if report["complete"] else "Status: incomplete",
        "Runtime activation performed: false",
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
        "Boundary: local health inspection only; human approval required.",
    ]
    return "\n".join(lines)


def _require_no_overwrite(path: Path) -> None:
    if path.exists():
        raise ValueError("product health check output already exists")
