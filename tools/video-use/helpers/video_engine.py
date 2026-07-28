"""Location-independent launcher for the repository's unified engine CLI."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[3]
    executable = root / ".venv" / "bin" / "video-engine"
    if executable.is_file():
        os.execv(executable, [str(executable), *sys.argv[1:]])
    # The launcher itself is named video_engine.py, so package source must win.
    sys.path.insert(0, str(root / "src"))
    from video_engine.cli.main import main as engine_main

    raise SystemExit(engine_main(sys.argv[1:]))


if __name__ == "__main__":
    main()
