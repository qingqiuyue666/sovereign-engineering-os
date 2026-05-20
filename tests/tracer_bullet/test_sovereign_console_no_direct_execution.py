"""Source guards for the Sovereign Console execution boundary."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path


class SovereignConsoleNoDirectExecutionTests(unittest.TestCase):
    def test_ui_source_has_no_shell_or_direct_process_calls(self) -> None:
        source = _ui_source()
        forbidden = ("shell=True", "subprocess.run", "subprocess.Popen")
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_ui_source_has_no_direct_queue_mutation_calls(self) -> None:
        source = _ui_source()
        forbidden = (
            ".create_job(",
            ".admit_job(",
            ".enqueue_job(",
            ".start_job(",
            ".succeed_job(",
            ".fail_job(",
            ".quarantine_job(",
            ".cancel_job(",
            ".record_artifact(",
            "INSERT INTO jobs",
            "UPDATE jobs",
            "DELETE FROM jobs",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_ui_source_has_no_network_dcc_or_env_surface(self) -> None:
        source = _ui_source().lower()
        forbidden = (
            "requests.",
            "httpx.",
            "urllib.request",
            "socket.",
            "hython",
            "houdini",
            "comfyui",
            "davinci",
            "dotenv",
            'open(".env"',
            "open('.env'",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

    def test_desktop_module_has_no_module_level_calls_except_exit_guard(self) -> None:
        source = Path("apps/sovereign_desktop.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        module_calls = []
        for node in tree.body:
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                module_calls.append(ast.unparse(node.value))
        self.assertEqual(module_calls, [])


def _ui_source() -> str:
    paths = (Path("apps/sovereign_desktop.py"), *tuple(sorted(Path("apps/ui").glob("*.py"))))
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)


if __name__ == "__main__":
    unittest.main()
