"""Tests for SEOS JSON-RPC cross-DCC probe."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from execution_plane.rpc_gateway import invoke_rpc


class SeosRpcCrossDccProbeV1Tests(unittest.TestCase):
    def test_cross_dcc_probe_writes_workflow_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            payload = json.loads(Path("examples/rpc/cross_dcc_probe.json").read_text(encoding="utf-8"))
            payload["params"]["output_root"] = str(Path(tempdir) / "rpc")
            response = invoke_rpc(payload)
            receipt_path = Path(tempdir) / "rpc" / "workflow_receipt.json"
            self.assertTrue(receipt_path.exists())
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(response["jsonrpc"], "2.0")
        result = response["result"]
        self.assertEqual(result["workflow_id"], "cross_dcc_probe_v1")
        self.assertIn(result["terminal_status"], {"TERMINAL_SUCCEEDED", "TERMINAL_FAILED"})
        self.assertEqual(len(result["node_results"]), 4)
        fake_node = next(item for item in result["node_results"] if item["node_id"] == "fake_probe")
        self.assertEqual(fake_node["result"]["status"], "SUCCEEDED")
        self.assertTrue(fake_node["result"]["artifact_refs"])
        self.assertNotIn(tempdir, json.dumps(result, sort_keys=True))
        self.assertEqual(receipt["workflow_id"], result["workflow_id"])


if __name__ == "__main__":
    unittest.main()
