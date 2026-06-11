"""Markdown rendering for SEOS knowledge objects."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json

from kernel.knowledge.frontmatter import dump_frontmatter
from kernel.knowledge.object_model import KnowledgeObject
from kernel.knowledge.redaction import redact_note_if_needed

__all__ = [
    "render_json_block",
    "render_knowledge_note",
    "render_properties_table",
    "render_relation_list",
]


def render_knowledge_note(
    knowledge_object: KnowledgeObject,
    *,
    summary: str = "",
    sections: Mapping[str, object] | None = None,
    public: bool = True,
) -> tuple[str, dict[str, object]]:
    """Render a knowledge object to Markdown with SEOS frontmatter.

    The rendered note is a human-facing mirror/proposal artifact. It explicitly
    states that it does not grant execution authority. The second return value is
    redaction metadata from the shared bounded secret scanner.
    """

    frontmatter = knowledge_object.frontmatter()
    frontmatter["public"] = public
    lines = [
        dump_frontmatter(frontmatter).rstrip(),
        "",
        f"# {knowledge_object.title or knowledge_object.object_id}",
        "",
        "> SEOS knowledge note: human-readable only. This note does not approve, permit, or execute work.",
        "",
        "## Authority Boundary",
        "",
        f"- authority: `{knowledge_object.authority}`",
        "- execution_authority_granted: `false`",
        "- authoritative execution state remains in SEOS task contracts, receipts, permits, result envelopes, and evidence traces.",
        "",
    ]
    if summary:
        lines.extend(["## Summary", "", summary, ""])
    if knowledge_object.properties:
        lines.extend(["## Properties", "", render_properties_table(knowledge_object.properties), ""])
    if knowledge_object.relations:
        lines.extend(["## Relations", "", render_relation_list([relation.as_dict() for relation in knowledge_object.relations]), ""])
    for heading, value in (sections or {}).items():
        lines.extend([f"## {heading}", "", _render_value(value), ""])
    lines.extend(
        [
            "## Canonical Object",
            "",
            render_json_block(knowledge_object.as_dict(include_digest=True)),
            "",
        ]
    )
    rendered = "\n".join(lines).rstrip() + "\n"
    return redact_note_if_needed(rendered, path=f"knowledge:{knowledge_object.object_type}:{knowledge_object.object_id}")


def render_properties_table(properties: Mapping[str, object]) -> str:
    rows = ["| Key | Value |", "| --- | --- |"]
    for key in sorted(properties):
        rows.append(f"| `{_escape_cell(str(key))}` | {_escape_cell(_short_value(properties[key]))} |")
    return "\n".join(rows)


def render_relation_list(relations: Sequence[Mapping[str, object]]) -> str:
    lines = []
    for relation in relations:
        relation_type = relation.get("relation_type", "related_to")
        target_type = relation.get("target_type", "unknown")
        target_id = relation.get("target_id", "unknown")
        lines.append(f"- `{relation_type}` -> `{target_type}:{target_id}`")
    return "\n".join(lines) if lines else "none"


def render_json_block(payload: object) -> str:
    return "```json\n" + json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n```"


def _render_value(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return render_json_block(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        if not value:
            return "none"
        if all(isinstance(item, str) for item in value):
            return "\n".join(f"- {item}" for item in value)
        return render_json_block(value)
    return str(value)


def _short_value(value: object) -> str:
    if isinstance(value, (dict, list, tuple)):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        text = str(value)
    return text if len(text) <= 160 else text[:157] + "..."


def _escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
