"""Evidence-backed source analysis over canonical engine media."""

from __future__ import annotations

from itertools import combinations
from pathlib import Path
from urllib.parse import unquote, urlparse

import numpy as np

from editorial_brain.analysis.audio_events import AudioWindow, analyze_audio_windows
from editorial_brain.analysis.contact_sheets import build_contact_sheet
from editorial_brain.analysis.frames import extract_representative_frames
from editorial_brain.analysis.music import analyze_music
from editorial_brain.analysis.pauses import classify_pauses
from editorial_brain.analysis.shots import detect_shot_ranges, subshot_ranges
from editorial_brain.analysis.speech import build_phrases
from editorial_brain.analysis.synchronization import correlate_audio
from editorial_brain.core.hashing import file_sha256
from editorial_brain.core.models import (
    AudioEvent,
    CameraDescriptor,
    Confidence,
    EvidenceBundle,
    EvidenceKind,
    EvidenceRef,
    MediaUnderstandingIndex,
    PauseEvent,
    Shot,
    ShotFrame,
    ShotQuality,
    ShotSemantics,
    SourceSynchronization,
    Transcript,
)
from editorial_brain.providers.base import (
    ProviderStatus,
    TranscriptionProvider,
    TranscriptionRequest,
)
from video_engine.api import FrameRate, MediaReference, Project, RationalTime, TimeRange


class MediaAnalysisPipeline:
    def __init__(
        self,
        artifact_root: Path,
        *,
        analysis_version: str = "media-understanding-v1",
        transcription_provider: TranscriptionProvider | None = None,
    ) -> None:
        self.artifact_root = artifact_root.resolve()
        self.analysis_version = analysis_version
        self.transcription_provider = transcription_provider
        self.provider_failures: list[str] = []

    def analyze(self, project: Project) -> MediaUnderstandingIndex:
        shots: list[Shot] = []
        boundaries = []
        transcripts: list[Transcript] = []
        pauses = []
        audio_events = []
        music_events = []
        evidence = []
        provider_evidence = []
        media_hashes: dict[str, str] = {}
        windows_by_media: dict[str, list[AudioWindow]] = {}
        for media in sorted(project.media, key=lambda value: value.id):
            path = _media_path(media)
            digest = _verified_hash(media, path)
            media_hashes[media.id] = digest
            video_stream = next(
                (stream for stream in media.streams if stream.codec_type == "video"), None
            )
            audio_stream = next(
                (stream for stream in media.streams if stream.codec_type == "audio"), None
            )
            if video_stream is not None:
                available_range = _available_range(media)
                frame_rate = video_stream.frame_rate or project.settings.frame_rate
                source_ranges, source_boundaries, boundary_evidence = detect_shot_ranges(
                    path,
                    media_id=media.id,
                    media_sha256=digest,
                    frame_rate=frame_rate,
                    available_range=available_range,
                )
                boundaries.extend(source_boundaries)
                evidence.extend(boundary_evidence)
                for position, source_range in enumerate(source_ranges):
                    shot, shot_evidence = self._shot(
                        path,
                        media=media,
                        digest=digest,
                        position=position,
                        source_range=source_range,
                        frame_rate=frame_rate,
                    )
                    shots.append(shot)
                    evidence.extend(shot_evidence)
            windows: list[AudioWindow] = []
            events: list[AudioEvent] = []
            if audio_stream is not None:
                windows, events, audio_evidence = analyze_audio_windows(
                    path,
                    media_id=media.id,
                    media_sha256=digest,
                )
                audio_events.extend(events)
                windows_by_media[media.id] = windows
                evidence.extend(audio_evidence)
                measured_music, music_evidence = analyze_music(
                    path,
                    media_id=media.id,
                    media_sha256=digest,
                )
                music_events.extend(measured_music)
                evidence.extend(music_evidence)
            transcript = self._transcribe(media, path, digest)
            if transcript is not None:
                transcript = build_phrases(transcript)
                transcripts.append(transcript)
                pauses.extend(
                    classify_pauses(
                        transcript,
                        audio_windows=windows,
                        audio_events=events,
                    )
                )
                if transcript.provider_evidence is not None:
                    provider_evidence.append(transcript.provider_evidence)
        for pause in pauses:
            evidence.extend(pause.evidence)
        derived_shots, derived_evidence = _derive_subshots(
            shots,
            transcripts,
            pauses,
            audio_events,
            analysis_version=self.analysis_version,
        )
        shots.extend(derived_shots)
        evidence.extend(derived_evidence)
        contact_sheets = _contact_sheets(self.artifact_root, shots)
        synchronizations = _synchronize_sources(windows_by_media, media_hashes)
        for synchronization in synchronizations:
            evidence.extend(synchronization.evidence)
        return MediaUnderstandingIndex(
            project_id=project.id,
            analysis_version=self.analysis_version,
            media_hashes=media_hashes,
            shots=shots,
            shot_boundaries=boundaries,
            transcripts=transcripts,
            pauses=pauses,
            audio_events=audio_events,
            music_events=music_events,
            synchronizations=synchronizations,
            evidence=EvidenceBundle(refs=evidence),
            provider_evidence=provider_evidence,
            extensions={
                "editorial_brain:provider_unavailable": self.provider_failures,
                "editorial_brain:contact_sheets": contact_sheets,
            },
        )

    def _shot(
        self,
        path: Path,
        *,
        media: MediaReference,
        digest: str,
        position: int,
        source_range: TimeRange,
        frame_rate: FrameRate,
    ) -> tuple[Shot, list[EvidenceRef]]:
        shot_id = f"shot:{media.id}:{position:06d}"
        frame_dir = self.artifact_root / "frames" / media.id
        frames, frame_evidence, measured = extract_representative_frames(
            path,
            frame_dir,
            media_id=media.id,
            media_sha256=digest,
            shot_id=shot_id,
            source_range=source_range,
            frame_rate=frame_rate,
        )
        inner = _safe_inner_range(source_range, frame_rate)
        measured_confidence = Confidence(
            score=1,
            basis=EvidenceKind.MEASURED,
            calibration="decoded_representative_frames",
            sample_size=len(frames),
        )
        unknown_confidence = Confidence(
            score=0,
            basis=EvidenceKind.DERIVED,
            calibration="not_yet_classified",
        )
        shot = Shot(
            id=shot_id,
            media_id=media.id,
            media_sha256=digest,
            source_range=source_range,
            inner_usable_range=inner,
            frames=frames,
            camera=CameraDescriptor(
                shot_scale="unknown",
                motion="unknown",
                confidence=unknown_confidence,
            ),
            quality=ShotQuality(
                sharpness=measured.sharpness,
                exposure=measured.exposure,
                stability=max(0, 1 - measured.motion_energy),
                composition=0.5,
                confidence=measured_confidence,
            ),
            semantics=ShotSemantics(
                summary="Unclassified source shot; semantic provider has not contributed",
                confidence=unknown_confidence,
            ),
            motion_energy=measured.motion_energy,
            mean_luminance=measured.mean_luminance,
            color_histogram=measured.color_histogram,
            evidence=frame_evidence,
        )
        return shot, frame_evidence

    def _transcribe(self, media: MediaReference, path: Path, digest: str) -> Transcript | None:
        if self.transcription_provider is None:
            return None
        result = self.transcription_provider.transcribe(
            TranscriptionRequest(
                request_id=f"transcribe:{media.id}:{digest[:12]}",
                media_id=media.id,
                media_sha256=digest,
                source_path=path,
            )
        )
        if result.status is ProviderStatus.UNAVAILABLE:
            self.provider_failures.append(
                f"{self.transcription_provider.provider_name}:{result.error_code or 'unavailable'}"
            )
            return None
        if result.status is not ProviderStatus.SUCCESS or result.output is None:
            raise RuntimeError(result.error_message or "transcription provider failed")
        return result.output


def _media_path(media: MediaReference) -> Path:
    parsed = urlparse(media.uri)
    if parsed.scheme not in {"", "file"}:
        raise ValueError(f"Brain analysis accepts only local canonical media: {media.uri!r}")
    raw = unquote(parsed.path) if parsed.scheme == "file" else media.uri
    path = Path(raw).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def _verified_hash(media: MediaReference, path: Path) -> str:
    digest = file_sha256(path)
    if media.sha256 is None:
        raise ValueError(f"canonical media {media.id!r} lacks SHA-256 identity")
    if digest != media.sha256:
        raise ValueError(f"canonical media hash mismatch for {media.id!r}")
    return digest


def _available_range(media: MediaReference) -> TimeRange:
    if media.available_range is None or media.available_range.duration.value <= 0:
        raise ValueError(f"video media {media.id!r} lacks a positive available range")
    return media.available_range


def _safe_inner_range(source_range: TimeRange, frame_rate: FrameRate) -> TimeRange:
    handle = min(frame_rate.frame_duration * 2, source_range.duration / 10)
    if source_range.duration <= handle * 2:
        return source_range
    return TimeRange.from_start_end(source_range.start + handle, source_range.end - handle)


def _derive_subshots(
    shots: list[Shot],
    transcripts: list[Transcript],
    pauses: list[PauseEvent],
    audio_events: list[AudioEvent],
    *,
    analysis_version: str,
) -> tuple[list[Shot], list[EvidenceRef]]:
    structural: dict[str, set[RationalTime]] = {}
    for transcript in transcripts:
        values = structural.setdefault(transcript.media_id, set())
        for phrase in transcript.phrases:
            values.update({phrase.source_range.start, phrase.source_range.end})
    for pause in pauses:
        values = structural.setdefault(pause.media_id, set())
        values.update({pause.source_range.start, pause.source_range.end})
    for event in audio_events:
        if event.kind in {"transient", "speech_start", "speech_end"}:
            values = structural.setdefault(event.media_id, set())
            values.update({event.source_range.start, event.source_range.end})

    derived: list[Shot] = []
    evidence: list[EvidenceRef] = []
    minimum = RationalTime(value=1, timescale=2)
    for shot in shots:
        ranges = subshot_ranges(
            shot.source_range,
            list(structural.get(shot.media_id, set())),
            minimum_duration=minimum,
        )
        if len(ranges) < 2:
            continue
        for position, source_range in enumerate(ranges):
            subshot_id = f"{shot.id}:moment:{position:04d}"
            confidence = Confidence(
                score=0.9,
                basis=EvidenceKind.DERIVED,
                calibration="verified_structural_boundaries_v1",
            )
            ref = EvidenceRef(
                id=f"evidence:{subshot_id}",
                kind=EvidenceKind.DERIVED,
                media_id=shot.media_id,
                media_sha256=shot.media_sha256,
                source_range=source_range,
                shot_id=subshot_id,
                analysis_version=analysis_version,
                confidence=confidence,
                summary="candidate moment bounded by verified speech or audio structure",
            )
            inner_start = max(source_range.start, shot.inner_usable_range.start)
            inner_end = min(source_range.end, shot.inner_usable_range.end)
            inner = (
                TimeRange.from_start_end(inner_start, inner_end)
                if inner_end > inner_start
                else source_range
            )
            derived.append(
                shot.model_copy(
                    update={
                        "id": subshot_id,
                        "parent_shot_id": shot.id,
                        "source_range": source_range,
                        "inner_usable_range": inner,
                        "frames": [
                            frame for frame in shot.frames if source_range.contains(frame.time)
                        ],
                        "evidence": [*shot.evidence, ref],
                    },
                    deep=True,
                )
            )
            evidence.append(ref)
    return derived, evidence


def _contact_sheets(artifact_root: Path, shots: list[Shot]) -> dict[str, str]:
    by_media: dict[str, list[ShotFrame]] = {}
    for shot in shots:
        if shot.parent_shot_id is None:
            by_media.setdefault(shot.media_id, []).extend(shot.frames)
    paths: dict[str, str] = {}
    for media_id, values in sorted(by_media.items()):
        if not values:
            continue
        destination = artifact_root / "shots" / media_id / "contact-sheet.png"
        paths[media_id] = str(build_contact_sheet(values, destination))
    return paths


def _synchronize_sources(
    windows_by_media: dict[str, list[AudioWindow]], media_hashes: dict[str, str]
) -> list[SourceSynchronization]:
    results: list[SourceSynchronization] = []
    for reference_id, target_id in combinations(sorted(windows_by_media), 2):
        reference = np.asarray(
            [window.rms for window in windows_by_media[reference_id]], dtype=np.float64
        )
        target = np.asarray(
            [window.rms for window in windows_by_media[target_id]], dtype=np.float64
        )
        if reference.size < 2 or target.size < 2:
            continue
        results.append(
            correlate_audio(
                reference,
                target,
                sample_rate=10,
                reference_media_id=reference_id,
                target_media_id=target_id,
                reference_media_sha256=media_hashes[reference_id],
                target_media_sha256=media_hashes[target_id],
            )
        )
    return results
