"""Measurable reference-edit analysis; outputs priors, never copied frames."""

from __future__ import annotations

from pathlib import Path

from editorial_brain.analysis.audio_events import analyze_audio_windows
from editorial_brain.analysis.frames import extract_representative_frames
from editorial_brain.analysis.shots import detect_shot_ranges
from editorial_brain.core.models import (
    CameraDescriptor,
    Confidence,
    EvidenceKind,
    EvidenceRef,
    ReferenceEditProfile,
    Shot,
    ShotQuality,
    ShotSemantics,
)
from editorial_brain.reference.audio import audio_profile
from editorial_brain.reference.captions import caption_density, visual_overlay_density
from editorial_brain.reference.grammar import motion_frequency, repetition, scale_distribution
from editorial_brain.reference.pacing import duration_quantiles, rhythm_curve
from video_engine.api import FrameRate, RationalTime, TimeRange, VideoEngine


class ReferenceAnalyzer:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()

    def analyze(self, source: Path) -> ReferenceEditProfile:
        source = source.resolve()
        record = VideoEngine(self.project_root).media().import_media(source, copy_into_store=False)
        video = record.probe.video_streams[0] if record.probe.video_streams else None
        if video is None or record.probe.duration is None:
            raise ValueError("reference analysis requires a video with measured duration")
        frame_rate = video.average_frame_rate or FrameRate(numerator=24)
        available = TimeRange(start=RationalTime.zero(), duration=record.probe.duration)
        ranges, _, boundary_evidence = detect_shot_ranges(
            source,
            media_id=record.id,
            media_sha256=record.sha256,
            frame_rate=frame_rate,
            available_range=available,
            analysis_version="reference-scenes-v1",
        )
        shots: list[Shot] = []
        evidence: list[EvidenceRef] = list(boundary_evidence)
        for position, source_range in enumerate(ranges):
            shot_id = f"reference-shot:{position:06d}"
            frames, refs, measured = extract_representative_frames(
                source,
                self.project_root / ".editorial-brain" / "reference" / record.sha256 / "frames",
                media_id=record.id,
                media_sha256=record.sha256,
                shot_id=shot_id,
                source_range=source_range,
                frame_rate=frame_rate,
                analysis_version="reference-frames-v1",
            )
            confidence = Confidence(
                score=1,
                basis=EvidenceKind.MEASURED,
                calibration="reference_frame_measurement",
                sample_size=len(frames),
            )
            shots.append(
                Shot(
                    id=shot_id,
                    media_id=record.id,
                    media_sha256=record.sha256,
                    source_range=source_range,
                    inner_usable_range=source_range,
                    frames=frames,
                    camera=CameraDescriptor(
                        shot_scale="unknown", motion="unknown", confidence=confidence
                    ),
                    quality=ShotQuality(
                        sharpness=measured.sharpness,
                        exposure=measured.exposure,
                        stability=max(0, 1 - measured.motion_energy),
                        composition=0.5,
                        confidence=confidence,
                    ),
                    semantics=ShotSemantics(
                        summary="reference shot measured without semantic identity inference",
                        confidence=Confidence(
                            score=0,
                            basis=EvidenceKind.DERIVED,
                            calibration="not_semantically_classified",
                        ),
                    ),
                    motion_energy=measured.motion_energy,
                    mean_luminance=measured.mean_luminance,
                    color_histogram=measured.color_histogram,
                    evidence=refs,
                )
            )
            evidence.extend(refs)
        windows, audio_events, audio_evidence = (
            analyze_audio_windows(
                source,
                media_id=record.id,
                media_sha256=record.sha256,
                analysis_version="reference-audio-v1",
            )
            if record.probe.audio_streams
            else ([], [], [])
        )
        evidence.extend(audio_evidence)
        energy_curve, silence_ratio = audio_profile(windows)
        duration_seconds = max(float(record.probe.duration.fraction), 0.001)
        subtitle_count = sum(stream.kind.value == "subtitle" for stream in record.probe.streams)
        overlay_density, placements = visual_overlay_density(
            [
                Path(frame.artifact_path)
                for shot in shots
                for frame in shot.frames
                if frame.artifact_path is not None
            ]
        )
        transient_events = [event for event in audio_events if event.kind == "transient"]
        cut_times = [item.start for item in ranges[1:]]
        music_sync = (
            sum(
                any(
                    abs(cut.fraction - event.source_range.start.fraction)
                    <= RationalTime(value=3, timescale=25).fraction
                    for event in transient_events
                )
                for cut in cut_times
            )
            / len(cut_times)
            if cut_times
            else 0
        )
        return ReferenceEditProfile(
            id=f"reference:{record.sha256[:16]}",
            source_sha256=record.sha256,
            shot_duration_quantiles=duration_quantiles(ranges),
            cut_frequency_hz=max(0, len(ranges) - 1) / duration_seconds,
            shot_scale_distribution=scale_distribution(shots),
            camera_motion_frequency=motion_frequency(shots),
            caption_density=caption_density(subtitle_count, record.probe.duration),
            caption_placement_distribution=placements if subtitle_count else {},
            graphic_density=overlay_density,
            transition_frequency=0,
            transition_type_distribution={"cut": 1.0} if len(ranges) > 1 else {},
            audio_energy_curve=energy_curve,
            sfx_event_density=len(transient_events) / duration_seconds,
            silence_ratio=silence_ratio,
            silence_placements=[window.source_range.start for window in windows if window.silent],
            music_sync_score=music_sync,
            rhythm_curve=rhythm_curve(ranges),
            repetition_score=repetition(shots),
            evidence=evidence,
        )
