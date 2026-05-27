#!/usr/bin/env python3
"""Render static install/config/packaging readiness."""

from __future__ import annotations

import argparse
from pathlib import Path

from kernel.install_config.packaging_readiness import (
    build_packaging_readiness_report,
    render_packaging_readiness_report,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate install/config/packaging metadata without installing.")
    parser.add_argument("repo_root", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report = build_packaging_readiness_report(args.repo_root)
    print(render_packaging_readiness_report(report), end="")
    return 0 if report.accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
