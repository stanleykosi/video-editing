"""Deprecated command path forwarding to canonical color compatibility tools."""

from __future__ import annotations

import sys
from pathlib import Path

VIDEO_USE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(VIDEO_USE_ROOT))

from compat.grade import main  # noqa: E402

if __name__ == "__main__":
    main()
