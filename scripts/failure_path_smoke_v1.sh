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
  echo "failure_path_smoke_v1: FAIL: $*" >&2
  exit 1
}

ADVERSARIAL_JSON="$TMP_ROOT/adversarial-smoke.json"
python3 "$REPO_ROOT/scripts/adversarial_smoke_v1.py" --json >"$ADVERSARIAL_JSON"
grep -q '"status":"passed"' "$ADVERSARIAL_JSON"

NETWORK_LOG="$TMP_ROOT/network-failure.log"
if bash -c 'set -euo pipefail; false; echo PASSED' >"$NETWORK_LOG" 2>&1; then
  fail "synthetic network failure unexpectedly returned success"
fi
if grep -q "PASSED" "$NETWORK_LOG"; then
  fail "failed command printed PASSED"
fi

INTERRUPT_MARKER="$TMP_ROOT/interrupted-success.marker"
bash -c 'trap '\''rm -f "$1"; exit 130'\'' TERM INT; sleep 5; touch "$1"' interrupt-child "$INTERRUPT_MARKER" &
CHILD_PID="$!"
sleep 0.2
kill -TERM "$CHILD_PID"
if wait "$CHILD_PID"; then
  fail "interrupted child returned success"
fi
if [[ -e "$INTERRUPT_MARKER" ]]; then
  fail "interrupted child left success marker"
fi

echo "failure_path_smoke_v1: PASS"
