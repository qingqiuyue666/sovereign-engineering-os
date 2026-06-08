from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from creative.runners.houdini_local_runner import (
    HoudiniSmokeRequest,
    discover_hython,
    run_houdini_hython_smoke,
)

REPO = Path(__file__).resolve().parents[2]
OBSERVED_AT = "2026-06-08T00:00:00Z"


def _write_fake_hython(path: Path, body: str) -> None:
    path.write_text(
        "#!/usr/bin/env python3\n"
        "from __future__ import annotations\n"
        "import json\n"
        "import sys\n"
        "import time\n"
        "from pathlib import Path\n\n"
        f"{body}\n",
        encoding="utf-8",
    )
    path.chmod(0o700)


class HoudiniLocalRunnerV1Tests(unittest.TestCase):
    def test_discovery_honors_seos_hython_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            fake_hython = temp_dir / "fake_hython"
            _write_fake_hython(fake_hython, "raise SystemExit(0)\n")

            discovery = discover_hython(
                environ={
                    "PATH": "",
                    "SEOS_HYTHON_PATH": fake_hython.as_posix(),
                }
            )

            self.assertEqual(discovery.status, "FOUND_BUT_UNTESTED")
            self.assertEqual(discovery.source, "SEOS_HYTHON_PATH")
            self.assertEqual(Path(discovery.path), fake_hython.resolve())

    def test_env_not_found_returns_truthful_unavailable_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            result = run_houdini_hython_smoke(
                HoudiniSmokeRequest(
                    output_root=temp_dir / "out",
                    hython_executable=temp_dir / "missing_hython",
                    observed_at=OBSERVED_AT,
                )
            )

            self.assertEqual(result["status"], "ENV_NOT_FOUND")
            self.assertFalse(result["complete"])
            self.assertFalse(result["execution_attempted"])
            self.assertEqual(result["error_code"], "ENV_NOT_FOUND")
            self.assertFalse((temp_dir / "out" / "hython_smoke_output_v1.json").exists())
            self.assertEqual(result["materialization"]["status"], "blocked_resource_missing")

    def test_hython_found_requires_explicit_approval_before_process_launch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            fake_hython = temp_dir / "fake_hython"
            sentinel = temp_dir / "sentinel"
            _write_fake_hython(
                fake_hython,
                f"Path({str(sentinel)!r}).write_text('executed', encoding='utf-8')\n",
            )

            result = run_houdini_hython_smoke(
                HoudiniSmokeRequest(
                    output_root=temp_dir / "out",
                    hython_executable=fake_hython,
                    observed_at=OBSERVED_AT,
                )
            )

            self.assertEqual(result["status"], "USER_APPROVAL_REQUIRED")
            self.assertFalse(result["execution_attempted"])
            self.assertFalse(sentinel.exists())
            self.assertEqual(result["materialization"]["status"], "blocked_human_review_required")

    def test_fake_hython_success_writes_output_hash_and_materialization(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            fake_hython = temp_dir / "fake_hython"
            _write_fake_hython(
                fake_hython,
                textwrap.dedent(
                    """
                    output = Path(sys.argv[2])
                    output.parent.mkdir(parents=True, exist_ok=True)
                    output.write_text(json.dumps({
                        "kind": "houdini_hython_smoke_output_v1",
                        "hou_module_loaded": True,
                        "houdini_version": "fixture",
                    }, sort_keys=True) + "\\n", encoding="utf-8")
                    print("fake hython smoke ok")
                    raise SystemExit(0)
                    """
                ),
            )

            result = run_houdini_hython_smoke(
                HoudiniSmokeRequest(
                    output_root=temp_dir / "out",
                    hython_executable=fake_hython,
                    approved=True,
                    approval_id="approval-houdini-smoke-001",
                    observed_at=OBSERVED_AT,
                )
            )

            self.assertEqual(result["status"], "EXECUTED")
            self.assertTrue(result["complete"])
            self.assertTrue(result["execution_attempted"])
            self.assertEqual(result["error_code"], None)
            self.assertTrue(result["output"]["sha256"].startswith("sha256:"))
            self.assertEqual(result["output"]["relative_path"], "hython_smoke_output_v1.json")
            self.assertEqual(result["materialization"]["status"], "materialized_valid")
            self.assertNotIn("stdout", result["process"])
            self.assertNotIn("stderr", result["process"])

    def test_license_error_is_classified_as_license_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            fake_hython = temp_dir / "fake_hython"
            _write_fake_hython(
                fake_hython,
                "print('No licenses could be found for hython', file=sys.stderr)\nraise SystemExit(1)\n",
            )

            result = run_houdini_hython_smoke(
                HoudiniSmokeRequest(
                    output_root=temp_dir / "out",
                    hython_executable=fake_hython,
                    approved=True,
                    approval_id="approval-houdini-smoke-002",
                    observed_at=OBSERVED_AT,
                )
            )

            self.assertEqual(result["status"], "LICENSE_BLOCKED")
            self.assertEqual(result["error_code"], "LICENSE_BLOCKED")
            self.assertFalse(result["complete"])
            self.assertTrue(result["execution_attempted"])
            self.assertEqual(result["materialization"]["status"], "blocked_validation_failed")

    def test_timeout_is_classified_without_success_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            fake_hython = temp_dir / "fake_hython"
            _write_fake_hython(fake_hython, "time.sleep(3)\n")

            result = run_houdini_hython_smoke(
                HoudiniSmokeRequest(
                    output_root=temp_dir / "out",
                    hython_executable=fake_hython,
                    approved=True,
                    approval_id="approval-houdini-smoke-003",
                    timeout_seconds=0.1,
                    observed_at=OBSERVED_AT,
                )
            )

            self.assertEqual(result["status"], "LONG_TASK_BLOCKED")
            self.assertEqual(result["error_code"], "LONG_TASK_BLOCKED")
            self.assertFalse(result["complete"])
            self.assertTrue(result["process"]["timed_out"])

    def test_cli_writes_result_and_materialization_reports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            fake_hython = temp_dir / "fake_hython"
            result_json = temp_dir / "result.json"
            materialization_json = temp_dir / "materialization.json"
            _write_fake_hython(
                fake_hython,
                "Path(sys.argv[2]).write_text('{\"kind\":\"houdini_hython_smoke_output_v1\"}\\n', encoding='utf-8')\n",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "seos.py",
                    "creative",
                    "houdini-smoke",
                    "--hython",
                    fake_hython.as_posix(),
                    "--output-root",
                    (temp_dir / "out").as_posix(),
                    "--approve-local-execution",
                    "--approval-id",
                    "approval-houdini-smoke-cli",
                    "--observed-at",
                    OBSERVED_AT,
                    "--result-json",
                    result_json.as_posix(),
                    "--materialization-json",
                    materialization_json.as_posix(),
                ],
                cwd=REPO,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            payload = json.loads(completed.stdout)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["status"], "EXECUTED")
            self.assertTrue(result_json.exists())
            self.assertTrue(materialization_json.exists())
            self.assertEqual(json.loads(materialization_json.read_text(encoding="utf-8"))["status"], "materialized_valid")

    def test_optional_script_writes_unavailable_report_without_houdini(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            result_json = temp_dir / "unavailable.json"
            materialization_json = temp_dir / "unavailable_materialization.json"

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/creative_houdini_hython_smoke_v1.py",
                    "--hython",
                    (temp_dir / "missing_hython").as_posix(),
                    "--output-root",
                    (temp_dir / "out").as_posix(),
                    "--observed-at",
                    OBSERVED_AT,
                    "--result-json",
                    result_json.as_posix(),
                    "--materialization-json",
                    materialization_json.as_posix(),
                ],
                cwd=REPO,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["status"], "ENV_NOT_FOUND")
            self.assertTrue(result_json.exists())
            self.assertEqual(json.loads(result_json.read_text(encoding="utf-8"))["status"], "ENV_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
