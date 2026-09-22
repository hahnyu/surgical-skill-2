#!/usr/bin/env python3
"""Acquire the smallest Phase 2 data subset and verify source integrity.

Raw files remain under the Git-ignored data/raw tree. PatCut participant ZIPs
are never downloaded in full; only MAT members needed for kinematics, task
windows, and accuracy outcomes are extracted through HTTP ranges.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from surgical_skill2.remote_zip import open_remote_zip


RAW = ROOT / "data" / "raw"
MANIFESTS = ROOT / "data" / "manifests"


def digest(path: Path, algorithm: str) -> str:
    for attempt in range(3):
        try:
            result = hashlib.new(algorithm.lower())
            with path.open("rb") as handle:
                for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
                    result.update(block)
            return result.hexdigest()
        except TimeoutError:
            if attempt == 2:
                raise
    raise AssertionError("unreachable")


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def download(row: dict[str, str], target: Path) -> tuple[str, int, str]:
    target.parent.mkdir(parents=True, exist_ok=True)
    expected = row["provided_checksum"].lower()
    algorithm = row["provided_checksum_type"].lower()
    if target.exists() and target.stat().st_size == int(row["size_bytes"]):
        observed = digest(target, algorithm)
        if observed == expected:
            return target.as_posix(), target.stat().st_size, digest(target, "sha256")
    partial = target.with_suffix(target.suffix + ".part")
    expected_size = int(row["size_bytes"])
    for attempt in range(8):
        offset = partial.stat().st_size if partial.exists() else 0
        if offset == expected_size:
            break
        if offset > expected_size:
            partial.unlink()
            offset = 0
        command = [
            "curl", "-L", "--fail", "--silent", "--show-error",
            "--retry", "8", "--retry-all-errors", "--connect-timeout", "30",
            "--speed-time", "45", "--speed-limit", "1024",
            "--continue-at", "-", "--output", str(partial), row["download_url"],
        ]
        completed = subprocess.run(command, check=False)
        if completed.returncode and attempt == 7:
            raise IOError(f"curl failed repeatedly for {target} (exit {completed.returncode})")
    if partial.stat().st_size != expected_size:
        raise IOError(f"size mismatch after retries for {target}: {partial.stat().st_size} != {expected_size}")
    observed = digest(partial, algorithm)
    if observed != expected:
        raise IOError(f"{algorithm} mismatch for {target}: {observed} != {expected}")
    os.replace(partial, target)
    return target.as_posix(), target.stat().st_size, digest(target, "sha256")


def acquire_rosma(workers: int) -> list[tuple[str, int, str]]:
    rows = [
        row for row in read_rows(MANIFESTS / "rosma_files.csv")
        if row["path"] == "scores.csv" or re.match(r"^X\d{2}_.+\.csv$", row["path"])
    ]
    target_root = RAW / "rosma"
    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(download, row, target_root / row["path"]): row for row in rows}
        for index, future in enumerate(as_completed(futures), 1):
            results.append(future.result())
            if index % 20 == 0 or index == len(rows):
                print(f"ROSMA {index}/{len(rows)}", flush=True)
    return results


def acquire_bgu_skills(workers: int) -> list[tuple[str, int, str]]:
    task_keys = {
        "Knot Tying": "Knottying",
        "Ring Tower Transfer": "Ringtowertransfer",
        "Suturing": "Suturing",
    }
    selected = []
    for row in read_rows(MANIFESTS / "bgu_skills_files.csv"):
        path = Path(row["path"])
        directory = path.parts[0] if len(path.parts) > 1 else ""
        label = path.name
        if directory not in task_keys:
            continue
        key = task_keys[directory]
        if label == "Kinematics.zip":
            target = RAW / "bgu_skills" / f"{key}_Kinematics.zip"
        elif label.endswith("_Annotations_StartFinish_Events.csv") or label.startswith("Notes"):
            target = RAW / "bgu_skills" / label
        else:
            continue
        selected.append((row, target))
    results = []
    with ThreadPoolExecutor(max_workers=min(workers, 3)) as pool:
        futures = {pool.submit(download, row, target): target for row, target in selected}
        for index, future in enumerate(as_completed(futures), 1):
            results.append(future.result())
            print(f"BGU-SKILLS {index}/{len(selected)}: {futures[future].name}", flush=True)
    from openpyxl import load_workbook

    for xlsx in sorted((RAW / "bgu_skills").glob("Notes*.xlsx")):
        workbook = load_workbook(xlsx, read_only=True, data_only=True)
        sheet = workbook.active
        csv_path = xlsx.with_suffix(".csv")
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerows(sheet.iter_rows(values_only=True))
        workbook.close()
        results.append((csv_path.as_posix(), csv_path.stat().st_size, digest(csv_path, "sha256")))
    return results


def _extract_patcut_archive(row: dict[str, str]) -> list[tuple[str, int, str]]:
    experiment = "force" if "Force" in row["path"] else "motion"
    participant = re.search(r"subj_(\d+)\.zip$", row["path"]).group(1)
    target_root = RAW / "bgu_patcut" / experiment / participant
    target_root.mkdir(parents=True, exist_ok=True)
    results = []
    with open_remote_zip(row["download_url"], int(row["size_bytes"])) as zipped:
        selected = [
            info for info in zipped.infolist()
            if info.filename.endswith("AccuracyResults.mat")
            or info.filename.endswith("Segmentation.mat")
            or re.search(r"_trial_\d+\.mat$", info.filename)
        ]
        for info in sorted(selected, key=lambda item: item.filename):
            target = target_root / Path(info.filename).name
            if target.exists() and target.stat().st_size == info.file_size:
                results.append((target.as_posix(), info.file_size, digest(target, "sha256")))
                continue
            partial = target.with_suffix(target.suffix + ".part")
            with zipped.open(info) as source, partial.open("wb") as sink:
                shutil.copyfileobj(source, sink, length=4 * 1024 * 1024)
            if partial.stat().st_size != info.file_size:
                raise IOError(f"ZIP member size mismatch: {info.filename}")
            os.replace(partial, target)
            results.append((target.as_posix(), target.stat().st_size, digest(target, "sha256")))
    print(f"BGU-PatCut {experiment}/{participant}: {len(selected)} members", flush=True)
    return results


def acquire_bgu_patcut(workers: int) -> list[tuple[str, int, str]]:
    rows = [row for row in read_rows(MANIFESTS / "bgu_patcut_files.csv") if row["path"].endswith(".zip")]
    results = []
    with ThreadPoolExecutor(max_workers=min(workers, 3)) as pool:
        futures = [pool.submit(_extract_patcut_archive, row) for row in rows]
        for future in as_completed(futures):
            results.extend(future.result())
    return results


def write_local_manifest(rows: list[tuple[str, int, str]]) -> None:
    path = RAW / "phase2_acquisition_manifest.csv"
    merged: dict[str, tuple[int, str]] = {}
    if path.exists():
        for row in read_rows(path):
            merged[row["path"]] = (int(row["size_bytes"]), row["sha256"])
    for name, size, sha in rows:
        relative = str(Path(name).resolve().relative_to(ROOT.resolve()))
        merged[relative] = (int(size), sha)
    normalized = sorted((name, size, sha) for name, (size, sha) in merged.items())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["path", "size_bytes", "sha256"])
        writer.writerows(normalized)
    print(f"Wrote {path} with {len(normalized)} files", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=["all", "rosma", "bgu_skills", "bgu_patcut"], default="all")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    free = shutil.disk_usage(ROOT).free
    if free < 18_000_000_000 and args.dataset == "all":
        raise SystemExit(f"Phase 2 acquisition requires at least 18 GB free; found {free} bytes")
    results: list[tuple[str, int, str]] = []
    if args.dataset in {"all", "rosma"}:
        acquired = acquire_rosma(args.workers)
        results.extend(acquired)
        write_local_manifest(acquired)
    if args.dataset in {"all", "bgu_skills"}:
        acquired = acquire_bgu_skills(args.workers)
        results.extend(acquired)
        write_local_manifest(acquired)
    if args.dataset in {"all", "bgu_patcut"}:
        acquired = acquire_bgu_patcut(args.workers)
        results.extend(acquired)
        write_local_manifest(acquired)


if __name__ == "__main__":
    main()
