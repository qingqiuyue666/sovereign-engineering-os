"""CLI for SEOS knowledge and control-vault operations."""

from __future__ import annotations

from pathlib import Path
import json
import sys

from kernel.knowledge.adapters.anytype import export_anytype_object_bundle, import_anytype_object_bundle
from kernel.knowledge.adapters.logseq import export_workspace_to_logseq
from kernel.knowledge.adapters.notion import build_notion_readonly_dashboard, build_notion_readonly_source_mirror
from kernel.knowledge.graph import write_workspace_graph
from kernel.knowledge.proposal_ingest import ingest_proposal_note
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
  python3 -m kernel.knowledge.cli ingest-proposal --note PATH --workspace PATH [--private]
  python3 -m kernel.knowledge.cli export-logseq --workspace PATH --root PATH [--private]
  python3 -m kernel.knowledge.cli export-anytype --workspace PATH --output PATH [--private]
  python3 -m kernel.knowledge.cli import-anytype --source PATH --output PATH [--private]
  python3 -m kernel.knowledge.cli notion-dashboard --workspace PATH --output PATH [--private]
  python3 -m kernel.knowledge.cli sync-notion --mode readonly (--workspace PATH|--source PATH) --output PATH [--private]

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
        if command == "ingest-proposal":
            return _ingest_proposal(rest)
        if command == "export-logseq":
            return _export_logseq(rest)
        if command == "export-anytype":
            return _export_anytype(rest)
        if command == "import-anytype":
            return _import_anytype(rest)
        if command == "notion-dashboard":
            return _notion_dashboard(rest)
        if command == "sync-notion":
            return _sync_notion(rest)
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


def _ingest_proposal(args: list[str]) -> int:
    note = _option(args, "--note") or _positional(args, skip_values_for={"--workspace", "--note"})
    workspace = _option(args, "--workspace", ".")
    if not note:
        _emit({"ok": False, "error": "knowledge_ingest_proposal_requires_note"})
        return 2
    payload = ingest_proposal_note(note, workspace, public="--private" not in args)
    return _output(payload, _json_requested(args), _format_ingest_proposal)


def _export_logseq(args: list[str]) -> int:
    workspace = _option(args, "--workspace", ".")
    root = _option(args, "--root")
    if not root:
        _emit({"ok": False, "error": "knowledge_export_logseq_requires_root"})
        return 2
    payload = export_workspace_to_logseq(workspace, root, public="--private" not in args)
    return _output(payload, _json_requested(args), _format_generic_pathless)


def _export_anytype(args: list[str]) -> int:
    workspace = _option(args, "--workspace", ".")
    output = _option(args, "--output", "reports/knowledge/anytype_object_bundle.json")
    payload = export_anytype_object_bundle(workspace, output, public="--private" not in args)
    return _output(payload, _json_requested(args), _format_generic_path)


def _import_anytype(args: list[str]) -> int:
    source = _option(args, "--source") or _positional(args, skip_values_for={"--output", "--source"})
    output = _option(args, "--output", "reports/knowledge/anytype_import_record.json")
    if not source:
        _emit({"ok": False, "error": "knowledge_import_anytype_requires_source"})
        return 2
    payload = import_anytype_object_bundle(source, output, public="--private" not in args)
    return _output(payload, _json_requested(args), _format_generic_path)


def _notion_dashboard(args: list[str]) -> int:
    workspace = _option(args, "--workspace", ".")
    output = _option(args, "--output", "reports/knowledge/notion_readonly_dashboard.json")
    payload = build_notion_readonly_dashboard(workspace, output, public="--private" not in args)
    return _output(payload, _json_requested(args), _format_generic_path)


def _sync_notion(args: list[str]) -> int:
    mode = _option(args, "--mode", "readonly")
    if mode != "readonly":
        _emit({"ok": False, "error": "knowledge_sync_notion_readonly_mode_required"})
        return 2
    output = _option(args, "--output", "reports/knowledge/notion_readonly_sync_payload.json")
    source = _option(args, "--source")
    if source:
        payload = build_notion_readonly_source_mirror(source, output, public="--private" not in args)
    else:
        payload = build_notion_readonly_dashboard(_option(args, "--workspace", "."), output, public="--private" not in args)
    return _output(payload, _json_requested(args), _format_generic_path)


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


def _format_ingest_proposal(payload: dict[str, object]) -> str:
    proposal = payload.get("proposal", {}) if isinstance(payload.get("proposal"), dict) else {}
    return f"Proposal ingest ok={payload.get('ok')} proposal={proposal.get('proposal_id')} path={payload.get('path')}"


def _format_generic_path(payload: dict[str, object]) -> str:
    return f"Knowledge artifact ok={payload.get('ok')} path={payload.get('path')}"


def _format_generic_pathless(payload: dict[str, object]) -> str:
    return f"Knowledge export ok={payload.get('ok')} written={len(payload.get('written', []))}"


if __name__ == "__main__":
    raise SystemExit(main())
