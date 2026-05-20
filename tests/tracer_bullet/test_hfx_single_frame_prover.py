"""Tracer bullet tests for the HFX single-frame prover.

The prover's subprocess and ledger seams are mocked here so unittest discovery
is safe on CI hosts that do not have Houdini or hython installed.
"""

from __future__ import annotations

from collections.abc import Sequence
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch
import io
import json
import tempfile
import unittest

from kernel.vfx import hfx_single_frame_prover as prover


EXR_MAGIC = b"\x76\x2f\x31\x01"


class _FakeLedgerRecord:
    def as_dict(self) -> dict[str, object]:
        return {
            "ledger_version": "hfx-render-artifact-ledger-v1",
            "record_id": "unit-test-record",
        }


class _BaseFakePopen:
    def __init__(
        self,
        argv: Sequence[str],
        *_args: object,
        **_kwargs: object,
    ) -> None:
        self.argv = tuple(argv)
        self.returncode = 0
        self._write_frame_from_config(Path(self.argv[2]))

    def communicate(self, timeout: float | None = None) -> tuple[str, str]:
        return ("fake hython stdout", "")

    def poll(self) -> int | None:
        return self.returncode

    def wait(self, timeout: float | None = None) -> int:
        return self.returncode

    def kill(self) -> None:
        self.returncode = -9

    def _write_frame_from_config(self, config_path: Path) -> None:
        raise NotImplementedError


class _ZeroByteFramePopen(_BaseFakePopen):
    def _write_frame_from_config(self, config_path: Path) -> None:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        frame_path = Path(config["output_pattern"].replace("$F4", "0001"))
        frame_path.parent.mkdir(parents=True, exist_ok=True)
        frame_path.write_bytes(b"")


class _AllBlackPayloadPopen(_BaseFakePopen):
    def _write_frame_from_config(self, config_path: Path) -> None:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        frame_path = Path(config["output_pattern"].replace("$F4", "0001"))
        frame_path.parent.mkdir(parents=True, exist_ok=True)
        frame_path.write_bytes(EXR_MAGIC + (b"\x00" * 256))


class _ValidFramePopen(_BaseFakePopen):
    def _write_frame_from_config(self, config_path: Path) -> None:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        frame_path = Path(config["output_pattern"].replace("$F4", "0001"))
        frame_path.parent.mkdir(parents=True, exist_ok=True)
        frame_path.write_bytes(EXR_MAGIC + (bytes(range(256)) * 2))


def _write_fake_hython(path: Path) -> None:
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(0o700)


def _write_audit_json(
    path: Path,
    *,
    hip_file: Path,
    status: str = "PASS",
    classification: str = "Real Asset",
    effective_point_count: int = 2_048,
    minimum_real_asset_points: int = 1_000,
) -> None:
    payload: dict[str, object] = {
        "classification": classification,
        "effective_point_count": effective_point_count,
        "hip_file": hip_file.as_posix(),
        "minimum_real_asset_points": minimum_real_asset_points,
        "render_node_candidates": [
            {
                "output_parameter": "picture",
                "path": "/out/hfx_final_render",
                "type_name": "opengl",
                "valid_renderer": True,
            }
        ],
        "schema_version": "hfx-topology-auditor-v1",
        "selected_render_node": {
            "output_parameter": "picture",
            "path": "/out/hfx_final_render",
            "type_name": "opengl",
            "valid_renderer": True,
        },
        "status": status,
    }
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def _proof_workspace() -> tempfile.TemporaryDirectory[str]:
    return tempfile.TemporaryDirectory()


class HfxSingleFrameProverTracerBulletTests(unittest.TestCase):
    def test_placeholder_audit_raises_and_main_exits_2_without_popen_or_ledger(self) -> None:
        with _proof_workspace() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            hip_file = temp_dir / "asset.hip"
            hip_file.write_text("fake hip", encoding="utf-8")
            audit_json = temp_dir / "audit.json"
            _write_audit_json(
                audit_json,
                hip_file=hip_file,
                status="FAIL",
                classification="Placeholder Guide",
                effective_point_count=999,
            )
            fake_hython = temp_dir / "hython"
            _write_fake_hython(fake_hython)

            with self.assertRaisesRegex(
                prover.HfxSingleFrameProofError,
                "not a Real Asset PASS",
            ):
                prover.load_admitted_audit(audit_json)

            stdout = io.StringIO()
            with (
                patch("subprocess.run") as subprocess_run,
                patch("kernel.vfx.hfx_single_frame_prover.subprocess.Popen") as popen,
                patch("kernel.vfx.hfx_single_frame_prover.record_render_artifact") as ledger,
                redirect_stdout(stdout),
            ):
                exit_code = prover.main(
                    [
                        "--audit-json",
                        audit_json.as_posix(),
                        "--hython",
                        fake_hython.as_posix(),
                        "--output-root",
                        (temp_dir / "renders").as_posix(),
                    ]
                )

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 2)
            self.assertFalse(payload["complete"])
            self.assertIn("not a Real Asset PASS", payload["error"])
            subprocess_run.assert_not_called()
            popen.assert_not_called()
            ledger.assert_not_called()

    def test_zero_kb_frame_is_rejected_exit_2_and_never_ledgered(self) -> None:
        with _proof_workspace() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            hip_file = temp_dir / "asset.hip"
            hip_file.write_text("fake hip", encoding="utf-8")
            audit_json = temp_dir / "audit.json"
            _write_audit_json(audit_json, hip_file=hip_file)
            fake_hython = temp_dir / "hython"
            _write_fake_hython(fake_hython)

            zero_byte_frame = temp_dir / "zero.exr"
            zero_byte_frame.write_bytes(b"")
            with self.assertRaisesRegex(prover.HfxSingleFrameProofError, "0 bytes"):
                prover._validate_rendered_frame(
                    zero_byte_frame,
                    image_extension="exr",
                    minimum_frame_bytes=1,
                )

            stdout = io.StringIO()
            with (
                patch("subprocess.run") as subprocess_run,
                patch(
                    "kernel.vfx.hfx_single_frame_prover.subprocess.Popen",
                    side_effect=lambda *args, **kwargs: _ZeroByteFramePopen(*args, **kwargs),
                ) as popen,
                patch("kernel.vfx.hfx_single_frame_prover.record_render_artifact") as ledger,
                redirect_stdout(stdout),
            ):
                exit_code = prover.main(
                    [
                        "--audit-json",
                        audit_json.as_posix(),
                        "--hython",
                        fake_hython.as_posix(),
                        "--output-root",
                        (temp_dir / "renders").as_posix(),
                        "--minimum-frame-bytes",
                        "1",
                    ]
                )

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 2)
            self.assertFalse(payload["complete"])
            self.assertEqual(len(payload["attempts"]), 1)
            self.assertIn("0 bytes", payload["attempts"][0]["failure"])
            subprocess_run.assert_not_called()
            self.assertEqual(popen.call_count, 1)
            ledger.assert_not_called()

    def test_all_black_payload_is_rejected_exit_2_and_never_ledgered(self) -> None:
        with _proof_workspace() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            hip_file = temp_dir / "asset.hip"
            hip_file.write_text("fake hip", encoding="utf-8")
            audit_json = temp_dir / "audit.json"
            _write_audit_json(audit_json, hip_file=hip_file)
            fake_hython = temp_dir / "hython"
            _write_fake_hython(fake_hython)

            stdout = io.StringIO()
            with (
                patch(
                    "kernel.vfx.hfx_single_frame_prover.subprocess.Popen",
                    side_effect=lambda *args, **kwargs: _AllBlackPayloadPopen(*args, **kwargs),
                ),
                patch("kernel.vfx.hfx_single_frame_prover.record_render_artifact") as ledger,
                redirect_stdout(stdout),
            ):
                exit_code = prover.main(
                    [
                        "--audit-json",
                        audit_json.as_posix(),
                        "--hython",
                        fake_hython.as_posix(),
                        "--output-root",
                        (temp_dir / "renders").as_posix(),
                        "--minimum-frame-bytes",
                        "1",
                    ]
                )

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 2)
            self.assertFalse(payload["complete"])
            self.assertIn("all zero bytes", payload["attempts"][0]["failure"])
            ledger.assert_not_called()

    def test_valid_frame_uses_mocked_popen_and_mocked_ledger_only(self) -> None:
        with _proof_workspace() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            hip_file = temp_dir / "asset.hip"
            hip_file.write_text("fake hip", encoding="utf-8")
            audit_json = temp_dir / "audit.json"
            _write_audit_json(audit_json, hip_file=hip_file)
            fake_hython = temp_dir / "hython"
            _write_fake_hython(fake_hython)
            ledger_mock: Mock = Mock(return_value=_FakeLedgerRecord())

            with (
                patch("subprocess.run") as subprocess_run,
                patch(
                    "kernel.vfx.hfx_single_frame_prover.subprocess.Popen",
                    side_effect=lambda *args, **kwargs: _ValidFramePopen(*args, **kwargs),
                ) as popen,
                patch(
                    "kernel.vfx.hfx_single_frame_prover.record_render_artifact",
                    ledger_mock,
                ),
            ):
                result = prover.prove_single_frame(
                    audit_json,
                    output_root=temp_dir / "renders",
                    hython_executable=fake_hython,
                    minimum_frame_bytes=1,
                )

            self.assertTrue(result.complete)
            self.assertIsNotNone(result.ledger_record)
            subprocess_run.assert_not_called()
            self.assertEqual(popen.call_count, 1)
            self.assertEqual(ledger_mock.call_count, 1)
            ledger_kwargs = ledger_mock.call_args.kwargs
            self.assertEqual(ledger_kwargs["sequence_glob"], "hfx_single_frame_proof.*.exr")
            self.assertEqual(
                ledger_kwargs["metadata"]["executor"],
                "kernel.vfx.hfx_single_frame_prover",
            )


if __name__ == "__main__":
    unittest.main()
