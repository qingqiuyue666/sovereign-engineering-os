"""Read-only local asset scanning runtime v1."""

from collections import deque
from hashlib import sha256
from pathlib import Path
import json

from kernel.assets.local_asset_classifier import classify_local_asset
from kernel.assets.local_asset_quarantine import (
    has_hidden_part,
    is_secret_looking_path,
    is_unsafe_directory_name,
    quarantine_record,
    symlink_quarantine_record,
)
from kernel.assets.local_asset_reporter import (
    build_asset_index,
    build_asset_manifest,
    build_audit_events,
    build_duplicates_report,
    build_quarantine_manifest,
    build_validation_report,
    render_media_inventory_markdown,
)
from kernel.assets.local_asset_schema import (
    ASSET_INDEX_FILE,
    ASSET_MANIFEST_FILE,
    AUDIT_LOG_FILE,
    DUPLICATES_REPORT_FILE,
    MEDIA_INVENTORY_FILE,
    OUTPUT_FILENAMES,
    QUARANTINE_MANIFEST_FILE,
    VALIDATION_REPORT_FILE,
    LocalAssetRuntimeResult,
)

__all__ = [
    "LocalAssetRuntimeResult",
    "run_local_asset_runtime",
]


def run_local_asset_runtime(
    input_dir: Path,
    output_dir: Path,
    *,
    recursive: bool = False,
    include_hidden: bool = False,
    project_id: str | None = None,
) -> LocalAssetRuntimeResult:
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_paths = _validate_preflight(input_path, output_path)

    scan_result = _scan_input_dir(
        input_path,
        recursive=recursive,
        include_hidden=include_hidden,
    )
    assets = scan_result["assets"]
    quarantine_items = scan_result["quarantine_items"]
    duplicates_report = build_duplicates_report(assets)
    duplicates = duplicates_report["duplicate_groups"]
    quarantine_manifest = build_quarantine_manifest(quarantine_items)

    payloads = {
        ASSET_MANIFEST_FILE: build_asset_manifest(
            assets=assets,
            quarantine_items=quarantine_items,
            duplicates=duplicates,
            input_dir_name=input_path.name,
            recursive=recursive,
            include_hidden=include_hidden,
            project_id=project_id,
        ),
        ASSET_INDEX_FILE: build_asset_index(assets),
        DUPLICATES_REPORT_FILE: duplicates_report,
        VALIDATION_REPORT_FILE: build_validation_report(
            assets=assets,
            quarantine_items=quarantine_items,
            duplicates=duplicates,
            recursive=recursive,
            include_hidden=include_hidden,
            skipped_hidden_paths=scan_result["skipped_hidden_paths"],
            skipped_nonrecursive_dirs=scan_result["skipped_nonrecursive_dirs"],
            project_id=project_id,
        ),
        QUARANTINE_MANIFEST_FILE: quarantine_manifest,
    }
    markdown_payload = render_media_inventory_markdown(
        assets=assets,
        duplicates=duplicates,
        quarantine_manifest=quarantine_manifest,
        project_id=project_id,
    )
    audit_events = build_audit_events(
        assets=assets,
        quarantine_items=quarantine_items,
        duplicates=duplicates,
        recursive=recursive,
        include_hidden=include_hidden,
        project_id=project_id,
        skipped_hidden_paths=scan_result["skipped_hidden_paths"],
        skipped_nonrecursive_dirs=scan_result["skipped_nonrecursive_dirs"],
        output_filenames=OUTPUT_FILENAMES,
    )

    _write_json_exclusive(output_paths[ASSET_MANIFEST_FILE], payloads[ASSET_MANIFEST_FILE])
    _write_json_exclusive(output_paths[ASSET_INDEX_FILE], payloads[ASSET_INDEX_FILE])
    _write_json_exclusive(
        output_paths[DUPLICATES_REPORT_FILE],
        payloads[DUPLICATES_REPORT_FILE],
    )
    _write_text_exclusive(output_paths[MEDIA_INVENTORY_FILE], markdown_payload)
    _write_jsonl_exclusive(output_paths[AUDIT_LOG_FILE], audit_events)
    _write_json_exclusive(
        output_paths[VALIDATION_REPORT_FILE],
        payloads[VALIDATION_REPORT_FILE],
    )
    _write_json_exclusive(
        output_paths[QUARANTINE_MANIFEST_FILE],
        payloads[QUARANTINE_MANIFEST_FILE],
    )

    return LocalAssetRuntimeResult(
        input_dir=input_path,
        output_dir=output_path,
        output_paths=output_paths,
        files_scanned=len(assets),
        bytes_scanned=sum(asset["size_bytes"] for asset in assets),
        duplicate_groups=len(duplicates),
        quarantined_paths=len(quarantine_items),
        recursive=recursive,
        include_hidden=include_hidden,
        project_id=project_id,
    )


def _validate_preflight(input_path: Path, output_path: Path) -> dict[str, Path]:
    if not input_path.exists():
        raise ValueError("input_dir is missing")
    if not input_path.is_dir():
        raise ValueError("input_dir is not a directory")
    if input_path.is_symlink():
        raise ValueError("input_dir must not be a symlink")
    if not output_path.exists():
        raise ValueError("output_dir is missing")
    if not output_path.is_dir():
        raise ValueError("output_dir is not a directory")
    if output_path.is_symlink():
        raise ValueError("output_dir must not be a symlink")
    if _path_is_inside(output_path, input_path):
        raise ValueError("output_dir must be outside input_dir")

    output_paths = {filename: output_path / filename for filename in OUTPUT_FILENAMES}
    for filename, path in output_paths.items():
        if not _path_is_inside(path, output_path):
            raise ValueError(f"output path escapes output_dir: {filename}")
        if path.exists():
            raise ValueError(f"asset runtime output already exists: {filename}")
    return output_paths


def _scan_input_dir(
    input_path: Path,
    *,
    recursive: bool,
    include_hidden: bool,
) -> dict:
    assets = []
    quarantine_items = []
    skipped_hidden_paths = 0
    skipped_nonrecursive_dirs = 0
    pending_dirs = deque([input_path])

    while pending_dirs:
        current_dir = pending_dirs.popleft()
        try:
            children = sorted(
                current_dir.iterdir(),
                key=lambda path: path.relative_to(input_path).as_posix(),
            )
        except OSError:
            quarantine_items.append(
                quarantine_record(
                    current_dir.relative_to(input_path),
                    reason="directory_unreadable",
                    path_type="directory",
                    detail="directory could not be listed and was skipped",
                )
            )
            continue

        for child in children:
            relative_path = child.relative_to(input_path)

            if child.is_symlink():
                quarantine_items.append(symlink_quarantine_record(child, input_path))
                continue

            if child.is_dir():
                if is_unsafe_directory_name(child.name):
                    quarantine_items.append(
                        quarantine_record(
                            relative_path,
                            reason="unsafe_directory",
                            path_type="directory",
                            detail="reserved dependency/cache/source-control directory was not traversed",
                        )
                    )
                    continue
                if is_secret_looking_path(relative_path):
                    quarantine_items.append(
                        quarantine_record(
                            relative_path,
                            reason="secret_looking_path",
                            path_type="directory",
                            detail="secret-looking directory was not traversed",
                        )
                    )
                    continue
                if has_hidden_part(relative_path) and not include_hidden:
                    skipped_hidden_paths += 1
                    continue
                if recursive:
                    pending_dirs.append(child)
                else:
                    skipped_nonrecursive_dirs += 1
                continue

            if not child.is_file():
                quarantine_items.append(
                    quarantine_record(
                        relative_path,
                        reason="unsupported_filesystem_entry",
                        path_type="other",
                        detail="non-file filesystem entry was skipped",
                    )
                )
                continue

            if is_secret_looking_path(relative_path):
                quarantine_items.append(
                    quarantine_record(
                        relative_path,
                        reason="secret_looking_path",
                        path_type="file",
                        detail="secret-looking file contents were not read",
                    )
                )
                continue
            if has_hidden_part(relative_path) and not include_hidden:
                skipped_hidden_paths += 1
                continue

            asset = _asset_record(child, input_path)
            if asset is None:
                quarantine_items.append(
                    quarantine_record(
                        relative_path,
                        reason="file_unreadable",
                        path_type="file",
                        detail="file could not be hashed and was skipped",
                    )
                )
            else:
                assets.append(asset)

    assets.sort(key=lambda record: record["relative_path"])
    quarantine_items.sort(
        key=lambda record: (
            record["relative_path"],
            record["reason"],
            record.get("path_type", ""),
        )
    )
    return {
        "assets": assets,
        "quarantine_items": quarantine_items,
        "skipped_hidden_paths": skipped_hidden_paths,
        "skipped_nonrecursive_dirs": skipped_nonrecursive_dirs,
    }


def _asset_record(path: Path, input_path: Path) -> dict | None:
    try:
        file_stat = path.stat()
        digest = _sha256_file(path)
    except OSError:
        return None
    relative_path = path.relative_to(input_path).as_posix()
    asset_type = classify_local_asset(path)
    return {
        "asset_id": _asset_id(relative_path, digest),
        "asset_type": asset_type,
        "extension": path.suffix.lower(),
        "file_name": path.name,
        "relative_path": relative_path,
        "sha256": digest,
        "size_bytes": int(file_stat.st_size),
    }


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _asset_id(relative_path: str, digest: str) -> str:
    return "asset_" + sha256(f"{relative_path}\0{digest}".encode("utf-8")).hexdigest()[
        :16
    ]


def _write_json_exclusive(path: Path, payload: dict) -> None:
    _write_text_exclusive(
        path,
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
    )


def _write_jsonl_exclusive(path: Path, entries: list[dict]) -> None:
    lines = [
        json.dumps(entry, separators=(",", ":"), sort_keys=True) for entry in entries
    ]
    _write_text_exclusive(path, "\n".join(lines) + "\n")


def _write_text_exclusive(path: Path, content: str) -> None:
    try:
        with path.open("x", encoding="utf-8", newline="\n") as output_file:
            output_file.write(content)
            output_file.flush()
    except FileExistsError as error:
        raise ValueError(f"asset runtime output already exists: {path.name}") from error


def _path_is_inside(candidate_path: Path, root_path: Path) -> bool:
    try:
        Path(candidate_path).resolve(strict=False).relative_to(
            Path(root_path).resolve(strict=True)
        )
    except (OSError, ValueError):
        return False
    return True
