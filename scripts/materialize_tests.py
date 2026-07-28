#!/usr/bin/env python3
"""Materialize the review-collapsed test suite for CI or local verification."""

from __future__ import annotations

import argparse
import gzip
import json
import os
import tarfile
import tempfile
from pathlib import Path

from baseline_bundle import extract_archive

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "testdata" / "engine" / "tests.tar.gz"


def package_tests(source: Path, archive: Path = ARCHIVE) -> None:
    """Create a deterministic archive of the ignored local test tree."""
    if not source.is_dir():
        raise ValueError(f"test source directory does not exist: {source}")
    archive.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{archive.name}.", dir=archive.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with (
            temporary.open("wb") as raw,
            gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed,
            tarfile.open(fileobj=compressed, mode="w") as bundle,
        ):
            paths = [source, *source.rglob("*")]
            for path in sorted(paths, key=lambda item: item.as_posix()):
                if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
                    continue
                member = bundle.gettarinfo(
                    str(path), arcname=path.relative_to(source.parent).as_posix()
                )
                member.uid = member.gid = 0
                member.uname = member.gname = ""
                member.mtime = 0
                if member.isfile():
                    with path.open("rb") as handle:
                        bundle.addfile(member, handle)
                else:
                    bundle.addfile(member)
        temporary.replace(archive)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=ROOT)
    parser.add_argument(
        "--pack",
        action="store_true",
        help="replace the committed archive from the ignored local tests directory",
    )
    args = parser.parse_args()
    if args.pack:
        source = ROOT / "tests"
        package_tests(source)
        print(
            json.dumps(
                {
                    "ok": True,
                    "archive": str(ARCHIVE),
                    "source": str(source),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    destination = args.destination.resolve()
    target = destination / "tests"
    if target.exists():
        raise SystemExit(f"refusing to overwrite existing test directory: {target}")
    destination.mkdir(parents=True, exist_ok=True)
    extract_archive(ARCHIVE, destination)
    required = (
        target / "unit" / "test_time.py",
        target / "integration" / "test_render_engine.py",
        target / "golden" / "test_canonical_projects.py",
    )
    missing = [str(path) for path in required if not path.is_file()]
    print(
        json.dumps(
            {
                "ok": not missing,
                "archive": str(ARCHIVE),
                "destination": str(target),
                "missing": missing,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if not missing else 2


if __name__ == "__main__":
    raise SystemExit(main())
