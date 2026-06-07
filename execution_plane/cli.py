"""CLI for SEOS Controlled Execution Plane V1."""

from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

from creative.common import load_json, write_json
from execution_plane.adapters.fake_dcc import run_fake_dcc
from execution_plane.adapters.houdini_hython import run_houdini_hython_smoke
from execution_plane.permits.builder import create_execution_permit
from execution_plane.permits.validator import ExecutionPermitValidationError


HELP_TEXT = (
    "SEOS controlled execution plane: permit-gated local worker execution, "
    "not RPA, not desktop control, not autonomous authority."
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=HELP_TEXT)
    subparsers = parser.add_subparsers(dest="command")

    permit_parser = subparsers.add_parser("permit", help="create or inspect execution permits")
    permit_subparsers = permit_parser.add_subparsers(dest="permit_command")
    create_parser = permit_subparsers.add_parser("create", help="create a digest-bound execution permit")
    create_parser.add_argument("--task-id", required=True)
    create_parser.add_argument("--approval-id", required=True)
    create_parser.add_argument("--adapter", default="fake_dcc", choices=("fake_dcc", "houdini_hython"))
    create_parser.add_argument("--action", default="smoke_generate_file")
    create_parser.add_argument("--input-root", action="append", default=[])
    create_parser.add_argument("--output-root", required=True)
    create_parser.add_argument("--permit-out", required=True)
    create_parser.add_argument("--max-runtime-seconds", type=int, default=60)
    create_parser.add_argument("--max-output-bytes", type=int, default=104_857_600)
    create_parser.add_argument("--max-files", type=int, default=100)
    create_parser.add_argument("--json", action="store_true")

    run_parser = subparsers.add_parser("run", help="run a permitted local adapter")
    run_parser.add_argument("--permit", required=True)
    run_parser.add_argument("--job")
    run_parser.add_argument("--result-out")
    run_parser.add_argument("--json", action="store_true")

    result_parser = subparsers.add_parser("result", help="show execution result envelopes")
    result_subparsers = result_parser.add_subparsers(dest="result_command")
    show_parser = result_subparsers.add_parser("show", help="show a result envelope")
    show_parser.add_argument("--path", required=True)
    show_parser.add_argument("--json", action="store_true")

    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if args.command == "permit" and args.permit_command == "create":
            return _permit_create(args)
        if args.command == "run":
            return _run(args)
        if args.command == "result" and args.result_command == "show":
            return _result_show(args)
    except ExecutionPermitValidationError as exc:
        return _emit({"ok": False, "error": "permit_validation_failed", "errors": exc.errors}, json_mode=True, code=1)
    except Exception as exc:
        return _emit({"ok": False, "error": exc.__class__.__name__, "message": str(exc)}, json_mode=True, code=1)

    parser.print_help()
    return 2


def _permit_create(args: argparse.Namespace) -> int:
    permit = create_execution_permit(
        task_id=args.task_id,
        operator_approval_id=args.approval_id,
        allowed_adapter=args.adapter,
        allowed_action=args.action,
        allowed_input_roots=args.input_root,
        allowed_output_root=args.output_root,
        max_runtime_seconds=args.max_runtime_seconds,
        max_output_bytes=args.max_output_bytes,
        max_files=args.max_files,
    )
    output_path = Path(args.permit_out)
    write_json(output_path, permit)
    payload = {"ok": True, "permit_id": permit["permit_id"], "permit_path": output_path.as_posix()}
    if args.json:
        payload["permit"] = permit
    return _emit(payload, json_mode=args.json)


def _run(args: argparse.Namespace) -> int:
    permit = load_json(Path(args.permit))
    job = load_json(Path(args.job)) if args.job else None
    adapter = permit.get("allowed_adapter")
    if adapter == "fake_dcc":
        result = run_fake_dcc(permit, job=job)
    elif adapter == "houdini_hython":
        result = run_houdini_hython_smoke(permit)
    else:
        return _emit({"ok": False, "error": "unsupported_adapter", "adapter": adapter}, json_mode=True, code=1)
    result_out = Path(args.result_out) if args.result_out else Path(str(permit["allowed_output_root"])) / "execution_result.json"
    write_json(result_out, result)
    return _emit(
        {
            "ok": result["status"] == "SUCCEEDED",
            "status": result["status"],
            "run_id": result["run_id"],
            "result_path": result_out.as_posix(),
            "result": result if args.json else None,
        },
        json_mode=args.json,
        code=0 if result["status"] == "SUCCEEDED" else 1,
    )


def _result_show(args: argparse.Namespace) -> int:
    result = load_json(Path(args.path))
    return _emit(
        {
            "ok": True,
            "run_id": result.get("run_id"),
            "status": result.get("status"),
            "adapter": result.get("adapter"),
            "output_count": len(result.get("outputs", [])),
            "result": result if args.json else None,
        },
        json_mode=args.json,
    )


def _emit(payload: dict[str, object], *, json_mode: bool, code: int | None = None) -> int:
    if not json_mode:
        payload = {key: value for key, value in payload.items() if value is not None and key != "result"}
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    if code is not None:
        return code
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

