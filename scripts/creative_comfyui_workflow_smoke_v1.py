#!/usr/bin/env python3
"""Run the SEOS local ComfyUI workflow smoke wrapper."""

from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from creative.runners.comfyui_local_runner import (  # noqa: E402
    ComfyUIHttpResponse,
    ComfyUIWorkflowRequest,
    run_comfyui_workflow_smoke,
    write_comfyui_smoke_reports,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a gated local ComfyUI workflow smoke")
    parser.add_argument("--workflow-json", default="tests/fixtures/creative/comfyui/api_workflow_fixture_v1.json")
    parser.add_argument("--output-root", default="work/creative_runs/comfyui_smoke")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8188")
    parser.add_argument("--mode", choices=("public", "local"), default="public")
    parser.add_argument("--approve-local-execution", action="store_true")
    parser.add_argument("--approval-id", default="")
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--poll-interval-seconds", type=float, default=1.0)
    parser.add_argument("--no-download-outputs", action="store_true")
    parser.add_argument("--max-output-artifacts", type=int, default=12)
    parser.add_argument("--max-artifact-bytes", type=int, default=26_214_400)
    parser.add_argument("--observed-at")
    parser.add_argument("--fixture-service-unavailable", action="store_true")
    parser.add_argument("--result-json")
    parser.add_argument("--materialization-json")
    args = parser.parse_args(argv)

    result = run_comfyui_workflow_smoke(
        ComfyUIWorkflowRequest(
            workflow_json=Path(args.workflow_json),
            output_root=Path(args.output_root),
            endpoint_url=args.endpoint,
            mode=args.mode,
            approved=bool(args.approve_local_execution),
            approval_id=args.approval_id,
            timeout_seconds=args.timeout_seconds,
            poll_interval_seconds=args.poll_interval_seconds,
            download_outputs=not args.no_download_outputs,
            max_output_artifacts=args.max_output_artifacts,
            max_artifact_bytes=args.max_artifact_bytes,
            observed_at=args.observed_at,
        ),
        transport=_fixture_service_unavailable_transport if args.fixture_service_unavailable else None,
    )
    if args.fixture_service_unavailable and isinstance(result.get("service"), dict):
        result["service"]["duration_seconds"] = 0.0
    outputs = write_comfyui_smoke_reports(
        result,
        result_json=Path(args.result_json) if args.result_json else None,
        materialization_json=Path(args.materialization_json) if args.materialization_json else None,
    )
    print(json.dumps(result | {"ok": True, "outputs": outputs}, sort_keys=True, separators=(",", ":")))
    return 0


def _fixture_service_unavailable_transport(
    method: str,
    url: str,
    body: bytes | None,
    headers: object,
    timeout_seconds: float,
    max_response_bytes: int,
) -> ComfyUIHttpResponse:
    del method, url, body, headers, timeout_seconds, max_response_bytes
    raise OSError("fixture ComfyUI service unavailable")


if __name__ == "__main__":
    raise SystemExit(main())
