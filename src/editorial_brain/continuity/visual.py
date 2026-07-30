"""Pairwise visual continuity with motivated-discontinuity override."""

from __future__ import annotations

from editorial_brain.analysis.quality import histogram_similarity
from editorial_brain.continuity.motion import motion_score
from editorial_brain.continuity.screen_direction import screen_direction_score
from editorial_brain.continuity.semantic import semantic_continuity
from editorial_brain.continuity.shot_scale import shot_scale_score
from editorial_brain.core.models import ContinuityScore, Shot

MOTIVATED_DISCONTINUITIES = {
    "smash_cut",
    "surprise",
    "comedy",
    "time_jump",
    "contrast",
    "montage",
    "hard_reset",
}


def continuity_score(
    left: Shot,
    right: Shot,
    *,
    intent: str | None = None,
    room_tone: float = 0.5,
    dialogue: float = 0.5,
) -> ContinuityScore:
    position = _subject_position(left, right)
    direction = screen_direction_score(left.camera, right.camera)
    movement = motion_score(left, right)
    scale = shot_scale_score(left.camera, right.camera)
    angle = _angle(left, right)
    luminance = 1 - abs(left.mean_luminance - right.mean_luminance)
    color = (
        histogram_similarity(left.color_histogram, right.color_histogram)
        if left.color_histogram and right.color_histogram
        else 0.5
    )
    background = semantic_continuity(left, right)
    semantic = background
    action = _action(left, right)
    motivated = intent in MOTIVATED_DISCONTINUITIES
    values = [
        position,
        direction,
        movement,
        scale,
        angle,
        luminance,
        color,
        background,
        room_tone,
        dialogue,
        semantic,
        action,
    ]
    overall = sum(values) / len(values)
    if motivated:
        overall = max(overall, 0.75)
    return ContinuityScore(
        subject_position=position,
        screen_direction=direction,
        movement_direction=movement,
        shot_scale=scale,
        camera_angle=angle,
        camera_motion=movement,
        luminance=max(0, luminance),
        color=color,
        background=background,
        room_tone=room_tone,
        dialogue=dialogue,
        semantic=semantic,
        temporal_action=action,
        motivated_discontinuity=motivated,
        overall=overall,
    )


def _subject_position(left: Shot, right: Shot) -> float:
    left_subject = next((subject for subject in left.subjects if subject.role == "main"), None)
    right_subject = next((subject for subject in right.subjects if subject.role == "main"), None)
    if (
        left_subject is None
        or right_subject is None
        or left_subject.position_x is None
        or right_subject.position_x is None
    ):
        return 0.6
    return max(0, 1 - abs(left_subject.position_x - right_subject.position_x))


def _angle(left: Shot, right: Shot) -> float:
    if "unknown" in {left.camera.angle, right.camera.angle}:
        return 0.6
    return 1 if left.camera.angle == right.camera.angle else 0.7


def _action(left: Shot, right: Shot) -> float:
    if not left.actions or not right.actions:
        return 0.6
    left_labels = {action.label for action in left.actions}
    right_labels = {action.label for action in right.actions}
    return 1 if left_labels & right_labels else 0.5
