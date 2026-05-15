"""Static health report for controlled runtime activation surfaces."""

from dataclasses import dataclass
from pathlib import Path

from kernel.personal_ai.io_utils import write_json_atomically
from kernel.personal_ai.markdown_utils import write_markdown_atomically

__all__ = [
    "RuntimeActivationHealthResult",
    "build_runtime_activation_health_report",
    "write_runtime_activation_health_report",
]

_REPORT_FILE = "runtime_activation_health_report.json"
_SUMMARY_FILE = "runtime_activation_health_summary.md"
_REQUIRED_MODULES = (
    "kernel/personal_ai/adapters/model_provider_activation_package.py",
    "kernel/personal_ai/adapters/model_provider_live_smoke.py",
    "kernel/personal_ai/adapters/browser_local_smoke.py",
    "kernel/personal_ai/adapters/comfyui_activation_package.py",
    "kernel/personal_ai/adapters/blender_activation_package.py",
)
_REQUIRED_TESTS = (
    "tests/personal_ai/test_model_provider_activation_package.py",
    "tests/personal_ai/test_final_system_controlled_runtime_activation.py",
)


@dataclass(frozen=True)
class RuntimeActivationHealthResult:
    output_dir: Path
    report_path: Path
    summary_path: Path
    complete: bool
    required_human_approval: bool


def build_runtime_activation_health_report(repo_root: Path | None = None) -> dict[str, object]:
    root = Path.cwd() if repo_root is None else Path(repo_root)
    modules = {path: (root / path).is_file() for path in _REQUIRED_MODULES}
    tests = {path: (root / path).is_file() for path in _REQUIRED_TESTS}
    complete = all(modules.values()) and all(tests.values())
    return {
        "health_type": "personal_ai_runtime_activation_health_v1",
        "complete": complete,
        "authority": "non_authority",
        "repo_root": root.as_posix(),
        "required_modules": modules,
        "required_tests": tests,
        "static_health_only": True,
        "does_not_execute_runtime": True,
        "does_not_call_model_provider": True,
        "does_not_launch_browser": True,
        "does_not_call_comfyui_endpoint": True,
        "does_not_launch_blender": True,
        "network_used": False,
        "subprocess_used": False,
        "api_key_value_persisted": False,
        "api_key_value_logged": False,
        "activation_surfaces": [
            "model_provider_controlled_activation_package",
            "disabled_model_provider_live_smoke_plan",
            "browser_local_smoke_plan",
            "comfyui_controlled_activation_package",
            "blender_controlled_activation_package",
        ],
        "live_runtimes_still_disabled_by_default": True,
        "required_human_approval": True,
        "next_allowed_action": "human_review_runtime_activation_health_report",
    }


def write_runtime_activation_health_report(
    output_dir: Path,
    *,
    repo_root: Path | None = None,
    report_file_name: str = _REPORT_FILE,
    summary_file_name: str = _SUMMARY_FILE,
) -> RuntimeActivationHealthResult:
    output_path = Path(output_dir)
    if not output_path.exists() or not output_path.is_dir():
        raise ValueError("output_dir is missing")
    report_path = output_path / report_file_name
    summary_path = output_path / summary_file_name
    _require_no_overwrite(report_path)
    _require_no_overwrite(summary_path)
    report = build_runtime_activation_health_report(repo_root)
    write_json_atomically(report_path, report)
    write_markdown_atomically(summary_path, _render_summary(report))
    return RuntimeActivationHealthResult(
        output_dir=output_path,
        report_path=report_path,
        summary_path=summary_path,
        complete=bool(report["complete"]),
        required_human_approval=True,
    )


def _render_summary(report: dict[str, object]) -> str:
    return "\n".join(
        [
            "# Runtime Activation Health",
            "",
            "Status: complete" if report["complete"] else "Status: incomplete",
            "Static health only: true",
            "Runtime executed: false",
            "Network used: false",
            "Subprocess used: false",
            "Live runtimes disabled by default: true",
            "Next action: human review runtime activation health report",
            "",
        ]
    )


def _require_no_overwrite(path: Path) -> None:
    if path.exists():
        raise ValueError("runtime activation health output already exists")
