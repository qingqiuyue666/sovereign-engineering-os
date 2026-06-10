#!/usr/bin/env bash
set -euo pipefail

PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path.cwd()
REPORT_JSON = REPO_ROOT / "reports" / "audits" / "independent_verification_execution_v1.json"
REPORT_MD = REPO_ROOT / "reports" / "audits" / "independent_verification_execution_v1.md"

EXPECTED_HEAD = os.environ.get(
    "INDEPENDENT_VERIFICATION_EXPECTED_HEAD",
    "2f46520b9aa107d83689b86d3314919ad4bca7b8",
)
EXPECTED_TAG_TARGET = "9a363f95b85602ffc598db463dc6181a9bbbdf3c"
RC_TAG = "v0.1.0-rc3"
FINAL_STATUS_PASS = "CODEX_RUN_INDEPENDENT_VERIFICATION_EXECUTED"

commands: list[dict[str, Any]] = []
findings: list[dict[str, Any]] = []
clone_url = ""
tag_target = "not_checked"
observed_head = "not_checked"
temp_workspace_policy = "temporary clean directory outside the working tree; absolute path intentionally omitted"


def main() -> int:
    success = False
    workspace = Path(tempfile.mkdtemp(prefix="seos-independent-verification-v1-"))
    try:
        success = execute(workspace)
        final_status = FINAL_STATUS_PASS if success else "CODEX_RUN_INDEPENDENT_VERIFICATION_FAILED"
        write_reports(final_status)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    if success:
        print("independent_verification_execute_v1: PASS")
        return 0
    print("independent_verification_execute_v1: FAIL", file=sys.stderr)
    return 1


def execute(workspace: Path) -> bool:
    global clone_url, observed_head, tag_target

    clone_url = _origin_url()
    clone_dir = workspace / "clean-clone"

    steps: list[tuple[str, list[str], Path, str, str]] = [
        (
            "git_clone",
            ["git", "clone", "--quiet", clone_url, str(clone_dir)],
            workspace,
            "git clone --quiet <repository-url> <temporary-clean-clone>",
            "temporary_workspace",
        ),
        (
            "checkout_expected_head",
            ["git", "checkout", "--quiet", EXPECTED_HEAD],
            clone_dir,
            f"git checkout --quiet {EXPECTED_HEAD}",
            "clean_clone",
        ),
        (
            "verify_starting_head",
            ["git", "rev-parse", "HEAD"],
            clone_dir,
            "git rev-parse HEAD",
            "clean_clone",
        ),
        (
            "verify_rc3_tag",
            ["git", "rev-parse", f"{RC_TAG}^{{}}"],
            clone_dir,
            f"git rev-parse '{RC_TAG}^{{}}'",
            "clean_clone",
        ),
        (
            "create_fresh_venv",
            [sys.executable, "-m", "venv", ".venv"],
            clone_dir,
            "python3 -m venv .venv",
            "clean_clone",
        ),
    ]
    for step_id, args, cwd, display_command, cwd_policy in steps:
        completed = run_required(step_id, args, cwd, display_command, cwd_policy)
        if not completed:
            return False
        if step_id == "verify_starting_head":
            observed_head = completed.stdout.strip()
            if observed_head != EXPECTED_HEAD:
                record_finding(
                    "IV-001",
                    "P1 blocker",
                    "Independent verification checkout did not match expected main HEAD.",
                    f"expected {EXPECTED_HEAD}, observed {observed_head}",
                    "verify_starting_head",
                )
                return False
        if step_id == "verify_rc3_tag":
            tag_target = completed.stdout.strip()
            if tag_target != EXPECTED_TAG_TARGET:
                record_finding(
                    "IV-002",
                    "P1 blocker",
                    "Release-candidate tag target changed during independent verification.",
                    f"expected {EXPECTED_TAG_TARGET}, observed {tag_target}",
                    "verify_rc3_tag",
                )
                return False

    venv_python = _venv_python(clone_dir)
    venv_bin = venv_python.parent
    verification_steps: list[tuple[str, list[str], str]] = [
        ("install_project", [str(venv_python), "-m", "pip", "install", "."], ".venv/bin/python -m pip install ."),
        (
            "clean_install_artifacts_after_install",
            ["bash", "-lc", "rm -rf build sovereign_engineering_os.egg-info && test -z \"$(git status --short -- build sovereign_engineering_os.egg-info)\""],
            "rm -rf build sovereign_engineering_os.egg-info && git status --short is empty for install artifacts",
        ),
        ("cli_help_seos", [str(venv_bin / "seos"), "--help"], ".venv/bin/seos --help"),
        ("cli_help_seos_local", [str(venv_bin / "seos-local"), "--help"], ".venv/bin/seos-local --help"),
        ("external_audit_packet_check", [str(venv_python), "scripts/external_audit_packet_check_v1.py"], ".venv/bin/python scripts/external_audit_packet_check_v1.py"),
        ("claim_to_evidence_check", [str(venv_python), "scripts/claim_to_evidence_check_v1.py"], ".venv/bin/python scripts/claim_to_evidence_check_v1.py"),
        ("security_control_check", [str(venv_python), "scripts/security_control_check_v1.py"], ".venv/bin/python scripts/security_control_check_v1.py"),
        ("supply_chain_check", [str(venv_python), "scripts/supply_chain_check_v1.py"], ".venv/bin/python scripts/supply_chain_check_v1.py"),
        ("secret_context_safety_check", [str(venv_python), "scripts/secret_context_safety_check_v1.py"], ".venv/bin/python scripts/secret_context_safety_check_v1.py"),
        ("release_invariant_check", [str(venv_python), "scripts/release_invariant_check_v1.py"], ".venv/bin/python scripts/release_invariant_check_v1.py"),
        ("ai_admission_check", [str(venv_python), "scripts/ai_admission_check_v1.py"], ".venv/bin/python scripts/ai_admission_check_v1.py"),
        ("dogfood_evidence_check", [str(venv_python), "scripts/dogfood_evidence_check_v1.py"], ".venv/bin/python scripts/dogfood_evidence_check_v1.py"),
        ("reliability_benchmark", [str(venv_python), "scripts/reliability_benchmark_v1.py"], ".venv/bin/python scripts/reliability_benchmark_v1.py"),
        ("schema_compatibility_check", [str(venv_python), "scripts/schema_compatibility_check_v1.py"], ".venv/bin/python scripts/schema_compatibility_check_v1.py"),
        ("observation_check", [str(venv_python), "scripts/observation_check_v1.py"], ".venv/bin/python scripts/observation_check_v1.py"),
        ("failure_path_smoke", ["bash", "scripts/failure_path_smoke_v1.sh"], "bash scripts/failure_path_smoke_v1.sh"),
        ("adversarial_smoke", [str(venv_python), "scripts/adversarial_smoke_v1.py"], ".venv/bin/python scripts/adversarial_smoke_v1.py"),
        ("make_verify", ["make", f"PYTHON={venv_python.as_posix()}", "verify"], "make PYTHON=.venv/bin/python verify"),
        (
            "clean_install_artifacts_before_ci",
            ["bash", "-lc", "rm -rf build sovereign_engineering_os.egg-info && test -z \"$(git status --short -- build sovereign_engineering_os.egg-info)\""],
            "rm -rf build sovereign_engineering_os.egg-info && git status --short is empty for install artifacts",
        ),
        ("make_ci", ["make", f"PYTHON={venv_python.as_posix()}", "ci"], "make PYTHON=.venv/bin/python ci"),
    ]
    for step_id, args, display_command in verification_steps:
        if not run_required(step_id, args, clone_dir, display_command, "clean_clone"):
            record_finding(
                f"IV-{len(findings) + 3:03d}",
                "P1 blocker",
                f"Required independent verification command failed: {step_id}",
                display_command,
                step_id,
            )
            return False
    return True


def _origin_url() -> str:
    completed = subprocess.run(
        ["git", "config", "--get", "remote.origin.url"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0 and completed.stdout.strip():
        return completed.stdout.strip()
    return "https://github.com/qqyqqyqqy666-wq/sovereign-engineering-os.git"


def _venv_python(clone_dir: Path) -> Path:
    if os.name == "nt":
        return clone_dir / ".venv" / "Scripts" / "python.exe"
    return clone_dir / ".venv" / "bin" / "python"


def run_required(
    step_id: str,
    args: list[str],
    cwd: Path,
    display_command: str,
    cwd_policy: str,
) -> subprocess.CompletedProcess[str] | None:
    print(f"RUN {step_id}: {display_command}", flush=True)
    completed = subprocess.run(
        args,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    result = "PASS" if completed.returncode == 0 else "FAIL"
    commands.append(
        {
            "id": step_id,
            "command": display_command,
            "cwd_policy": cwd_policy,
            "required": True,
            "result": result,
            "exit_code": completed.returncode,
        }
    )
    if completed.returncode != 0:
        print(f"FAIL {step_id}: exit_code={completed.returncode}", file=sys.stderr, flush=True)
        return None
    print(f"OK {step_id}", flush=True)
    return completed


def record_finding(
    finding_id: str,
    severity: str,
    title: str,
    evidence: str,
    command_id: str,
) -> None:
    findings.append(
        {
            "finding_id": finding_id,
            "source": "independent_verification",
            "severity": severity,
            "title": title,
            "evidence": evidence,
            "command_id": command_id,
            "status": "open",
            "remediation_required": True,
        }
    )


def write_reports(final_status: str) -> None:
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "independent_verification_execution_v1",
        "execution_id": "codex_run_independent_verification_v1",
        "reviewer_type": "Codex-run local independent verification",
        "human_third_party_audit": False,
        "external_signoff_confirmed": False,
        "global_recognition_claimed": False,
        "global_recognition_confirmed_by_codex": False,
        "repository": {
            "name": "qqyqqyqqy666-wq/sovereign-engineering-os",
            "origin_url": clone_url,
            "clone_strategy": "fresh clone into a temporary directory outside the working tree",
            "target_head": EXPECTED_HEAD,
            "observed_head": observed_head,
        },
        "release_candidate_tag": {
            "name": RC_TAG,
            "expected_target": EXPECTED_TAG_TARGET,
            "observed_target": tag_target,
            "moved_or_recreated_by_this_execution": False,
        },
        "environment_summary": {
            "clean_clone": True,
            "fresh_venv": True,
            "temp_workspace_policy": temp_workspace_policy,
            "temp_workspace_path_recorded": False,
            "temp_workspace_cleanup": "deleted after execution",
            "python_version": platform.python_version(),
            "platform": platform.system(),
        },
        "commands": commands,
        "findings": findings,
        "artifacts_generated": [
            "reports/audits/independent_verification_execution_v1.json",
            "reports/audits/independent_verification_execution_v1.md",
        ],
        "known_limitations": [
            "This is a Codex-run local independent verification, not a human third-party audit.",
            "The execution verifies machine-checkable repository evidence only.",
            "External human review remains required before any external recognition claim.",
            "Real-world 30-90 day operation evidence remains required for final recognition analysis.",
        ],
        "explicit_statements": [
            "This is not a human third-party external audit.",
            "External recognition is not confirmed by Codex.",
            "Global top engineer signoff is not confirmed by Codex.",
            "Human or independent external review remains required.",
        ],
        "final_status": final_status,
    }
    REPORT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_MD.write_text(render_markdown(payload), encoding="utf-8")


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Independent Verification Execution V1",
        "",
        f"Final status: {payload['final_status']}",
        "",
        "Reviewer type: Codex-run local independent verification.",
        "",
        "This is not a human third-party external audit.",
        "External recognition is not confirmed by Codex.",
        "Global top engineer signoff is not confirmed by Codex.",
        "",
        "## Scope",
        "",
        "- Repository: `qqyqqyqqy666-wq/sovereign-engineering-os`",
        f"- Target main HEAD: `{EXPECTED_HEAD}`",
        f"- Release-candidate tag: `{RC_TAG}`",
        f"- Expected tag target: `{EXPECTED_TAG_TARGET}`",
        "- Clean clone: yes",
        "- Fresh venv: yes",
        "- Temporary workspace path: intentionally omitted from the report",
        "",
        "## Commands",
        "",
        "| Command ID | Command / Procedure | Result |",
        "| --- | --- | --- |",
    ]
    for command in payload["commands"]:
        lines.append(f"| `{command['id']}` | `{command['command']}` | {command['result']} |")
    lines.extend(["", "## Findings", ""])
    if payload["findings"]:
        for finding in payload["findings"]:
            lines.append(f"- `{finding['finding_id']}` ({finding['severity']}): {finding['title']}")
    else:
        lines.append("- No independent verification findings were recorded because every required command returned exit code 0.")
    lines.extend(
        [
            "",
            "## Known Limitations",
            "",
        ]
    )
    for limitation in payload["known_limitations"]:
        lines.append(f"- {limitation}")
    lines.extend(["", "## Evidence Artifacts", ""])
    for artifact in payload["artifacts_generated"]:
        lines.append(f"- `{artifact}`")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
PY
