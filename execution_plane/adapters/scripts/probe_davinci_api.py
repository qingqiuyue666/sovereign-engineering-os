#!/usr/bin/env python3
"""Probe DaVinci Resolve scripting API availability."""

from __future__ import annotations


def main() -> int:
    try:
        import DaVinciResolveScript  # type: ignore[import-not-found]
    except Exception:
        return 1
    return 0 if DaVinciResolveScript.scriptapp("Resolve") else 1


if __name__ == "__main__":
    raise SystemExit(main())
