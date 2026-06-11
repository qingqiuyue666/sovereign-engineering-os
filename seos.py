#!/usr/bin/env python3
"""SEOS V12 dry-run CLI entrypoint."""

from __future__ import annotations

import sys

from apps.operator_cli.main import main


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "knowledge":
        from kernel.knowledge.cli import main as knowledge_main

        raise SystemExit(knowledge_main(sys.argv[2:]))
    raise SystemExit(main())
