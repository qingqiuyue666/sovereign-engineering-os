"""Bottom live event stream for bounded technical telemetry."""

from __future__ import annotations

from apps.ui import QPlainTextEdit
from apps.ui.read_models import EventRow, RuntimeSnapshot

MAX_EVENT_BLOCKS = 1_000


class LiveEventStream(QPlainTextEdit):
    def __init__(self, parent: object | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("LiveEventStream")
        self.setReadOnly(True)
        self.setMaximumBlockCount(MAX_EVENT_BLOCKS)
        self.setMinimumHeight(150)

    def render_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        self.setPlainText("\n".join(event.line() for event in snapshot.latest_events))

    def append_event(self, event: EventRow) -> None:
        self.appendPlainText(event.line())

    def capped_blocks(self) -> int:
        return MAX_EVENT_BLOCKS
