"""Camera descriptors from explicit semantic labels and measured motion."""

from __future__ import annotations

from typing import Literal, cast

from editorial_brain.core.models import CameraDescriptor, Confidence, EvidenceKind, Shot

SCALES = {"extreme_wide", "wide", "medium", "close", "detail"}
MOTIONS = {"locked", "pan", "tilt", "push", "pull", "dolly", "handheld", "zoom"}


def camera_from_labels(shot: Shot) -> CameraDescriptor:
    labels = {label.lower().replace(" ", "_") for label in shot.semantics.search_terms}
    scale = next((label for label in sorted(labels) if label in SCALES), "unknown")
    motion = next((label for label in sorted(labels) if label in MOTIONS), "unknown")
    if motion == "unknown" and shot.motion_energy < 0.05:
        motion = "locked"
    confidence = shot.semantics.confidence
    if motion == "locked" and shot.semantics.confidence.score == 0:
        confidence = Confidence(
            score=0.6,
            basis=EvidenceKind.DERIVED,
            calibration="low_optical_flow",
        )
    return CameraDescriptor(
        shot_scale=cast(
            Literal["extreme_wide", "wide", "medium", "close", "detail", "unknown"],
            scale,
        ),
        motion=cast(
            Literal[
                "locked", "pan", "tilt", "push", "pull", "dolly", "handheld", "zoom", "unknown"
            ],
            motion,
        ),
        confidence=confidence,
    )
