
#!/usr/bin/env python3

"""Allowlisted local-core verification stage."""

from __future__ import annotations

import subprocess

import sys

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def run(command: tuple[str, ...]) -> int:

    result = subprocess.run(

        command,

        cwd=ROOT,

        text=True,

        stdout=sys.stdout,

        stderr=sys.stderr,

        check=False,

    )

    return result.returncode

def main() -> int:

    commands = (

        ("python3", "-m", "unittest", "tests.tracer_bullet.test_local_core_operating_foundation", "-v"),

        ("python3", "-m", "unittest", "tests.tracer_bullet.test_local_core_authority_gate", "-v"),

        ("git", "diff", "--check"),

    )

    for command in commands:

        code = run(command)

        if code != 0:

            return code

    return 0

if __name__ == "__main__":

    raise SystemExit(main())

