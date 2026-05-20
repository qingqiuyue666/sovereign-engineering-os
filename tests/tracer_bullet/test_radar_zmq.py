"""Tracer-bullet tests for the desktop ZeroMQ radar boundary."""

from __future__ import annotations

import json
import unittest

from kernel.ipc.radar_zmq import (
    RadarEndpointRejected,
    RadarZmqSubscriber,
    parse_radar_event,
)


class RadarZmqTests(unittest.TestCase):
    def test_malformed_payload_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "valid JSON"):
            parse_radar_event(b"{not-json", topic="macro")

    def test_non_object_json_payload_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "object"):
            parse_radar_event(json.dumps(["STRONG_SIGNAL"]).encode("utf-8"))

    def test_valid_strong_signal_payload_is_normalized(self) -> None:
        payload = {
            "event_type": "STRONG_SIGNAL",
            "symbol": "ES",
            "strength": 0.91,
            "topic": "macro",
        }

        event = parse_radar_event(json.dumps(payload).encode("utf-8"))

        self.assertTrue(event.is_strong_signal)
        self.assertEqual(event.symbol, "ES")
        self.assertEqual(event.topic, "macro")

    def test_non_loopback_endpoint_is_rejected(self) -> None:
        with self.assertRaises(RadarEndpointRejected):
            RadarZmqSubscriber("tcp://10.0.0.7:5555")


if __name__ == "__main__":
    unittest.main()
