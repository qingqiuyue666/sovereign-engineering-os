#!/usr/bin/env python3
"""Optional local Houdini/hython smoke runner."""

from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if REPO_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, REPO_ROOT.as_posix())

from creative.runners.houdini_local_runner import (
    HoudiniSmokeRequest,
    run_houdini_hython_smoke,
    write_houdini_smoke_reports,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run or truthfully skip a local hython smoke.")
    parser.add_argument("--output-root", default="work/creative_runs/houdini_smoke")
    parser.add_argument("--hython", default="")
    parser.add_argument("--mode", default="public", choices=("public", "local"))
    parser.add_argument("--approve-local-execution", action="store_true")
    parser.add_argument("--approval-id", default="")
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--observed-at", default="")
    parser.add_argument("--result-json", default="")
    parser.add_argument("--materialization-json", default="")
    args = parser.parse_args(argv)

    result = run_houdini_hython_smoke(
        HoudiniSmokeRequest(
            output_root=args.output_root,
            hython_executable=args.hython or None,
            mode=args.mode,
            approved=args.approve_local_execution,
            approval_id=args.approval_id,
            timeout_seconds=args.timeout_seconds,
            observed_at=args.observed_at or None,
        )
    )
    outputs = write_houdini_smoke_reports(
        result,
        result_json=Path(args.result_json) if args.result_json else None,
        materialization_json=Path(args.materialization_json) if args.materialization_json else None,
    )
    print(json.dumps(result | {"ok": True, "outputs": outputs}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
