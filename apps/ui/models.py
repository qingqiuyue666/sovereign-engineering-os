"""Qt table models for bounded Sovereign Console read models."""

from __future__ import annotations

from apps.ui import QAbstractTableModel, QModelIndex, Qt
from apps.ui.i18n import localize_status
from apps.ui.read_models import ArtifactRow, JobRow
from apps.ui.status_chip_delegate import normalize_status_label

JOB_QUEUE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("job_id", "Job ID"),
    ("job_type", "Job Type"),
    ("status", "Status"),
    ("worker", "Worker"),
    ("created_at", "Created"),
    ("runtime", "Runtime"),
    ("event_count", "Events"),
    ("artifact_count", "Artifacts"),
    ("human_review_required", "Human Review"),
    ("failure_reason", "Failure Reason"),
)

ARTIFACT_STORE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("artifact_type", "Type"),
    ("artifact_id", "Artifact ID"),
    ("job_id", "Job ID"),
    ("sha256", "SHA256"),
    ("size_bytes", "Size"),
    ("review_status", "Review"),
    ("quarantine_status", "Quarantine"),
    ("local_only", "Local-only"),
    ("safe_to_publish", "Safe to Publish"),
)


class JobQueueTableModel(QAbstractTableModel):
    """Read-only QAbstractTableModel for the Phase 1 job queue page."""

    def __init__(self, jobs: list[JobRow] | tuple[JobRow, ...] | None = None, parent: object | None = None) -> None:
        super().__init__(parent)
        self._jobs = list(jobs or [])
        self._language = "en"

    def rowCount(self, _parent: QModelIndex | None = None) -> int:  # noqa: N802 - Qt API.
        return len(self._jobs)

    def columnCount(self, _parent: QModelIndex | None = None) -> int:  # noqa: N802 - Qt API.
        return len(JOB_QUEUE_COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object | None:
        if not _index_is_valid(index):
            return None
        row = int(index.row())
        column = int(index.column())
        if row < 0 or row >= len(self._jobs) or column < 0 or column >= len(JOB_QUEUE_COLUMNS):
            return None
        job = self._jobs[row]
        key = JOB_QUEUE_COLUMNS[column][0]
        if role == Qt.ItemDataRole.DisplayRole:
            value = getattr(job, key)
            if key == "status":
                return localize_status(normalize_status_label(value), self._language)
            if key == "human_review_required":
                return "Required" if value else "No"
            return str(value)
        if role == Qt.ItemDataRole.TextAlignmentRole and key in {"event_count", "artifact_count"}:
            return Qt.AlignmentFlag.AlignCenter
        if role == Qt.ItemDataRole.UserRole:
            return job
        return None

    def headerData(  # noqa: N802 - Qt API.
        self,
        section: int,
        orientation: object,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object | None:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal and 0 <= int(section) < len(JOB_QUEUE_COLUMNS):
            return JOB_QUEUE_COLUMNS[int(section)][1]
        return int(section) + 1

    def flags(self, index: QModelIndex) -> object:
        if not _index_is_valid(index):
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def set_jobs(self, jobs: list[JobRow] | tuple[JobRow, ...]) -> None:
        self.beginResetModel()
        self._jobs = list(jobs)
        self.endResetModel()

    def set_language(self, language: str) -> None:
        self._language = language
        self.beginResetModel()
        self.endResetModel()

    def job_at(self, row: int) -> JobRow | None:
        if row < 0 or row >= len(self._jobs):
            return None
        return self._jobs[row]


class ArtifactStoreTableModel(QAbstractTableModel):
    """Read-only QAbstractTableModel for artifact metadata projections."""

    def __init__(
        self,
        artifacts: list[ArtifactRow] | tuple[ArtifactRow, ...] | None = None,
        parent: object | None = None,
    ) -> None:
        super().__init__(parent)
        self._artifacts = list(artifacts or [])

    def rowCount(self, _parent: QModelIndex | None = None) -> int:  # noqa: N802 - Qt API.
        return len(self._artifacts)

    def columnCount(self, _parent: QModelIndex | None = None) -> int:  # noqa: N802 - Qt API.
        return len(ARTIFACT_STORE_COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object | None:
        if not _index_is_valid(index):
            return None
        row = int(index.row())
        column = int(index.column())
        if row < 0 or row >= len(self._artifacts) or column < 0 or column >= len(ARTIFACT_STORE_COLUMNS):
            return None
        artifact = self._artifacts[row]
        key = ARTIFACT_STORE_COLUMNS[column][0]
        if role == Qt.ItemDataRole.DisplayRole:
            value = getattr(artifact, key)
            if key == "sha256":
                return artifact.sha256_short()
            if key in {"local_only", "safe_to_publish"}:
                return "Yes" if value else "No"
            if key == "size_bytes":
                return f"{value} B"
            return str(value)
        if role == Qt.ItemDataRole.UserRole:
            return artifact
        return None

    def headerData(  # noqa: N802 - Qt API.
        self,
        section: int,
        orientation: object,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> object | None:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal and 0 <= int(section) < len(ARTIFACT_STORE_COLUMNS):
            return ARTIFACT_STORE_COLUMNS[int(section)][1]
        return int(section) + 1

    def flags(self, index: QModelIndex) -> object:
        if not _index_is_valid(index):
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def set_artifacts(self, artifacts: list[ArtifactRow] | tuple[ArtifactRow, ...]) -> None:
        self.beginResetModel()
        self._artifacts = list(artifacts)
        self.endResetModel()

    def artifact_at(self, row: int) -> ArtifactRow | None:
        if row < 0 or row >= len(self._artifacts):
            return None
        return self._artifacts[row]


def _index_is_valid(index: object) -> bool:
    return bool(index is not None and hasattr(index, "isValid") and index.isValid())
