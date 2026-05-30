"""Build a static HTML dashboard from Creative Pipeline reports."""

from __future__ import annotations

from pathlib import Path

PAGES = {
    "index.html": "SEOS Creative Pipeline Dashboard",
    "assets.html": "Asset Registry",
    "shots.html": "Shot OS",
    "evidence.html": "Evidence Ledger",
    "software.html": "Software Doctor",
    "archive_integrity.html": "Archive Integrity",
}

def build_dashboard(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    for file_name, title in PAGES.items():
        (output_dir / file_name).write_text(_page(title), encoding="utf-8")
    return {"ok": True, "output_dir": output_dir.as_posix(), "pages": sorted(PAGES)}

def _page(title: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>{title}</title><style>body{{font-family:system-ui;margin:2rem;max-width:960px}}code{{background:#f2f2f2;padding:.1rem .25rem}}</style></head>
<body><h1>{title}</h1><p>Fixture-backed local-first dashboard. Live DCC execution is not performed by this report.</p><ul><li>Private assets stay local.</li><li>Adapter jobs default to dry-run.</li><li>External adoption is tracked only from real evidence.</li></ul></body>
</html>
"""
