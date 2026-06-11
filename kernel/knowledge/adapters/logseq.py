"""Logseq-compatible Markdown/Org-style journal mirror adapter.

The adapter is intentionally file-only. It writes public-safe pages and journals
that point back to SEOS artifacts, but it does not treat Logseq as a database of
record and does not execute commands from blocks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable
import json

from kernel.knowledge.graph import build_workspace_graph
from kernel.knowledge.redaction import public_path_ref

__all__ = ["export_workspace_to_logseq"]


def export_workspace_to_logseq(workspace: str | Path, root: str | Path, *, public: bool = True) -> dict[str, object]:
    """Write a minimal Logseq-compatible page set from a SEOS workspace graph."""

    workspace_root = Path(workspace).resolve()
    logseq_root = Path(root).expanduser().resolve()
    pages_root = logseq_root / "pages"
    journals_root = logseq_root / "journals"
    pages_root.mkdir(parents=True, exist_ok=True)
    journals_root.mkdir(parents=True, exist_ok=True)

    graph = build_workspace_graph(workspace_root, public=public)
    task_nodes = [node for node in graph["nodes"] if node.get("object_type") == "seos.task"]
    written: list[str] = []
    index = pages_root / "SEOS_Control.md"
    index.write_text(_index_page(graph, task_nodes), encoding="utf-8")
    written.append(index.as_posix())
    for node in task_nodes:
        path = pages_root / f"{_page_name(str(node.get('object_id')))}.md"
        path.write_text(_task_page(node), encoding="utf-8")
        written.append(path.as_posix())
    journal = journals_root / "seos_operations.md"
    journal.write_text(_journal_page(workspace_root, task_nodes, public=public), encoding="utf-8")
    written.append(journal.as_posix())
    return {
        "ok": True,
        "schema": "seos_logseq_export_v1",
        "root": logseq_root.as_posix(),
        "workspace_ref": public_path_ref(workspace_root) if public else workspace_root.as_posix(),
        "public": public,
        "authority": "mirror",
        "execution_authority_granted": False,
        "written": written,
        "task_count": len(task_nodes),
    }


def _index_page(graph: dict[str, object], task_nodes: Iterable[dict[str, object]]) -> str:
    lines = [
        "- # SEOS Control",
        "  - authority:: mirror",
        "  - execution_authority_granted:: false",
        f"  - graph_digest:: {graph.get('digest')}",
        f"  - node_count:: {graph.get('node_count')}",
        f"  - edge_count:: {graph.get('edge_count')}",
        "  - Tasks",
    ]
    for node in task_nodes:
        lines.append(f"    - [[{_page_name(str(node.get('object_id')))}]] status:: {node.get('properties', {}).get('status')}")
    return "\n".join(lines) + "\n"


def _task_page(node: dict[str, object]) -> str:
    properties = node.get("properties", {}) if isinstance(node.get("properties"), dict) else {}
    lines = [
        f"- # {node.get('title') or node.get('object_id')}",
        "  - authority:: mirror",
        "  - execution_authority_granted:: false",
        f"  - seos_type:: {node.get('object_type')}",
        f"  - seos_id:: {node.get('object_id')}",
        f"  - digest:: {node.get('digest')}",
        "  - Properties",
    ]
    for key in sorted(properties):
        value = properties[key]
        if isinstance(value, (dict, list, tuple)):
            value_text = json.dumps(value, ensure_ascii=False, sort_keys=True)
        else:
            value_text = str(value)
        lines.append(f"    - {key}:: {value_text}")
    return "\n".join(lines) + "\n"


def _journal_page(workspace_root: Path, task_nodes: list[dict[str, object]], *, public: bool) -> str:
    lines = [
        "- # SEOS Operations Journal",
        "  - authority:: mirror",
        "  - execution_authority_granted:: false",
        f"  - workspace_ref:: {public_path_ref(workspace_root) if public else workspace_root.as_posix()}",
        "  - Exported tasks",
    ]
    for node in task_nodes:
        lines.append(f"    - [[{_page_name(str(node.get('object_id')))}]]")
    return "\n".join(lines) + "\n"


def _page_name(value: str) -> str:
    return "SEOS_" + "".join(char if char.isalnum() or char in "_-" else "_" for char in value)
