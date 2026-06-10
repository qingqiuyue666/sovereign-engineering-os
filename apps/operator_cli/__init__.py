"""Operator CLI package for V12 local dry-run commands."""

from __future__ import annotations


def main(argv: list[str] | None = None) -> int:
    from .main import main as _main

    return _main(argv)

__all__ = ["main"]
