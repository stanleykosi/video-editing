"""Small deterministic, non-binary fixtures for editorial behavior benchmarks."""

from __future__ import annotations

from pathlib import Path

from editorial_brain.benchmark.scenarios import GoldenScenario
from editorial_brain.core.models import (
    CameraDescriptor,
    Confidence,
    EditorialBrief,
    EditorialConstraints,
    EvidenceBundle,
    EvidenceKind,
    EvidenceRef,
    MediaUnderstandingIndex,
    MusicEvent,
    ReferenceEditProfile,
    Shot,
    ShotBoundary,
    ShotQuality,
    ShotSemantics,
    SourceSynchronization,
    Transcript,
    TranscriptPhrase,
    TranscriptWord,
    VisibleReaction,
)
from video_engine.api import MediaReference, Project, RationalTime, TimeRange, VideoEngine

FIXTURE_SHA = "d3b7d6a1e2e46063a12597d9b00f884257c9355d840ac1d208e8c3e7fc0ae37c"


def synthetic_fixture(
    project_root: Path, scenario: GoldenScenario
) -> tuple[Project, EditorialBrief, MediaUnderstandingIndex, set[str]]:
    project = (
        VideoEngine(project_root)
        .create_project(f"Benchmark {scenario.id}")
        .model_copy(update={"id": f"benchmark-project-{scenario.id}"})
    )
    source_path = project_root / "synthetic-not-decoded.mp4"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    if not source_path.exists():
        source_path.write_bytes(b"editorial-brain deterministic benchmark placeholder\n")
    media = MediaReference.model_validate(
        {
            "id": "benchmark-media",
            "uri": str(source_path),
            "sha256": FIXTURE_SHA,
            "available_range": _range(0, 12).model_dump(mode="json"),
            "streams": [
                {"index": 0, "codec_type": "video", "codec_name": "h264"},
                {
                    "index": 1,
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "sample_rate": 48_000,
                    "channels": 2,
                },
            ],
        }
    )
    project = project.model_copy(update={"media": [media]}, deep=True)
    brief = EditorialBrief(
        id=f"benchmark-brief-{scenario.id}",
        objective=f"Demonstrate {scenario.title} editorial behavior",
        script_text=(
            "Hold the unusual [visual:subject] proof."
            if scenario.id == "intentional_long_hold"
            else "Show the [visual:subject] proof. Hold the reaction payoff."
        ),
        profile=scenario.profile,
        modifiers=scenario.modifiers,
        constraints=EditorialConstraints(
            target_duration=RationalTime(
                value=4 if scenario.id == "intentional_long_hold" else 7,
                timescale=1,
            ),
            must_include_media_ids=["benchmark-media"],
            must_exclude_media_ids=[],
            top_k_selects=3,
            beam_width=8,
        ),
        seed=17,
    )
    index = _index(project.id, long_hold=scenario.id == "intentional_long_hold")
    if scenario.id == "multicam_conversation":
        camera_media = media.model_copy(update={"id": "benchmark-camera-b"}, deep=True)
        project = project.model_copy(update={"media": [media, camera_media]}, deep=True)
        source_shot = index.shots[0]
        camera_evidence = source_shot.evidence[0].model_copy(
            update={
                "id": "evidence:benchmark-camera-b",
                "media_id": "benchmark-camera-b",
            }
        )
        camera_shot = source_shot.model_copy(
            update={
                "id": "shot-camera-b-speaker",
                "media_id": "benchmark-camera-b",
                "semantics": source_shot.semantics.model_copy(
                    update={
                        "search_terms": [
                            *source_shot.semantics.search_terms,
                            "speaker:speaker-1",
                        ]
                    }
                ),
                "evidence": [camera_evidence],
            },
            deep=True,
        )
        synchronization = SourceSynchronization(
            reference_media_id="benchmark-media",
            target_media_id="benchmark-camera-b",
            target_offset=RationalTime.zero(),
            correlation=0.95,
            confidence=Confidence(
                score=0.95,
                basis=EvidenceKind.MEASURED,
                calibration="golden_audio_correlation",
            ),
            evidence=[index.shots[0].evidence[0], camera_evidence],
        )
        index = index.model_copy(
            update={
                "shots": [*index.shots, camera_shot],
                "media_hashes": {
                    **index.media_hashes,
                    "benchmark-camera-b": FIXTURE_SHA,
                },
                "synchronizations": [synchronization],
                "evidence": index.evidence.model_copy(
                    update={"refs": [*index.evidence.refs, camera_evidence]}
                ),
            },
            deep=True,
        )
    expected = (
        {"shot-subject"}
        if scenario.id == "intentional_long_hold"
        else {
            "shot-subject",
            "shot-reaction",
        }
    )
    return project, brief, index, expected


def synthetic_reference_profile(scenario: GoldenScenario) -> ReferenceEditProfile | None:
    if scenario.id != "reference_led":
        return None
    return ReferenceEditProfile(
        id="reference:golden-measured-grammar",
        source_sha256="f" * 64,
        shot_duration_quantiles={
            "p25": RationalTime(value=3, timescale=2),
            "p50": RationalTime(value=5, timescale=2),
            "p75": RationalTime(value=4, timescale=1),
        },
        cut_frequency_hz=0.4,
        shot_scale_distribution={"detail": 0.4, "close": 0.4, "wide": 0.2},
        camera_motion_frequency=0.3,
        caption_density=0.2,
        graphic_density=0.1,
        transition_frequency=0.05,
        transition_type_distribution={"cut": 0.95, "dissolve": 0.05},
        audio_energy_curve=[0.2, 0.5, 0.8, 0.4],
        sfx_event_density=0.1,
        silence_ratio=0.08,
        music_sync_score=0.45,
        rhythm_curve=[0.3, 0.6, 0.8, 0.4],
        repetition_score=0.1,
    )


def _index(project_id: str, *, long_hold: bool) -> MediaUnderstandingIndex:
    shot_ranges = [_range(0, 4), _range(4, 4), _range(8, 4)]
    shot_ids = ["shot-subject", "shot-reaction", "shot-irrelevant"]
    summaries = [
        ("clear unusual subject product proof", ["subject", "proof", "unusual", "detail"]),
        ("visible reaction payoff and listener gesture", ["reaction", "payoff", "gesture"]),
        ("unrelated decorative background", ["background", "decorative"]),
    ]
    refs = [
        _evidence(f"shot-{position}", source_range, shot_id=shot_ids[position])
        for position, source_range in enumerate(shot_ranges)
    ]
    observed = Confidence(
        score=0.95,
        basis=EvidenceKind.OBSERVED,
        calibration="golden_annotation",
    )
    shots = []
    for position, source_range in enumerate(shot_ranges):
        inner = TimeRange.from_start_end(
            source_range.start + RationalTime(value=1, timescale=4),
            source_range.end - RationalTime(value=1, timescale=4),
        )
        reactions = []
        if position == 1 and not long_hold:
            reactions = [
                VisibleReaction(
                    id="reaction-payoff",
                    cue="long_silent_reaction",
                    source_range=TimeRange(
                        start=RationalTime(value=5, timescale=1),
                        duration=RationalTime(value=1, timescale=1),
                    ),
                    salience=0.95,
                    confidence=observed,
                )
            ]
        shots.append(
            Shot(
                id=shot_ids[position],
                media_id="benchmark-media",
                media_sha256=FIXTURE_SHA,
                source_range=source_range,
                inner_usable_range=(source_range if long_hold and position == 0 else inner),
                reactions=reactions,
                camera=CameraDescriptor(
                    shot_scale=("detail", "close", "wide")[position],
                    motion=("locked", "push", "pan")[position],
                    screen_direction="left_to_right",
                    confidence=observed,
                ),
                quality=ShotQuality(
                    sharpness=[0.98, 0.9, 0.5][position],
                    exposure=[0.9, 0.88, 0.5][position],
                    stability=[0.95, 0.8, 0.4][position],
                    composition=[0.95, 0.9, 0.45][position],
                    confidence=observed,
                ),
                semantics=ShotSemantics(
                    summary=summaries[position][0],
                    search_terms=summaries[position][1],
                    reaction_value=0.95 if position == 1 else 0,
                    evidence_value=0.95 if position == 0 else 0.4,
                    cutaway_value=0.8 if position == 1 else 0.1,
                    confidence=observed,
                ),
                motion_energy=[0.05, 0.35, 0.6][position],
                mean_luminance=[0.52, 0.55, 0.25][position],
                color_histogram=_histogram(position),
                evidence=[refs[position]],
            )
        )
    words, phrases, transcript_refs = _transcript(long_hold=long_hold)
    refs.extend(transcript_refs)
    boundaries = [
        ShotBoundary(
            id=f"boundary-{position}",
            media_id="benchmark-media",
            time=source_range.start,
            kind="source_start" if position == 0 else "hard_cut",
            strength=1,
            evidence=[refs[position]],
        )
        for position, source_range in enumerate(shot_ranges)
    ]
    boundaries.append(
        ShotBoundary(
            id="boundary-end",
            media_id="benchmark-media",
            time=RationalTime(value=12, timescale=1),
            kind="source_end",
            strength=1,
            evidence=[refs[2]],
        )
    )
    music = [
        MusicEvent(
            id=f"music-bar-{position}",
            media_id="benchmark-media",
            source_range=TimeRange(
                start=RationalTime(value=position * 2, timescale=1),
                duration=RationalTime(value=1, timescale=100),
            ),
            kind="bar",
            strength=1,
            tempo_bpm=120,
            confidence=Confidence(
                score=0.8,
                basis=EvidenceKind.MEASURED,
                calibration="synthetic_music_grid",
            ),
        )
        for position in range(6)
    ]
    refs.extend(
        EvidenceRef(
            id=f"evidence:{event.id}",
            kind=EvidenceKind.MEASURED,
            media_id="benchmark-media",
            media_sha256=FIXTURE_SHA,
            source_range=event.source_range,
            audio_window_id=f"music-window:{event.id}",
            analysis_version="benchmark-v1",
            confidence=event.confidence,
            summary="synthetic measured music bar",
        )
        for event in music
    )
    return MediaUnderstandingIndex(
        project_id=project_id,
        analysis_version="benchmark-v1",
        media_hashes={"benchmark-media": FIXTURE_SHA},
        shots=shots,
        shot_boundaries=boundaries,
        transcripts=[
            Transcript(
                id="benchmark-transcript",
                media_id="benchmark-media",
                media_sha256=FIXTURE_SHA,
                language="en",
                words=words,
                phrases=phrases,
            )
        ],
        music_events=music,
        evidence=EvidenceBundle(refs=refs),
    )


def _transcript(
    *, long_hold: bool
) -> tuple[list[TranscriptWord], list[TranscriptPhrase], list[EvidenceRef]]:
    texts = (
        ["Hold", "the", "unusual", "subject", "proof"]
        if long_hold
        else [
            "Show",
            "the",
            "subject",
            "proof",
            "Hold",
            "the",
            "reaction",
            "payoff",
        ]
    )
    words = [
        TranscriptWord(
            id=f"benchmark-word-{position}",
            text=text,
            punctuated_text=text,
            source_range=TimeRange(
                start=RationalTime(value=position, timescale=2),
                duration=RationalTime(value=1, timescale=2),
            ),
            speaker_id="speaker-1",
            confidence=Confidence(
                score=0.98,
                basis=EvidenceKind.OBSERVED,
                calibration="golden_word_annotation",
            ),
        )
        for position, text in enumerate(texts)
    ]
    split = len(words) if long_hold else 4
    groups = [words] if long_hold else [words[:split], words[split:]]
    phrases = [
        TranscriptPhrase(
            id=f"benchmark-phrase-{position}",
            text=" ".join(word.text for word in group),
            source_range=TimeRange.from_start_end(
                group[0].source_range.start, group[-1].source_range.end
            ),
            word_ids=[word.id for word in group],
            speaker_id="speaker-1",
            kind="claim" if position == 0 else "punchline",
            emphasis=0.9,
            named_visual_references=["subject"] if position == 0 else ["reaction"],
            confidence=Confidence(
                score=0.95,
                basis=EvidenceKind.OBSERVED,
                calibration="golden_phrase_annotation",
            ),
        )
        for position, group in enumerate(groups)
    ]
    refs = [
        EvidenceRef(
            id=f"evidence:{word.id}",
            kind=EvidenceKind.OBSERVED,
            media_id="benchmark-media",
            media_sha256=FIXTURE_SHA,
            source_range=word.source_range,
            transcript_id="benchmark-transcript",
            transcript_word_id=word.id,
            analysis_version="benchmark-v1",
            confidence=word.confidence,
            summary="hand-annotated word timing",
        )
        for word in words
    ]
    refs.extend(
        EvidenceRef(
            id=f"evidence:{phrase.id}",
            kind=EvidenceKind.OBSERVED,
            media_id="benchmark-media",
            media_sha256=FIXTURE_SHA,
            source_range=phrase.source_range,
            transcript_id="benchmark-transcript",
            transcript_phrase_id=phrase.id,
            analysis_version="benchmark-v1",
            confidence=phrase.confidence,
            summary="hand-annotated phrase timing",
        )
        for phrase in phrases
    )
    return words, phrases, refs


def _evidence(identifier: str, source_range: TimeRange, *, shot_id: str) -> EvidenceRef:
    return EvidenceRef(
        id=f"evidence:{identifier}",
        kind=EvidenceKind.MEASURED,
        media_id="benchmark-media",
        media_sha256=FIXTURE_SHA,
        source_range=source_range,
        shot_id=shot_id,
        analysis_version="benchmark-v1",
        confidence=Confidence(
            score=1,
            basis=EvidenceKind.MEASURED,
            calibration="synthetic_exact_range",
        ),
        summary="synthetic source range",
    )


def _range(start: int, duration: int) -> TimeRange:
    return TimeRange(
        start=RationalTime(value=start, timescale=1),
        duration=RationalTime(value=duration, timescale=1),
    )


def _histogram(channel: int) -> list[float]:
    values = [0.0] * 48
    for offset in range(3):
        values[offset * 16 + channel] = 1.0
    return values
