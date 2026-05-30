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
  echo "clean_clone_observation_smoke_v1: FAIL: $*" >&2
  exit 1
}

CURRENT_BRANCH="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)"
if [[ -n "$(git -C "$REPO_ROOT" status --short)" ]]; then
  fail "source worktree is not clean"
fi

EXPECTED_HEAD="$(git -C "$REPO_ROOT" rev-parse HEAD)"
EXPECTED_TAG_SHA="$(git -C "$REPO_ROOT" rev-list -n 1 v0.1.0-rc3)"
REQUIRED_TAG_SHA="9a363f95b85602ffc598db463dc6181a9bbbdf3c"

if [[ "$EXPECTED_TAG_SHA" != "$REQUIRED_TAG_SHA" ]]; then
  fail "v0.1.0-rc3 tag mismatch: $EXPECTED_TAG_SHA"
fi

CLONE_DIR="$TMP_ROOT/clean-clone"
git clone --no-local --branch "$CURRENT_BRANCH" "$REPO_ROOT" "$CLONE_DIR" >/dev/null
git -C "$CLONE_DIR" checkout "$CURRENT_BRANCH" >/dev/null

CLONE_HEAD="$(git -C "$CLONE_DIR" rev-parse HEAD)"
if [[ "$CLONE_HEAD" != "$EXPECTED_HEAD" ]]; then
  fail "clone main HEAD mismatch: $CLONE_HEAD != $EXPECTED_HEAD"
fi

CLONE_TAG_SHA="$(git -C "$CLONE_DIR" rev-list -n 1 v0.1.0-rc3)"
if [[ "$CLONE_TAG_SHA" != "$REQUIRED_TAG_SHA" ]]; then
  fail "clone v0.1.0-rc3 tag mismatch: $CLONE_TAG_SHA"
fi

(
  cd "$CLONE_DIR"
  python3 scripts/observation_check_v1.py >/dev/null
  python3 scripts/identity_boundary_check_v1.py >/dev/null
  python3 -m apps.operator_cli.main --help >/dev/null

  WORKSPACE="$TMP_ROOT/workspace"
  TASK_ID="clean-clone-smoke-v1"
  python3 -m apps.operator_cli.main init --workspace "$WORKSPACE" >/dev/null
  python3 -m apps.operator_cli.main task create \
    --workspace "$WORKSPACE" \
    --title "clean clone smoke" \
    --objective "Validate local clean-clone governance smoke" \
    --task-id "$TASK_ID" \
    --json >/dev/null
  python3 -m apps.operator_cli.main approve "$TASK_ID" \
    --workspace "$WORKSPACE" \
    --reason "operator approved clean clone smoke" \
    --json >/dev/null
  python3 -m apps.operator_cli.main run "$TASK_ID" \
    --workspace "$WORKSPACE" \
    --dry-run \
    --json >/dev/null

  TRACE_JSON="$TMP_ROOT/evidence-trace.json"
  REPLAY_JSON="$TMP_ROOT/replay-explain.json"
  BUNDLE_JSON="$TMP_ROOT/context-bundle.json"
  ROI_JSON="$TMP_ROOT/token-roi.json"

  python3 -m apps.operator_cli.main evidence trace "$TASK_ID" \
    --workspace "$WORKSPACE" \
    --json >"$TRACE_JSON"
  python3 -m apps.operator_cli.main replay explain "$TASK_ID" \
    --workspace "$WORKSPACE" \
    --json >"$REPLAY_JSON"
  python3 -m apps.operator_cli.main ai bundle "$TASK_ID" \
    --workspace "$WORKSPACE" \
    --json >"$BUNDLE_JSON"
  python3 -m apps.operator_cli.main ai token-roi "$TASK_ID" \
    --workspace "$WORKSPACE" \
    --json >"$ROI_JSON"

  grep -q '"trace_status":"complete"' "$TRACE_JSON"
  grep -q '"replay_status":"dry_run_reconstructable"' "$REPLAY_JSON"
  grep -q '"route":"deterministic_local_first"' "$BUNDLE_JSON"
  grep -q '"deterministic_local_first"' "$ROI_JSON"

  if [[ -n "$(git status --short)" ]]; then
    fail "clone worktree is not clean after smoke"
  fi
)

echo "clean_clone_observation_smoke_v1: PASS"
