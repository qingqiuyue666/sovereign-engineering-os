"""Runs view absorbing the old job queue and worker execution trail."""

from __future__ import annotations

from apps.ui import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
    Signal,
)
from apps.ui.i18n import UiText
from apps.ui.models import JOB_QUEUE_COLUMNS, JobQueueTableModel
from apps.ui.read_models import JobRow, RuntimeSnapshot
from apps.ui.status_chip_delegate import StatusChipDelegate

RUNS_REQUIRED_FIELDS: tuple[str, ...] = (
    "run table",
    "selected run inspector handoff",
    "status chips",
    "worker",
    "runtime",
    "event count",
    "artifact count",
    "failure reason",
    "human review required",
    "filters/search",
)


class RunsPage(QWidget):
    run_selected = Signal(object)

    def __init__(self, parent: object | None = None, *, language: str = "en") -> None:
        super().__init__(parent)
        self.text = UiText(language)
        self.model = JobQueueTableModel()
        self.model.set_language(language)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        self.title = QLabel(self.text.tr("page.runs"), self)
        self.title.setObjectName("RunsTitle")
        layout.addWidget(self.title)

        self.filter_strip = QLabel(self.text.tr("runs.filters"), self)
        self.filter_strip.setObjectName("RunsFilterStrip")
        self.filter_strip.setProperty("role", "eyebrow")
        layout.addWidget(self.filter_strip)

        self.table = QTableView(self)
        self.table.setObjectName("RunsTable")
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.status_delegate = StatusChipDelegate(self.table, language=language)
        self.table.setItemDelegateForColumn(2, self.status_delegate)

        controls = QFrame(self)
        control_layout = QHBoxLayout(controls)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.addStretch(1)
        self.cancel_button = QPushButton(self.text.tr("runs.cancel"), controls)
        self.retry_button = QPushButton(self.text.tr("runs.retry"), controls)
        for button in (self.cancel_button, self.retry_button):
            button.setEnabled(False)
            button.setToolTip(self.text.tr("common.disabled_until_facade"))
            control_layout.addWidget(button)

        layout.addWidget(self.table, stretch=1)
        layout.addWidget(controls)

        selection_model = self.table.selectionModel()
        if selection_model is not None:
            selection_model.selectionChanged.connect(self._selection_changed)

    def render_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        self.model.set_jobs(snapshot.latest_jobs)

    def action_controls(self) -> tuple[QPushButton, ...]:
        return (self.cancel_button, self.retry_button)

    def selected_run_at(self, row: int) -> JobRow | None:
        return self.model.job_at(row)

    def required_fields(self) -> tuple[str, ...]:
        return RUNS_REQUIRED_FIELDS

    def column_keys(self) -> tuple[str, ...]:
        return tuple(key for key, _label in JOB_QUEUE_COLUMNS)

    def absorbed_domains(self) -> tuple[str, ...]:
        return ("Job Queue", "worker status", "event trail", "execution state")

    def apply_language(self, language: str) -> None:
        self.text.set_language(language)
        self.title.setText(self.text.tr("page.runs"))
        self.filter_strip.setText(self.text.tr("runs.filters"))
        self.cancel_button.setText(self.text.tr("runs.cancel"))
        self.retry_button.setText(self.text.tr("runs.retry"))
        for button in self.action_controls():
            button.setToolTip(self.text.tr("common.disabled_until_facade"))
        self.model.set_language(language)
        self.status_delegate.set_language(language)

    def _selection_changed(self, *_args: object) -> None:
        indexes = self.table.selectionModel().selectedRows() if self.table.selectionModel() is not None else []
        if not indexes:
            self.run_selected.emit(None)
            return
        run = self.model.job_at(int(indexes[0].row()))
        self.run_selected.emit(run)
