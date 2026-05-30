#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

export PYTHONDONTWRITEBYTECODE=1

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_ROOT="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_ROOT"
}
trap cleanup EXIT INT TERM

fail() {
  echo "fresh_venv_install_smoke_v1: FAIL: $*" >&2
  exit 1
}

if [[ -n "$(git -C "$REPO_ROOT" status --short)" ]]; then
  fail "source worktree is not clean"
fi

VENV_DIR="$TMP_ROOT/venv"
python3 -m venv --system-site-packages "$VENV_DIR"
PYTHON_BIN="$VENV_DIR/bin/python"
SEOS_BIN="$VENV_DIR/bin/seos"

"$PYTHON_BIN" -m pip install --no-index --no-build-isolation --no-deps -e "$REPO_ROOT" >/dev/null

"$SEOS_BIN" --help >/dev/null
"$PYTHON_BIN" -m apps.operator_cli.main --help >/dev/null

WORKSPACE="$TMP_ROOT/workspace"
TASK_ID="fresh-venv-smoke-v1"
"$SEOS_BIN" init --workspace "$WORKSPACE" >/dev/null
"$SEOS_BIN" task create \
  --workspace "$WORKSPACE" \
  --title "fresh venv smoke" \
  --objective "Validate editable install CLI smoke" \
  --task-id "$TASK_ID" \
  --json >/dev/null
"$SEOS_BIN" approve "$TASK_ID" \
  --workspace "$WORKSPACE" \
  --reason "operator approved fresh venv smoke" \
  --json >/dev/null
"$SEOS_BIN" run "$TASK_ID" \
  --workspace "$WORKSPACE" \
  --dry-run \
  --json >/dev/null
"$SEOS_BIN" evidence trace "$TASK_ID" \
  --workspace "$WORKSPACE" \
  --json >"$TMP_ROOT/evidence-trace.json"

grep -q '"trace_status":"complete"' "$TMP_ROOT/evidence-trace.json"

echo "fresh_venv_install_smoke_v1: PASS"
