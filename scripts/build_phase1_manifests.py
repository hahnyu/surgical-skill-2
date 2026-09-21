#!/usr/bin/env python3
"""Build deterministic Phase 1 file manifests without copying raw data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


def sha256_file(path: Path, block_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(block_size), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_jigsaws(root: Path, output: Path) -> tuple[int, int, str]:
    root = root.resolve(strict=True)
    private_rows: list[dict] = []
    grouped: dict[tuple[str, str], list[tuple[str, int, str]]] = defaultdict(list)

    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != ".DS_Store"):
        relative = path.relative_to(root).as_posix()
        size = path.stat().st_size
        digest = sha256_file(path)
        parts = Path(relative).parts
        group = "/".join(parts[:2]) if len(parts) > 1 else parts[0]
        suffix = path.suffix.lower() or "[none]"
        private_rows.append(
            {"dataset": "JIGSAWS", "relative_path": relative, "size_bytes": size, "sha256": digest}
        )
        grouped[(group, suffix)].append((relative, size, digest))

    write_csv(
        output / "private" / "jigsaws_files.csv",
        private_rows,
        ["dataset", "relative_path", "size_bytes", "sha256"],
    )

    public_rows: list[dict] = []
    for (group, suffix), entries in sorted(grouped.items()):
        tree = hashlib.sha256()
        for relative, size, digest in entries:
            tree.update(f"{relative}\0{size}\0{digest}\n".encode())
        public_rows.append(
            {
                "dataset": "JIGSAWS",
                "group": group,
                "extension": suffix,
                "file_count": len(entries),
                "size_bytes": sum(item[1] for item in entries),
                "tree_sha256": tree.hexdigest(),
            }
        )
    write_csv(
        output / "jigsaws_inventory.csv",
        public_rows,
        ["dataset", "group", "extension", "file_count", "size_bytes", "tree_sha256"],
    )

    overall = hashlib.sha256()
    for row in private_rows:
        overall.update(
            f"{row['relative_path']}\0{row['size_bytes']}\0{row['sha256']}\n".encode()
        )
    return len(private_rows), sum(int(row["size_bytes"]) for row in private_rows), overall.hexdigest()


def build_rosma(source: Path, output: Path) -> tuple[int, int]:
    record = json.loads(source.read_text(encoding="utf-8"))
    rows = []
    for item in sorted(record["files"], key=lambda value: value["key"]):
        checksum_type, checksum_value = item["checksum"].split(":", 1)
        rows.append(
            {
                "dataset": "ROSMA",
                "version": record["doi"],
                "path": item["key"],
                "size_bytes": item["size"],
                "provided_checksum_type": checksum_type.upper(),
                "provided_checksum": checksum_value,
                "sha256": "not_computed_remote_file",
                "download_url": item["links"]["self"],
            }
        )
    fields = ["dataset", "version", "path", "size_bytes", "provided_checksum_type", "provided_checksum", "sha256", "download_url"]
    write_csv(output / "rosma_files.csv", rows, fields)
    return len(rows), sum(int(row["size_bytes"]) for row in rows)


def build_dataverse(source: Path, dataset: str, filename: str, output: Path) -> tuple[int, int]:
    record = json.loads(source.read_text(encoding="utf-8"))["data"]
    version = record["latestVersion"]
    rows = []
    for item in sorted(version["files"], key=lambda value: ((value.get("directoryLabel") or ""), value["label"])):
        data_file = item["dataFile"]
        directory = item.get("directoryLabel") or data_file.get("directoryLabel") or ""
        path = f"{directory}/{item['label']}" if directory else item["label"]
        checksum = data_file.get("checksum", {})
        rows.append(
            {
                "dataset": dataset,
                "version": f"{version['versionNumber']}.{version['versionMinorNumber']}",
                "path": path,
                "file_id": data_file["id"],
                "size_bytes": data_file["filesize"],
                "restricted": item.get("restricted", False),
                "provided_checksum_type": checksum.get("type", ""),
                "provided_checksum": checksum.get("value", ""),
                "sha256": "not_computed_remote_file",
                "download_url": f"https://edmond.mpg.de/api/access/datafile/{data_file['id']}",
            }
        )
    fields = ["dataset", "version", "path", "file_id", "size_bytes", "restricted", "provided_checksum_type", "provided_checksum", "sha256", "download_url"]
    write_csv(output / filename, rows, fields)
    return len(rows), sum(int(row["size_bytes"]) for row in rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jigsaws-root", type=Path, default=Path("data/raw/jigsaws"))
    parser.add_argument("--manifest-dir", type=Path, default=Path("data/manifests"))
    parser.add_argument("--rosma-json", type=Path, default=Path("data/manifests/source_metadata/rosma_zenodo_7100542.json"))
    parser.add_argument("--bgu-skills-json", type=Path, default=Path("data/manifests/source_metadata/bgu_skills_315275_v1.0.json"))
    parser.add_argument("--bgu-patcut-json", type=Path, default=Path("data/manifests/source_metadata/bgu_patcut_251697_v2.1.json"))
    args = parser.parse_args()

    args.manifest_dir.mkdir(parents=True, exist_ok=True)
    j_count, j_bytes, j_tree = build_jigsaws(args.jigsaws_root, args.manifest_dir)
    r_count, r_bytes = build_rosma(args.rosma_json, args.manifest_dir)
    s_count, s_bytes = build_dataverse(args.bgu_skills_json, "BGU-SKILLS", "bgu_skills_files.csv", args.manifest_dir)
    p_count, p_bytes = build_dataverse(args.bgu_patcut_json, "BGU-PatCut", "bgu_patcut_files.csv", args.manifest_dir)

    summaries = [
        {"dataset": "JIGSAWS", "version": "paper1-local-authorized-copy", "file_count": j_count, "size_bytes": j_bytes, "integrity": f"SHA-256 per file; private path manifest; public tree={j_tree}"},
        {"dataset": "ROSMA", "version": "10.5281/zenodo.7100542", "file_count": r_count, "size_bytes": r_bytes, "integrity": "repository MD5; SHA-256 deferred until selected files are acquired"},
        {"dataset": "BGU-SKILLS", "version": "1.0", "file_count": s_count, "size_bytes": s_bytes, "integrity": "repository MD5; SHA-256 deferred until selected files are acquired"},
        {"dataset": "BGU-PatCut", "version": "2.1", "file_count": p_count, "size_bytes": p_bytes, "integrity": "repository MD5; SHA-256 deferred until selected files are acquired"},
    ]
    write_csv(args.manifest_dir / "dataset_files_summary.csv", summaries, ["dataset", "version", "file_count", "size_bytes", "integrity"])

    source_rows = []
    for path in sorted((args.manifest_dir / "source_metadata").glob("*.json")):
        source_rows.append({"path": path.as_posix(), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    write_csv(args.manifest_dir / "source_metadata_sha256.csv", source_rows, ["path", "size_bytes", "sha256"])


if __name__ == "__main__":
    main()

