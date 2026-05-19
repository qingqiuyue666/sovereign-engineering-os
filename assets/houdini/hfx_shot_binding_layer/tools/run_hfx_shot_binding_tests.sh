#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../../" && pwd)"
cd "${REPO_ROOT}"

export PYTHONDONTWRITEBYTECODE=1

python3 -m unittest discover \
  -s assets/houdini/hfx_shot_binding_layer/tests \
  -p 'test_*.py'

python3 assets/houdini/hfx_shot_binding_layer/tools/hfx_shot_binding_global_seal.py
