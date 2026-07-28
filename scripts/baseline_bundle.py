"""Materialize the immutable engine baseline bundle outside the checkout."""

from __future__ import annotations

import atexit
import shutil
import tarfile
import tempfile
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "testdata" / "engine" / "baseline.tar.gz"


def extract_archive(archive: Path, destination: Path) -> None:
    """Extract a trusted repository archive after rejecting unsafe members."""
    destination_root = destination.resolve()
    with tarfile.open(archive, "r:gz") as bundle:
        for member in bundle.getmembers():
            target = (destination / member.name).resolve()
            if not target.is_relative_to(destination_root) or member.issym() or member.islnk():
                raise ValueError(f"unsafe archive member: {member.name}")
        bundle.extractall(destination)


@cache
def materialize_baseline(archive: Path = ARCHIVE) -> Path:
    """Extract the frozen baseline safely into a process-owned temporary directory."""
    destination = Path(tempfile.mkdtemp(prefix="video-engine-baseline-"))
    atexit.register(shutil.rmtree, destination, True)
    extract_archive(archive, destination)
    baseline = destination / "engine_baseline"
    if not (baseline / "baseline_manifest.json").is_file():
        raise ValueError("baseline archive does not contain its manifest")
    return baseline
