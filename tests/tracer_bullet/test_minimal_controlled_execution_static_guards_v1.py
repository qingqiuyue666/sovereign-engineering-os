"""Repository-level static guards for minimal controlled execution."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from kernel.execution import minimal_controlled_git_diff_check_runner as diff_runner
from kernel.execution import minimal_controlled_git_status_runner as status_runner
from kernel.execution import minimal_controlled_preflight_sequence as preflight
from kernel.execution.minimal_controlled_execution_contract import INITIAL_COMMAND_REGISTRY


EXECUTION_ROOT = Path("kernel/execution")
MINIMAL_FILES = tuple(sorted(EXECUTION_ROOT.glob("minimal_controlled_*.py")))
CONTRACT_ONLY_FILES = (
    EXECUTION_ROOT / "minimal_controlled_execution_contract.py",
)
ADMISSION_WAL_VERIFIER_FILES = (
    EXECUTION_ROOT / "minimal_controlled_execution_admission_wal_verifier.py",
)
RUNNER_FILES = (
    EXECUTION_ROOT / "minimal_controlled_git_status_runner.py",
    EXECUTION_ROOT / "minimal_controlled_git_diff_check_runner.py",
)
PREFLIGHT_FILE = EXECUTION_ROOT / "minimal_controlled_preflight_sequence.py"


class MinimalControlledExecutionStaticGuardsV1Tests(unittest.TestCase):
    def test_contract_only_modules_contain_no_subprocess(self):
        for path in CONTRACT_ONLY_FILES:
            with self.subTest(path=str(path)):
                self.assertFalse(_imports_module(path, "subprocess"))
                self.assertFalse(_calls_subprocess(path))

    def test_admission_wal_verifier_modules_contain_no_subprocess(self):
        for path in ADMISSION_WAL_VERIFIER_FILES:
            with self.subTest(path=str(path)):
                self.assertFalse(_imports_module(path, "subprocess"))
                self.assertFalse(_calls_subprocess(path))

    def test_preflight_sequence_contains_no_subprocess(self):
        self.assertFalse(_imports_module(PREFLIGHT_FILE, "subprocess"))
        self.assertFalse(_calls_subprocess(PREFLIGHT_FILE))

    def test_runner_modules_may_use_only_subprocess_run(self):
        for path in RUNNER_FILES:
            with self.subTest(path=str(path)):
                tree = _tree(path)
                calls = [
                    node
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "subprocess"
                ]
                self.assertTrue(calls)
                self.assertEqual({call.func.attr for call in calls}, {"run"})

    def test_forbidden_process_and_dynamic_execution_surfaces(self):
        forbidden_markers = (
            "shell=True",
            "Popen",
            "os.system",
            "exec(",
            "eval(",
        )
        for path in MINIMAL_FILES:
            source = _source(path)
            with self.subTest(path=str(path)):
                for marker in forbidden_markers:
                    self.assertNotIn(marker, source)

    def test_argparse_click_typer_forbidden(self):
        for path in MINIMAL_FILES:
            with self.subTest(path=str(path)):
                imported = _imported_modules(path)
                self.assertFalse({"argparse", "click", "typer"}.intersection(imported))

    def test_provider_browser_dcc_mcp_markers_forbidden(self):
        markers = (
            "requests",
            "httpx",
            "urllib",
            "socket",
            "webbrowser",
            "playwright",
            "openai",
            "anthropic",
            "bpy",
            "hou",
            "unreal",
            "comfyui",
            "mcp",
        )
        for path in RUNNER_FILES + (PREFLIGHT_FILE,):
            source = _source(path)
            with self.subTest(path=str(path)):
                for marker in markers:
                    self.assertNotIn(marker, source)

    def test_broad_runtime_imports_forbidden(self):
        forbidden_import_prefixes = (
            "kernel.runtime",
            "kernel.os_engine",
            "tools.local_execution_kernel",
        )
        for path in MINIMAL_FILES:
            imported = _imported_modules(path)
            with self.subTest(path=str(path)):
                self.assertFalse(
                    any(
                        module == prefix or module.startswith(prefix + ".")
                        for module in imported
                        for prefix in forbidden_import_prefixes
                    ),
                    imported,
                )

    def test_raw_stdout_stderr_fields_forbidden_in_persisted_objects(self):
        raw_fields = {"stdout", "stderr", "stdout_text", "stderr_text", "raw_stdout", "raw_stderr"}
        persisted_classes = (
            status_runner.MinimalControlledExecutionReceipt,
            status_runner.MinimalControlledExecutionFailureBundle,
            status_runner.MinimalControlledExecutionVerifierInput,
            status_runner.MinimalControlledExecutionVerifierBinding,
            diff_runner.MinimalControlledExecutionReceipt,
            diff_runner.MinimalControlledExecutionFailureBundle,
            diff_runner.MinimalControlledExecutionVerifierInput,
            diff_runner.MinimalControlledExecutionVerifierBinding,
            preflight.MinimalControlledPreflightResult,
        )
        for persisted_class in persisted_classes:
            with self.subTest(persisted_class=persisted_class.__name__):
                self.assertFalse(raw_fields.intersection(persisted_class.__dataclass_fields__))

    def test_registry_remains_exactly_status_and_diff_check(self):
        self.assertEqual(tuple(INITIAL_COMMAND_REGISTRY), ("git_status_short", "git_diff_check"))

    def test_git_status_executable_ids_exactly_status(self):
        self.assertEqual(status_runner.EXECUTABLE_COMMAND_IDS, ("git_status_short",))

    def test_git_diff_executable_ids_exactly_diff_check(self):
        self.assertEqual(diff_runner.EXECUTABLE_COMMAND_IDS, ("git_diff_check",))

    def test_preflight_order_exactly_status_then_diff_check(self):
        self.assertEqual(preflight.PREFLIGHT_ORDER, ("git_status_short", "git_diff_check"))


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _tree(path: Path) -> ast.Module:
    return ast.parse(_source(path))


def _imports_module(path: Path, module_name: str) -> bool:
    return module_name in _imported_modules(path)


def _calls_subprocess(path: Path) -> bool:
    for node in ast.walk(_tree(path)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess"
        ):
            return True
    return False


def _imported_modules(path: Path) -> set[str]:
    imported: set[str] = set()
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


if __name__ == "__main__":
    unittest.main()
