"""Compatibility import path for legacy EDL ASS preparation."""

from __future__ import annotations

import sys
from pathlib import Path

VIDEO_USE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(VIDEO_USE_ROOT))

from compat.caption_styles import (  # noqa: E402
    available_caption_styles,
    build_master_ass,
)

__all__ = ["available_caption_styles", "build_master_ass"]
