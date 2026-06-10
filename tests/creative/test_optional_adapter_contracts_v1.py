from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from creative.adapters.optional_contracts import (
    OPTIONAL_ADAPTERS,
    build_optional_adapter_contracts,
)

REPO = Path(__file__).resolve().parents[2]
DOCTOR_FIXTURE = REPO / "tests/fixtures/creative/software_discovery/local_tool_health_doctor_fixture_v1.json"


class OptionalAdapterContractsV1Tests(unittest.TestCase):
    def test_report_covers_all_optional_adapters_without_execution_claims(self) -> None:
        doctor = json.loads(DOCTOR_FIXTURE.read_text(encoding="utf-8"))
        report = build_optional_adapter_contracts(doctor, mode="public")

        self.assertTrue(report["ok"])
        self.assertFalse(report["dcc_or_ai_tools_launched"])
        self.assertFalse(report["default_ci_requires_proprietary_tools"])
        adapters = {item["adapter"]: item for item in report["adapters"]}
        self.assertEqual(tuple(adapters), OPTIONAL_ADAPTERS)
        self.assertEqual(report["summary"]["adapter_count"], 5)
        self.assertEqual(report["summary"]["execution_supported_count"], 0)
        for item in adapters.values():
            self.assertFalse(item["supports_execute"])
            self.assertEqual(item["execution_support"], "CONTRACT_ONLY")
            self.assertIn("launch_dcc_application", item["disallowed_actions"])
            self.assertIn("claim_live_execution_without_runner_evidence", item["disallowed_actions"])
            self.assertTrue(item["existing_artifacts"])

    def test_report_uses_discovery_status_and_sanitizes_paths(self) -> None:
        doctor = json.loads(DOCTOR_FIXTURE.read_text(encoding="utf-8"))
        report = build_optional_adapter_contracts(doctor, mode="public")
        adapters = {item["adapter"]: item for item in report["adapters"]}

        self.assertEqual(adapters["blender"]["contract_status"], "READY_FOR_MANUAL_DRY_RUN")
        self.assertEqual(adapters["blender"]["discovery"]["configured_path"], "<local-path:Blender.app>")
        self.assertEqual(adapters["after_effects"]["contract_status"], "CONFIG_REQUIRED")
        self.assertEqual(adapters["davinci"]["contract_status"], "CONFIG_REQUIRED")
        self.assertEqual(adapters["unreal"]["contract_status"], "CONFIG_REQUIRED")
        self.assertEqual(adapters["zbrush"]["contract_status"], "ENV_NOT_FOUND")

    def test_cli_writes_json_and_markdown_contract_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            output_json = temp_dir / "optional_adapter_contracts.json"
            output_md = temp_dir / "optional_adapter_contracts.md"

            completed = subprocess.run(
                [
                    sys.executable,
                    "seos.py",
                    "creative",
                    "optional-adapter-contracts",
                    "--mode",
                    "public",
                    "--doctor-json",
                    DOCTOR_FIXTURE.as_posix(),
                    "--output-json",
                    output_json.as_posix(),
                    "--output-md",
                    output_md.as_posix(),
                ],
                cwd=REPO,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["kind"], "optional_adapter_contracts_v1")
            self.assertTrue(output_json.exists())
            self.assertTrue(output_md.exists())
            markdown = output_md.read_text(encoding="utf-8")
            self.assertIn("SEOS Optional Adapter Contracts V1", markdown)
            self.assertIn("Future runners require separate approval-gated slices", markdown)

    def test_adapter_contracts_alias_matches_direct_command(self) -> None:
        direct = subprocess.run(
            [
                sys.executable,
                "seos.py",
                "creative",
                "optional-adapter-contracts",
                "--doctor-json",
                DOCTOR_FIXTURE.as_posix(),
            ],
            cwd=REPO,
            check=False,
            capture_output=True,
            text=True,
        )
        alias = subprocess.run(
            [
                sys.executable,
                "seos.py",
                "creative",
                "adapter",
                "contracts",
                "--doctor-json",
                DOCTOR_FIXTURE.as_posix(),
            ],
            cwd=REPO,
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(direct.returncode, 0, direct.stderr + direct.stdout)
        self.assertEqual(alias.returncode, 0, alias.stderr + alias.stdout)
        self.assertEqual(json.loads(direct.stdout)["summary"], json.loads(alias.stdout)["summary"])


if __name__ == "__main__":
    unittest.main()
