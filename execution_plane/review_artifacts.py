"""Multimodal review artifact writer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from creative.common import load_json, write_json
from execution_plane.permits.builder import stable_id
from execution_plane.runner.result_envelope import utc_now


def create_review_artifact(
    subject_id: str,
    *,
    runtime_root: str | Path = "work/production_runtime",
    package_root: str | Path = "work/packages",
    output_root: str | Path = "work/review_artifacts",
) -> dict[str, Any]:
    subject = _load_subject(subject_id, runtime_root, package_root)
    artifact_refs = subject.get("artifact_refs", [])
    review_id = stable_id("REVIEW", subject_id, utc_now())
    review_dir = Path(output_root) / review_id
    slots = _slots_from_refs(artifact_refs)
    artifact = {
        "schema_version": "seos.multimodal_review_artifact.v1",
        "review_id": review_id,
        "subject_id": subject_id,
        "subject_kind": subject["subject_kind"],
        "created_at": utc_now(),
        "terminal_status": subject.get("terminal_status"),
        "slots": slots,
        "artifact_refs": artifact_refs,
        "review_notes": [],
    }
    write_json(review_dir / "review_artifact.json", artifact)
    (review_dir / "review_packet.md").write_text(_markdown(artifact), encoding="utf-8")
    return {"ok": True, "review_path": (review_dir / "review_artifact.json").as_posix(), "packet_path": (review_dir / "review_packet.md").as_posix(), "review": artifact}


def _load_subject(subject_id: str, runtime_root: str | Path, package_root: str | Path) -> dict[str, Any]:
    shot_path = Path(runtime_root) / "shots" / subject_id / "shot.json"
    if shot_path.exists():
        shot = load_json(shot_path)
        refs = []
        terminal = None
        for run in shot.get("runs", []):
            receipt_path = Path(str(run.get("receipt_path", "")))
            if receipt_path.exists():
                receipt = load_json(receipt_path)
                refs.extend(receipt.get("artifact_refs", []))
                terminal = receipt.get("terminal_status")
        return {"subject_kind": "shot", "artifact_refs": refs, "terminal_status": terminal}
    package_manifest = Path(package_root) / "shots" / subject_id / "manifest.json"
    if package_manifest.exists():
        payload = load_json(package_manifest)
        return {"subject_kind": "shot_package", "artifact_refs": payload.get("artifact_refs", []), "terminal_status": None}
    raise FileNotFoundError(f"review_subject_not_found:{subject_id}")


def _slots_from_refs(refs: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    slots = {"text": [], "image": [], "video": [], "audio": [], "data": []}
    for ref in refs:
        media_type = str(ref.get("media_type", ""))
        if media_type.startswith("image/"):
            slots["image"].append(ref)
        elif media_type.startswith("video/"):
            slots["video"].append(ref)
        elif media_type.startswith("audio/"):
            slots["audio"].append(ref)
        elif media_type.startswith("text/"):
            slots["text"].append(ref)
        else:
            slots["data"].append(ref)
    return slots


def _markdown(artifact: dict[str, Any]) -> str:
    counts = {key: len(value) for key, value in artifact["slots"].items()}
    return "\n".join(
        [
            f"# Review {artifact['review_id']}",
            "",
            f"Subject: {artifact['subject_kind']} {artifact['subject_id']}",
            f"Terminal status: {artifact.get('terminal_status')}",
            "",
            "Slots:",
            *[f"- {key}: {value}" for key, value in sorted(counts.items())],
            "",
        ]
    )
