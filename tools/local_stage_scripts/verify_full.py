
#!/usr/bin/env python3

"""Allowlisted full verification stage."""

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

        ("python3", "-m", "unittest", "discover", "-s", "tests/tracer_bullet", "-v"),

        ("python3", "-m", "unittest", "discover", "-s", "tests/schemas", "-v"),

        ("python3", "-m", "unittest", "discover", "-s", "validation/tests/acceptance", "-v"),

        ("make", "ci"),

        ("git", "diff", "--check"),

    )

    for command in commands:

        code = run(command)

        if code != 0:

            return code

    return 0

if __name__ == "__main__":

    raise SystemExit(main())

