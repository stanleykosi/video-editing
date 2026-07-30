"""Strict, versioned editorial domain models.

These models contain decisions and evidence only. The canonical executable
timeline remains in :mod:`video_engine`.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator

from video_engine.api import RationalTime, TimeRange

BRAIN_SCHEMA_VERSION: Literal["1.0.0"] = "1.0.0"
JsonValue: TypeAlias = str | int | float | bool | None | list[Any] | dict[str, Any]


class BrainModel(BaseModel):
    """Base for persisted Brain contracts."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class VersionedModel(BrainModel):
    schema_version: Literal["1.0.0"] = BRAIN_SCHEMA_VERSION
    extensions: dict[str, JsonValue] = Field(default_factory=dict)


class EvidenceKind(StrEnum):
    MEASURED = "measured"
    OBSERVED = "observed"
    MODEL_INFERRED = "model_inferred"
    USER_SUPPLIED = "user_supplied"
    DERIVED = "derived"


class ReviewMode(StrEnum):
    STRICT = "strict"
    BALANCED = "balanced"
    AUTONOMOUS = "autonomous"


class Confidence(BrainModel):
    score: float = Field(ge=0, le=1)
    basis: EvidenceKind
    calibration: str = Field(default="unverified", min_length=1)
    sample_size: int | None = Field(default=None, ge=1)


class ProviderUsage(BrainModel):
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    audio_seconds: float | None = Field(default=None, ge=0)
    requests: int = Field(default=1, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)


class ProviderEvidence(BrainModel):
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    provider_fingerprint: str = Field(min_length=1)
    prompt_fingerprint: str = Field(min_length=1)
    request_id: str | None = None
    usage: ProviderUsage = Field(default_factory=ProviderUsage)
    confidence: Confidence


class EvidenceRef(BrainModel):
    id: str = Field(min_length=1)
    kind: EvidenceKind
    media_id: str | None = None
    media_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    source_range: TimeRange | None = None
    transcript_id: str | None = None
    transcript_word_id: str | None = None
    transcript_phrase_id: str | None = None
    shot_id: str | None = None
    frame_id: str | None = None
    audio_window_id: str | None = None
    provider_evidence: ProviderEvidence | None = None
    analysis_version: str = Field(min_length=1)
    confidence: Confidence
    summary: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def grounded(self) -> EvidenceRef:
        locators = (
            self.media_id,
            self.transcript_id,
            self.shot_id,
            self.frame_id,
            self.audio_window_id,
            self.provider_evidence,
        )
        if not any(value is not None for value in locators):
            raise ValueError("evidence must reference source or provider material")
        if self.kind is EvidenceKind.MODEL_INFERRED and self.provider_evidence is None:
            raise ValueError("model-inferred evidence requires provider evidence")
        return self


class EvidenceBundle(VersionedModel):
    refs: list[EvidenceRef] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_refs(self) -> EvidenceBundle:
        _ensure_unique("evidence", [ref.id for ref in self.refs])
        return self


class EditorialProfile(StrEnum):
    NEUTRAL = "neutral"
    DIALOGUE = "dialogue"
    NARRATION = "narration"
    MONTAGE = "montage"


class WorkflowModifier(StrEnum):
    SHORT_FORM = "short_form"
    LONG_FORM = "long_form"
    INTERVIEW = "interview"
    PODCAST_CLIP = "podcast_clip"
    FACELESS_NARRATION = "faceless_narration"
    DOCUMENTARY = "documentary"
    RECAP = "recap"
    ADVERTISEMENT = "advertisement"
    PRODUCT_VIDEO = "product_video"


class EditorialConstraints(VersionedModel):
    target_duration: RationalTime | None = None
    minimum_duration: RationalTime | None = None
    maximum_duration: RationalTime | None = None
    must_include_media_ids: list[str] = Field(default_factory=list)
    must_include_shot_ids: list[str] = Field(default_factory=list)
    must_exclude_media_ids: list[str] = Field(default_factory=list)
    must_exclude_ranges: list[TimeRange] = Field(default_factory=list)
    locked_beat_ids: list[str] = Field(default_factory=list)
    top_k_selects: int = Field(default=5, ge=1, le=100)
    beam_width: int = Field(default=12, ge=1, le=1000)
    review_mode: ReviewMode = ReviewMode.BALANCED

    @model_validator(mode="after")
    def duration_order(self) -> EditorialConstraints:
        if (
            self.minimum_duration
            and self.maximum_duration
            and self.minimum_duration > self.maximum_duration
        ):
            raise ValueError("minimum duration exceeds maximum duration")
        if (
            self.target_duration
            and self.minimum_duration
            and self.target_duration < self.minimum_duration
        ):
            raise ValueError("target duration is below minimum")
        if (
            self.target_duration
            and self.maximum_duration
            and self.target_duration > self.maximum_duration
        ):
            raise ValueError("target duration exceeds maximum")
        overlap = set(self.must_include_media_ids) & set(self.must_exclude_media_ids)
        if overlap:
            raise ValueError(f"media cannot be both required and excluded: {sorted(overlap)}")
        return self


class EditorialBrief(VersionedModel):
    id: str = Field(min_length=1)
    objective: str = Field(min_length=1)
    audience: str = "general"
    platform: str | None = None
    script_text: str | None = None
    narration_media_id: str | None = None
    narration_transcript_id: str | None = None
    storyboard_requirements: list[str] = Field(default_factory=list)
    profile: EditorialProfile = EditorialProfile.NEUTRAL
    modifiers: list[WorkflowModifier] = Field(default_factory=list)
    constraints: EditorialConstraints = Field(default_factory=EditorialConstraints)
    knowledge_mode: Literal["auto", "off", "explicit"] = "auto"
    knowledge_include: list[str] = Field(default_factory=list)
    knowledge_exclude: list[str] = Field(default_factory=list)
    knowledge_max_items: int = Field(default=40, ge=1, le=200)
    style_keywords: list[str] = Field(default_factory=list)
    reference_influence: float = Field(default=0.35, ge=0, le=0.6)
    seed: int = 0
    user_evidence: list[EvidenceRef] = Field(default_factory=list)


class EditorialProject(VersionedModel):
    id: str = Field(min_length=1)
    engine_project_id: str = Field(min_length=1)
    engine_project_revision: int = Field(ge=1)
    brief: EditorialBrief
    analysis_version: str = Field(min_length=1)
    provider_fingerprints: list[str] = Field(default_factory=list)


class TranscriptWord(BrainModel):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    source_range: TimeRange
    speaker_id: str | None = None
    confidence: Confidence
    punctuated_text: str | None = None
    is_filler_candidate: bool = False

    @model_validator(mode="after")
    def positive_duration(self) -> TranscriptWord:
        _require_positive_range("word", self.source_range)
        return self


class TranscriptPhrase(BrainModel):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    source_range: TimeRange
    word_ids: list[str] = Field(min_length=1)
    speaker_id: str | None = None
    kind: Literal[
        "sentence",
        "question",
        "claim",
        "punchline",
        "topic_change",
        "false_start",
        "repeated_attempt",
        "audio_event",
        "unknown",
    ] = "unknown"
    emphasis: float = Field(default=0, ge=0, le=1)
    named_visual_references: list[str] = Field(default_factory=list)
    confidence: Confidence


class SpeakerSegment(BrainModel):
    id: str = Field(min_length=1)
    speaker_id: str = Field(min_length=1)
    source_range: TimeRange
    confidence: Confidence
    overlapping_speaker_ids: list[str] = Field(default_factory=list)


class Transcript(VersionedModel):
    id: str = Field(min_length=1)
    media_id: str = Field(min_length=1)
    media_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    language: str = "und"
    words: list[TranscriptWord] = Field(default_factory=list)
    phrases: list[TranscriptPhrase] = Field(default_factory=list)
    speakers: list[SpeakerSegment] = Field(default_factory=list)
    provider_evidence: ProviderEvidence | None = None

    @model_validator(mode="after")
    def coherent_transcript(self) -> Transcript:
        _ensure_unique("word", [word.id for word in self.words])
        _ensure_unique("phrase", [phrase.id for phrase in self.phrases])
        word_ids = {word.id for word in self.words}
        previous: RationalTime | None = None
        for word in self.words:
            if previous is not None and word.source_range.start < previous:
                raise ValueError("transcript words must be ordered and non-overlapping")
            previous = word.source_range.end
        for phrase in self.phrases:
            if missing := set(phrase.word_ids) - word_ids:
                raise ValueError(f"phrase references missing words: {sorted(missing)}")
        return self


class PauseClass(StrEnum):
    DEAD_SPACE = "dead_space"
    TECHNICAL_DELAY = "technical_delay"
    BREATH = "breath"
    THINKING_PAUSE = "thinking_pause"
    REACTION_HOLD = "reaction_hold"
    DRAMATIC_PAUSE = "dramatic_pause"
    COMEDIC_PAUSE = "comedic_pause"
    TRANSITION_SPACE = "transition_space"
    UNKNOWN = "unknown"


class PauseEvent(BrainModel):
    id: str = Field(min_length=1)
    media_id: str = Field(min_length=1)
    source_range: TimeRange
    classification: PauseClass = PauseClass.UNKNOWN
    protected: bool = False
    evidence: list[EvidenceRef] = Field(default_factory=list)
    confidence: Confidence


class AudioEvent(BrainModel):
    id: str = Field(min_length=1)
    media_id: str = Field(min_length=1)
    source_range: TimeRange
    kind: Literal["speech", "breath", "laugh", "applause", "transient", "ambience", "other"]
    energy: float = Field(ge=0)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    confidence: Confidence


class MusicEvent(BrainModel):
    id: str = Field(min_length=1)
    media_id: str = Field(min_length=1)
    source_range: TimeRange
    kind: Literal["beat", "bar", "phrase", "downbeat", "section"]
    strength: float = Field(ge=0, le=1)
    tempo_bpm: float | None = Field(default=None, gt=0)
    confidence: Confidence


class ShotBoundary(BrainModel):
    id: str = Field(min_length=1)
    media_id: str = Field(min_length=1)
    time: RationalTime
    kind: Literal["hard_cut", "fade", "dissolve", "subshot", "source_start", "source_end"]
    strength: float = Field(ge=0, le=1)
    evidence: list[EvidenceRef] = Field(default_factory=list)


class ShotFrame(BrainModel):
    id: str = Field(min_length=1)
    media_id: str = Field(min_length=1)
    time: RationalTime
    artifact_path: str | None = None
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    role: Literal["opening", "middle", "closing", "action_peak", "representative"]
    evidence: list[EvidenceRef] = Field(default_factory=list)


class VisibleSubject(BrainModel):
    label: str = Field(min_length=1)
    role: Literal["main", "secondary", "background"] = "secondary"
    position_x: float | None = Field(default=None, ge=0, le=1)
    position_y: float | None = Field(default=None, ge=0, le=1)
    salience: float = Field(default=0, ge=0, le=1)
    confidence: Confidence


class VisibleAction(BrainModel):
    label: str = Field(min_length=1)
    source_range: TimeRange
    completes: bool | None = None
    direction: Literal["left_to_right", "right_to_left", "toward", "away", "none", "unknown"] = (
        "unknown"
    )
    confidence: Confidence


class VisibleReaction(BrainModel):
    id: str = Field(min_length=1)
    cue: Literal[
        "smiles",
        "laughs",
        "looks_away",
        "surprised_visible_reaction",
        "long_silent_reaction",
        "head_turn",
        "gesture",
        "other",
    ]
    source_range: TimeRange
    salience: float = Field(ge=0, le=1)
    confidence: Confidence


class CameraDescriptor(BrainModel):
    shot_scale: Literal["extreme_wide", "wide", "medium", "close", "detail", "unknown"]
    motion: Literal["locked", "pan", "tilt", "push", "pull", "dolly", "handheld", "zoom", "unknown"]
    angle: Literal["low", "eye", "high", "overhead", "dutch", "unknown"] = "unknown"
    screen_direction: Literal["left_to_right", "right_to_left", "neutral", "unknown"] = "unknown"
    confidence: Confidence


class ShotQuality(BrainModel):
    sharpness: float = Field(ge=0, le=1)
    exposure: float = Field(ge=0, le=1)
    stability: float = Field(ge=0, le=1)
    composition: float = Field(ge=0, le=1)
    occlusion_penalty: float = Field(default=0, ge=0, le=1)
    watermark_risk: float = Field(default=0, ge=0, le=1)
    confidence: Confidence


class ShotSemantics(BrainModel):
    summary: str = Field(min_length=1)
    search_terms: list[str] = Field(default_factory=list)
    establishing_value: float = Field(default=0, ge=0, le=1)
    reaction_value: float = Field(default=0, ge=0, le=1)
    evidence_value: float = Field(default=0, ge=0, le=1)
    cutaway_value: float = Field(default=0, ge=0, le=1)
    atmosphere_value: float = Field(default=0, ge=0, le=1)
    text_present: bool = False
    confidence: Confidence


class Shot(BrainModel):
    id: str = Field(min_length=1)
    parent_shot_id: str | None = None
    media_id: str = Field(min_length=1)
    media_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_range: TimeRange
    inner_usable_range: TimeRange
    frames: list[ShotFrame] = Field(default_factory=list)
    subjects: list[VisibleSubject] = Field(default_factory=list)
    actions: list[VisibleAction] = Field(default_factory=list)
    reactions: list[VisibleReaction] = Field(default_factory=list)
    camera: CameraDescriptor
    quality: ShotQuality
    semantics: ShotSemantics
    motion_energy: float = Field(default=0, ge=0)
    mean_luminance: float = Field(default=0.5, ge=0, le=1)
    color_histogram: list[float] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)

    @model_validator(mode="after")
    def usable_is_inside(self) -> Shot:
        _require_positive_range("shot", self.source_range)
        _require_positive_range("usable shot", self.inner_usable_range)
        if (
            self.inner_usable_range.start < self.source_range.start
            or self.inner_usable_range.end > self.source_range.end
        ):
            raise ValueError("inner usable range must be contained by shot")
        if self.color_histogram and (
            len(self.color_histogram) != 48
            or any(value < 0 or value > 1 for value in self.color_histogram)
        ):
            raise ValueError("shot color histogram must contain 48 normalized channel bins")
        return self


class SourceSynchronization(BrainModel):
    reference_media_id: str = Field(min_length=1)
    target_media_id: str = Field(min_length=1)
    target_offset: RationalTime
    correlation: float = Field(ge=-1, le=1)
    confidence: Confidence
    evidence: list[EvidenceRef] = Field(min_length=2)


class MediaUnderstandingIndex(VersionedModel):
    project_id: str = Field(min_length=1)
    analysis_version: str = Field(min_length=1)
    media_hashes: dict[str, str]
    shots: list[Shot] = Field(default_factory=list)
    shot_boundaries: list[ShotBoundary] = Field(default_factory=list)
    transcripts: list[Transcript] = Field(default_factory=list)
    pauses: list[PauseEvent] = Field(default_factory=list)
    audio_events: list[AudioEvent] = Field(default_factory=list)
    music_events: list[MusicEvent] = Field(default_factory=list)
    synchronizations: list[SourceSynchronization] = Field(default_factory=list)
    evidence: EvidenceBundle = Field(default_factory=EvidenceBundle)
    provider_evidence: list[ProviderEvidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def coherent_index(self) -> MediaUnderstandingIndex:
        _ensure_unique("shot", [shot.id for shot in self.shots])
        _ensure_unique("transcript", [item.id for item in self.transcripts])
        for media_id, digest in self.media_hashes.items():
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise ValueError(f"invalid SHA-256 for media {media_id!r}")
        return self


class NarrativeFunction(StrEnum):
    HOOK = "hook"
    SETUP = "setup"
    CONTEXT = "context"
    QUESTION = "question"
    PROBLEM = "problem"
    EVIDENCE = "evidence"
    EXAMPLE = "example"
    REACTION = "reaction"
    ESCALATION = "escalation"
    CONTRAST = "contrast"
    TURN = "turn"
    REVEAL = "reveal"
    RESOLUTION = "resolution"
    PAYOFF = "payoff"
    CALL_TO_ACTION = "call_to_action"
    TRANSITION = "transition"
    BREATHING_SPACE = "breathing_space"


class RevealTiming(StrEnum):
    BEFORE_PHRASE = "before_phrase"
    ON_PHRASE = "on_phrase"
    AFTER_PHRASE = "after_phrase"
    FLEXIBLE = "flexible"


class VisualRequirement(BrainModel):
    id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    entity: str | None = None
    required: bool = True
    reveal_timing: RevealTiming = RevealTiming.ON_PHRASE
    narration_range: TimeRange | None = None
    early_handoff: RationalTime = Field(default_factory=RationalTime.zero)
    minimum_hold: RationalTime = Field(default_factory=RationalTime.zero)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    confidence: Confidence


class AudioRequirement(BrainModel):
    id: str = Field(min_length=1)
    kind: Literal["dialogue", "voice_over", "music", "ambience", "silence", "event"]
    description: str = Field(min_length=1)
    required: bool = True
    target_range: TimeRange | None = None
    evidence: list[EvidenceRef] = Field(default_factory=list)


class StoryBeat(BrainModel):
    id: str = Field(min_length=1)
    function: NarrativeFunction
    purpose: str = Field(min_length=1)
    importance: float = Field(ge=0, le=1)
    mandatory: bool = True
    source_text: str | None = None
    source_phrase_kind: (
        Literal[
            "sentence",
            "question",
            "claim",
            "punchline",
            "topic_change",
            "false_start",
            "repeated_attempt",
            "audio_event",
            "unknown",
        ]
        | None
    ) = None
    evidence: list[EvidenceRef] = Field(default_factory=list)
    required_information: list[str] = Field(default_factory=list)
    optional_information: list[str] = Field(default_factory=list)
    visual_requirements: list[VisualRequirement] = Field(default_factory=list)
    audio_requirements: list[AudioRequirement] = Field(default_factory=list)
    target_duration: RationalTime
    must_follow: list[str] = Field(default_factory=list)
    confidence: Confidence

    @model_validator(mode="after")
    def positive_target(self) -> StoryBeat:
        if self.target_duration.value <= 0:
            raise ValueError("beat target duration must be positive")
        return self


class StoryMap(VersionedModel):
    brief_id: str = Field(min_length=1)
    beats: list[StoryBeat] = Field(min_length=1)

    @model_validator(mode="after")
    def valid_order(self) -> StoryMap:
        ids = [beat.id for beat in self.beats]
        _ensure_unique("beat", ids)
        known: set[str] = set()
        for beat in self.beats:
            missing = set(beat.must_follow) - known
            if missing:
                raise ValueError(f"beat {beat.id!r} has unsatisfied order dependencies")
            known.add(beat.id)
        return self


class SelectScore(BrainModel):
    semantic_relevance: float = Field(ge=0, le=1)
    visual_clarity: float = Field(ge=0, le=1)
    action_completeness: float = Field(ge=0, le=1)
    shot_quality: float = Field(ge=0, le=1)
    reaction_value: float = Field(ge=0, le=1)
    evidence_value: float = Field(ge=0, le=1)
    novelty: float = Field(ge=0, le=1)
    repetition_penalty: float = Field(ge=0, le=1)
    overall: float = Field(ge=0, le=1)


class SelectCandidate(BrainModel):
    id: str = Field(min_length=1)
    beat_id: str = Field(min_length=1)
    shot_id: str = Field(min_length=1)
    media_id: str = Field(min_length=1)
    media_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_range: TimeRange
    inner_usable_range: TimeRange
    handle_before: RationalTime
    handle_after: RationalTime
    score: SelectScore
    evidence: list[EvidenceRef] = Field(min_length=1)
    reasons: list[str] = Field(min_length=1)
    confidence: Confidence
    alternative_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def valid_select(self) -> SelectCandidate:
        if self.handle_before.value < 0 or self.handle_after.value < 0:
            raise ValueError("select handles cannot be negative")
        if (
            self.inner_usable_range.start < self.source_range.start
            or self.inner_usable_range.end > self.source_range.end
        ):
            raise ValueError("select usable range must be contained by source range")
        return self


class CutPointCandidate(BrainModel):
    id: str = Field(min_length=1)
    media_id: str = Field(min_length=1)
    time: RationalTime
    kind: Literal[
        "word",
        "sentence",
        "phrase",
        "pause",
        "breath",
        "shot",
        "motion_start",
        "motion_end",
        "gesture",
        "head_turn",
        "blink",
        "action_peak",
        "object_entry",
        "object_exit",
        "camera_motion",
        "audio_transient",
        "music_beat",
        "music_bar",
        "visual_reveal",
        "reaction_start",
        "reaction_end",
        "source_handle",
    ]
    edge: Literal["in", "out", "either"] = "either"
    strength: float = Field(ge=0, le=1)
    evidence: list[EvidenceRef] = Field(min_length=1)


class ContinuityScore(BrainModel):
    subject_position: float = Field(ge=0, le=1)
    screen_direction: float = Field(ge=0, le=1)
    movement_direction: float = Field(ge=0, le=1)
    shot_scale: float = Field(ge=0, le=1)
    camera_angle: float = Field(ge=0, le=1)
    camera_motion: float = Field(ge=0, le=1)
    luminance: float = Field(ge=0, le=1)
    color: float = Field(ge=0, le=1)
    background: float = Field(ge=0, le=1)
    room_tone: float = Field(ge=0, le=1)
    dialogue: float = Field(ge=0, le=1)
    semantic: float = Field(ge=0, le=1)
    temporal_action: float = Field(ge=0, le=1)
    motivated_discontinuity: bool = False
    overall: float = Field(ge=0, le=1)


class RhythmScore(BrainModel):
    duration_fit: float = Field(ge=0, le=1)
    energy_fit: float = Field(ge=0, le=1)
    density_fit: float = Field(ge=0, le=1)
    novelty: float = Field(ge=0, le=1)
    breathing_room: float = Field(ge=0, le=1)
    repetition_penalty: float = Field(ge=0, le=1)
    overall: float = Field(ge=0, le=1)


class CutScore(BrainModel):
    semantic_completeness: float = Field(ge=0, le=1)
    story_progression: float = Field(ge=0, le=1)
    visual_relevance: float = Field(ge=0, le=1)
    visual_continuity: float = Field(ge=0, le=1)
    action_continuity: float = Field(ge=0, le=1)
    screen_direction: float = Field(ge=0, le=1)
    shot_scale_compatibility: float = Field(ge=0, le=1)
    composition_compatibility: float = Field(ge=0, le=1)
    motion_compatibility: float = Field(ge=0, le=1)
    audio_continuity: float = Field(ge=0, le=1)
    speech_integrity: float = Field(ge=0, le=1)
    reaction_preservation: float = Field(ge=0, le=1)
    emotional_continuity: float = Field(ge=0, le=1)
    rhythm: float = Field(ge=0, le=1)
    information_density: float = Field(ge=0, le=1)
    visual_novelty: float = Field(ge=0, le=1)
    shot_quality: float = Field(ge=0, le=1)
    source_handle_safety: float = Field(ge=0, le=1)
    style_profile_fit: float = Field(ge=0, le=1)
    technical_feasibility: float = Field(ge=0, le=1)
    deterministic_score: float = Field(ge=0, le=1)
    semantic_model_score: float | None = Field(default=None, ge=0, le=1)
    overall: float = Field(ge=0, le=1)


class CutCandidate(BrainModel):
    id: str = Field(min_length=1)
    from_select_id: str | None = None
    to_select_id: str = Field(min_length=1)
    out_point_id: str | None = None
    in_point_id: str = Field(min_length=1)
    score: CutScore
    continuity: ContinuityScore
    hard_rejections: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    confidence: Confidence

    @property
    def valid(self) -> bool:
        return not self.hard_rejections


class AudioPictureRelationship(StrEnum):
    HARD_AV = "hard_av"
    J_CUT = "j_cut"
    L_CUT = "l_cut"
    AUDIO_BRIDGE = "audio_bridge"
    BROLL_CONTINUING_DIALOGUE = "broll_continuing_dialogue"
    REACTION_CONTINUING_DIALOGUE = "reaction_continuing_dialogue"
    AMBIENCE_CONTINUATION = "ambience_continuation"
    MUSIC_LED = "music_led"
    INTENTIONAL_SILENCE = "intentional_silence"


class PlannedSegment(BrainModel):
    id: str = Field(min_length=1)
    beat_id: str = Field(min_length=1)
    select_id: str = Field(min_length=1)
    media_id: str = Field(min_length=1)
    media_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_range: TimeRange
    timeline_range: TimeRange
    role: Literal[
        "primary",
        "broll",
        "cutaway",
        "reaction",
        "wide_reset",
        "proof",
        "montage",
    ] = "primary"
    audio_relationship: AudioPictureRelationship = AudioPictureRelationship.HARD_AV
    audio_source_range: TimeRange | None = None
    transition: Literal["cut", "dissolve", "dip_to_color", "none"] = "cut"
    protected: bool = False
    evidence: list[EvidenceRef] = Field(default_factory=list)
    confidence: Confidence


class AssemblyScore(BrainModel):
    story_coverage: float = Field(ge=0, le=1)
    duration_fit: float = Field(ge=0, le=1)
    selects_quality: float = Field(ge=0, le=1)
    continuity: float = Field(ge=0, le=1)
    diversity: float = Field(ge=0, le=1)
    pacing: float = Field(ge=0, le=1)
    audio_picture: float = Field(ge=0, le=1)
    repetition_penalty: float = Field(ge=0, le=1)
    constraint_penalty: float = Field(ge=0, le=1)
    overall: float


class CandidateAssembly(BrainModel):
    id: str = Field(min_length=1)
    segments: list[PlannedSegment] = Field(min_length=1)
    score: AssemblyScore
    rhythm: RhythmScore
    cut_ids: list[str] = Field(default_factory=list)
    covered_beat_ids: list[str] = Field(default_factory=list)
    review_flags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def ordered_nonoverlap(self) -> CandidateAssembly:
        previous: RationalTime | None = None
        for segment in self.segments:
            _require_positive_range("planned segment", segment.timeline_range)
            if previous is not None and segment.timeline_range.start < previous:
                raise ValueError("assembly segments must be ordered and non-overlapping")
            previous = segment.timeline_range.end
        return self


class ReviewFlag(BrainModel):
    id: str = Field(min_length=1)
    code: Literal[
        "weak_semantic_match",
        "near_equal_candidates",
        "uncertain_speaker_reaction",
        "insufficient_broll",
        "ambiguous_sync",
        "poor_source_quality",
        "uncertain_continuity",
        "missing_visual_proof",
        "insufficient_handles",
        "duration_meaning_conflict",
    ]
    message: str = Field(min_length=1)
    decision_id: str | None = None
    confidence: Confidence
    blocking: bool = False


class EditorialDecision(BrainModel):
    id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    selected_id: str | None = None
    alternative_ids: list[str] = Field(default_factory=list)
    alternative_scores: dict[str, float] = Field(default_factory=dict)
    reasons: list[str] = Field(min_length=1)
    constraints: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    confidence: Confidence
    policy_ids: list[str] = Field(default_factory=list)
    provider_evidence: list[ProviderEvidence] = Field(default_factory=list)
    engine_operation_indexes: list[int] = Field(default_factory=list)


class DecisionTrace(VersionedModel):
    run_id: str = Field(min_length=1)
    decisions: list[EditorialDecision] = Field(default_factory=list)
    stage_metrics: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def unique_decisions(self) -> DecisionTrace:
        _ensure_unique("decision", [decision.id for decision in self.decisions])
        return self


class EditorialPlan(VersionedModel):
    id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    project_revision: int = Field(ge=1)
    brief_id: str = Field(min_length=1)
    narration_media_id: str | None = None
    narration_source_range: TimeRange | None = None
    story: StoryMap
    assembly: CandidateAssembly
    cut_points: list[CutPointCandidate] = Field(default_factory=list)
    cut_candidates: list[CutCandidate] = Field(default_factory=list)
    alternatives: list[CandidateAssembly] = Field(default_factory=list)
    decisions: list[EditorialDecision] = Field(default_factory=list)
    review_flags: list[ReviewFlag] = Field(default_factory=list)
    trace: DecisionTrace
    policy_id: str = Field(min_length=1)
    reference_profile_id: str | None = None
    seed: int = 0
    deterministic_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class EditorialVariant(BrainModel):
    id: str = Field(min_length=1)
    rank: int = Field(ge=1)
    plan: EditorialPlan
    differentiators: list[str] = Field(default_factory=list)


class ReferenceEditProfile(VersionedModel):
    id: str = Field(min_length=1)
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    shot_duration_quantiles: dict[str, RationalTime]
    cut_frequency_hz: float = Field(ge=0)
    shot_scale_distribution: dict[str, float] = Field(default_factory=dict)
    camera_motion_frequency: float = Field(default=0, ge=0)
    caption_density: float = Field(default=0, ge=0)
    caption_placement_distribution: dict[str, float] = Field(default_factory=dict)
    graphic_density: float = Field(default=0, ge=0)
    transition_frequency: float = Field(default=0, ge=0)
    transition_type_distribution: dict[str, float] = Field(default_factory=dict)
    audio_energy_curve: list[float] = Field(default_factory=list)
    sfx_event_density: float = Field(default=0, ge=0)
    silence_ratio: float = Field(default=0, ge=0, le=1)
    silence_placements: list[RationalTime] = Field(default_factory=list)
    music_sync_score: float = Field(default=0, ge=0, le=1)
    rhythm_curve: list[float] = Field(default_factory=list)
    repetition_score: float = Field(default=0, ge=0, le=1)
    evidence: list[EvidenceRef] = Field(default_factory=list)


def _require_positive_range(label: str, value: TimeRange) -> None:
    if value.duration.value <= 0:
        raise ValueError(f"{label} range must have positive duration")


def _ensure_unique(label: str, values: list[str]) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} ids must be unique")
