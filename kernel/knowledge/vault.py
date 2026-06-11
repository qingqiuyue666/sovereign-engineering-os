"""Local Markdown control vault exporter for SEOS knowledge objects."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable
import json

from kernel.knowledge.graph import write_workspace_graph
from kernel.knowledge.markdown_renderer import render_knowledge_note, render_json_block
from kernel.knowledge.object_model import KnowledgeObject, KnowledgeRelation, digest_payload, now_utc, safe_id
from kernel.knowledge.redaction import public_path_ref

__all__ = [
    "CONTROL_VAULT_DIRS",
    "export_task_to_vault",
    "export_workspace_to_vault",
    "init_control_vault",
]

CONTROL_VAULT_DIRS = (
    "00_Index",
    "01_Tasks",
    "02_Approvals",
    "03_Permits",
    "04_Evidence",
    "05_Assets",
    "06_Shots",
    "07_Runs",
    "08_Releases",
    "09_Audit",
    "99_Graph",
)


def init_control_vault(vault: str | Path, *, profile: str = "obsidian") -> dict[str, object]:
    """Create the local control-vault directory layout.

    The vault is a human-readable mirror/proposal workspace. Creating it does
    not grant approval, permit execution, mutate production assets, or call any
    external provider.
    """

    if profile != "obsidian":
        return {"ok": False, "error": "unsupported_profile", "profile": profile}
    vault_root = Path(vault).expanduser().resolve()
    created: list[str] = []
    for relative in CONTROL_VAULT_DIRS:
        path = vault_root / relative
        path.mkdir(parents=True, exist_ok=True)
        created.append(path.as_posix())
    obsidian_dir = vault_root / ".obsidian"
    obsidian_dir.mkdir(parents=True, exist_ok=True)
    _write_if_missing(
        obsidian_dir / "app.json",
        json.dumps({"alwaysUpdateLinks": True, "newFileLocation": "folder", "promptDelete": False}, indent=2, sort_keys=True) + "\n",
    )
    _write_if_missing(vault_root / "00_Index" / "README.md", _index_note())
    manifest = {
        "schema": "seos_control_vault_manifest_v1",
        "created_at": now_utc(),
        "profile": profile,
        "authority": "mirror",
        "execution_authority_granted": False,
        "public_default": True,
        "directories": list(CONTROL_VAULT_DIRS),
    }
    (vault_root / "seos_control_vault_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "ok": True,
        "profile": profile,
        "vault": vault_root.as_posix(),
        "created_directories": created,
        "manifest_path": (vault_root / "seos_control_vault_manifest.json").as_posix(),
    }


def export_workspace_to_vault(
    workspace: str | Path,
    vault: str | Path,
    *,
    profile: str = "obsidian",
    public: bool = True,
) -> dict[str, object]:
    init = init_control_vault(vault, profile=profile)
    if not init.get("ok"):
        return init
    workspace_root = Path(workspace).resolve()
    vault_root = Path(vault).expanduser().resolve()
    task_paths = list(_iter_json(workspace_root / ".seos" / "tasks"))
    exported = []
    for task_path in task_paths:
        task_id = str(_read_json(task_path).get("task_id") or task_path.stem)
        exported.append(export_task_to_vault(workspace_root, vault_root, task_id=task_id, profile=profile, public=public))
    graph_output = vault_root / "99_Graph" / "seos_control_graph.json"
    graph_result = write_workspace_graph(workspace_root, graph_output, public=public)
    dashboard = _workspace_dashboard(workspace_root, exported, graph_result, public=public)
    dashboard_path = vault_root / "00_Index" / "Workspace Dashboard.md"
    dashboard_path.write_text(dashboard, encoding="utf-8")
    return {
        "ok": all(item.get("ok") for item in exported) and graph_result.get("ok", False),
        "workspace": workspace_root.as_posix(),
        "vault": vault_root.as_posix(),
        "public": public,
        "task_count": len(task_paths),
        "exported": exported,
        "graph_path": graph_output.as_posix(),
        "dashboard_path": dashboard_path.as_posix(),
    }


def export_task_to_vault(
    workspace: str | Path,
    vault: str | Path,
    *,
    task_id: str,
    profile: str = "obsidian",
    public: bool = True,
) -> dict[str, object]:
    if profile != "obsidian":
        return {"ok": False, "error": "unsupported_profile", "profile": profile}
    workspace_root = Path(workspace).resolve()
    seos_root = workspace_root / ".seos"
    vault_root = Path(vault).expanduser().resolve()
    task_path = seos_root / "tasks" / f"{task_id}.json"
    if not task_path.exists():
        return {"ok": False, "error": "task_not_found", "task_id": task_id}
    task = _read_json(task_path)
    safe_task_id = safe_id(task.get("task_id") or task_id, fallback=task_id)
    receipt_paths = [path for path in _iter_json(seos_root / "receipts") if _read_json(path).get("task_id") == task_id]
    task_object = KnowledgeObject(
        "seos.task",
        safe_task_id,
        "mirror",
        title=str(task.get("title") or safe_task_id),
        properties={
            "status": task.get("status"),
            "task_type": task.get("task_type"),
            "classification": task.get("classification"),
            "objective_summary": task.get("objective_summary"),
            "approval_required": task.get("approval_required"),
            "requested_capabilities": task.get("requested_capabilities", []),
            "source_refs": task.get("source_refs", []),
            "task_digest": digest_payload(task),
            "path_ref": public_path_ref(task_path, root=workspace_root) if public else task_path.as_posix(),
        },
        relations=tuple(KnowledgeRelation("has_receipt", "seos.receipt", _receipt_object_id(path, workspace_root)) for path in receipt_paths),
        public=public,
        local_path_redacted=public,
    )
    task_note, task_redaction = render_knowledge_note(
        task_object,
        summary=str(task.get("objective_summary") or "No objective summary recorded."),
        sections={
            "Receipts": [_receipt_summary(path, workspace_root, public=public) for path in receipt_paths],
            "Source Task Contract": render_json_block(_public_task_payload(task, public=public)),
        },
        public=public,
    )
    task_note_path = vault_root / "01_Tasks" / f"{safe_task_id}.md"
    task_note_path.parent.mkdir(parents=True, exist_ok=True)
    task_note_path.write_text(task_note, encoding="utf-8")

    receipt_notes = []
    for receipt_path in receipt_paths:
        receipt_result = _export_receipt_note(vault_root, workspace_root, receipt_path, task_id=safe_task_id, public=public)
        receipt_notes.append(receipt_result)

    evidence_note = _export_evidence_trace_note(vault_root, workspace_root, safe_task_id, receipt_paths, public=public)
    return {
        "ok": True,
        "task_id": safe_task_id,
        "task_note": task_note_path.as_posix(),
        "receipt_notes": receipt_notes,
        "evidence_note": evidence_note,
        "redaction": task_redaction,
        "authority": "mirror",
        "execution_authority_granted": False,
    }


def _export_receipt_note(vault_root: Path, workspace_root: Path, receipt_path: Path, *, task_id: str, public: bool) -> dict[str, object]:
    receipt = _read_json(receipt_path)
    receipt_type = safe_id(receipt.get("receipt_type"), fallback="receipt")
    object_id = _receipt_object_id(receipt_path, workspace_root)
    target_dir = "02_Approvals" if receipt_type in {"approval", "rejection"} else "07_Runs"
    receipt_object = KnowledgeObject(
        "seos.receipt",
        object_id,
        "receipt",
        title=f"{receipt_type} receipt for {task_id}",
        properties={
            "task_id": task_id,
            "receipt_type": receipt.get("receipt_type"),
            "created_at": receipt.get("created_at"),
            "approved": receipt.get("approved"),
            "dry_run": receipt.get("dry_run"),
            "execution_performed": receipt.get("execution_performed"),
            "result": receipt.get("result"),
            "digest": receipt.get("digest"),
            "path_ref": public_path_ref(receipt_path, root=workspace_root) if public else receipt_path.as_posix(),
        },
        relations=(KnowledgeRelation("for_task", "seos.task", task_id),),
        public=public,
        local_path_redacted=public,
    )
    note, redaction = render_knowledge_note(
        receipt_object,
        summary=f"SEOS {receipt_type} receipt mirror for task `{task_id}`.",
        sections={"Receipt Summary": _public_receipt_payload(receipt), "Authority Note": "Receipt summaries are mirrors of SEOS receipt artifacts, not editable approvals."},
        public=public,
    )
    path = vault_root / target_dir / f"{object_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(note, encoding="utf-8")
    return {"path": path.as_posix(), "receipt_type": receipt_type, "redaction": redaction}


def _export_evidence_trace_note(vault_root: Path, workspace_root: Path, task_id: str, receipt_paths: list[Path], *, public: bool) -> dict[str, object]:
    evidence_object = KnowledgeObject(
        "seos.evidence_trace",
        f"{task_id}.trace",
        "mirror",
        title=f"Evidence trace for {task_id}",
        properties={
            "task_id": task_id,
            "receipt_count": len(receipt_paths),
            "receipt_refs": [public_path_ref(path, root=workspace_root) if public else path.as_posix() for path in receipt_paths],
            "complete": bool(receipt_paths),
        },
        relations=tuple(KnowledgeRelation("summarizes", "seos.receipt", _receipt_object_id(path, workspace_root)) for path in receipt_paths),
        public=public,
        local_path_redacted=public,
    )
    note, redaction = render_knowledge_note(
        evidence_object,
        summary="Public-safe evidence trace summary generated from SEOS workspace receipts.",
        sections={"Receipt Files": [public_path_ref(path, root=workspace_root) if public else path.as_posix() for path in receipt_paths]},
        public=public,
    )
    path = vault_root / "04_Evidence" / f"{task_id}.trace.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(note, encoding="utf-8")
    return {"path": path.as_posix(), "redaction": redaction}


def _workspace_dashboard(workspace_root: Path, exported: list[dict[str, object]], graph_result: dict[str, object], *, public: bool) -> str:
    task_lines = [f"- [[{Path(str(item.get('task_note'))).stem}]] `{item.get('task_id')}`" for item in exported if item.get("ok")]
    return "\n".join(
        [
            "---",
            "schema: \"seos_control_vault_dashboard_v1\"",
            "authority: \"mirror\"",
            "execution_authority_granted: false",
            f"public: {'true' if public else 'false'}",
            "---",
            "",
            "# SEOS Control Vault Dashboard",
            "",
            "> Human-facing mirror only. Execution still requires SEOS approval, permit, runner, receipt, and evidence controls.",
            "",
            "## Workspace",
            "",
            f"- workspace_ref: `{public_path_ref(workspace_root) if public else workspace_root.as_posix()}`",
            f"- exported_tasks: `{len(task_lines)}`",
            f"- graph: `{graph_result.get('path')}`",
            "",
            "## Tasks",
            "",
            *(task_lines or ["No tasks exported."]),
            "",
        ]
    )


def _public_task_payload(task: dict[str, object], *, public: bool) -> dict[str, object]:
    payload = dict(task)
    if public:
        payload.pop("task_manifest", None)
    return payload


def _public_receipt_payload(receipt: dict[str, object]) -> dict[str, object]:
    allowed_keys = {
        "schema",
        "receipt_type",
        "task_id",
        "created_at",
        "approved",
        "human_reviewed",
        "dry_run",
        "execution_performed",
        "command",
        "network_accessed",
        "secret_value_read",
        "ai_provider_call_performed",
        "runtime_authority_introduced",
        "result",
        "digest",
    }
    return {key: receipt.get(key) for key in sorted(allowed_keys) if key in receipt}


def _receipt_summary(path: Path, workspace_root: Path, *, public: bool) -> dict[str, object]:
    receipt = _read_json(path)
    return {
        "receipt_type": receipt.get("receipt_type"),
        "created_at": receipt.get("created_at"),
        "digest": receipt.get("digest"),
        "path_ref": public_path_ref(path, root=workspace_root) if public else path.as_posix(),
    }


def _receipt_object_id(path: Path, workspace_root: Path) -> str:
    receipt = _read_json(path)
    task_id = safe_id(receipt.get("task_id"), fallback="unknown_task")
    receipt_type = safe_id(receipt.get("receipt_type"), fallback="receipt")
    digest = str(receipt.get("digest") or digest_payload(receipt))
    return safe_id(f"{task_id}:{receipt_type}:{digest[-16:]}", fallback=path.stem)


def _iter_json(path: Path) -> Iterable[Path]:
    if not path.exists():
        return []
    return sorted(item for item in path.glob("*.json") if item.is_file())


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_if_missing(path: Path, text: str) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _index_note() -> str:
    return "\n".join(
        [
            "# SEOS Control Vault",
            "",
            "This vault is a local Markdown control room for SEOS knowledge objects.",
            "",
            "It is not an approval authority, execution permit, sandbox, RPA system, or secret store.",
            "",
            "## Start Here",
            "",
            "- [[Workspace Dashboard]]",
            "- [[../99_Graph/seos_control_graph.json|Knowledge Graph JSON]]",
            "",
        ]
    )
