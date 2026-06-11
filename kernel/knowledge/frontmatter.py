"""Small YAML-frontmatter subset for SEOS knowledge notes.

SEOS intentionally avoids adding a YAML dependency here. The knowledge vault only
needs a conservative scalar subset for Markdown note metadata: strings, booleans,
integers, and null. Rich data stays in fenced JSON blocks in the note body or in
SEOS canonical JSON artifacts.
"""

from __future__ import annotations

from collections.abc import Mapping
import json

__all__ = ["dump_frontmatter", "parse_frontmatter", "split_frontmatter"]


def dump_frontmatter(values: Mapping[str, object]) -> str:
    lines = ["---"]
    for key in sorted(values):
        if not _safe_key(key):
            raise ValueError(f"unsafe frontmatter key: {key!r}")
        lines.append(f"{key}: {_format_scalar(values[key])}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def split_frontmatter(text: str) -> tuple[dict[str, object], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    end_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = index
            break
    if end_index is None:
        return {}, text
    header: dict[str, object] = {}
    for raw_line in lines[1:end_index]:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"invalid frontmatter line: {raw_line!r}")
        key, value = line.split(":", 1)
        key = key.strip()
        if not _safe_key(key):
            raise ValueError(f"unsafe frontmatter key: {key!r}")
        header[key] = _parse_scalar(value.strip())
    body = "\n".join(lines[end_index + 1 :])
    if text.endswith("\n"):
        body += "\n"
    return header, body


def parse_frontmatter(text: str) -> dict[str, object]:
    header, _body = split_frontmatter(text)
    return header


def _safe_key(value: str) -> bool:
    return bool(value) and all(char.isalnum() or char in "_-" for char in value)


def _format_scalar(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if value is None:
        return "null"
    return json.dumps(str(value), ensure_ascii=False)


def _parse_scalar(value: str) -> object:
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None
    if value.startswith(('"', "'")):
        try:
            return json.loads(value)
        except Exception:
            return value.strip('"\'')
    try:
        return int(value)
    except ValueError:
        return value
