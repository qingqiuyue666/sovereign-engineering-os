"""Global right inspector for selected console objects."""

from __future__ import annotations

from apps.ui import QFrame, QFormLayout, QLabel, QVBoxLayout
from apps.ui.i18n import UiText
from apps.ui.read_models import ArtifactRow, EventRow, JobRow


class RightInspector(QFrame):
    def __init__(self, parent: object | None = None, *, language: str = "en") -> None:
        super().__init__(parent)
        self.text = UiText(language)
        self.setObjectName("Inspector")
        self.setFixedWidth(320)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        self.title = QLabel("Inspector", self)
        self.title.setObjectName("InspectorTitle")
        layout.addWidget(self.title)
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
                "artifact_id": artifact_id or "--",
                "state": "Metadata projection pending",
            },
        )

    def show_artifact(self, artifact: ArtifactRow | None) -> None:
        if artifact is None:
            self.show_no_selection()
            return
        self._render("Selected Artifact", artifact.metadata())

    def show_system_health(self, values: dict[str, object]) -> None:
        self._render("System Health", values)

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

    def apply_language(self, language: str) -> None:
        self.text.set_language(language)
        self.title.setText("Inspector")

    def _clear(self) -> None:
        while self.form.rowCount():
            self.form.removeRow(0)
        self._labels.clear()
