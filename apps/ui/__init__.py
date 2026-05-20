"""Shared optional Qt boundary for Sovereign Console UI modules."""

from __future__ import annotations

try:  # pragma: no cover - exercised on developer machines with Qt installed.
    from PySide6.QtCore import QAbstractTableModel, QModelIndex, QObject, QPoint, QRect, QSize, Qt, QTimer, Signal, Slot
    from PySide6.QtGui import QColor, QFont, QPainter, QPen
    from PySide6.QtWidgets import (
        QApplication,
        QAbstractItemView,
        QFrame,
        QFormLayout,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QMainWindow,
        QPlainTextEdit,
        QPushButton,
        QSizePolicy,
        QStackedWidget,
        QStyle,
        QStyledItemDelegate,
        QTableView,
        QToolButton,
        QVBoxLayout,
        QWidget,
    )

    PYSIDE6_AVAILABLE = True
except Exception as _qt_import_error:  # pragma: no cover - depends on host image.
    PYSIDE6_AVAILABLE = False
    QT_IMPORT_ERROR = _qt_import_error

    class _MissingApplication:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            raise RuntimeError("PySide6 is required to start the Sovereign Console GUI") from QT_IMPORT_ERROR

    class _QtObjectShim:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            self._visible = False
            self._enabled = True
            self._text = ""

        def __getattr__(self, _name: str) -> object:
            def _noop(*_args: object, **_kwargs: object) -> object | None:
                return None

            return _noop

        def setVisible(self, value: bool) -> None:  # noqa: N802 - mirrors Qt API.
            self._visible = bool(value)

        def isVisible(self) -> bool:  # noqa: N802 - mirrors Qt API.
            return self._visible

        def setEnabled(self, value: bool) -> None:  # noqa: N802 - mirrors Qt API.
            self._enabled = bool(value)

        def isEnabled(self) -> bool:  # noqa: N802 - mirrors Qt API.
            return self._enabled

        def setText(self, value: object) -> None:  # noqa: N802 - mirrors Qt API.
            self._text = str(value)

        def text(self) -> str:
            return self._text

    class _SignalShim:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            self._callbacks: list[object] = []

        def connect(self, callback: object) -> None:
            self._callbacks.append(callback)

        def emit(self, *args: object, **kwargs: object) -> None:
            for callback in list(self._callbacks):
                if callable(callback):
                    callback(*args, **kwargs)

    class _QtNamespace:
        class ItemDataRole:
            DisplayRole = 0
            UserRole = 256
            TextAlignmentRole = 1

        class Orientation:
            Horizontal = 1
            Vertical = 2

        class AlignmentFlag:
            AlignCenter = 0x0004
            AlignLeft = 0x0001
            AlignVCenter = 0x0080

        class ItemFlag:
            NoItemFlags = 0
            ItemIsEnabled = 1
            ItemIsSelectable = 2

        class SortOrder:
            AscendingOrder = 0
            DescendingOrder = 1

        class PenStyle:
            NoPen = 0

    def Slot(*_args: object, **_kwargs: object) -> object:
        def decorator(function: object) -> object:
            return function

        return decorator

    QApplication = _MissingApplication
    QAbstractItemView = _QtObjectShim
    QAbstractTableModel = _QtObjectShim
    QColor = _QtObjectShim
    QFrame = _QtObjectShim
    QFormLayout = _QtObjectShim
    QGridLayout = _QtObjectShim
    QHBoxLayout = _QtObjectShim
    QHeaderView = _QtObjectShim
    QLabel = _QtObjectShim
    QMainWindow = _QtObjectShim
    QModelIndex = _QtObjectShim
    QObject = _QtObjectShim
    QPainter = _QtObjectShim
    QPen = _QtObjectShim
    QPlainTextEdit = _QtObjectShim
    QPoint = _QtObjectShim
    QPushButton = _QtObjectShim
    QRect = _QtObjectShim
    QSize = _QtObjectShim
    QSizePolicy = _QtObjectShim
    QStackedWidget = _QtObjectShim
    QStyle = _QtObjectShim
    QStyledItemDelegate = _QtObjectShim
    QTableView = _QtObjectShim
    QTimer = _QtObjectShim
    QToolButton = _QtObjectShim
    QVBoxLayout = _QtObjectShim
    QWidget = _QtObjectShim
    Qt = _QtNamespace
    Signal = _SignalShim
