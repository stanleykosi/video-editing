"""Select range and handle helpers."""

from editorial_brain.core.models import Shot
from video_engine.api import RationalTime, TimeRange


def safe_handles(shot: Shot) -> tuple[RationalTime, RationalTime]:
    return (
        shot.inner_usable_range.start - shot.source_range.start,
        shot.source_range.end - shot.inner_usable_range.end,
    )


def fit_select_duration(shot: Shot, target: RationalTime) -> TimeRange:
    """Return the verified usable range; target duration is not a timestamp authority.

    Fine-cut refinement may shorten this range only at enumerated structural
    candidates. A centered arithmetic trim would create an arbitrary cut.
    """
    usable = shot.inner_usable_range
    del target
    return usable
