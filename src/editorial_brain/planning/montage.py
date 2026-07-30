"""Progressive montage ordering with bounded music influence."""

from editorial_brain.core.models import MusicEvent, SelectCandidate
from video_engine.api import RationalTime

DEFAULT_MONTAGE_SPACING = RationalTime(value=3, timescale=10)


def order_montage(
    candidates: list[SelectCandidate], music_events: list[MusicEvent]
) -> list[SelectCandidate]:
    progression = sorted(
        candidates,
        key=lambda item: (
            item.score.action_completeness,
            item.score.visual_clarity,
            item.score.novelty,
            item.id,
        ),
    )
    if len(progression) > 1:
        strongest_final = max(
            progression,
            key=lambda item: (item.score.evidence_value + item.score.visual_clarity, item.id),
        )
        progression = [item for item in progression if item.id != strongest_final.id]
        progression.append(strongest_final)
    return progression


def montage_cut_anchors(
    events: list[MusicEvent],
    *,
    minimum_spacing: RationalTime = DEFAULT_MONTAGE_SPACING,
) -> list[RationalTime]:
    """Prefer phrase/bar structure and deliberately skip a mechanical beat grid."""
    structural = [
        event for event in events if event.kind in {"phrase", "section", "bar", "downbeat"}
    ]
    anchors: list[RationalTime] = []
    for event in sorted(structural, key=lambda item: (item.source_range.start, item.id)):
        time = event.source_range.start
        if not anchors or time - anchors[-1] >= minimum_spacing:
            anchors.append(time)
    return anchors
