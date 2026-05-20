"""Read-only Artifact Store page for local artifact metadata."""

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
from apps.ui.models import ARTIFACT_STORE_COLUMNS, ArtifactStoreTableModel
from apps.ui.read_models import ArtifactRow, RuntimeSnapshot

ARTIFACT_STORE_REQUIRED_FIELDS: tuple[str, ...] = (
    "type",
    "artifact_id",
    "job_id",
    "sha256",
    "size",
    "review_status",
    "quarantine_status",
    "local_only",
    "safe_to_publish",
)


class ArtifactStorePage(QWidget):
    artifact_selected = Signal(object)

    def __init__(self, parent: object | None = None, *, language: str = "en") -> None:
        super().__init__(parent)
        self.text = UiText(language)
        self.model = ArtifactStoreTableModel()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        self.title = QLabel(self.text.tr("page.artifact_store"), self)
        self.title.setObjectName("ArtifactStoreTitle")
        layout.addWidget(self.title)

        body = QHBoxLayout()
        self.table = QTableView(self)
        self.table.setObjectName("ArtifactStoreTable")
        self.table.setModel(self.model)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        body.addWidget(self.table, stretch=3)

        self.preview = QFrame(self)
        self.preview.setObjectName("ArtifactPreview")
        preview_layout = QVBoxLayout(self.preview)
        preview_layout.setContentsMargins(12, 12, 12, 12)
        self.preview_title = QLabel(self.text.tr("common.preview_placeholder"), self.preview)
        self.preview_title.setProperty("role", "eyebrow")
        self.preview_metadata = QLabel("artifact_id: --\nsha256: --\nreview_status: --", self.preview)
        self.preview_metadata.setWordWrap(True)
        self.open_folder_button = QPushButton(self.text.tr("artifact.open_folder"), self.preview)
        self.open_folder_button.setEnabled(False)
        self.open_folder_button.setToolTip(self.text.tr("common.disabled_until_facade"))
        preview_layout.addWidget(self.preview_title)
        preview_layout.addWidget(self.preview_metadata)
        preview_layout.addStretch(1)
        preview_layout.addWidget(self.open_folder_button)
        body.addWidget(self.preview, stretch=1)
        layout.addLayout(body, stretch=1)

        selection_model = self.table.selectionModel()
        if selection_model is not None:
            selection_model.selectionChanged.connect(self._selection_changed)

    def render_snapshot(self, snapshot: RuntimeSnapshot) -> None:
        self.model.set_artifacts(snapshot.latest_artifacts)
        if snapshot.latest_artifacts:
            self.show_artifact(snapshot.latest_artifacts[0])

    def show_artifact(self, artifact: ArtifactRow | None) -> None:
        if artifact is None:
            self.preview_metadata.setText("artifact_id: --\nsha256: --\nreview_status: --")
            return
        self.preview_metadata.setText(
            "\n".join(
                (
                    f"artifact_id: {artifact.artifact_id}",
                    f"job_id: {artifact.job_id}",
                    f"sha256: {artifact.sha256_short()}",
                    f"review_status: {artifact.review_status}",
                    f"quarantine_status: {artifact.quarantine_status}",
                    f"local_only: {artifact.local_only}",
                    f"safe_to_publish: {artifact.safe_to_publish}",
                )
            )
        )

    def action_controls(self) -> tuple[QPushButton, ...]:
        return (self.open_folder_button,)

    def required_fields(self) -> tuple[str, ...]:
        return ARTIFACT_STORE_REQUIRED_FIELDS

    def column_keys(self) -> tuple[str, ...]:
        return tuple(key for key, _label in ARTIFACT_STORE_COLUMNS)

    def apply_language(self, language: str) -> None:
        self.text.set_language(language)
        self.title.setText(self.text.tr("page.artifact_store"))
        self.preview_title.setText(self.text.tr("common.preview_placeholder"))
        self.open_folder_button.setText(self.text.tr("artifact.open_folder"))
        self.open_folder_button.setToolTip(self.text.tr("common.disabled_until_facade"))

    def _selection_changed(self, *_args: object) -> None:
        indexes = self.table.selectionModel().selectedRows() if self.table.selectionModel() is not None else []
        if not indexes:
            self.show_artifact(None)
            self.artifact_selected.emit(None)
            return
        artifact = self.model.artifact_at(int(indexes[0].row()))
        self.show_artifact(artifact)
        self.artifact_selected.emit(artifact)
