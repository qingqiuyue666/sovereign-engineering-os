"""Command dispatcher for the V12 dry-run CLI."""

from __future__ import annotations

from .commands import dispatch


def main(argv: list[str] | None = None) -> int:
    return dispatch(argv)
