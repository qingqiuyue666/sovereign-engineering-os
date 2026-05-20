"""Read-only Job Queue page backed by QTableView and QAbstractTableModel."""

from __future__ import annotations

from apps.ui import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
    Signal,
)
from apps.ui.models import JobQueueTableModel
from apps.ui.read_models import JobRow, RuntimeSnapshot
from apps.ui.status_chip_delegate import StatusChipDelegate


class JobQueuePage(QWidget):
    job_selected = Signal(object)

    def __init__(self, parent: object | None = None) -> None:
        super().__init__(parent)
        self.model = JobQueueTableModel()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

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
        self.table.setItemDelegateForColumn(2, StatusChipDelegate(self.table))

        controls = QFrame(self)
        control_layout = QHBoxLayout(controls)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.addStretch(1)
        self.cancel_button = QPushButton("Cancel (Phase 2)", controls)
        self.retry_button = QPushButton("Retry (Phase 2)", controls)
        self.cancel_button.setEnabled(False)
        self.retry_button.setEnabled(False)
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

    def _selection_changed(self, *_args: object) -> None:
        indexes = self.table.selectionModel().selectedRows() if self.table.selectionModel() is not None else []
        if not indexes:
            self.job_selected.emit(None)
            return
        job = self.model.job_at(int(indexes[0].row()))
        self.job_selected.emit(job)
