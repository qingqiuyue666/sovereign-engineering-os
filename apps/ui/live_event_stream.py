"""Compact bottom event stream for bounded black-box telemetry."""

from __future__ import annotations

from apps.ui import QFrame, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout
from apps.ui.i18n import UiText
from apps.ui.read_models import EventRow, RuntimeSnapshot

MAX_EVENT_BLOCKS = 120
COLLAPSED_HEIGHT = 42
EXPANDED_HEIGHT = 120


class LiveEventStream(QFrame):
    def __init__(self, parent: object | None = None, *, language: str = "en") -> None:
        super().__init__(parent)
        self.text = UiText(language)
        self.setObjectName("LiveEventStreamFrame")
        self._expanded = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title_bar = QFrame(self)
        title_bar.setObjectName("EventStreamTitleBar")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(12, 4, 12, 4)
        self.title = QLabel(self._title_text(), title_bar)
        self.title.setObjectName("EventStreamTitle")
        self.title.setProperty("role", "eyebrow")
        self.count_label = QLabel("0", title_bar)
        self.toggle_button = QPushButton("Show", title_bar)
        clicked = getattr(self.toggle_button, "clicked", None)
        if hasattr(clicked, "connect"):
            clicked.connect(self.toggle_expanded)
        title_layout.addWidget(self.title)
        title_layout.addStretch(1)
        title_layout.addWidget(self.count_label)
        title_layout.addWidget(self.toggle_button)
        layout.addWidget(title_bar)

        self.editor = QPlainTextEdit(self)
        self.editor.setObjectName("LiveEventStream")
        self.editor.setReadOnly(True)
        self.editor.setMaximumBlockCount(MAX_EVENT_BLOCKS)
        self.editor.setMaximumHeight(EXPANDED_HEIGHT)
        layout.addWidget(self.editor)
        self.set_expanded(False)

    def render_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        rows = tuple(snapshot.latest_events[-MAX_EVENT_BLOCKS:])
        self.editor.setPlainText("\n".join(_structured_event_line(event) for event in rows))
        self.count_label.setText(str(len(rows)))
        self.setToolTip(f"{len(rows)} canonical event records")

    def append_event(self, event: EventRow) -> None:
        self.editor.appendPlainText(_structured_event_line(event))

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = bool(expanded)
        self.editor.setVisible(self._expanded)
        self.setMinimumHeight(EXPANDED_HEIGHT if self._expanded else COLLAPSED_HEIGHT)
        self.setMaximumHeight(EXPANDED_HEIGHT if self._expanded else COLLAPSED_HEIGHT)
        self.toggle_button.setText("Hide" if self._expanded else "Show")

    def toggle_expanded(self) -> None:
        self.set_expanded(not self._expanded)

    def is_expanded(self) -> bool:
        return self._expanded

    def capped_blocks(self) -> int:
        return MAX_EVENT_BLOCKS

    def rendered_lines(self) -> tuple[str, ...]:
        text = self.editor.toPlainText() if hasattr(self.editor, "toPlainText") else ""
        return tuple(line for line in text.splitlines() if line)

    def title_text(self) -> str:
        return self.title.text()

    def apply_language(self, language: str) -> None:
        self.text.set_language(language)
        self.title.setText(self._title_text())

    def _title_text(self) -> str:
        return f"{self.text.tr('event_stream.title')} / {self.text.tr('event_stream.black_box')}"


def _structured_event_line(event: EventRow) -> str:
    return " | ".join(
        (
            _event_severity(event),
            event.occurred_at,
            event.event_type,
            event.job_id,
            event.reason or "--",
        )
    )


def _event_severity(event: EventRow) -> str:
    text = f"{event.event_type} {event.reason}".lower()
    if "failed" in text or "quarantined" in text or "rejected" in text:
        return "error"
    if "blocked" in text or "warning" in text:
        return "warning"
    return "info"
