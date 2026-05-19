#!/usr/bin/env python3
"""CLI for validating and sealing the HFX Factory shot-binding layer."""

from __future__ import annotations

import argparse
import json
import sys

sys.dont_write_bytecode = True

from hfx_shot_binding_lib import HFXShotBindingError, run_global_shot_binding_seal


def main() -> int:
    argparse.ArgumentParser(description="Run the HFX shot-binding global seal.").parse_args()
    try:
        result = run_global_shot_binding_seal()
    except HFXShotBindingError as exc:
        print(f"HFX_SHOT_BINDING_GLOBAL_SEAL_FAIL: {exc}", file=sys.stderr)
        return 1

    print(json.dumps({"status": result["status"], "validated": result["validated"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
