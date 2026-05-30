#!/usr/bin/env python3
"""Run a clean-clone reproducibility check and write a receipt."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Source repository path")
    parser.add_argument("--output-dir", required=True, help="Directory for the receipt and clean clone")
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    branch = _run(["git", "-C", repo.as_posix(), "branch", "--show-current"], cwd=repo).stdout.strip()
    source_head = _run(["git", "-C", repo.as_posix(), "rev-parse", "HEAD"], cwd=repo).stdout.strip()
    clone_path = output_dir / "clean_clone"
    if clone_path.exists():
        shutil.rmtree(clone_path)

    commands: list[dict[str, object]] = []
    clone_cmd = ["git", "clone", "--no-hardlinks", "--branch", branch, repo.as_posix(), clone_path.as_posix()]
    commands.append(_record(clone_cmd, cwd=output_dir))
    validation_env = dict(os.environ)
    validation_env["PYTHONDONTWRITEBYTECODE"] = "1"
    validation_env["PYTHONPATH"] = clone_path.as_posix()
    for command in (
        [sys.executable, "seos.py", "version"],
        [sys.executable, "seos.py", "status"],
        [
            sys.executable,
            "-m",
            "unittest",
            "tests.tracer_bullet.test_cli_foundation",
            "tests.tracer_bullet.test_operator_cli",
            "tests.tracer_bullet.test_landing_ready_program_v1",
        ],
        ["git", "diff", "--check"],
    ):
        commands.append(_record(command, cwd=clone_path, env=validation_env))

    clone_head = _run(["git", "-C", clone_path.as_posix(), "rev-parse", "HEAD"], cwd=clone_path).stdout.strip()
    passed = all(item["returncode"] == 0 for item in commands)
    receipt = {
        "schema": "landing_ready_clean_clone_receipt_v1",
        "created_at": _now(),
        "source_repo": repo.as_posix(),
        "source_branch": branch,
        "source_head": source_head,
        "clean_clone_path": clone_path.as_posix(),
        "clean_clone_head": clone_head,
        "environment_assumptions": [
            "python interpreter used for validation is recorded in commands",
            "no network service is required after local clone creation",
            "minimum meaningful validation covers CLI, operator task flow, and diff hygiene",
        ],
        "commands": commands,
        "passed": passed,
        "blockers": [] if passed else ["clean_clone_validation_failed"],
    }
    receipt["sha256"] = _sha256(json.dumps(receipt, sort_keys=True).encode("utf-8"))
    receipt_path = output_dir / "clean_clone_reproducibility_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(receipt_path.as_posix())
    return 0 if passed else 1


def _record(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> dict[str, object]:
    completed = subprocess.run(command, cwd=cwd, env=env, check=False, capture_output=True, text=True)
    return {
        "command": " ".join(command),
        "cwd": cwd.as_posix(),
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout.splitlines()[-40:],
        "stderr_tail": completed.stderr.splitlines()[-40:],
    }


def _run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
