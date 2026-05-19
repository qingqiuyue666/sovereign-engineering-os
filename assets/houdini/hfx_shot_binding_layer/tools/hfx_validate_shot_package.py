#!/usr/bin/env python3
"""CLI for validating deterministic HFX shot-binding packages."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from hfx_shot_binding_lib import HFXShotBindingError, validate_shot_package


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an HFX shot-binding package.")
    parser.add_argument("--shot-package", required=True, help="Path to the generated shot package root.")
    args = parser.parse_args()

    try:
        result = validate_shot_package(Path(args.shot_package))
    except HFXShotBindingError as exc:
        print(f"HFX_VALIDATE_SHOT_PACKAGE_FAIL: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
