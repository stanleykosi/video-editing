"""Inspect or translate legacy color decisions without rendering media.

This compatibility utility exposes the canonical measured-color service and the
typed equivalents of the historical named presets. It deliberately has no
output-file or raw-filter execution mode; production rendering belongs to the
``video-engine`` timeline and render API.

Usage:
    python helpers/grade.py --analyze INPUT [--start S --duration S] [--json]
    python helpers/grade.py --print-preset NAME [--json]
    python helpers/grade.py --list-presets [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from video_engine.api.engine import VideoEngine  # noqa: E402
from video_engine.color.models import CreativeGrade, MeasuredAutoGrade  # noqa: E402
from video_engine.core.schema import Effect, EffectKind  # noqa: E402
from video_engine.core.time import RationalTime, TimeRange  # noqa: E402

PRESETS: dict[str, CreativeGrade | None] = {
    "subtle": CreativeGrade(contrast=1.03, saturation=0.98),
    "neutral_punch": CreativeGrade(contrast=1.06),
    "warm_cinematic": CreativeGrade(
        exposure_stops=-0.03,
        temperature=0.08,
        contrast=1.12,
        saturation=0.88,
        highlights=-0.05,
        shadows=-0.03,
    ),
    "none": None,
}


def get_preset(name: str) -> CreativeGrade | None:
    """Return a typed historical preset translation."""
    if name not in PRESETS:
        raise KeyError(f"unknown preset '{name}'. Available: {', '.join(sorted(PRESETS))}")
    return PRESETS[name]


def preset_effect(name: str) -> Effect | None:
    grade = get_preset(name)
    if grade is None:
        return None
    return Effect(
        id=f"legacy-preset-{name}",
        kind=EffectKind.COLOR_GRADE,
        parameters=grade.model_dump(mode="json"),
        extensions={"legacy_preset": name},
    )


def auto_grade_for_clip(
    video: Path,
    start: Fraction = Fraction(0),
    duration: Fraction | None = None,
) -> MeasuredAutoGrade:
    """Return a measured canonical correction for one exact source range."""
    if start < 0:
        raise ValueError("auto-grade start must be nonnegative")
    if start and duration is None:
        raise ValueError("auto-grade duration is required when start is nonzero")
    if duration is not None and duration <= 0:
        raise ValueError("auto-grade duration must be positive")
    source_range = None
    if duration is not None:
        source_range = TimeRange(
            start=RationalTime.from_fraction(start),
            duration=RationalTime.from_fraction(duration),
        )
    return VideoEngine(ROOT).color().auto_grade(video, source_range=source_range)


def _payload_for_preset(name: str) -> dict[str, Any]:
    effect = preset_effect(name)
    return {
        "preset": name,
        "effect": effect.model_dump(mode="json") if effect is not None else None,
    }


def _print(payload: Any, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    if isinstance(payload, dict) and "preset" in payload:
        print(f"{payload['preset']}: {json.dumps(payload['effect'], sort_keys=True)}")
        return
    print(json.dumps(payload, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect canonical measured color or translate legacy presets"
    )
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--analyze", type=Path, metavar="INPUT")
    action.add_argument("--print-preset", choices=sorted(PRESETS))
    action.add_argument("--list-presets", action="store_true")
    parser.add_argument(
        "--start",
        type=Fraction,
        default=Fraction(0),
        help="Exact source-range start as seconds or a rational N/D.",
    )
    parser.add_argument(
        "--duration",
        type=Fraction,
        help="Exact source-range duration as seconds or a rational N/D.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.list_presets:
        _print(
            [_payload_for_preset(name) for name in sorted(PRESETS)],
            as_json=args.json,
        )
        return
    if args.print_preset is not None:
        _print(_payload_for_preset(args.print_preset), as_json=args.json)
        return

    assert args.analyze is not None
    if not args.analyze.is_file():
        parser.error(f"input not found: {args.analyze}")
    measured = auto_grade_for_clip(
        args.analyze,
        start=args.start,
        duration=args.duration,
    )
    _print(measured.model_dump(mode="json"), as_json=args.json)


if __name__ == "__main__":
    main()
