"""Native Sovereign Console Phase 1 entrypoint.

Importing this module is intentionally passive: it does not create a
QApplication, open the local database, submit work, or contact external tools.
"""

from __future__ import annotations

import sys
from pathlib import Path

from apps.ui import QApplication, PYSIDE6_AVAILABLE, QMainWindow
from apps.ui.main_window import SovereignConsoleMainWindow
from apps.ui.read_models import ReadModelProvider, RuntimeSnapshot

__all__ = [
    "DesktopOsEngineFacade",
    "PYSIDE6_AVAILABLE",
    "QApplication",
    "QMainWindow",
    "SovereignConsoleMainWindow",
    "SovereignDesktopWindow",
    "main",
]

APP_TITLE = "Sovereign Console"


def runtime_root() -> Path:
    return Path.home() / ".sovereign_engineering_os"


def repo_root_from_here() -> Path:
    return Path(__file__).resolve().parents[1]


class DesktopOsEngineFacade:
    """Read-only desktop facade over bounded OS runtime projections."""

    def __init__(self, *, repo_root: Path, runtime_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.runtime_root = runtime_root.expanduser().resolve()
        self.read_models = ReadModelProvider(runtime_root=self.runtime_root)

    def initialize(self) -> None:
        """Kept for compatibility; Phase 1 desktop startup performs no writes."""

    def snapshot(self) -> RuntimeSnapshot:
        return self.read_models.snapshot_runtime_status()

    def selected_job_snapshot(self, job_id: str) -> RuntimeSnapshot:
        return self.read_models.snapshot_selected_job(job_id)

    def close(self) -> None:
        """The read-only facade owns no persistent connection."""


class SovereignDesktopWindow(SovereignConsoleMainWindow):
    """Backward-compatible name for the Phase 1 console shell."""

    def __init__(self, repo_root: Path | None = None, parent: object | None = None) -> None:
        resolved_repo = (repo_root or repo_root_from_here()).resolve()
        facade = DesktopOsEngineFacade(repo_root=resolved_repo, runtime_root=runtime_root())
        super().__init__(snapshot_provider=facade.snapshot, parent=parent)
        self.repo_root = resolved_repo
        self.os_engine = facade


def main(argv: list[str] | None = None) -> int:
    if not PYSIDE6_AVAILABLE:
        raise RuntimeError("PySide6 is required to run the Sovereign Console desktop shell")
    app = QApplication(argv or sys.argv)
    app.setApplicationName(APP_TITLE)
    window = SovereignDesktopWindow()
    window.show()
    return int(app.exec())


if __name__ == "__main__":
    raise SystemExit(main())
