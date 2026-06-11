"""CLI for SEOS knowledge and control-vault operations."""

from __future__ import annotations

from pathlib import Path
import json
import sys

from kernel.knowledge.graph import write_workspace_graph
from kernel.knowledge.vault import export_task_to_vault, export_workspace_to_vault, init_control_vault
from kernel.knowledge.vault_scanner import scan_control_vault

__all__ = ["main"]

_HELP = """SEOS knowledge CLI

Usage:
  python3 -m kernel.knowledge.cli init --vault PATH [--profile obsidian]
  python3 -m kernel.knowledge.cli export-workspace --workspace PATH --vault PATH [--profile obsidian] [--private]
  python3 -m kernel.knowledge.cli export-task TASK_ID --workspace PATH --vault PATH [--profile obsidian] [--private]
  python3 -m kernel.knowledge.cli graph build --workspace PATH --output PATH [--private]
  python3 -m kernel.knowledge.cli scan --vault PATH [--private] [--output-json PATH]

Authority boundary:
  Knowledge artifacts are proposal/mirror/receipt summaries only. They do not
  approve work, create permits, execute local tools, or replace SEOS evidence.
"""


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"--help", "-h", "help"}:
        print(_HELP)
        return 0
    command = args[0]
    rest = args[1:]
    try:
        if command == "init":
            return _init(rest)
        if command == "export-workspace":
            return _export_workspace(rest)
        if command == "export-task":
            return _export_task(rest)
        if command == "graph":
            return _graph(rest)
        if command == "scan":
            return _scan(rest)
    except Exception as exc:
        _emit({"ok": False, "error": "knowledge_command_failed", "detail": exc.__class__.__name__, "message": str(exc)})
        return 1
    _emit({"ok": False, "error": "unknown_knowledge_command", "command": command})
    return 2


def _init(args: list[str]) -> int:
    vault = _option(args, "--vault")
    if not vault:
        _emit({"ok": False, "error": "knowledge_init_requires_vault"})
        return 2
    payload = init_control_vault(vault, profile=_option(args, "--profile", "obsidian"))
    return _output(payload, _json_requested(args), _format_init)


def _export_workspace(args: list[str]) -> int:
    workspace = _option(args, "--workspace", ".")
    vault = _option(args, "--vault")
    if not vault:
        _emit({"ok": False, "error": "knowledge_export_workspace_requires_vault"})
        return 2
    payload = export_workspace_to_vault(
        workspace,
        vault,
        profile=_option(args, "--profile", "obsidian"),
        public="--private" not in args,
    )
    return _output(payload, _json_requested(args), _format_export_workspace)


def _export_task(args: list[str]) -> int:
    task_id = _positional(args, skip_values_for={"--workspace", "--vault", "--profile"})
    workspace = _option(args, "--workspace", ".")
    vault = _option(args, "--vault")
    if not task_id or not vault:
        _emit({"ok": False, "error": "knowledge_export_task_requires_task_and_vault"})
        return 2
    payload = export_task_to_vault(
        workspace,
        vault,
        task_id=task_id,
        profile=_option(args, "--profile", "obsidian"),
        public="--private" not in args,
    )
    return _output(payload, _json_requested(args), _format_export_task)


def _graph(args: list[str]) -> int:
    if not args or args[0] != "build":
        _emit({"ok": False, "error": "knowledge_graph_build_required"})
        return 2
    rest = args[1:]
    workspace = _option(rest, "--workspace", ".")
    output = _option(rest, "--output", "reports/knowledge/seos_control_graph.json")
    payload = write_workspace_graph(workspace, output, public="--private" not in rest)
    return _output(payload, _json_requested(rest), _format_graph)


def _scan(args: list[str]) -> int:
    vault = _option(args, "--vault")
    if not vault:
        _emit({"ok": False, "error": "knowledge_scan_requires_vault"})
        return 2
    payload = scan_control_vault(vault, public="--private" not in args)
    output = _option(args, "--output-json")
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        payload = dict(payload)
        payload["output_json"] = path.as_posix()
    return _output(payload, _json_requested(args), _format_scan)


def _emit(payload: dict[str, object]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


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


def _positional(args: list[str], *, skip_values_for: set[str]) -> str:
    skip_next = False
    for item in args:
        if skip_next:
            skip_next = False
            continue
        if item in {"--json", "--private"}:
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


def _format_init(payload: dict[str, object]) -> str:
    return f"Control vault ready: {payload.get('vault')}"


def _format_export_workspace(payload: dict[str, object]) -> str:
    return f"Exported {payload.get('task_count')} tasks to {payload.get('vault')}"


def _format_export_task(payload: dict[str, object]) -> str:
    return f"Exported task {payload.get('task_id')} to {payload.get('task_note')}"


def _format_graph(payload: dict[str, object]) -> str:
    graph = payload.get("graph", {}) if isinstance(payload.get("graph"), dict) else {}
    return f"Knowledge graph {graph.get('node_count')} nodes / {graph.get('edge_count')} edges -> {payload.get('path')}"


def _format_scan(payload: dict[str, object]) -> str:
    return f"Control vault scan ok={payload.get('ok')} notes={payload.get('note_count')} problems={payload.get('problem_count')}"


if __name__ == "__main__":
    raise SystemExit(main())
