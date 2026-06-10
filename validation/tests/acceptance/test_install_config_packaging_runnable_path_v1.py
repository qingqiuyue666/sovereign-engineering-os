"""Acceptance for #525 install/config/packaging runnable path."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from kernel.install_config.local_runtime_path import (
    bootstrap_local_runtime,
    default_local_runtime_config,
    reset_local_runtime,
    run_local_runtime_smoke,
    stop_local_runtime,
    validate_local_runtime_config,
)


class InstallConfigPackagingRunnablePathAcceptanceTests(unittest.TestCase):
    def test_fresh_clone_can_bootstrap_smoke_stop_and_reset_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            clone_root = Path(tempdir) / "fresh-local-clone"
            clone_root.mkdir()
            shutil.copyfile(Path.cwd() / "pyproject.toml", clone_root / "pyproject.toml")
            config = default_local_runtime_config()

            validation = validate_local_runtime_config(clone_root, config)
            bootstrap = bootstrap_local_runtime(clone_root, config, apply=True)
            smoke = run_local_runtime_smoke(clone_root, config, apply=True)
            stop = stop_local_runtime(clone_root, config, apply=True)
            reset = reset_local_runtime(clone_root, config, apply=True)

            self.assertTrue(validation.accepted)
            self.assertTrue(bootstrap.accepted)
            self.assertTrue(smoke.accepted)
            self.assertTrue(stop.accepted)
            self.assertTrue(reset.accepted)
            self.assertFalse((clone_root / ".seos-runtime").exists())
            for receipt in (bootstrap, smoke, stop, reset):
                self.assertFalse(receipt.runtime_enabled)
                self.assertFalse(receipt.network_accessed)
                self.assertFalse(receipt.subprocess_spawned)
                self.assertFalse(receipt.dependency_install_performed)
                self.assertFalse(receipt.provider_execution_performed)
                self.assertFalse(receipt.entrypoint_executed)
                self.assertEqual(receipt.failure_codes, ())
                self.assertTrue(receipt.config_hash)
                self.assertTrue(receipt.layout_hash)
                self.assertIn("python3 tools/local_runtime_setup.py bootstrap . --apply", receipt.one_command_bootstrap)


if __name__ == "__main__":
    unittest.main()
