"""Read-only local job queue event summary CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TextIO

from kernel.runtime.local_job_queue import summarize_job_event_records


def main(argv: list[str] | None = None, *, stdout: TextIO | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize local job queue events.")
    parser.add_argument("--events", required=True, help="Path to a JSON array of job event records.")
    args = parser.parse_args(argv)

    events_path = Path(args.events)
    records = json.loads(events_path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("events_file_must_contain_json_array")
    summary = summarize_job_event_records(records)
    output = stdout or sys.stdout
    output.write(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
