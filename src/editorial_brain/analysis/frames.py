"""Boundary-aware representative-frame extraction and measured features."""

from __future__ import annotations

from itertools import pairwise
from pathlib import Path
from typing import Any, Literal, cast

import numpy as np

from editorial_brain.analysis.motion import optical_flow_energy
from editorial_brain.analysis.quality import color_histogram, frame_quality
from editorial_brain.core.hashing import file_sha256
from editorial_brain.core.models import (
    BrainModel,
    Confidence,
    EvidenceKind,
    EvidenceRef,
    ShotFrame,
)
from video_engine.api import FrameRate, RationalTime, RoundingMode, TimeRange


def representative_times(source_range: TimeRange, frame_rate: FrameRate) -> list[RationalTime]:
    if source_range.duration <= frame_rate.frame_duration:
        return [source_range.start]
    inset = min(frame_rate.frame_duration, source_range.duration / 10)
    candidates = [
        source_range.start + inset,
        source_range.start + source_range.duration / 2,
        source_range.end - inset,
    ]
    return sorted(set(candidates))


def extract_representative_frames(
    path: Path,
    output_dir: Path,
    *,
    media_id: str,
    media_sha256: str,
    shot_id: str,
    source_range: TimeRange,
    frame_rate: FrameRate,
    analysis_version: str = "frames-opencv-v1",
) -> tuple[list[ShotFrame], list[EvidenceRef], FrameMeasurements]:
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("frame extraction requires the brain-analysis dependencies") from exc
    output_dir.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"cannot decode media: {path}")
    frames: list[ShotFrame] = []
    evidence: list[EvidenceRef] = []
    arrays: list[np.ndarray[Any, Any]] = []
    qualities: list[dict[str, float]] = []
    histograms: list[list[float]] = []
    roles = ["opening", "representative", "closing"]
    try:
        for position, (time, role) in enumerate(
            zip(representative_times(source_range, frame_rate), roles, strict=False)
        ):
            frame_index = frame_rate.time_to_frames(time, rounding=RoundingMode.NEAREST)
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, frame = capture.read()
            if not ok or frame is None:
                raise ValueError(f"failed to decode representative frame {frame_index}")
            destination = output_dir / f"{shot_id}-{position:02d}.jpg"
            if not cv2.imwrite(str(destination), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 92]):
                raise OSError(f"failed to write representative frame {destination}")
            digest = file_sha256(destination)
            evidence_ref = EvidenceRef(
                id=f"evidence:{shot_id}:frame:{position:02d}",
                kind=EvidenceKind.MEASURED,
                media_id=media_id,
                media_sha256=media_sha256,
                source_range=TimeRange(start=time, duration=frame_rate.frame_duration),
                frame_id=f"frame:{shot_id}:{position:02d}",
                analysis_version=analysis_version,
                confidence=Confidence(
                    score=1,
                    basis=EvidenceKind.MEASURED,
                    calibration="decoded_frame",
                ),
                summary="decoded representative frame",
            )
            evidence.append(evidence_ref)
            frames.append(
                ShotFrame(
                    id=f"frame:{shot_id}:{position:02d}",
                    media_id=media_id,
                    time=time,
                    artifact_path=str(destination),
                    sha256=digest,
                    role=cast(
                        Literal["opening", "middle", "closing", "action_peak", "representative"],
                        role,
                    ),
                    evidence=[evidence_ref],
                )
            )
            arrays.append(frame)
            qualities.append(frame_quality(frame))
            histograms.append(color_histogram(frame))
    finally:
        capture.release()
    motion = [optical_flow_energy(left, right) for left, right in pairwise(arrays)]
    aggregate = FrameMeasurements(
        sharpness=_mean([item["sharpness"] for item in qualities]),
        exposure=_mean([item["exposure"] for item in qualities]),
        motion_energy=_mean(motion),
        mean_luminance=_mean([item["mean_luminance"] for item in qualities]),
        color_histogram=[
            _mean([histogram[index] for histogram in histograms]) for index in range(48)
        ],
    )
    return frames, evidence, aggregate


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0


class FrameMeasurements(BrainModel):
    sharpness: float
    exposure: float
    motion_energy: float
    mean_luminance: float
    color_histogram: list[float]
