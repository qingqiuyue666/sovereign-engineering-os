"""Read-only Job Queue page backed by QTableView and QAbstractTableModel."""

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
from apps.ui.models import JobQueueTableModel
from apps.ui.read_models import JobRow, RuntimeSnapshot
from apps.ui.status_chip_delegate import StatusChipDelegate


class JobQueuePage(QWidget):
    job_selected = Signal(object)

    def __init__(self, parent: object | None = None, *, language: str = "en") -> None:
        super().__init__(parent)
        self.text = UiText(language)
        self.model = JobQueueTableModel()
        self.model.set_language(language)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        self.title = QLabel(self.text.tr("page.job_queue"), self)
        self.title.setObjectName("JobQueueTitle")
        layout.addWidget(self.title)

        self.filter_strip = QLabel(self.text.tr("job_queue.search"), self)
        self.filter_strip.setObjectName("JobQueueFilterStrip")
        self.filter_strip.setProperty("role", "eyebrow")
        layout.addWidget(self.filter_strip)

        self.table = QTableView(self)
        self.table.setObjectName("JobQueueTable")
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
        self.cancel_button = QPushButton(self.text.tr("job_queue.cancel"), controls)
        self.retry_button = QPushButton(self.text.tr("job_queue.retry"), controls)
        self.cancel_button.setEnabled(False)
        self.retry_button.setEnabled(False)
        self.cancel_button.setToolTip(self.text.tr("common.disabled_until_facade"))
        self.retry_button.setToolTip(self.text.tr("common.disabled_until_facade"))
        control_layout.addWidget(self.cancel_button)
        control_layout.addWidget(self.retry_button)

        layout.addWidget(self.table, stretch=1)
        layout.addWidget(controls)

        selection_model = self.table.selectionModel()
        if selection_model is not None:
            selection_model.selectionChanged.connect(self._selection_changed)

    def render_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        self.model.set_jobs(snapshot.latest_jobs)

    def action_controls(self) -> tuple[QPushButton, ...]:
        return (self.cancel_button, self.retry_button)

    def selected_job_at(self, row: int) -> JobRow | None:
        return self.model.job_at(row)

    def apply_language(self, language: str) -> None:
        self.text.set_language(language)
        self.title.setText(self.text.tr("page.job_queue"))
        self.filter_strip.setText(self.text.tr("job_queue.search"))
        self.cancel_button.setText(self.text.tr("job_queue.cancel"))
        self.retry_button.setText(self.text.tr("job_queue.retry"))
        self.cancel_button.setToolTip(self.text.tr("common.disabled_until_facade"))
        self.retry_button.setToolTip(self.text.tr("common.disabled_until_facade"))
        self.model.set_language(language)
        self.status_delegate.set_language(language)

    def _selection_changed(self, *_args: object) -> None:
        indexes = self.table.selectionModel().selectedRows() if self.table.selectionModel() is not None else []
        if not indexes:
            self.job_selected.emit(None)
            return
        job = self.model.job_at(int(indexes[0].row()))
        self.job_selected.emit(job)
