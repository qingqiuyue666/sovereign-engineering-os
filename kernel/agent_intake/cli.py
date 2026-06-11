"""CLI for SEOS external-agent intake."""

from __future__ import annotations

from pathlib import Path
import json
import sys

from kernel.agent_intake.boundary import evaluate_agent_request
from kernel.agent_intake.mcp_manifest import write_agent_intake_manifest
from kernel.agent_intake.proposals import write_agent_proposal

__all__ = ["main"]

_HELP = """SEOS agent-intake CLI

Usage:
  python3 -m kernel.agent_intake.cli evaluate REQUEST.json [--json]
  python3 -m kernel.agent_intake.cli propose REQUEST.json --workspace PATH [--source NAME] [--json]
  python3 -m kernel.agent_intake.cli manifest --output reports/agent_intake/mcp_manifest.json [--json]

Authority boundary:
  Agent intake accepts only proposal/read-only intents. It does not approve work,
  create permits, run commands, read secrets, or mutate authority stores.
"""


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"--help", "-h", "help"}:
        print(_HELP)
        return 0
    command = args[0]
    rest = args[1:]
    try:
        if command == "evaluate":
            return _evaluate(rest)
        if command == "propose":
            return _propose(rest)
        if command == "manifest":
            return _manifest(rest)
    except Exception as exc:
        _emit({"ok": False, "error": "agent_intake_command_failed", "detail": exc.__class__.__name__, "message": str(exc)})
        return 1
    _emit({"ok": False, "error": "unknown_agent_intake_command", "command": command})
    return 2


def _evaluate(args: list[str]) -> int:
    path = _positional(args, skip_values_for=set())
    if not path:
        _emit({"ok": False, "error": "agent_evaluate_requires_request_json"})
        return 2
    request = _read_json(path)
    decision = evaluate_agent_request(request)
    payload = {"ok": bool(decision.get("accepted")), "decision": decision}
    return _output(payload, _json_requested(args), _format_decision)


def _propose(args: list[str]) -> int:
    path = _positional(args, skip_values_for={"--workspace", "--source"})
    workspace = _option(args, "--workspace", ".")
    if not path:
        _emit({"ok": False, "error": "agent_propose_requires_request_json"})
        return 2
    request = _read_json(path)
    payload = write_agent_proposal(workspace, request, source=_option(args, "--source", "external_agent"))
    return _output(payload, _json_requested(args), _format_proposal)


def _manifest(args: list[str]) -> int:
    output = _option(args, "--output", "reports/agent_intake/mcp_manifest.json")
    payload = write_agent_intake_manifest(output)
    return _output(payload, _json_requested(args), _format_manifest)


def _read_json(path: str) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


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
        if item == "--json":
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


def _format_decision(payload: dict[str, object]) -> str:
    decision = payload.get("decision", {}) if isinstance(payload.get("decision"), dict) else {}
    return f"Agent request {decision.get('terminal_status')} intent={decision.get('intent')}"


def _format_proposal(payload: dict[str, object]) -> str:
    proposal = payload.get("proposal", {}) if isinstance(payload.get("proposal"), dict) else {}
    return f"Agent proposal ok={payload.get('ok')} request={proposal.get('request_id')} path={payload.get('path')}"


def _format_manifest(payload: dict[str, object]) -> str:
    manifest = payload.get("manifest", {}) if isinstance(payload.get("manifest"), dict) else {}
    return f"Agent intake manifest tools={len(manifest.get('tools', []))} resources={len(manifest.get('resources', []))} path={payload.get('path')}"


if __name__ == "__main__":
    raise SystemExit(main())
