#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

export PYTHONDONTWRITEBYTECODE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cleanup() {
  :
}
trap cleanup EXIT INT TERM

python3 - "$REPO_ROOT" <<'PY'
from __future__ import annotations

import importlib
import sys
import tomllib
from pathlib import Path

repo_root = Path(sys.argv[1])
payload = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))

project = payload.get("project", {})
if project.get("name") != "sovereign-engineering-os":
    raise SystemExit("project name mismatch")
if project.get("requires-python") != ">=3.13":
    raise SystemExit("requires-python mismatch")

scripts = project.get("scripts", {})
expected_scripts = {
    "seos": "apps.operator_cli.main:main",
    "seos-agent": "kernel.agent_intake.cli:main",
    "seos-knowledge": "kernel.knowledge.cli:main",
    "seos-local": "kernel.personal_ai.local_mvp_cli:main",
}
if scripts != expected_scripts:
    raise SystemExit(f"script map mismatch: {scripts!r}")

for entrypoint in expected_scripts.values():
    module_name, function_name = entrypoint.split(":", 1)
    module = importlib.import_module(module_name)
    target = getattr(module, function_name)
    if not callable(target):
        raise SystemExit(f"entrypoint is not callable: {entrypoint}")

build_system = payload.get("build-system", {})
if build_system.get("build-backend") != "setuptools.build_meta":
    raise SystemExit("build backend mismatch")
PY

(
  cd "$REPO_ROOT"
  python3 seos.py --help >/dev/null
  python3 seos.py agent --help >/dev/null
  python3 seos.py knowledge --help >/dev/null
  python3 -m apps.operator_cli.main --help >/dev/null
  python3 -m kernel.agent_intake.cli --help >/dev/null
  python3 -m kernel.knowledge.cli --help >/dev/null
)

echo "package_build_smoke_v1: PASS"
