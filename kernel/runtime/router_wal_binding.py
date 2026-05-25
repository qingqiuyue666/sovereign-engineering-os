"""Router to WAL binding v1.

Connects the command envelope admission router to the SQLite WAL execution
journal without changing either component's authority. XML is only routed; the
journal receives structured report or receipt digests and safe metadata.
"""

from __future__ import annotations

from dataclasses import dataclass

from kernel.runtime.command_envelope_admission_router import (
    CommandAdmissionReport,
    CommandExecutionReceipt,
    route_envelope,
)
from kernel.runtime.sqlite_wal_execution_journal import (
    JournalAppendReceipt,
    SQLiteWalExecutionJournal,
)

__all__ = [
    "RouterWalBindingResult",
    "RouterWalBinding",
    "bind_router_envelope_to_wal",
]


@dataclass(frozen=True)
class RouterWalBindingResult:
    report: CommandAdmissionReport
    receipt: CommandExecutionReceipt | None
    admission_event: JournalAppendReceipt | None
    quarantine_event: JournalAppendReceipt | None
    receipt_event: JournalAppendReceipt | None

    def as_dict(self) -> dict[str, object]:
        return {
            "report": self.report.as_dict(),
            "receipt": None if self.receipt is None else self.receipt.as_dict(),
            "admission_event": None
            if self.admission_event is None
            else self.admission_event.as_dict(),
            "quarantine_event": None
            if self.quarantine_event is None
            else self.quarantine_event.as_dict(),
            "receipt_event": None
            if self.receipt_event is None
            else self.receipt_event.as_dict(),
        }


class RouterWalBinding:
    """Small binding object for repeated envelope routing into one journal."""

    def __init__(self, journal: SQLiteWalExecutionJournal):
        self.journal = journal

    def bind(
        self,
        xml_envelope: str,
        *,
        execute: bool = False,
    ) -> RouterWalBindingResult:
        return bind_router_envelope_to_wal(
            xml_envelope,
            self.journal,
            execute=execute,
        )


def bind_router_envelope_to_wal(
    xml_envelope: str,
    journal: SQLiteWalExecutionJournal,
    *,
    execute: bool = False,
) -> RouterWalBindingResult:
    """Route one envelope and append the resulting safe journal event."""

    report, receipt = route_envelope(xml_envelope, execute=execute)
    admission_event: JournalAppendReceipt | None = None
    quarantine_event: JournalAppendReceipt | None = None
    receipt_event: JournalAppendReceipt | None = None

    if report.admitted:
        admission_event = journal.append_admission(report)
    else:
        quarantine_event = journal.append_quarantine(report)

    if receipt is not None:
        receipt_event = journal.append_receipt(receipt)

    return RouterWalBindingResult(
        report=report,
        receipt=receipt,
        admission_event=admission_event,
        quarantine_event=quarantine_event,
        receipt_event=receipt_event,
    )
