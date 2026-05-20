"""Fail-closed tests for the isolated HFX hython ROP executor."""

from __future__ import annotations

from pathlib import Path
import os
import tempfile
import textwrap
import unittest

from kernel.vfx.hython_rop_executor import (
    HythonRenderRequest,
    execute_hython_rop,
)


EXR_MAGIC = b"\x76\x2f\x31\x01"


def _write_valid_exr(path: Path, *, label: bytes = b"frame") -> None:
    path.write_bytes(EXR_MAGIC + label + (b"\x00" * 32))


def _write_fake_hython(path: Path, body: str) -> None:
    path.write_text(
        "#!/usr/bin/env python3\n"
        "from __future__ import annotations\n"
        "import json\n"
        "import sys\n"
        "from pathlib import Path\n\n"
        f"{body}\n",
        encoding="utf-8",
    )
    path.chmod(0o700)


class HythonRopExecutorFailClosedTests(unittest.TestCase):
    def test_missing_frame_in_exr_sequence_is_incomplete_and_unledgered(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            hip_file = temp_dir / "shot.hip"
            output_dir = temp_dir / "renders"
            ledger_root = temp_dir / "private-ledger"
            fake_hython = temp_dir / "fake_hython"
            hip_file.write_text("placeholder hip", encoding="utf-8")
            _write_fake_hython(
                fake_hython,
                textwrap.dedent(
                    """
                    config = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
                    pattern = config["houdini_output_pattern"]
                    for frame in range(int(config["start_frame"]), int(config["end_frame"]) + 1):
                        if frame == 4:
                            continue
                        frame_path = Path(pattern.replace("$F4", f"{frame:04d}"))
                        frame_path.parent.mkdir(parents=True, exist_ok=True)
                        frame_path.write_bytes(b"\\x76\\x2f\\x31\\x01" + b"ok" + (b"\\x00" * 32))
                    raise SystemExit(0)
                    """
                ),
            )

            result = execute_hython_rop(
                HythonRenderRequest(
                    hip_file=hip_file,
                    rop_node_path="/out/hfx_render",
                    output_directory=output_dir,
                    end_frame=5,
                    hython_executable=fake_hython,
                    ledger_root=ledger_root,
                )
            )

            self.assertTrue(result.process_ok)
            self.assertFalse(result.audit.passed)
            self.assertFalse(result.complete)
            self.assertEqual(result.audit.missing_frames, (4,))
            self.assertEqual(result.audit.valid_frames, (1, 2, 3, 5))
            self.assertIsNone(result.ledger_record)
            self.assertIsNone(result.ledger_error)
            self.assertFalse((ledger_root / "latest.json").exists())

    def test_hython_crash_mid_render_is_incomplete_and_unledgered(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            hip_file = temp_dir / "shot.hip"
            output_dir = temp_dir / "renders"
            ledger_root = temp_dir / "private-ledger"
            fake_hython = temp_dir / "fake_hython"
            hip_file.write_text("placeholder hip", encoding="utf-8")
            _write_fake_hython(
                fake_hython,
                textwrap.dedent(
                    """
                    config = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
                    frame_path = Path(config["houdini_output_pattern"].replace("$F4", "0001"))
                    frame_path.parent.mkdir(parents=True, exist_ok=True)
                    frame_path.write_bytes(b"\\x76\\x2f\\x31\\x01" + b"partial" + (b"\\x00" * 32))
                    print("simulated hython crash after frame 1", file=sys.stderr)
                    raise SystemExit(42)
                    """
                ),
            )

            result = execute_hython_rop(
                HythonRenderRequest(
                    hip_file=hip_file,
                    rop_node_path="/out/hfx_render",
                    output_directory=output_dir,
                    end_frame=3,
                    hython_executable=fake_hython,
                    ledger_root=ledger_root,
                )
            )

            self.assertEqual(result.returncode, 42)
            self.assertFalse(result.process_ok)
            self.assertFalse(result.audit.passed)
            self.assertFalse(result.complete)
            self.assertEqual(result.audit.valid_frames, (1,))
            self.assertEqual(result.audit.missing_frames, (2, 3))
            self.assertIn("simulated hython crash", result.stderr)
            self.assertIsNone(result.ledger_record)
            self.assertIsNone(result.ledger_error)
            self.assertFalse((ledger_root / "latest.json").exists())

    def test_audit_rejects_missing_frame_without_spawning_hython(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            hip_file = temp_dir / "shot.hip"
            output_dir = temp_dir / "renders"
            hip_file.write_text("placeholder hip", encoding="utf-8")
            output_dir.mkdir()
            for frame in (1, 2, 3, 5):
                _write_valid_exr(output_dir / f"hfx_render.{frame:04d}.exr")

            request = HythonRenderRequest(
                hip_file=hip_file,
                rop_node_path="/out/hfx_render",
                output_directory=output_dir,
                end_frame=5,
                hython_executable=Path(os.devnull),
                write_ledger=False,
                allow_existing_frames=True,
            )

            from kernel.vfx.hython_rop_executor import audit_exr_sequence

            audit = audit_exr_sequence(request)

            self.assertFalse(audit.passed)
            self.assertEqual(audit.missing_frames, (4,))
            self.assertEqual(audit.valid_frames, (1, 2, 3, 5))


if __name__ == "__main__":
    unittest.main()
