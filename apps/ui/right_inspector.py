"""Global right inspector for selected console objects."""

from __future__ import annotations

from apps.ui import QFrame, QFormLayout, QLabel, QVBoxLayout
from apps.ui.read_models import EventRow, JobRow


class RightInspector(QFrame):
    def __init__(self, parent: object | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Inspector")
        self.setFixedWidth(280)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        title = QLabel("Inspector", self)
        title.setObjectName("InspectorTitle")
        layout.addWidget(title)
        self.state_label = QLabel("No Selection", self)
        self.state_label.setProperty("role", "eyebrow")
        layout.addWidget(self.state_label)
        self.form = QFormLayout()
        self.form.setSpacing(7)
        layout.addLayout(self.form)
        layout.addStretch(1)
        self._labels: list[QLabel] = []
        self.show_no_selection()

    def show_no_selection(self) -> None:
        self._render("No Selection", {"state": "Select a job, event, or artifact"})

    def show_job(self, job: JobRow | None) -> None:
        if job is None:
            self.show_no_selection()
            return
        self._render("Selected Job", job.metadata())

    def show_event(self, event: EventRow | None) -> None:
        if event is None:
            self.show_no_selection()
            return
        self._render(
            "Selected Event",
            {
                "event_id": event.event_id,
                "job_id": event.job_id,
                "sequence": event.sequence,
                "event_type": event.event_type,
                "occurred_at": event.occurred_at,
                "reason": event.reason,
            },
        )

    def show_artifact_placeholder(self, artifact_id: str = "") -> None:
        self._render(
            "Selected Artifact",
            {
                "artifact_id": artifact_id or "Placeholder: Phase 2",
                "state": "Placeholder: Phase 2",
            },
        )

    def values(self) -> dict[str, str]:
        return {self.form.itemAt(index * 2).widget().text(): self.form.itemAt(index * 2 + 1).widget().text() for index in range(self.form.rowCount())}

    def _render(self, state: str, values: dict[str, object]) -> None:
        self._clear()
        self.state_label.setText(state)
        for key, value in values.items():
            key_label = QLabel(str(key), self)
            key_label.setProperty("role", "eyebrow")
            value_label = QLabel(str(value), self)
            value_label.setWordWrap(True)
            self.form.addRow(key_label, value_label)
            self._labels.extend([key_label, value_label])

    def _clear(self) -> None:
        while self.form.rowCount():
            self.form.removeRow(0)
        self._labels.clear()
