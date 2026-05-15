"""Manual CLI for the model-provider live-smoke path.

This CLI is disabled by default and requires explicit flags plus environment
flags before it can call the explicit OpenAI transport. Normal tests exercise
only denial and injected-transport paths.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from kernel.personal_ai.adapters.model_provider_disabled_live_smoke_runner import (
    run_model_provider_disabled_live_smoke,
)
from kernel.personal_ai.adapters.openai_explicit_transport import (
    run_openai_explicit_transport,
    stdlib_openai_responses_transport,
)
from kernel.personal_ai.io_utils import write_json_atomically

__all__ = ["main", "run_manual_model_provider_live_smoke"]


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        payload = run_manual_model_provider_live_smoke(
            plan_path=Path(args.plan_path),
            output_dir=Path(args.output_dir),
            provider=args.provider,
            allow_live_smoke=_parse_exact_true(
                args.allow_live_smoke, "--allow-live-smoke"
            ),
            allow_network=_parse_exact_true(args.allow_network, "--allow-network"),
            confirm_manual_live_smoke=_parse_exact_true(
                args.confirm_manual_live_smoke,
                "--confirm-manual-live-smoke",
            ),
            use_stdlib_openai_transport=_parse_exact_true(
                args.use_stdlib_openai_transport,
                "--use-stdlib-openai-transport",
            ),
            output_payload_path=_optional_path(args.output_payload_path),
        )
    except ValueError as error:
        payload = {
            "complete": False,
            "status": "failed_closed",
            "error_type": error.__class__.__name__,
            "error_message": str(error),
            "required_human_approval": True,
        }
        print(_to_compact_json(payload))
        return 1
    print(_to_compact_json(payload))
    return 0 if payload["complete"] else 1


def run_manual_model_provider_live_smoke(
    *,
    plan_path: Path,
    output_dir: Path,
    provider: str,
    allow_live_smoke: bool,
    allow_network: bool,
    confirm_manual_live_smoke: bool,
    use_stdlib_openai_transport: bool,
    output_payload_path: Path | None = None,
) -> dict[str, object]:
    if provider != "openai":
        raise ValueError("provider must be openai")
    if allow_live_smoke is not True:
        raise ValueError("--allow-live-smoke must be exactly true")
    if allow_network is not True:
        raise ValueError("--allow-network must be exactly true")
    if confirm_manual_live_smoke is not True:
        raise ValueError("--confirm-manual-live-smoke must be exactly true")
    if use_stdlib_openai_transport is not True:
        raise ValueError("--use-stdlib-openai-transport must be exactly true")
    output_path = Path(output_dir)
    if not output_path.exists() or not output_path.is_dir():
        raise ValueError("output_dir is missing")

    transport_output_dir = output_path / "openai_explicit_transport"
    if transport_output_dir.exists():
        raise ValueError("openai transport output dir already exists")
    transport_output_dir.mkdir()

    def live_transport(request: dict[str, object]) -> dict[str, object]:
        transport_result = run_openai_explicit_transport(
            request,
            transport_output_dir,
            allow_network=True,
            http_transport=stdlib_openai_responses_transport,
        )
        if transport_result.result_path is None:
            raise ValueError("openai explicit transport failed closed")
        return {"status": "ok", "provider_id": "openai"}

    result = run_model_provider_disabled_live_smoke(
        Path(plan_path),
        output_path,
        allow_live_smoke=True,
        live_transport=live_transport,
    )
    payload = {
        "complete": result.status == "completed_via_explicit_transport",
        "status": result.status,
        "provider": provider,
        "plan_path": Path(plan_path).as_posix(),
        "output_dir": output_path.as_posix(),
        "runner_result_path": None
        if result.result_path is None
        else result.result_path.as_posix(),
        "runner_failure_path": None
        if result.failure_path is None
        else result.failure_path.as_posix(),
        "transport_output_dir": transport_output_dir.as_posix(),
        "live_provider_called": result.live_provider_called,
        "network_used_by_runner": result.network_used_by_runner,
        "api_key_value_persisted": result.api_key_value_persisted,
        "api_key_value_logged": result.api_key_value_logged,
        "raw_provider_response_persisted": False,
        "tool_calls_allowed": False,
        "file_edits_allowed": False,
        "required_human_approval": True,
    }
    if output_payload_path is not None:
        if output_payload_path.exists():
            raise ValueError("output_payload_path already exists")
        if not output_payload_path.parent.exists() or not output_payload_path.parent.is_dir():
            raise ValueError("output_payload_path parent is missing")
        write_json_atomically(output_payload_path, payload)
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run manually authorized model-provider live smoke.",
    )
    parser.add_argument("--plan-path", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--provider", required=True, choices=("openai",))
    parser.add_argument("--allow-live-smoke", required=True)
    parser.add_argument("--allow-network", required=True)
    parser.add_argument("--confirm-manual-live-smoke", required=True)
    parser.add_argument("--use-stdlib-openai-transport", required=True)
    parser.add_argument("--output-payload-path")
    return parser


def _parse_exact_true(value: str, flag_name: str) -> bool:
    if value != "true":
        raise ValueError(flag_name + " must be exactly true")
    return True


def _optional_path(value: str | None) -> Path | None:
    if value is None:
        return None
    return Path(value)


def _to_compact_json(payload: dict[str, object]) -> str:
    import json

    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
