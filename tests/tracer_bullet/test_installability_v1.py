"""Tests for Wave 2 reproducibility and installability evidence."""

from __future__ import annotations

import subprocess
import sys
import tomllib
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_SCRIPTS = (
    Path("scripts/clean_clone_observation_smoke_v1.sh"),
    Path("scripts/fresh_venv_install_smoke_v1.sh"),
    Path("scripts/package_build_smoke_v1.sh"),
    Path("scripts/installability_check_v1.py"),
)


def _read(relative_path: Path) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


class InstallabilityV1Tests(unittest.TestCase):
    def test_required_scripts_exist(self) -> None:
        for relative_path in REQUIRED_SCRIPTS:
            self.assertTrue(
                (REPO_ROOT / relative_path).exists(),
                f"missing {relative_path.as_posix()}",
            )

    def test_installability_check_script_passes(self) -> None:
        completed = subprocess.run(
            [sys.executable, "scripts/installability_check_v1.py"],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            completed.returncode,
            0,
            completed.stdout + completed.stderr,
        )
        self.assertIn("installability_check_v1: PASS", completed.stdout)

    def test_shell_scripts_are_fail_closed(self) -> None:
        for relative_path in REQUIRED_SCRIPTS[:3]:
            text = _read(relative_path)
            self.assertTrue(text.startswith("#!/usr/bin/env bash\n"))
            self.assertIn("set -euo pipefail", text)
            self.assertIn("trap cleanup EXIT INT TERM", text)
            self.assertNotIn("curl | bash", text)
            self.assertNotIn("wget | bash", text)
            self.assertNotIn("cat .env", text)

    def test_clean_clone_smoke_covers_required_flow(self) -> None:
        text = _read(Path("scripts/clean_clone_observation_smoke_v1.sh"))
        for phrase in (
            "git clone --no-local",
            "v0.1.0-rc3",
            "observation_check_v1.py",
            "identity_boundary_check_v1.py",
            "task create",
            "approve",
            "run",
            "evidence trace",
            "replay explain",
            "ai bundle",
            "ai token-roi",
            "deterministic_local_first",
            "git status --short",
        ):
            self.assertIn(phrase, text)

    def test_pyproject_entrypoints_are_declared(self) -> None:
        payload = tomllib.loads(_read(Path("pyproject.toml")))
        scripts = payload["project"]["scripts"]
        self.assertEqual(scripts["seos"], "apps.operator_cli.main:main")
        self.assertEqual(scripts["seos-local"], "kernel.personal_ai.local_mvp_cli:main")

    def test_makefile_declares_wave_2_targets(self) -> None:
        text = _read(Path("Makefile"))
        for target in (
            "installability-check:",
            "test-installability:",
            "package-build-smoke:",
            "clean-clone-smoke:",
            "install-smoke:",
            "smoke:",
            "verify:",
            "final-audit-check:",
        ):
            self.assertIn(target, text)


if __name__ == "__main__":
    unittest.main()
