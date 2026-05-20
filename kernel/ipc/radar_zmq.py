"""Qt-safe ZeroMQ subscriber for the desktop Macro Radar surface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final
from urllib.parse import urlparse
import json
import threading
import time

try:
    from PySide6.QtCore import QObject, Signal, Slot

    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False

    class QObject:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

    class Signal:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def connect(self, *_args: object, **_kwargs: object) -> None:
            pass

        def emit(self, *_args: object, **_kwargs: object) -> None:
            pass

    def Slot(*_args: object, **_kwargs: object) -> object:
        def decorator(function: object) -> object:
            return function

        return decorator

__all__ = [
    "DEFAULT_RADAR_ENDPOINT",
    "PYSIDE6_AVAILABLE",
    "RadarEndpointRejected",
    "RadarEvent",
    "RadarZmqSubscriber",
    "parse_radar_event",
]

DEFAULT_RADAR_ENDPOINT: Final[str] = "tcp://127.0.0.1:5555"
_LOOPBACK_HOSTS: Final[frozenset[str]] = frozenset({"127.0.0.1", "localhost", "::1"})
_MAX_PAYLOAD_BYTES: Final[int] = 1_048_576
_POLL_TIMEOUT_MS: Final[int] = 250


class RadarEndpointRejected(ValueError):
    """Raised when a ZeroMQ endpoint is not a loopback tcp subscriber target."""


@dataclass(frozen=True, slots=True)
class RadarEvent:
    """Normalized market signal emitted from the ZeroMQ listener thread."""

    event_type: str
    topic: str
    symbol: str
    strength: float | None
    payload: dict[str, Any] = field(default_factory=dict)
    received_at: float = field(default_factory=time.time)

    @property
    def is_strong_signal(self) -> bool:
        return self.event_type == "STRONG_SIGNAL" or (
            self.strength is not None and self.strength >= 0.85
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "is_strong_signal": self.is_strong_signal,
            "payload": self.payload,
            "received_at": self.received_at,
            "strength": self.strength,
            "symbol": self.symbol,
            "topic": self.topic,
        }


class RadarZmqSubscriber(QObject):
    """Long-running ZeroMQ SUB worker intended to live inside a QThread."""

    status_changed = Signal(str)
    message_received = Signal(dict)
    strong_signal_detected = Signal(dict)
    error_occurred = Signal(str)
    finished = Signal()

    def __init__(
        self,
        endpoint: str = DEFAULT_RADAR_ENDPOINT,
        *,
        topic_filter: str = "",
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._endpoint = _validated_endpoint(endpoint)
        self._topic_filter = topic_filter
        self._stop_requested = threading.Event()

    @Slot()
    def run(self) -> None:
        socket = None
        poller = None
        try:
            import zmq

            context = zmq.Context.instance()
            socket = context.socket(zmq.SUB)
            socket.setsockopt(zmq.LINGER, 0)
            socket.setsockopt_string(zmq.SUBSCRIBE, self._topic_filter)
            socket.connect(self._endpoint)
            poller = zmq.Poller()
            poller.register(socket, zmq.POLLIN)
            self.status_changed.emit(f"SUB connected {self._endpoint}")
            while not self._stop_requested.is_set():
                events = dict(poller.poll(_POLL_TIMEOUT_MS))
                if socket not in events:
                    continue
                try:
                    topic, payload = _receive_payload(socket)
                    event = parse_radar_event(payload, topic=topic)
                except ValueError as exc:
                    self.error_occurred.emit(f"radar payload rejected: {exc}")
                    continue
                event_payload = event.as_dict()
                self.message_received.emit(event_payload)
                if event.is_strong_signal:
                    self.strong_signal_detected.emit(event_payload)
        except ImportError as exc:
            self.error_occurred.emit("pyzmq is required for Macro Radar IPC")
        except Exception as exc:
            self.error_occurred.emit(f"radar subscriber failed: {exc}")
        finally:
            if poller is not None and socket is not None:
                try:
                    poller.unregister(socket)
                except Exception:
                    pass
            if socket is not None:
                socket.close(linger=0)
            self.status_changed.emit("SUB stopped")
            self.finished.emit()

    @Slot()
    def stop(self) -> None:
        self._stop_requested.set()


def parse_radar_event(payload: bytes | str, *, topic: str = "") -> RadarEvent:
    """Parse a ZeroMQ payload into a bounded, Qt-friendly dict payload."""

    if isinstance(payload, bytes):
        if len(payload) > _MAX_PAYLOAD_BYTES:
            raise ValueError("radar payload exceeded maximum size")
        text = payload.decode("utf-8", errors="replace")
    else:
        text = payload
    text = text.strip()
    if not text:
        raise ValueError("radar payload was empty")

    decoded: dict[str, Any]
    try:
        material = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("radar payload must be valid JSON") from exc
    if not isinstance(material, dict):
        raise ValueError("radar payload JSON must be an object")
    decoded = dict(material)

    event_type = _string_field(decoded, "event_type") or _string_field(decoded, "signal") or _infer_event_type(text)
    symbol = _string_field(decoded, "symbol") or _string_field(decoded, "asset") or "UNKNOWN"
    payload_topic = _string_field(decoded, "topic")
    strength = _float_field(decoded, "strength")
    if strength is None:
        strength = _float_field(decoded, "confidence")
    return RadarEvent(
        event_type=event_type,
        topic=payload_topic or topic,
        symbol=symbol,
        strength=strength,
        payload=decoded,
    )


def _validated_endpoint(endpoint: str) -> str:
    parsed = urlparse(endpoint.strip())
    if parsed.scheme != "tcp":
        raise RadarEndpointRejected("radar endpoint must use tcp://")
    if parsed.hostname not in _LOOPBACK_HOSTS:
        raise RadarEndpointRejected("radar endpoint must be explicit loopback")
    if parsed.username or parsed.password:
        raise RadarEndpointRejected("radar endpoint credentials are not allowed")
    if not parsed.port:
        raise RadarEndpointRejected("radar endpoint must include an explicit port")
    if parsed.path not in {"", "/"}:
        raise RadarEndpointRejected("radar endpoint must not include a path")
    return endpoint.strip()


def _receive_payload(socket: Any) -> tuple[str, bytes]:
    frames = socket.recv_multipart()
    if not frames:
        raise ValueError("radar message contained no frames")
    if len(frames) == 1:
        return "", frames[0]
    topic = frames[0].decode("utf-8", errors="replace")
    return topic, frames[-1]


def _string_field(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if isinstance(value, str):
        return value.strip()
    return ""


def _float_field(payload: dict[str, Any], key: str) -> float | None:
    value = payload.get(key)
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _infer_event_type(text: str) -> str:
    upper_text = text.upper()
    if "STRONG_SIGNAL" in upper_text:
        return "STRONG_SIGNAL"
    return "MARKET_EVENT"
