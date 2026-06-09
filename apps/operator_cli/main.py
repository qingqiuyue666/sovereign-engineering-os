"""Local operator CLI for V12 foundation and landing-ready commands."""

from __future__ import annotations

from pathlib import Path
import json
import os
import sys

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    repo_root_text = repo_root.as_posix()
    if repo_root_text not in sys.path:
        sys.path.insert(0, repo_root_text)

from kernel.cli.commands import dispatch as legacy_dispatch
from kernel.landing_ready import (
    approve_task,
    build_context_bundle,
    build_repo_map,
    create_task,
    evidence_show,
    explain_failure,
    explain_replay,
    init_workspace,
    list_receipts,
    list_tasks,
    reject_task,
    release_check,
    run_task,
    show_receipt,
    show_task,
    status_report,
    trace_task,
    write_failure_bundle,
    write_token_roi_report,
)
from kernel.status.health_plan import ordered_health_plan
from kernel.tasks.task_contracts import create_operator_task_envelope
from kernel.tasks.task_manifest import validate_task_manifest

__all__ = ["main"]

_LEGACY_COMMANDS = {
    "explain-gates",
    "health-plan",
    "security-scan-text",
    "validate-task",
    "version",
}

_HELP_TEXT = """SEOS operator CLI

Usage:
  python3 apps/operator_cli/main.py <command> [options]
  python3 -m apps.operator_cli.main <command> [options]

Commands:
  init --workspace PATH
  status --workspace PATH [--json|--human]
  task create|list|show|validate
  approve TASK_ID --workspace PATH
  reject TASK_ID --workspace PATH
  run TASK_ID --workspace PATH --dry-run
  release check --workspace PATH
  evidence trace|show
  receipt list|show
  replay explain
  failure compress|explain
  rpc invoke TEMPLATE.json [--json]
  repair create|invoke|apply|ledger
  ai bundle|repo-map|token-roi
  creative init|scan-assets|archive-check|asset|shot|adapter|comfyui|blender|evidence|dashboard|doctor|launch-check|health|adoption-status
"""


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        return legacy_dispatch(args)
    command = args[0]
    try:
        if command in {"--help", "-h", "help"}:
            print(_HELP_TEXT)
            return 0
        if command in _LEGACY_COMMANDS:
            return legacy_dispatch(args)
        if command == "health":
            _emit({"ok": True, "dry_run_only": True, "health_plan": ["test-root-integrity", *ordered_health_plan()]})
            return 0
        if command == "init":
            return _init(args[1:])
        if command == "status":
            return _status(args[1:])
        if command == "task":
            return _task(args[1:])
        if command == "approve":
            return _approve(args[1:])
        if command == "reject":
            return _reject(args[1:])
        if command == "run" and len(args) > 1 and args[1] in {"list", "inspect", "cancel", "worker-once"}:
            return _run_queue(args[1:])
        if command == "run":
            return _run(args[1:])
        if command == "release":
            return _release(args[1:])
        if command == "evidence":
            return _evidence(args[1:])
        if command == "receipt":
            return _receipt(args[1:])
        if command == "replay":
            return _replay(args[1:])
        if command == "failure":
            return _failure(args[1:])
        if command == "rpc":
            return _rpc(args[1:])
        if command == "repair":
            return _repair(args[1:])
        if command == "ai":
            return _ai(args[1:])
        if command == "creative":
            from creative.cli import main as creative_main

            return creative_main(args[1:])
        if command == "run-ledger":
            return _run_ledger(args[1:])
        if command == "audit":
            return _audit(args[1:])
    except Exception as exc:
        _emit({"ok": False, "error": "command_failed", "detail": exc.__class__.__name__, "message": str(exc)})
        return 1
    _emit({"ok": False, "error": "unknown_command", "command": command})
    return 2


def _init(args: list[str]) -> int:
    workspace = Path(_option(args, "--workspace", "."))
    payload = init_workspace(workspace)
    return _output(payload, _json_requested(args), _format_init)


def _status(args: list[str]) -> int:
    workspace = Path(_option(args, "--workspace", "."))
    payload = status_report(workspace, Path(os.getcwd()))
    return _output(payload, not _human_requested(args), _format_status)


def _task(args: list[str]) -> int:
    if not args:
        _emit({"ok": False, "error": "task_subcommand_required"})
        return 2
    subcommand = args[0]
    rest = args[1:]
    if subcommand == "validate":
        if len(rest) != 1:
            _emit({"ok": False, "error": "task_validate_requires_path"})
            return 2
        try:
            payload = json.loads(Path(rest[0]).read_text(encoding="utf-8"))
        except Exception as exc:
            _emit({"ok": False, "error": "task_file_unreadable_or_invalid_json", "detail": exc.__class__.__name__})
            return 2
        result = validate_task_manifest(payload)
        _emit({"ok": result.accepted, "task_id": result.manifest.get("task_id"), "failures": list(result.failures)})
        return 0 if result.accepted else 1
    if subcommand == "create":
        if rest != ["--dry-run"]:
            workspace = Path(_option(rest, "--workspace", "."))
            title = _option(rest, "--title")
            objective = _option(rest, "--objective")
            if not title or not objective:
                _emit({"ok": False, "error": "task_create_requires_title_and_objective"})
                return 2
            payload = create_task(
                workspace,
                title=title,
                objective=objective,
                task_id=_option(rest, "--task-id") or None,
                task_type=_option(rest, "--type", "engineering_task"),
                source_refs=_options(rest, "--source"),
            )
            return _output(payload, _json_requested(rest), _format_task_created)
        payload = {
            "objective": "operator cli dry run",
            "requested_capabilities": ["local_validation"],
            "classification": "PUBLIC",
            "policy_version": "v12",
            "code_version": "operator-cli",
            "descriptor": {"descriptor_type": "text", "content_digest": "sha256:operator-cli-dry-run"},
        }
        result = create_operator_task_envelope(payload)
        _emit({"ok": result.accepted, "dry_run": True, "task_id": result.envelope.get("task_id"), "failures": list(result.failures)})
        return 0 if result.accepted else 1
    if subcommand == "list":
        workspace = Path(_option(rest, "--workspace", "."))
        payload = list_tasks(workspace)
        return _output(payload, _json_requested(rest), _format_task_list)
    if subcommand == "show":
        workspace = Path(_option(rest, "--workspace", "."))
        task_id = _positional(rest, skip_values_for={"--workspace"})
        if not task_id:
            _emit({"ok": False, "error": "task_show_requires_task_id"})
            return 2
        payload = show_task(workspace, task_id)
        return _output(payload, _json_requested(rest), _format_task_show)
    _emit({"ok": False, "error": "unknown_task_subcommand", "subcommand": subcommand})
    return 2


def _approve(args: list[str]) -> int:
    workspace = Path(_option(args, "--workspace", "."))
    task_id = _positional(args, skip_values_for={"--workspace", "--reason"})
    if not task_id:
        _emit({"ok": False, "error": "approve_requires_task_id"})
        return 2
    payload = approve_task(workspace, task_id, reason=_option(args, "--reason", "operator_approved"))
    return _output(payload, _json_requested(args), _format_receipt_result)


def _reject(args: list[str]) -> int:
    workspace = Path(_option(args, "--workspace", "."))
    task_id = _positional(args, skip_values_for={"--workspace", "--reason"})
    if not task_id:
        _emit({"ok": False, "error": "reject_requires_task_id"})
        return 2
    payload = reject_task(workspace, task_id, reason=_option(args, "--reason", "operator_rejected"))
    return _output(payload, _json_requested(args), _format_receipt_result)


def _run(args: list[str]) -> int:
    workspace = Path(_option(args, "--workspace", "."))
    task_id = _positional(args, skip_values_for={"--workspace", "--command"})
    if not task_id:
        _emit({"ok": False, "error": "run_requires_task_id"})
        return 2
    payload = run_task(
        workspace,
        task_id,
        dry_run="--dry-run" in args,
        command=_option(args, "--command", "dry-run"),
    )
    return _output(payload, _json_requested(args), _format_receipt_result)


def _release(args: list[str]) -> int:
    if not args or args[0] != "check":
        _emit({"ok": False, "error": "release_check_required"})
        return 2
    rest = args[1:]
    workspace = Path(_option(rest, "--workspace", "."))
    payload = release_check(workspace, Path(os.getcwd()))
    return _output(payload, _json_requested(rest), _format_release_check)


def _evidence(args: list[str]) -> int:
    if not args:
        _emit({"ok": False, "error": "evidence_subcommand_required"})
        return 2
    subcommand = args[0]
    rest = args[1:]
    workspace = Path(_option(rest, "--workspace", "."))
    if subcommand == "trace":
        task_id = _positional(rest, skip_values_for={"--workspace"})
        if not task_id:
            _emit({"ok": False, "error": "evidence_trace_requires_task_id"})
            return 2
        payload = trace_task(workspace, task_id)
        return _output(payload, _json_requested(rest), _format_trace)
    if subcommand == "show":
        evidence_ref = _positional(rest, skip_values_for={"--workspace"})
        if not evidence_ref:
            _emit({"ok": False, "error": "evidence_show_requires_ref"})
            return 2
        payload = evidence_show(workspace, evidence_ref)
        return _output(payload, _json_requested(rest), _format_evidence_show)
    _emit({"ok": False, "error": "unknown_evidence_subcommand", "subcommand": subcommand})
    return 2


def _receipt(args: list[str]) -> int:
    if not args:
        _emit({"ok": False, "error": "receipt_subcommand_required"})
        return 2
    subcommand = args[0]
    rest = args[1:]
    workspace = Path(_option(rest, "--workspace", "."))
    if subcommand == "show":
        ref = _positional(rest, skip_values_for={"--workspace"}) or "latest"
        payload = show_receipt(workspace, ref)
        return _output(payload, _json_requested(rest), _format_receipt_show)
    if subcommand == "list":
        payload = list_receipts(workspace)
        return _output(payload, _json_requested(rest), _format_receipt_list)
    _emit({"ok": False, "error": "unknown_receipt_subcommand", "subcommand": subcommand})
    return 2


def _replay(args: list[str]) -> int:
    if not args or args[0] != "explain":
        _emit({"ok": False, "error": "replay_explain_required"})
        return 2
    rest = args[1:]
    workspace = Path(_option(rest, "--workspace", "."))
    task_id = _positional(rest, skip_values_for={"--workspace"})
    if not task_id:
        _emit({"ok": False, "error": "replay_explain_requires_task_id"})
        return 2
    payload = explain_replay(workspace, task_id)
    return _output(payload, _json_requested(rest), _format_replay)


def _failure(args: list[str]) -> int:
    if not args:
        _emit({"ok": False, "error": "failure_subcommand_required"})
        return 2
    subcommand = args[0]
    rest = args[1:]
    workspace = Path(_option(rest, "--workspace", "."))
    if subcommand == "explain":
        ref = _positional(rest, skip_values_for={"--workspace"}) or "latest"
        payload = explain_failure(workspace, ref)
        return _output(payload, _json_requested(rest), _format_failure)
    if subcommand == "compress":
        command = _option(rest, "--command", "unknown")
        exit_code = int(_option(rest, "--exit-code", "1"))
        log_text = _option(rest, "--log", "")
        payload = write_failure_bundle(workspace, command=command, exit_code=exit_code, log_text=log_text)
        return _output(payload, _json_requested(rest), _format_failure_written)
    _emit({"ok": False, "error": "unknown_failure_subcommand", "subcommand": subcommand})
    return 2


def _ai(args: list[str]) -> int:
    if not args:
        _emit({"ok": False, "error": "ai_subcommand_required"})
        return 2
    subcommand = args[0]
    rest = args[1:]
    workspace = Path(_option(rest, "--workspace", "."))
    if subcommand == "bundle":
        task_id = _positional(rest, skip_values_for={"--workspace", "--budget", "--source"})
        if not task_id:
            _emit({"ok": False, "error": "ai_bundle_requires_task_id"})
            return 2
        payload = build_context_bundle(
            workspace,
            Path(os.getcwd()),
            task_id,
            source_paths=_options(rest, "--source"),
            budget_tokens=int(_option(rest, "--budget", "4000")),
        )
        return _output(payload, _json_requested(rest), _format_ai_bundle)
    if subcommand == "repo-map":
        payload = build_repo_map(Path(os.getcwd()), workspace)
        return _output(payload, _json_requested(rest), _format_repo_map)
    if subcommand == "token-roi":
        payload = write_token_roi_report(workspace)
        return _output(payload, _json_requested(rest), _format_token_roi)
    _emit({"ok": False, "error": "unknown_ai_subcommand", "subcommand": subcommand})
    return 2


def _rpc(args: list[str]) -> int:
    if not args or args[0] not in {"invoke", "enqueue"}:
        _emit({"ok": False, "error": "rpc_invoke_required"})
        return 2
    path = _positional(args[1:], skip_values_for=set())
    if not path:
        _emit({"ok": False, "error": "rpc_invoke_requires_path"})
        return 2
    if args[0] == "enqueue":
        from execution_plane.runtime.run_queue import FileRunQueue

        run = FileRunQueue().enqueue_rpc_template(Path(path))
        _emit({"ok": True, "run_id": run["run_id"], "status": run["status"], "run": run})
        return 0
    from execution_plane.rpc_gateway import invoke_rpc_file

    response = invoke_rpc_file(Path(path))
    ok = "error" not in response
    payload = {"ok": ok, "response": response}
    if _json_requested(args):
        _emit(payload)
    else:
        result = response.get("result", {}) if isinstance(response.get("result"), dict) else {}
        print(f"RPC invoke: {result.get('terminal_status', 'UNKNOWN')}")
    return 0 if ok else 1


def _run_queue(args: list[str]) -> int:
    from execution_plane.runtime.run_queue import FileRunQueue

    queue = FileRunQueue()
    subcommand = args[0]
    if subcommand == "list":
        _emit({"ok": True, "runs": queue.list_runs()})
        return 0
    if subcommand == "inspect":
        run_id = _positional(args[1:], skip_values_for=set())
        if not run_id:
            _emit({"ok": False, "error": "run_inspect_requires_run_id"})
            return 2
        try:
            _emit({"ok": True, "run": queue.inspect(run_id)})
            return 0
        except KeyError:
            _emit({"ok": False, "error": "run_not_found", "run_id": run_id})
            return 1
    if subcommand == "cancel":
        run_id = _positional(args[1:], skip_values_for=set())
        if not run_id:
            _emit({"ok": False, "error": "run_cancel_requires_run_id"})
            return 2
        try:
            run = queue.cancel(run_id)
            _emit({"ok": True, "run_id": run_id, "status": run["status"], "run": run})
            return 0
        except KeyError:
            _emit({"ok": False, "error": "run_not_found", "run_id": run_id})
            return 1
    if subcommand == "worker-once":
        run = queue.process_next()
        _emit({"ok": True, "run": run})
        return 0
    _emit({"ok": False, "error": "unknown_run_subcommand", "subcommand": subcommand})
    return 2


def _repair(args: list[str]) -> int:
    if not args:
        _emit({"ok": False, "error": "repair_subcommand_required"})
        return 2
    subcommand = args[0]
    rest = args[1:]
    output_root = _option(rest, "--output-root", "work/repair_jobs")
    if subcommand == "create":
        from execution_plane.repair.writer import create_patch_repair_job

        bundle_path = _positional(rest, skip_values_for={"--output-root"})
        if not bundle_path:
            _emit({"ok": False, "error": "repair_create_requires_failure_bundle"})
            return 2
        payload = create_patch_repair_job(bundle_path, output_root=output_root)
        _emit(payload)
        return 0 if payload.get("ok") else 1
    if subcommand == "invoke":
        from execution_plane.repair.local_model_bridge import invoke_local_patch_tool

        job_path = _positional(rest, skip_values_for={"--output-root"})
        if not job_path:
            _emit({"ok": False, "error": "repair_invoke_requires_job_path"})
            return 2
        payload = invoke_local_patch_tool(job_path, output_root=output_root)
        _emit(payload)
        return 0 if payload.get("ok") else 1
    if subcommand == "apply":
        from execution_plane.repair.patch_apply import apply_patch_for_job

        positionals = [item for item in rest if not item.startswith("--") and item not in {"--json"}]
        if len(positionals) < 2:
            _emit({"ok": False, "error": "repair_apply_requires_job_and_patch"})
            return 2
        payload = apply_patch_for_job(positionals[0], positionals[1], output_root=output_root)
        _emit(payload)
        return 0 if payload.get("ok") else 1
    if subcommand == "ledger":
        from execution_plane.repair.repair_ledger import read_repair_ledger

        _emit({"ok": True, "events": read_repair_ledger(output_root)})
        return 0
    _emit({"ok": False, "error": "unknown_repair_subcommand", "subcommand": subcommand})
    return 2


def _run_ledger(args: list[str]) -> int:
    if args != ["create", "--dry-run"]:
        _emit({"ok": False, "error": "run_ledger_create_is_dry_run_only"})
        return 2
    _emit(
        {
            "ok": True,
            "dry_run": True,
            "ledger_write_performed": False,
            "network_accessed": False,
            "secret_value_read": False,
            "ai_provider_call_performed": False,
            "sqlite_mutation_performed": False,
            "production_autonomy_enabled": False,
        }
    )
    return 0


def _audit(args: list[str]) -> int:
    if args != ["summary"]:
        _emit({"ok": False, "error": "audit_summary_required"})
        return 2
    _emit(
        {
            "ok": True,
            "summary_type": "operator_cli_audit_summary_v1",
            "dry_run_only": True,
            "forbidden_runtime_surfaces_absent": True,
        }
    )
    return 0


def _emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))


def _output(payload: dict[str, object], as_json: bool, formatter) -> int:
    if as_json:
        _emit(payload)
    else:
        print(formatter(payload))
    return 0 if payload.get("ok") else 1


def _option(args: list[str], name: str, default: str = "") -> str:
    if name not in args:
        return default
    index = args.index(name)
    if index + 1 >= len(args):
        return default
    return args[index + 1]


def _options(args: list[str], name: str) -> list[str]:
    values: list[str] = []
    for index, item in enumerate(args):
        if item == name and index + 1 < len(args):
            values.append(args[index + 1])
    return values


def _positional(args: list[str], *, skip_values_for: set[str]) -> str:
    skip_next = False
    for item in args:
        if skip_next:
            skip_next = False
            continue
        if item in {"--json", "--human", "--dry-run"}:
            continue
        if item in skip_values_for:
            skip_next = True
            continue
        if item.startswith("--"):
            continue
        return item
    return ""


def _json_requested(args: list[str]) -> bool:
    return "--json" in args


def _human_requested(args: list[str]) -> bool:
    return "--human" in args


def _format_init(payload: dict[str, object]) -> str:
    return f"SEOS workspace ready: {payload.get('workspace')}\nNext: {payload.get('next_steps', [''])[0]}"


def _format_status(payload: dict[str, object]) -> str:
    git = payload.get("git", {})
    release = payload.get("release_readiness", {})
    blockers = payload.get("known_blockers", [])
    return "\n".join(
        [
            f"SEOS status: {payload.get('status')}",
            f"Workspace initialized: {payload.get('workspace_initialized')}",
            f"HEAD: {git.get('head')}",
            f"Dirty: {git.get('dirty')}",
            f"Release verdict: {release.get('verdict')}",
            "Known blockers: " + (", ".join(str(item) for item in blockers) if blockers else "none"),
        ]
    )


def _format_task_created(payload: dict[str, object]) -> str:
    task = payload.get("task", {})
    return f"Task {task.get('task_id')} ready with status {task.get('status')}"


def _format_task_list(payload: dict[str, object]) -> str:
    tasks = payload.get("tasks", [])
    if not tasks:
        return "No tasks found"
    return "\n".join(f"{task.get('task_id')} {task.get('status')} {task.get('title')}" for task in tasks)


def _format_task_show(payload: dict[str, object]) -> str:
    task = payload.get("task", {})
    return "\n".join(
        [
            f"Task: {task.get('task_id')}",
            f"Title: {task.get('title')}",
            f"Status: {task.get('status')}",
            f"Approval required: {task.get('approval_required')}",
        ]
    )


def _format_receipt_result(payload: dict[str, object]) -> str:
    receipt = payload.get("receipt", {})
    return f"Receipt {receipt.get('receipt_type')} for {receipt.get('task_id')}: {receipt.get('result', receipt.get('approved'))}"


def _format_release_check(payload: dict[str, object]) -> str:
    blockers = payload.get("blockers", [])
    return "\n".join(
        [
            f"Release verdict: {payload.get('verdict')}",
            f"Release ready: {payload.get('release_ready')}",
            "Blockers: " + (", ".join(str(item) for item in blockers) if blockers else "none"),
        ]
    )


def _format_trace(payload: dict[str, object]) -> str:
    task = payload.get("task", {})
    receipts = payload.get("receipts", [])
    missing = payload.get("missing_evidence", [])
    return "\n".join(
        [
            f"Trace for task {task.get('task_id')}: {payload.get('trace_status')}",
            "Receipts: " + ", ".join(str(item.get("receipt", {}).get("receipt_type")) for item in receipts),
            "Missing: " + (", ".join(str(item) for item in missing) if missing else "none"),
        ]
    )


def _format_evidence_show(payload: dict[str, object]) -> str:
    return f"Evidence {payload.get('path')} sha256={payload.get('sha256')} size={payload.get('size_bytes')}"


def _format_receipt_show(payload: dict[str, object]) -> str:
    receipt = payload.get("receipt", {})
    return f"Receipt {receipt.get('receipt_type')} task={receipt.get('task_id')} digest={receipt.get('digest')}"


def _format_receipt_list(payload: dict[str, object]) -> str:
    receipts = payload.get("receipts", [])
    if not receipts:
        return "No receipts found"
    return "\n".join(f"{item.get('created_at')} {item.get('receipt_type')} {item.get('task_id')}" for item in receipts)


def _format_replay(payload: dict[str, object]) -> str:
    return f"Replay {payload.get('replay_status')} for {payload.get('task_id')}: can_reconstruct={payload.get('can_reconstruct')}"


def _format_failure(payload: dict[str, object]) -> str:
    return f"Failure command={payload.get('command')} exit={payload.get('exit_code')} symptom={payload.get('root_symptom')}"


def _format_failure_written(payload: dict[str, object]) -> str:
    bundle = payload.get("failure_bundle", {})
    return f"Failure bundle written: {bundle.get('digest')}"


def _format_ai_bundle(payload: dict[str, object]) -> str:
    bundle = payload.get("context_bundle", {})
    return f"AI context bundle {bundle.get('budget_decision')} estimate={bundle.get('estimated_input_tokens')}"


def _format_repo_map(payload: dict[str, object]) -> str:
    repo_map = payload.get("repo_map", {})
    return f"Repo map indexed {repo_map.get('file_count')} files digest={repo_map.get('digest')}"


def _format_token_roi(payload: dict[str, object]) -> str:
    report = payload.get("token_roi_report", {})
    return f"Token ROI bundles={report.get('bundle_count')} estimated_input={report.get('total_estimated_input_tokens')}"


if __name__ == "__main__":
    raise SystemExit(main())
