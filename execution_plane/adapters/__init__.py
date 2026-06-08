"""DCC adapter contracts for the execution plane."""

from __future__ import annotations

from execution_plane.adapters.fake_dcc import run_fake_dcc
from execution_plane.adapters.houdini_hython import detect_hython, run_houdini_hython_smoke

__all__ = ["detect_hython", "run_fake_dcc", "run_houdini_hython_smoke"]

