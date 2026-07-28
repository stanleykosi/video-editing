#!/usr/bin/env python3
"""Validate the immutable phase-zero archive after legacy renderer removal."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from baseline_bundle import materialize_baseline

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_ROOT = Path("/home/stanley/video-editing")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relocate(value: str, baseline: Path) -> Path:
    path = Path(value)
    try:
        relative = path.relative_to(ARCHIVE_ROOT)
    except ValueError:
        return path
    baseline_relative = Path("test_projects") / "engine_baseline"
    if relative.is_relative_to(baseline_relative):
        return baseline / relative.relative_to(baseline_relative)
    return ROOT / relative


def validate_record(path: Path, expected: str, failures: list[dict[str, Any]]) -> None:
    actual = sha256_file(path) if path.is_file() else None
    if actual != expected:
        failures.append({"path": str(path), "expected_sha256": expected, "actual_sha256": actual})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--baseline-dir",
        type=Path,
        default=None,
    )
    args = parser.parse_args()
    directory = args.baseline_dir.resolve() if args.baseline_dir else materialize_baseline()
    manifest_path = directory / "baseline_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[dict[str, Any]] = []
    for path, digest in manifest["inputs"].items():
        validate_record(relocate(path, directory), digest, failures)
    for record in manifest["outputs"].values():
        validate_record(relocate(record["path"], directory), record["sha256"], failures)
    for record in manifest["contact_sheets"].values():
        validate_record(relocate(record["path"], directory), record["sha256"], failures)
    payload = {
        "ok": not failures,
        "manifest": str(manifest_path),
        "input_count": len(manifest["inputs"]),
        "output_count": len(manifest["outputs"]),
        "contact_sheet_count": len(manifest["contact_sheets"]),
        "failures": failures,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
