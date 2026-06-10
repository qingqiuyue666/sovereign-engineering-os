"""Failure Quarantine page for read-only incident inspection."""

from __future__ import annotations

from apps.ui import QFrame, QGridLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget
from apps.ui.i18n import UiText
from apps.ui.read_models import JobRow, RuntimeSnapshot

FAILURE_QUARANTINE_FIELDS: tuple[str, ...] = (
    "failed jobs list",
    "failed worker",
    "failure reason",
    "traceback excerpt",
    "event trail",
    "quarantine path",
    "retry allowed",
    "recommended fix",
    "export failure bundle",
)


class FailureQuarantinePage(QWidget):
    def __init__(self, parent: object | None = None, *, language: str = "en") -> None:
        super().__init__(parent)
        self.text = UiText(language)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        self.title = QLabel(self.text.tr("page.failure_quarantine"), self)
        self.title.setObjectName("FailureQuarantineTitle")
        layout.addWidget(self.title)

        grid = QGridLayout()
        grid.setSpacing(10)
        self.failed_jobs = QLabel("--", self)
        self.failed_worker = QLabel("--", self)
        self.failure_reason = QLabel("--", self)
        self.event_trail = QLabel("--", self)
        self.quarantine_path = QLabel("--", self)
        self.retry_allowed = QLabel("Blocked until reviewed", self)
        self.recommended_fix = QLabel("Inspect worker evidence and repair input contract", self)
        for widget in (
            self.failed_jobs,
            self.failed_worker,
            self.failure_reason,
            self.event_trail,
            self.quarantine_path,
            self.retry_allowed,
            self.recommended_fix,
        ):
            widget.setWordWrap(True)

        panels = (
            ("failed jobs list", self.failed_jobs),
            (self.text.tr("failure.failed_worker"), self.failed_worker),
            (self.text.tr("failure.failure_reason"), self.failure_reason),
            (self.text.tr("failure.event_trail"), self.event_trail),
            (self.text.tr("failure.quarantine_path"), self.quarantine_path),
            (self.text.tr("failure.retry_allowed"), self.retry_allowed),
            (self.text.tr("failure.recommended_fix"), self.recommended_fix),
        )
        for index, (label, widget) in enumerate(panels):
            grid.addWidget(_panel(label, widget), index // 2, index % 2)
        layout.addLayout(grid)

        self.traceback_excerpt = QPlainTextEdit(self)
        self.traceback_excerpt.setObjectName("TracebackExcerptPanel")
        self.traceback_excerpt.setReadOnly(True)
        self.traceback_excerpt.setPlainText("traceback excerpt unavailable in read-only projection")
        self.traceback_excerpt.setMinimumHeight(110)
        layout.addWidget(_panel(self.text.tr("failure.traceback_excerpt"), self.traceback_excerpt))

        self.export_bundle_button = QPushButton(self.text.tr("failure.export_bundle"), self)
        self.export_bundle_button.setEnabled(False)
        self.export_bundle_button.setToolTip(self.text.tr("common.disabled_until_facade"))
        layout.addWidget(self.export_bundle_button)

    def render_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        failed = tuple(job for job in snapshot.latest_jobs if job.status in {"Failed", "Quarantined"})
        self.render_failed_jobs(failed)
        if snapshot.latest_events:
            self.event_trail.setText("\n".join(event.line() for event in snapshot.latest_events[-4:]))

    def render_failed_jobs(self, jobs: tuple[JobRow, ...]) -> None:
        if not jobs:
            self.failed_jobs.setText("No failed jobs in current projection")
            self.failed_worker.setText("--")
            self.failure_reason.setText("--")
            self.quarantine_path.setText("--")
            return
        first = jobs[0]
        self.failed_jobs.setText("\n".join(f"{job.job_id} | {job.status}" for job in jobs))
        self.failed_worker.setText(first.worker or "Unknown")
        self.failure_reason.setText(first.failure_reason or first.quarantine_reason or "Reason not projected")
        self.quarantine_path.setText(f"local quarantine projection for {first.job_id}")

    def action_controls(self) -> tuple[QPushButton, ...]:
        return (self.export_bundle_button,)

    def required_fields(self) -> tuple[str, ...]:
        return FAILURE_QUARANTINE_FIELDS

    def apply_language(self, language: str) -> None:
        self.text.set_language(language)
        self.title.setText(self.text.tr("page.failure_quarantine"))
        self.export_bundle_button.setText(self.text.tr("failure.export_bundle"))
        self.export_bundle_button.setToolTip(self.text.tr("common.disabled_until_facade"))


def _panel(title: str, content: QWidget) -> QFrame:
    panel = QFrame()
    panel.setProperty("role", "metricCard")
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(12, 10, 12, 10)
    label = QLabel(title, panel)
    label.setProperty("role", "eyebrow")
    layout.addWidget(label)
    layout.addWidget(content)
    return panel
