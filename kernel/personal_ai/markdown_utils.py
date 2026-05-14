"""Atomic Markdown output helpers for Personal AI local artifacts."""

from pathlib import Path
import tempfile

__all__ = [
    "write_markdown_atomically",
]


def write_markdown_atomically(output_path: Path, content: str) -> None:
    output_file = Path(output_path)
    _require_existing_parent(output_file)
    if not isinstance(content, str):
        raise ValueError("markdown content must be text")

    normalized_content = content if content.endswith("\n") else content + "\n"
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=output_file.parent,
        prefix=f".{output_file.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary_file:
        temporary_path = Path(temporary_file.name)
        temporary_file.write(normalized_content)
        temporary_file.flush()

    temporary_path.replace(output_file)


def _require_existing_parent(output_file):
    parent = output_file.parent
    if not parent.exists() or not parent.is_dir():
        raise ValueError("output_path parent is missing")
