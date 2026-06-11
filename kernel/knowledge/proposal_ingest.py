"""Record Markdown proposal notes as non-authoritative SEOS artifacts."""

from __future__ import annotations

from pathlib import Path
import json

from kernel.knowledge.frontmatter import split_frontmatter
from kernel.knowledge.object_model import digest_payload, now_utc, safe_id
from kernel.knowledge.redaction import digest_text, public_path_ref
from kernel.security.secret_scanner import CoreSecretScanner

__all__ = ["ingest_proposal_note"]


def ingest_proposal_note(note: str | Path, workspace: str | Path, *, public: bool = True) -> dict[str, object]:
    workspace_root = Path(workspace).resolve()
    seos_root = workspace_root / ".seos"
    if not (seos_root / "workspace.json").exists():
        return {"ok": False, "error": "workspace_not_initialized", "workspace": workspace_root.as_posix()}

    note_path = Path(note).expanduser().resolve()
    if not note_path.exists() or not note_path.is_file():
        return {"ok": False, "error": "note_not_found", "note": note_path.as_posix()}

    text = note_path.read_text(encoding="utf-8", errors="replace")
    scan = CoreSecretScanner().scan_text(text, path=note_path.as_posix())
    if not scan.clean:
        return {
            "ok": False,
            "error": "note_failed_public_safety_scan",
            "finding_kinds": sorted({finding.kind for finding in scan.findings}),
            "note_ref": public_path_ref(note_path) if public else note_path.as_posix(),
        }

    frontmatter, body = split_frontmatter(text)
    authority = str(frontmatter.get("authority") or "proposal")
    if authority != "proposal":
        return {"ok": False, "error": "only_proposal_authority_is_ingestable", "authority": authority}

    proposal_id = safe_id(frontmatter.get("seos_id") or note_path.stem, fallback="proposal")
    proposal = {
        "schema": "seos_knowledge_proposal_v1",
        "created_at": now_utc(),
        "authority": "proposal",
        "source": "knowledge_note",
        "proposal_id": proposal_id,
        "seos_type": str(frontmatter.get("seos_type") or "proposal"),
        "title": str(frontmatter.get("title") or proposal_id),
        "objective_summary": _summary_from_body(body),
        "note_digest": digest_text(text),
        "body_digest": digest_text(body),
        "note_ref": public_path_ref(note_path, root=workspace_root) if public else note_path.as_posix(),
        "frontmatter": dict(frontmatter),
        "public": public,
        "local_path_redacted": public,
        "execution_authority_granted": False,
        "task_created": False,
        "approval_created": False,
        "permit_created": False,
    }
    proposal["digest"] = digest_payload(proposal)
    output = seos_root / "knowledge" / "proposals" / f"{proposal_id}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(proposal, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"ok": True, "proposal": proposal, "path": output.as_posix()}


def _summary_from_body(body: str) -> str:
    for line in body.splitlines():
        cleaned = line.strip()
        if cleaned and not cleaned.startswith("#") and not cleaned.startswith(">"):
            return cleaned[:400]
    return "Knowledge note proposal"
