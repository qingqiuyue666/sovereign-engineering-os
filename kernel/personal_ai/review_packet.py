"""Human review packet builder for Personal AI local planning artifacts."""

from dataclasses import dataclass
from pathlib import Path
import json

from kernel.personal_ai.io_utils import write_json_atomically

__all__ = [
    "ReviewPacketResult",
    "build_review_packet",
]

_NON_AUTHORIZATION_STATEMENT = (
    "This review packet does not authorize file mutation, task execution, "
    "API calls, external tool control, runtime authority, execution "
    "capability, or adapter implementation."
)


@dataclass(frozen=True)
class ReviewPacketResult:
    output_review_packet_path: Path
    files_recorded: int
    candidate_tasks: list[str]
    required_human_approval: bool


def build_review_packet(
    intake_ledger_path: Path,
    profile_path: Path,
    work_order_path: Path,
    output_review_packet_path: Path,
) -> ReviewPacketResult:
    ledger_file = Path(intake_ledger_path)
    profile_file = Path(profile_path)
    work_order_file = Path(work_order_path)
    output_path = Path(output_review_packet_path)

    if not ledger_file.exists():
        raise ValueError("intake_ledger_path is missing")
    if not profile_file.exists():
        raise ValueError("profile_path is missing")
    if not work_order_file.exists():
        raise ValueError("work_order_path is missing")
    if not output_path.parent.exists() or not output_path.parent.is_dir():
        raise ValueError("output_review_packet_path parent is missing")

    intake_entries = _read_ledger_entries(ledger_file)
    profile = json.loads(profile_file.read_text(encoding="utf-8"))
    work_order = json.loads(work_order_file.read_text(encoding="utf-8"))
    candidate_tasks = list(work_order.get("candidate_tasks", []))

    packet = {
        "packet_type": "personal_ai_local_review_packet",
        "authority": "non_authority",
        "execution_capability": "not_introduced",
        "required_human_approval": True,
        "sources": {
            "intake_ledger_path": ledger_file.as_posix(),
            "profile_path": profile_file.as_posix(),
            "work_order_path": work_order_file.as_posix(),
        },
        "intake_summary": {
            "files_recorded": len(intake_entries),
            "bytes_recorded": sum(
                entry["size_bytes"] for entry in intake_entries
            ),
        },
        "artifact_summary": {
            "total_files": profile.get("total_files", 0),
            "total_bytes": profile.get("total_bytes", 0),
            "categories": profile.get("categories", {}),
            "extensions": profile.get("extensions", {}),
            "largest_files": profile.get("largest_files", []),
        },
        "proposed_work_order": work_order,
        "non_authorization_statement": _NON_AUTHORIZATION_STATEMENT,
        "next_allowed_action": "human_review_only",
    }

    write_json_atomically(output_path, packet)

    return ReviewPacketResult(
        output_review_packet_path=output_path,
        files_recorded=len(intake_entries),
        candidate_tasks=candidate_tasks,
        required_human_approval=True,
    )


def _read_ledger_entries(ledger_file):
    entries = []
    with ledger_file.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                entries.append(json.loads(stripped))
    return entries
