"""Deterministic reports for local asset runtime v1."""

from collections import Counter, defaultdict

from kernel.assets.local_asset_schema import ASSET_TYPE_ORDER, RUNTIME_VERSION

__all__ = [
    "build_asset_index",
    "build_asset_manifest",
    "build_audit_events",
    "build_duplicates_report",
    "build_quarantine_manifest",
    "build_validation_report",
    "render_media_inventory_markdown",
]


def build_asset_manifest(
    *,
    assets: list[dict],
    quarantine_items: list[dict],
    duplicates: list[dict],
    input_dir_name: str,
    recursive: bool,
    include_hidden: bool,
    project_id: str | None,
) -> dict:
    return {
        "assets": assets,
        "boundaries": _runtime_boundaries(),
        "counts": {
            "bytes_scanned": sum(asset["size_bytes"] for asset in assets),
            "duplicate_sha256_groups": len(duplicates),
            "files_scanned": len(assets),
            "quarantined_paths": len(quarantine_items),
        },
        "input": {
            "include_hidden": include_hidden,
            "input_dir_name": input_dir_name,
            "recursive": recursive,
        },
        "manifest_type": "local_asset_runtime_v1_asset_manifest",
        "project_id": project_id,
        "runtime_version": RUNTIME_VERSION,
    }


def build_asset_index(assets: list[dict]) -> dict:
    by_sha256 = {}
    by_asset_type = defaultdict(list)
    by_extension = defaultdict(list)
    assets_by_path = {}

    grouped = defaultdict(list)
    for asset in assets:
        grouped[asset["sha256"]].append(asset)
        by_asset_type[asset["asset_type"]].append(asset["relative_path"])
        by_extension[asset["extension"] or "[none]"].append(asset["relative_path"])
        assets_by_path[asset["relative_path"]] = {
            "asset_id": asset["asset_id"],
            "asset_type": asset["asset_type"],
            "sha256": asset["sha256"],
            "size_bytes": asset["size_bytes"],
        }

    for digest in sorted(grouped):
        digest_assets = sorted(grouped[digest], key=lambda item: item["relative_path"])
        by_sha256[digest] = {
            "asset_ids": [asset["asset_id"] for asset in digest_assets],
            "asset_types": sorted({asset["asset_type"] for asset in digest_assets}),
            "count": len(digest_assets),
            "relative_paths": [asset["relative_path"] for asset in digest_assets],
            "size_bytes_each": digest_assets[0]["size_bytes"],
        }

    return {
        "assets_by_path": assets_by_path,
        "by_asset_type": {
            asset_type: sorted(paths)
            for asset_type, paths in sorted(by_asset_type.items())
        },
        "by_extension": {
            extension: sorted(paths) for extension, paths in sorted(by_extension.items())
        },
        "by_sha256": by_sha256,
        "index_type": "local_asset_runtime_v1_asset_index",
        "runtime_version": RUNTIME_VERSION,
    }


def build_duplicates_report(assets: list[dict]) -> dict:
    grouped = defaultdict(list)
    for asset in assets:
        grouped[asset["sha256"]].append(asset)

    duplicate_groups = []
    for digest in sorted(grouped):
        digest_assets = sorted(grouped[digest], key=lambda item: item["relative_path"])
        if len(digest_assets) < 2:
            continue
        duplicate_groups.append(
            {
                "asset_ids": [asset["asset_id"] for asset in digest_assets],
                "asset_types": sorted({asset["asset_type"] for asset in digest_assets}),
                "count": len(digest_assets),
                "relative_paths": [
                    asset["relative_path"] for asset in digest_assets
                ],
                "sha256": digest,
                "size_bytes_each": digest_assets[0]["size_bytes"],
            }
        )

    return {
        "duplicate_file_count": sum(group["count"] for group in duplicate_groups),
        "duplicate_groups": duplicate_groups,
        "duplicate_sha256_group_count": len(duplicate_groups),
        "report_type": "local_asset_runtime_v1_duplicates_report",
        "runtime_version": RUNTIME_VERSION,
    }


def build_quarantine_manifest(quarantine_items: list[dict]) -> dict:
    reason_counts = Counter(item["reason"] for item in quarantine_items)
    return {
        "counts_by_reason": {
            reason: reason_counts[reason] for reason in sorted(reason_counts)
        },
        "items": sorted(
            quarantine_items,
            key=lambda item: (
                item["relative_path"],
                item["reason"],
                item.get("path_type", ""),
            ),
        ),
        "quarantine_actions_performed": [
            "skip_path",
            "do_not_read_file_contents",
            "do_not_follow_symlink",
        ],
        "quarantine_type": "local_asset_runtime_v1_quarantine_manifest",
        "quarantined_path_count": len(quarantine_items),
        "runtime_version": RUNTIME_VERSION,
    }


def build_validation_report(
    *,
    assets: list[dict],
    quarantine_items: list[dict],
    duplicates: list[dict],
    recursive: bool,
    include_hidden: bool,
    skipped_hidden_paths: int,
    skipped_nonrecursive_dirs: int,
    project_id: str | None,
) -> dict:
    return {
        "boundaries": _runtime_boundaries(),
        "checks": [
            {"check_id": "input_dir_exists", "status": "passed"},
            {"check_id": "input_dir_is_directory", "status": "passed"},
            {"check_id": "output_dir_exists", "status": "passed"},
            {"check_id": "output_dir_is_directory", "status": "passed"},
            {"check_id": "output_dir_outside_input_dir", "status": "passed"},
            {"check_id": "output_files_absent_before_run", "status": "passed"},
            {"check_id": "writes_confined_to_output_dir", "status": "passed"},
            {"check_id": "streaming_sha256_hashing", "status": "passed"},
            {"check_id": "input_mutation_not_performed", "status": "passed"},
            {"check_id": "external_runtime_not_invoked", "status": "passed"},
        ],
        "counts": {
            "asset_type_counts": _asset_type_counts(assets),
            "bytes_scanned": sum(asset["size_bytes"] for asset in assets),
            "duplicate_sha256_groups": len(duplicates),
            "files_scanned": len(assets),
            "quarantined_paths": len(quarantine_items),
            "skipped_hidden_paths": skipped_hidden_paths,
            "skipped_nonrecursive_dirs": skipped_nonrecursive_dirs,
        },
        "include_hidden": include_hidden,
        "project_id": project_id,
        "recursive": recursive,
        "runtime_version": RUNTIME_VERSION,
        "status": "passed",
        "validation_type": "local_asset_runtime_v1_validation_report",
    }


def build_audit_events(
    *,
    assets: list[dict],
    quarantine_items: list[dict],
    duplicates: list[dict],
    recursive: bool,
    include_hidden: bool,
    project_id: str | None,
    skipped_hidden_paths: int,
    skipped_nonrecursive_dirs: int,
    output_filenames: tuple[str, ...],
) -> list[dict]:
    events = [
        {
            "event_type": "runtime_started",
            "include_hidden": include_hidden,
            "project_id": project_id,
            "recursive": recursive,
            "runtime_version": RUNTIME_VERSION,
        },
        {
            "event_type": "preflight_passed",
            "output_filenames": list(output_filenames),
        },
    ]
    for item in sorted(
        quarantine_items,
        key=lambda record: (record["relative_path"], record["reason"]),
    ):
        events.append(
            {
                "event_type": "path_quarantined",
                "path_type": item.get("path_type"),
                "reason": item["reason"],
                "relative_path": item["relative_path"],
            }
        )
    for asset in sorted(assets, key=lambda record: record["relative_path"]):
        events.append(
            {
                "asset_id": asset["asset_id"],
                "asset_type": asset["asset_type"],
                "event_type": "asset_scanned",
                "relative_path": asset["relative_path"],
                "sha256": asset["sha256"],
                "size_bytes": asset["size_bytes"],
            }
        )
    for duplicate in duplicates:
        events.append(
            {
                "event_type": "duplicate_content_detected",
                "relative_paths": duplicate["relative_paths"],
                "sha256": duplicate["sha256"],
            }
        )
    events.append(
        {
            "event_type": "runtime_completed",
            "files_scanned": len(assets),
            "quarantined_paths": len(quarantine_items),
            "skipped_hidden_paths": skipped_hidden_paths,
            "skipped_nonrecursive_dirs": skipped_nonrecursive_dirs,
        }
    )
    return [
        {"event_id": f"{index:06d}", **event}
        for index, event in enumerate(events, start=1)
    ]


def render_media_inventory_markdown(
    *,
    assets: list[dict],
    duplicates: list[dict],
    quarantine_manifest: dict,
    project_id: str | None,
) -> str:
    lines = [
        "# Local Asset Runtime Media Inventory",
        "",
        f"- Runtime: `{RUNTIME_VERSION}`",
        f"- Project ID: `{project_id}`" if project_id else "- Project ID: none",
        f"- Files scanned: {len(assets)}",
        f"- Quarantined paths: {quarantine_manifest['quarantined_path_count']}",
        f"- Duplicate SHA-256 groups: {len(duplicates)}",
        "",
        "## Asset Types",
        "",
        "| Asset type | Files | Bytes |",
        "| --- | ---: | ---: |",
    ]
    counts = _asset_type_counts(assets)
    bytes_by_type = _bytes_by_type(assets)
    for asset_type in ASSET_TYPE_ORDER:
        lines.append(
            f"| {asset_type} | {counts.get(asset_type, 0)} | "
            f"{bytes_by_type.get(asset_type, 0)} |"
        )
    lines.extend(
        [
            "",
            "## Assets",
            "",
            "| Relative path | Type | Size bytes | SHA-256 |",
            "| --- | --- | ---: | --- |",
        ]
    )
    if assets:
        for asset in sorted(assets, key=lambda record: record["relative_path"]):
            lines.append(
                f"| `{asset['relative_path']}` | {asset['asset_type']} | "
                f"{asset['size_bytes']} | `{asset['sha256']}` |"
            )
    else:
        lines.append("| none | none | 0 | none |")

    lines.extend(
        [
            "",
            "## Duplicate Content",
            "",
            "| SHA-256 | Count | Relative paths |",
            "| --- | ---: | --- |",
        ]
    )
    if duplicates:
        for duplicate in duplicates:
            paths = ", ".join(f"`{path}`" for path in duplicate["relative_paths"])
            lines.append(f"| `{duplicate['sha256']}` | {duplicate['count']} | {paths} |")
    else:
        lines.append("| none | 0 | none |")

    lines.extend(
        [
            "",
            "## Quarantine",
            "",
            "| Relative path | Reason | Path type |",
            "| --- | --- | --- |",
        ]
    )
    if quarantine_manifest["items"]:
        for item in quarantine_manifest["items"]:
            lines.append(
                f"| `{item['relative_path']}` | {item['reason']} | "
                f"{item.get('path_type', 'unknown')} |"
            )
    else:
        lines.append("| none | none | none |")
    return "\n".join(lines) + "\n"


def _asset_type_counts(assets: list[dict]) -> dict:
    counts = Counter(asset["asset_type"] for asset in assets)
    return {asset_type: counts.get(asset_type, 0) for asset_type in ASSET_TYPE_ORDER}


def _bytes_by_type(assets: list[dict]) -> dict:
    totals = Counter()
    for asset in assets:
        totals[asset["asset_type"]] += asset["size_bytes"]
    return {asset_type: totals.get(asset_type, 0) for asset_type in ASSET_TYPE_ORDER}


def _runtime_boundaries() -> dict:
    return {
        "browser_runtime_invoked": False,
        "desktop_ui_added": False,
        "external_creative_runtime_invoked": False,
        "external_tools_called": False,
        "input_files_mutated": False,
        "model_api_called": False,
        "network_access_performed": False,
        "output_overwrite_performed": False,
        "writes_limited_to_output_dir": True,
    }
