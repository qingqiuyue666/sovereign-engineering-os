"""Evidence report renderer."""

from __future__ import annotations

def render_evidence_markdown(rows: list[dict[str, object]]) -> str:
    lines = ["# Creative Evidence Report V3", "", f"Evidence rows: {len(rows)}", "", "| ID | Kind | Summary |", "| --- | --- | --- |"]
    for row in rows:
        lines.append(f"| {row.get('id')} | {row.get('kind')} | {row.get('summary')} |")
    return "\n".join(lines) + "\n"
