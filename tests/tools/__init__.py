"""Tests for repository tooling.

When `python3 -m unittest discover tests` runs, this package is imported as a
top-level `tools` package. Extend the package search path to the repository
`tools/` directory so existing tests can still import modules such as
`tools.local_stage_executor`.
"""

from __future__ import annotations

from pathlib import Path

REPO_TOOLS = Path(__file__).resolve().parents[2] / "tools"

if str(REPO_TOOLS) not in __path__:
    __path__.append(str(REPO_TOOLS))
