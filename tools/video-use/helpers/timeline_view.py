"""Deprecated command path forwarding to canonical timeline inspection."""

from __future__ import annotations

import sys
from pathlib import Path

VIDEO_USE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(VIDEO_USE_ROOT))

from compat import timeline_view as _implementation  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    _implementation.ENTRYPOINT_PATH = Path(__file__).resolve()
    return _implementation.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
