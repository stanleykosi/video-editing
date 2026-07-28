"""Compile canonical projects into backend-neutral render DAGs."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict

from video_engine.captions.layout import validate_caption_layout
from video_engine.config import EngineConfig
from video_engine.core.schema import (
    AdjustmentClip,
    AdjustmentTrack,
    AudioClip,
    AudioTrack,
    CaptionCue,
    CaptionTrack,
    Clip,
    ColorSpace,
    DeliveryProfile,
    Effect,
    EffectKind,
    Gap,
    GeneratorClip,
    GraphicsTrack,
    Interpolation,
    JsonValue,
    MediaReference,
    NestedSequenceClip,
    Project,
    Retime,
    Sequence,
    StillImageClip,
    Transition,
    TransitionKind,
    VideoTrack,
)
from video_engine.core.time import (
    AudioSampleTime,
    FrameRate,
    RationalTime,
    RoundingMode,
    TimeRange,
)
from video_engine.core.validation import validate_project
from video_engine.errors import EngineError, ErrorCode
from video_engine.graphics.models import GraphicAsset
from video_engine.graphics.registry import GraphicsRegistry, builtin_graphics_registry
from video_engine.media.identity import SourceIdentityStore
from video_engine.render.cache import sha256_file
from video_engine.render.effects import (
    AnchorParameters,
    BlendModeParameters,
    BlurParameters,
    ChromaKeyParameters,
    ColorInterpretationParameters,
    ColorNormalizationParameters,
    CornerRadiusParameters,
    CropParameters,
    DistortionParameters,
    FreezeParameters,
    GlowParameters,
    GradeParameters,
    LumaKeyParameters,
    LutParameters,
    MaskParameters,
    OpacityParameters,
    PerspectiveParameters,
    PositionParameters,
    ReframeParameters,
    RotationParameters,
    ScaleParameters,
    ShadowParameters,
    TrackMatteParameters,
    parse_audio_processor,
    parse_sidechain_parameters,
    parse_visual_parameters,
)
from video_engine.render.graph import RenderGraph, optimize_graph
from video_engine.render.models import RenderMode, RenderRequest
from video_engine.render.nodes import (
    ArtifactType,
    AudioMixInput,
    AudioMixNode,
    AudioProcessNode,
    AudioProcessor,
    AudioSidechainNode,
    BlurNode,
    CaptionNode,
    CaptionRenderCue,
    CaptionRenderWord,
    ColorConversionNode,
    CompositeLayer,
    CompositeNode,
    ConcatNode,
    ConformNode,
    CropNode,
    DecodeNode,
    DistortionNode,
    EncodeNode,
    FreezeNode,
    GlowNode,
    GradeNode,
    LoudnessNode,
    MaskNode,
    MotionGraphicNode,
    MuxNode,
    OutputTransformNode,
    PerspectiveNode,
    RenderNode,
    ReverseNode,
    ScaleNode,
    ShadowNode,
    SpeedNode,
    SpeedRampNode,
    TransformNode,
    TransitionNode,
    TrimNode,
    VisualAutomationPoint,
)
from video_engine.render.sections import (
    RenderSection,
    SectionPlan,
    SectionPlanner,
    chapter_range,
)

BlendModeName = Literal[
    "normal", "multiply", "screen", "overlay", "darken", "lighten", "difference"
]


class CompiledSectionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    section: RenderSection
    video_node_id: str
    audio_node_id: str


class CompiledRender(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    graph: RenderGraph
    sequence_id: str
    delivery_profile: DeliveryProfile
    timeline_range: TimeRange
    section_plan: SectionPlan
    section_outputs: tuple[CompiledSectionOutput, ...]


def _safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "node"


def _extension_float(value: object, *, name: str, default: float) -> float:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise EngineError(
            ErrorCode.INVALID_TIMELINE,
            "timeline extension must be numeric",
            context={"extension": name, "value": value},
        )
    try:
        return float(value)
    except ValueError as exc:
        raise EngineError(
            ErrorCode.INVALID_TIMELINE,
            "timeline extension must be numeric",
            context={"extension": name, "value": value},
        ) from exc


class RenderCompiler:
    def __init__(
        self,
        project: Project,
        project_root: Path,
        config: EngineConfig,
        graphics_registry: GraphicsRegistry | None = None,
    ) -> None:
        self.project = project
        self.project_root = project_root.resolve()
        self.config = config
        self.nodes: list[RenderNode] = []
        self._ids: set[str] = set()
        self._media = {media.id: media for media in project.media}
        self._resolved_media_paths: dict[str, Path] = {}
        self._source_hashes: dict[tuple[Path, int, int, int, int, int], str] = {}
        self._source_identity_store = SourceIdentityStore(
            self.project_root / ".video-engine" / "source-identities.json"
        )
        self._decode_nodes: dict[
            tuple[Path, ArtifactType, int | None, int | None, bool, str | None], str
        ] = {}
        self._nested_caption_languages: tuple[str, ...] | None = None
        self._working_color_space = project.settings.working_color_space
        self.graphics_registry = graphics_registry or builtin_graphics_registry()

    def compile(self, request: RenderRequest) -> CompiledRender:
        report = validate_project(self.project)
        if not report.valid:
            raise EngineError(
                ErrorCode.INVALID_PROJECT,
                "project failed invariant validation before render compilation",
                context=report.model_dump(mode="json"),
            )
        sequence = self._sequence(request.sequence_id)
        self._nested_caption_languages = request.caption_languages
        if request.caption_track_ids is not None:
            selected_tracks = [
                track
                for track in sequence.timeline.tracks
                if isinstance(track, CaptionTrack) and track.id in request.caption_track_ids
            ]
            self._nested_caption_languages = tuple(
                sorted({track.language for track in selected_tracks})
            )
        profile = self._profile(request)
        timeline_range = (
            chapter_range(sequence, request.chapter_id)
            if request.chapter_id is not None
            else request.timeline_range
            or TimeRange(start=RationalTime.zero(), duration=sequence.timeline.duration)
        )
        if timeline_range.duration.value <= 0:
            raise EngineError(ErrorCode.INVALID_TIMELINE, "render range must be positive")
        if timeline_range.start.value < 0 or timeline_range.end > sequence.timeline.duration:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "render range lies outside the sequence",
                context={
                    "range": timeline_range.model_dump(mode="json"),
                    "sequence_duration": sequence.timeline.duration.model_dump(mode="json"),
                },
            )
        self._validate_frame_grid(sequence, timeline_range, profile)
        self._validate_audio_sample_grid(sequence, profile)
        maximum_section_duration = (
            request.section_duration
            or RationalTime(value=self.config.render_section_duration_seconds, timescale=1)
            if request.sectioning
            else None
        )
        section_plan = SectionPlanner(
            frame_rate=profile.frame_rate,
            audio_sample_rate=profile.audio_sample_rate,
            max_duration=maximum_section_duration,
        ).plan(sequence, timeline_range)
        section_outputs: list[CompiledSectionOutput] = []
        video_sections: list[str] = []
        audio_sections: list[str] = []
        for section in section_plan.sections:
            visual_root, embedded_audio = self._compile_visual(
                sequence, section.timeline_range, profile
            )
            caption_root = self._compile_captions(
                sequence,
                section.timeline_range,
                profile,
                visual_root,
                selected_track_ids=request.caption_track_ids,
                selected_languages=request.caption_languages,
                strict_selection=True,
            )
            audio_root = self._compile_audio(
                sequence,
                section.timeline_range,
                profile,
                embedded_audio,
                request.mode,
                apply_loudness=False,
            )
            video_sections.append(caption_root)
            audio_sections.append(audio_root)
            section_outputs.append(
                CompiledSectionOutput(
                    section=section,
                    video_node_id=caption_root,
                    audio_node_id=audio_root,
                )
            )
        if len(section_outputs) == 1:
            caption_root = video_sections[0]
            audio_root = audio_sections[0]
        else:
            durations = tuple(section.timeline_range.duration for section in section_plan.sections)
            caption_root = self._bounded_concat(
                f"{sequence.id}-video-sections",
                video_sections,
                durations,
                ArtifactType.VIDEO,
                profile,
            )
            audio_root = self._bounded_concat(
                f"{sequence.id}-audio-sections",
                audio_sections,
                durations,
                ArtifactType.AUDIO,
                profile,
            )
        if profile.loudness is not None:
            loudness = LoudnessNode(
                id=self._id("audio-loudness"),
                inputs=(audio_root,),
                artifact_type=ArtifactType.AUDIO,
                profile=profile.loudness,
                mode="two_pass" if request.mode is RenderMode.FINAL else "single_pass",
                sample_rate=profile.audio_sample_rate,
            )
            self._add(loudness)
            audio_root = loudness.id
        output_transform = OutputTransformNode(
            id=self._id("output-transform"),
            inputs=(caption_root,),
            artifact_type=ArtifactType.VIDEO,
            width=profile.width,
            height=profile.height,
            frame_rate=profile.frame_rate,
            fit=profile.fit,
            input_color_space=(
                sequence.settings_override.working_color_space
                or self.project.settings.working_color_space
            ),
            color_space=profile.output_color_space,
            pixel_format=profile.pixel_format,
        )
        self._add(output_transform)
        video_encode = EncodeNode(
            id=self._id("encode-video"),
            inputs=(output_transform.id,),
            artifact_type=ArtifactType.ENCODED_VIDEO,
            codec=profile.video_codec,
            bitrate=profile.video_bitrate,
            crf=profile.crf,
            preset=profile.preset,
            pixel_format=profile.pixel_format,
        )
        self._add(video_encode)
        audio_encode = EncodeNode(
            id=self._id("encode-audio"),
            inputs=(audio_root,),
            artifact_type=ArtifactType.ENCODED_AUDIO,
            codec=profile.audio_codec,
            bitrate=profile.audio_bitrate,
            sample_rate=profile.audio_sample_rate,
            channels=profile.audio_channels,
            channel_layout=profile.audio_channel_layout,
        )
        self._add(audio_encode)
        mux = MuxNode(
            id=self._id("mux"),
            inputs=(video_encode.id, audio_encode.id),
            artifact_type=ArtifactType.CONTAINER,
            container="mp4",
            fast_start=profile.fast_start,
            shortest=False,
        )
        self._add(mux)
        graph = RenderGraph(nodes=tuple(self.nodes), outputs={"main": mux.id})
        return CompiledRender(
            graph=optimize_graph(graph).graph,
            sequence_id=sequence.id,
            delivery_profile=profile,
            timeline_range=timeline_range,
            section_plan=section_plan,
            section_outputs=tuple(section_outputs),
        )

    def _bounded_concat(
        self,
        prefix: str,
        inputs: list[str],
        durations: tuple[RationalTime, ...],
        artifact_type: Literal[ArtifactType.VIDEO, ArtifactType.AUDIO],
        profile: DeliveryProfile,
    ) -> str:
        maximum = self.config.max_render_inputs
        current = list(zip(inputs, durations, strict=True))
        stage = 0
        while len(current) > 1:
            grouped: list[tuple[str, RationalTime]] = []
            for group_index in range(0, len(current), maximum):
                group = current[group_index : group_index + maximum]
                if len(group) == 1:
                    grouped.append(group[0])
                    continue
                group_duration = RationalTime.zero()
                for _, duration in group:
                    group_duration += duration
                concat = ConcatNode(
                    id=self._id(f"{prefix}-{stage}-{group_index // maximum}"),
                    inputs=tuple(node_id for node_id, _ in group),
                    artifact_type=artifact_type,
                    segment_durations=tuple(duration for _, duration in group),
                    frame_rate=profile.frame_rate if artifact_type is ArtifactType.VIDEO else None,
                    sample_rate=(
                        profile.audio_sample_rate if artifact_type is ArtifactType.AUDIO else None
                    ),
                )
                self._add(concat)
                grouped.append((concat.id, group_duration))
            current = grouped
            stage += 1
        return current[0][0]

    def _sequence(self, sequence_id: str | None, revision: int | None = None) -> Sequence:
        target = sequence_id or self.project.active_sequence_id
        try:
            return self.project.resolve_sequence(target, revision)
        except StopIteration as exc:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "render sequence revision was not found",
                context={"sequence_id": target, "revision": revision},
            ) from exc

    def _profile(self, request: RenderRequest) -> DeliveryProfile:
        profile_id = request.delivery_profile_id
        if profile_id is None:
            profile_id = "final" if request.mode is RenderMode.FINAL else "preview"
        profile = next(
            (item for item in self.project.delivery_profiles if item.id == profile_id),
            None,
        )
        if profile is None:
            if not self.project.delivery_profiles:
                raise EngineError(ErrorCode.INVALID_PROJECT, "project has no delivery profiles")
            if request.delivery_profile_id is not None:
                raise EngineError(
                    ErrorCode.INVALID_PROJECT,
                    "requested delivery profile was not found",
                    context={"delivery_profile_id": request.delivery_profile_id},
                )
            profile = self.project.delivery_profiles[0]
        if request.mode is not RenderMode.DRAFT:
            return profile
        width, height = profile.width, profile.height
        longest = max(width, height)
        if longest > 1280:
            scale = 1280 / longest
            width = max(2, round(width * scale) // 2 * 2)
            height = max(2, round(height * scale) // 2 * 2)
        return profile.model_copy(
            update={
                "id": f"{profile.id}-draft",
                "name": f"{profile.name} Draft",
                "width": width,
                "height": height,
                "crf": 28,
                "preset": "ultrafast",
            }
        )

    @staticmethod
    def _sequence_profile(sequence: Sequence, parent_profile: DeliveryProfile) -> DeliveryProfile:
        override = sequence.settings_override
        return parent_profile.model_copy(
            update={
                "id": f"{parent_profile.id}-sequence-{_safe_id(sequence.id)}",
                "name": f"{parent_profile.name} / {sequence.name}",
                "width": override.width or parent_profile.width,
                "height": override.height or parent_profile.height,
                "frame_rate": override.frame_rate or parent_profile.frame_rate,
                "audio_sample_rate": override.audio_sample_rate or parent_profile.audio_sample_rate,
            }
        )

    @staticmethod
    def _validate_frame_grid(
        sequence: Sequence, timeline_range: TimeRange, profile: DeliveryProfile
    ) -> None:
        for label, value in {
            "render start": timeline_range.start,
            "render end": timeline_range.end,
        }.items():
            try:
                profile.frame_rate.time_to_frames(value, RoundingMode.EXACT)
            except ValueError as exc:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    f"{label} is not aligned to the output frame grid",
                    context={"time": value.model_dump(mode="json")},
                ) from exc
        for track in sequence.timeline.tracks:
            if not isinstance(track, (VideoTrack, GraphicsTrack)) or not track.enabled:
                continue
            for item in track.items:
                if (
                    isinstance(item, Gap)
                    or not item.enabled
                    or not item.timeline_range.overlaps(timeline_range)
                ):
                    continue
                for boundary in (item.timeline_range.start, item.timeline_range.end):
                    try:
                        profile.frame_rate.time_to_frames(boundary, RoundingMode.EXACT)
                    except ValueError as exc:
                        raise EngineError(
                            ErrorCode.INVALID_TIMELINE,
                            "visual item boundary is not aligned to the output frame grid",
                            context={
                                "item_id": item.id,
                                "time": boundary.model_dump(mode="json"),
                            },
                        ) from exc

    @staticmethod
    def _validate_audio_sample_grid(sequence: Sequence, profile: DeliveryProfile) -> None:
        """Reject implicit quantization of explicitly authored audio timing."""

        sample_rate = profile.audio_sample_rate

        def require_exact(
            value: RationalTime,
            *,
            label: str,
            item_id: str | None = None,
            effect_id: str | None = None,
        ) -> None:
            try:
                AudioSampleTime.from_time(value, sample_rate, RoundingMode.EXACT)
            except ValueError as exc:
                context: dict[str, JsonValue] = {
                    "time": value.model_dump(mode="json"),
                    "sample_rate": sample_rate,
                    "boundary": label,
                }
                if item_id is not None:
                    context["item_id"] = item_id
                if effect_id is not None:
                    context["effect_id"] = effect_id
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "explicit audio timing is not aligned to the output sample grid",
                    context=context,
                ) from exc

        for track in sequence.timeline.tracks:
            if not isinstance(track, AudioTrack) or not track.enabled:
                continue
            for item in track.items:
                if not isinstance(item, AudioClip) or not item.enabled:
                    continue
                require_exact(item.timeline_range.start, label="start", item_id=item.id)
                require_exact(item.timeline_range.end, label="end", item_id=item.id)
                for effect in item.effects:
                    if not effect.enabled:
                        continue
                    for keyframe in effect.keyframes:
                        require_exact(
                            item.timeline_range.start + keyframe.time,
                            label="automation",
                            item_id=item.id,
                            effect_id=effect.id,
                        )
            for effect in track.effects:
                if not effect.enabled:
                    continue
                for keyframe in effect.keyframes:
                    require_exact(
                        keyframe.time,
                        label="track_automation",
                        effect_id=effect.id,
                    )
        for bus in sequence.timeline.audio_buses:
            for effect in bus.effects:
                if not effect.enabled:
                    continue
                for keyframe in effect.keyframes:
                    require_exact(
                        keyframe.time,
                        label="bus_automation",
                        effect_id=effect.id,
                    )

    def _compile_visual(
        self,
        sequence: Sequence,
        timeline_range: TimeRange,
        profile: DeliveryProfile,
    ) -> tuple[str, list[tuple[Clip, TimeRange]]]:
        previous_working_space = self._working_color_space
        self._working_color_space = (
            sequence.settings_override.working_color_space or previous_working_space
        )
        try:
            return self._compile_visual_in_working_space(sequence, timeline_range, profile)
        finally:
            self._working_color_space = previous_working_space

    def _compile_visual_in_working_space(
        self,
        sequence: Sequence,
        timeline_range: TimeRange,
        profile: DeliveryProfile,
    ) -> tuple[str, list[tuple[Clip, TimeRange]]]:
        layers: list[CompositeLayer] = []
        embedded_audio: list[tuple[Clip, TimeRange]] = []
        z_index = 0
        for track in sequence.timeline.tracks:
            if not isinstance(track, (VideoTrack, GraphicsTrack)) or not track.enabled:
                continue
            for item in track.items:
                if isinstance(item, Gap) or not item.enabled:
                    continue
                intersection = item.timeline_range.intersection(timeline_range)
                if intersection is None:
                    continue
                node_id = self._compile_visual_item(sequence, item, intersection, profile)
                for segment_index, (segment, layer_opacity, blend_mode) in enumerate(
                    self._visual_layer_segments(item, intersection)
                ):
                    segment_node_id = node_id
                    if segment != intersection:
                        segment_node = TrimNode(
                            id=self._id(f"{item.id}-blend-segment-{segment_index}"),
                            inputs=(node_id,),
                            artifact_type=ArtifactType.VIDEO,
                            source_range=TimeRange(
                                start=segment.start - intersection.start,
                                duration=segment.duration,
                            ),
                        )
                        self._add(segment_node)
                        segment_node_id = segment_node.id
                    layers.append(
                        CompositeLayer(
                            input_id=segment_node_id,
                            timeline_range=TimeRange(
                                start=segment.start - timeline_range.start,
                                duration=segment.duration,
                            ),
                            z_index=z_index,
                            opacity=layer_opacity,
                            blend_mode=blend_mode,
                        )
                    )
                    z_index += 1
                if isinstance(item, Clip) and item.source_audio_enabled:
                    embedded_audio.append((item, intersection))
            item_by_id = {item.id: item for item in track.items}
            for transition in track.transitions:
                if transition.kind is TransitionKind.AUDIO_CROSSFADE:
                    raise EngineError(
                        ErrorCode.INVALID_TIMELINE,
                        "audio crossfade cannot be placed on a visual track",
                        context={"track_id": track.id, "transition_id": transition.id},
                    )
                left = item_by_id[transition.from_item_id]
                right = item_by_id[transition.to_item_id]
                if not isinstance(left, (Clip, StillImageClip)) or not isinstance(
                    right, (Clip, StillImageClip)
                ):
                    raise EngineError(
                        ErrorCode.UNSUPPORTED_CAPABILITY,
                        "visual transitions currently require media or still endpoints",
                        context={"transition_id": transition.id},
                    )
                transition_result = self._compile_visual_transition(
                    sequence,
                    transition,
                    left,
                    right,
                    timeline_range,
                    profile,
                )
                if transition_result is not None:
                    node_id, layer_range = transition_result
                    layers.append(
                        CompositeLayer(
                            input_id=node_id,
                            timeline_range=layer_range,
                            z_index=z_index,
                        )
                    )
                    z_index += 1
        composite_id = self._bounded_composite(
            sequence.id,
            layers,
            profile,
            timeline_range.duration,
        )
        current = self._compile_adjustments(sequence, timeline_range, profile, composite_id)
        return current, embedded_audio

    def _bounded_composite(
        self,
        prefix: str,
        layers: list[CompositeLayer],
        profile: DeliveryProfile,
        duration: RationalTime,
        *,
        background_color: str = "black",
    ) -> str:
        maximum = self.config.max_render_inputs
        if len(layers) <= maximum:
            composite = CompositeNode(
                id=self._id(f"{prefix}-composite"),
                inputs=tuple(layer.input_id for layer in layers),
                artifact_type=ArtifactType.VIDEO,
                width=profile.width,
                height=profile.height,
                frame_rate=profile.frame_rate,
                duration=duration,
                background_color=background_color,
                layers=tuple(layers),
            )
            self._add(composite)
            return composite.id

        first = layers[:maximum]
        composite = CompositeNode(
            id=self._id(f"{prefix}-composite-stage-0"),
            inputs=tuple(layer.input_id for layer in first),
            artifact_type=ArtifactType.VIDEO,
            width=profile.width,
            height=profile.height,
            frame_rate=profile.frame_rate,
            duration=duration,
            background_color=background_color,
            layers=tuple(first),
        )
        self._add(composite)
        current = composite.id
        cursor = maximum
        stage = 1
        while cursor < len(layers):
            additions = layers[cursor : cursor + maximum - 1]
            stage_layers = [
                CompositeLayer(
                    input_id=current,
                    timeline_range=TimeRange(start=RationalTime.zero(), duration=duration),
                    z_index=0,
                ),
                *[
                    layer.model_copy(update={"z_index": index})
                    for index, layer in enumerate(additions, start=1)
                ],
            ]
            composite = CompositeNode(
                id=self._id(f"{prefix}-composite-stage-{stage}"),
                inputs=tuple(layer.input_id for layer in stage_layers),
                artifact_type=ArtifactType.VIDEO,
                width=profile.width,
                height=profile.height,
                frame_rate=profile.frame_rate,
                duration=duration,
                background_color=background_color,
                layers=tuple(stage_layers),
            )
            self._add(composite)
            current = composite.id
            cursor += maximum - 1
            stage += 1
        return current

    @staticmethod
    def _visual_layer_segments(
        item: Clip | StillImageClip | GeneratorClip | NestedSequenceClip,
        intersection: TimeRange,
    ) -> tuple[tuple[TimeRange, float, BlendModeName], ...]:
        blend_effects = [
            effect
            for effect in item.effects
            if effect.enabled and effect.kind is EffectKind.BLEND_MODE
        ]
        if len(blend_effects) > 1:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "a visual item can have only one enabled blend-mode effect",
                context={"item_id": item.id},
            )
        if not blend_effects:
            return ((intersection, 1, "normal"),)
        effect = blend_effects[0]
        parsed = parse_visual_parameters(effect)
        assert isinstance(parsed, BlendModeParameters)
        if not effect.keyframes:
            return ((intersection, parsed.opacity, parsed.mode),)

        allowed_modes: set[str] = {
            "normal",
            "multiply",
            "screen",
            "overlay",
            "darken",
            "lighten",
            "difference",
        }
        seen: set[tuple[str, RationalTime]] = set()
        events: list[tuple[RationalTime, str, float | BlendModeName]] = []
        for keyframe in effect.keyframes:
            if keyframe.property_path not in {"mode", "opacity"}:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "blend-mode keyframe targets the wrong property",
                    context={
                        "effect_id": effect.id,
                        "property_path": keyframe.property_path,
                        "allowed": ["mode", "opacity"],
                    },
                )
            if keyframe.interpolation.value != "hold":
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "blend-mode automation is discrete and requires hold interpolation",
                    context={"effect_id": effect.id, "keyframe_id": keyframe.id},
                )
            event_key = (keyframe.property_path, keyframe.time)
            if event_key in seen:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "blend-mode automation has duplicate property values at one time",
                    context={
                        "effect_id": effect.id,
                        "property_path": keyframe.property_path,
                        "time": keyframe.time.model_dump(mode="json"),
                    },
                )
            seen.add(event_key)
            value: float | BlendModeName
            if keyframe.property_path == "mode":
                if not isinstance(keyframe.value, str) or keyframe.value not in allowed_modes:
                    raise EngineError(
                        ErrorCode.INVALID_TIMELINE,
                        "blend-mode keyframe value is unsupported",
                        context={"effect_id": effect.id, "keyframe_id": keyframe.id},
                    )
                value = cast(BlendModeName, keyframe.value)
            else:
                if isinstance(keyframe.value, bool) or not isinstance(keyframe.value, (int, float)):
                    raise EngineError(
                        ErrorCode.INVALID_TIMELINE,
                        "blend opacity keyframe value must be numeric",
                        context={"effect_id": effect.id, "keyframe_id": keyframe.id},
                    )
                value = float(keyframe.value)
                if not 0 <= value <= 1:
                    raise EngineError(
                        ErrorCode.INVALID_TIMELINE,
                        "blend opacity keyframe value must be between zero and one",
                        context={"effect_id": effect.id, "keyframe_id": keyframe.id},
                    )
            events.append(
                (item.timeline_range.start + keyframe.time, keyframe.property_path, value)
            )

        opacity = parsed.opacity
        mode: BlendModeName = parsed.mode
        cursor = intersection.start
        segments: list[tuple[TimeRange, float, BlendModeName]] = []
        events.sort(key=lambda event: (event[0], event[1]))
        index = 0
        while index < len(events):
            event_time = events[index][0]
            same_time: list[tuple[RationalTime, str, float | BlendModeName]] = []
            while index < len(events) and events[index][0] == event_time:
                same_time.append(events[index])
                index += 1
            if intersection.start < event_time < intersection.end:
                segments.append(
                    (
                        TimeRange(start=cursor, duration=event_time - cursor),
                        opacity,
                        mode,
                    )
                )
                cursor = event_time
            if event_time <= intersection.start or event_time < intersection.end:
                for _, property_path, value in same_time:
                    if property_path == "mode":
                        assert isinstance(value, str)
                        mode = value
                    else:
                        assert isinstance(value, float)
                        opacity = value
        segments.append(
            (
                TimeRange(start=cursor, duration=intersection.end - cursor),
                opacity,
                mode,
            )
        )
        return tuple(segments)

    def _compile_adjustments(
        self,
        sequence: Sequence,
        timeline_range: TimeRange,
        profile: DeliveryProfile,
        current: str,
    ) -> str:
        for track in sequence.timeline.tracks:
            if not isinstance(track, AdjustmentTrack) or not track.enabled:
                continue
            for item in track.items:
                if not isinstance(item, AdjustmentClip) or not item.enabled:
                    continue
                intersection = item.timeline_range.intersection(timeline_range)
                if intersection is None:
                    continue
                enabled_range = TimeRange(
                    start=intersection.start - timeline_range.start,
                    duration=intersection.duration,
                )
                for effect in item.effects:
                    if not effect.enabled:
                        continue
                    if effect.kind not in {EffectKind.COLOR_GRADE, EffectKind.LUT}:
                        raise EngineError(
                            ErrorCode.UNSUPPORTED_CAPABILITY,
                            "adjustment layers currently support grade and LUT effects",
                            context={
                                "item_id": item.id,
                                "effect_id": effect.id,
                                "effect_kind": effect.kind.value,
                            },
                        )
                    current = self._lower_visual_effect(
                        _safe_id(item.id),
                        current,
                        effect,
                        canvas=(profile.width, profile.height),
                        enabled_range=enabled_range,
                    )
        return current

    def _compile_visual_item(
        self,
        sequence: Sequence,
        item: Clip | StillImageClip | GeneratorClip | NestedSequenceClip,
        intersection: TimeRange,
        profile: DeliveryProfile,
        *,
        source_range_override: TimeRange | None = None,
        effect_time_offset_override: RationalTime | None = None,
        matte_intersection_override: TimeRange | None = None,
        matte_stack: tuple[str, ...] = (),
    ) -> str:
        prefix = _safe_id(item.id)
        sequence_frame_rate = (
            sequence.settings_override.frame_rate or self.project.settings.frame_rate
        )
        freeze = self._freeze_effect(item, sequence_frame_rate)
        effect_time_offset = (
            effect_time_offset_override
            if effect_time_offset_override is not None
            else intersection.start - item.timeline_range.start
        )
        matte_intersection = matte_intersection_override or intersection
        if isinstance(item, NestedSequenceClip):
            nested = self._sequence(item.sequence_id, item.sequence_version)
            nested_range = self._mapped_source_range(item, intersection)
            parent_working_space = self._working_color_space
            nested_profile = self._sequence_profile(nested, profile)
            self._validate_frame_grid(nested, nested_range, nested_profile)
            current, _ = self._compile_visual(nested, nested_range, nested_profile)
            current = self._compile_captions(
                nested,
                nested_range,
                nested_profile,
                current,
                selected_languages=self._nested_caption_languages,
                strict_selection=False,
            )
            nested_working_space = (
                nested.settings_override.working_color_space or parent_working_space
            )
            if nested_working_space is not parent_working_space:
                conversion = ColorConversionNode(
                    id=self._id(f"{prefix}-nested-working-color"),
                    inputs=(current,),
                    artifact_type=ArtifactType.VIDEO,
                    input_space=nested_working_space,
                    output_space=parent_working_space,
                    tone_map=(
                        "hable"
                        if nested_working_space in {ColorSpace.HLG, ColorSpace.PQ}
                        and parent_working_space in {ColorSpace.REC709, ColorSpace.REC2020}
                        else "none"
                    ),
                )
                self._add(conversion)
                current = conversion.id
            if nested_profile.frame_rate != profile.frame_rate:
                conform = ConformNode(
                    id=self._id(f"{prefix}-nested-conform"),
                    inputs=(current,),
                    artifact_type=ArtifactType.VIDEO,
                    frame_rate=profile.frame_rate,
                    sample_rate=profile.audio_sample_rate,
                )
                self._add(conform)
                current = conform.id
            current = self._lower_retime(
                prefix,
                current,
                item.retime,
                ArtifactType.VIDEO,
                timeline_offset=effect_time_offset,
                timeline_duration=intersection.duration,
                profile=profile,
            )
            current = self._fit_visual_item(
                prefix, current, item, profile, effect_time_offset, always=True
            )
            for effect in item.effects:
                if effect.enabled and effect.kind not in {
                    EffectKind.BLEND_MODE,
                    EffectKind.REFRAME,
                }:
                    current = self._lower_item_visual_effect(
                        sequence,
                        item,
                        matte_intersection,
                        profile,
                        matte_stack,
                        prefix,
                        current,
                        effect,
                        canvas=(profile.width, profile.height),
                        automation_offset=effect_time_offset,
                        frame_rate=profile.frame_rate,
                    )
            return current
        if isinstance(item, GeneratorClip):
            asset = item.properties.get("rendered_asset_path")
            if asset is not None:
                if not isinstance(asset, str):
                    raise EngineError(
                        ErrorCode.INVALID_TIMELINE,
                        "pre-rendered graphic path must be a string",
                        context={"item_id": item.id},
                    )
                path = Path(asset)
                if not path.is_absolute():
                    path = self.project_root / path
                path = path.resolve()
                if not path.is_file():
                    raise EngineError(
                        ErrorCode.MEDIA_NOT_FOUND,
                        "pre-rendered graphic asset is missing",
                        context={"item_id": item.id, "path": str(path)},
                    )
                decode = DecodeNode(
                    id=self._id(f"{prefix}-graphic-decode"),
                    artifact_type=ArtifactType.VIDEO,
                    source_uri=str(path),
                    source_sha256=sha256_file(path),
                )
                self._add(decode)
                local_start = intersection.start - item.timeline_range.start
                trim = TrimNode(
                    id=self._id(f"{prefix}-graphic-trim"),
                    inputs=(decode.id,),
                    artifact_type=ArtifactType.VIDEO,
                    source_range=TimeRange(
                        start=local_start,
                        duration=intersection.duration,
                    ),
                )
                self._add(trim)
                conform = ConformNode(
                    id=self._id(f"{prefix}-graphic-conform"),
                    inputs=(trim.id,),
                    artifact_type=ArtifactType.VIDEO,
                    frame_rate=profile.frame_rate,
                    sample_rate=profile.audio_sample_rate,
                )
                self._add(conform)
                current = self._fit_visual_item(
                    prefix, conform.id, item, profile, effect_time_offset, always=True
                )
                for effect in item.effects:
                    if effect.enabled and effect.kind not in {
                        EffectKind.BLEND_MODE,
                        EffectKind.REFRAME,
                    }:
                        current = self._lower_item_visual_effect(
                            sequence,
                            item,
                            matte_intersection,
                            profile,
                            matte_stack,
                            prefix,
                            current,
                            effect,
                            canvas=(profile.width, profile.height),
                            automation_offset=effect_time_offset,
                            frame_rate=profile.frame_rate,
                        )
                return current
            definition, props = self.graphics_registry.validate_props(
                item.generator_id,
                item.generator_version,
                item.properties,
            )
            graphic_assets: list[GraphicAsset] = []
            for reference in item.assets:
                media = self._media_reference(reference.media_reference_id)
                path = self._resolve_media(media)
                checksum = media.sha256 or sha256_file(path)
                media_type: Literal["image", "video"] = (
                    "image"
                    if path.suffix.lower()
                    in {".avif", ".bmp", ".gif", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
                    else "video"
                )
                staged_base = re.sub(r"[^A-Za-z0-9_.-]+", "-", path.name).strip(".-")
                staged_name = f"{checksum[:16]}-{reference.id}-{staged_base or 'asset'}"
                graphic_assets.append(
                    GraphicAsset(
                        id=reference.id,
                        source_path=path,
                        sha256=checksum,
                        media_type=media_type,
                        staged_name=staged_name,
                    )
                )
            self.graphics_registry.validate_asset_references(
                item.generator_id,
                props,
                {asset.id for asset in graphic_assets},
            )
            composition_frames = profile.frame_rate.time_to_frames(item.timeline_range.duration)
            render_start = profile.frame_rate.time_to_frames(
                intersection.start - item.timeline_range.start
            )
            render_frames = profile.frame_rate.time_to_frames(intersection.duration)
            motion = MotionGraphicNode(
                id=self._id(f"{prefix}-graphic"),
                artifact_type=ArtifactType.VIDEO,
                component_id=item.generator_id,
                component_version=item.generator_version,
                component_digest=definition.source_digest,
                bounds_policy=definition.bounds_policy,
                props=props,
                assets=tuple(graphic_assets),
                duration=intersection.duration,
                width=profile.width,
                height=profile.height,
                frame_rate=profile.frame_rate,
                composition_duration_frames=composition_frames,
                render_start_frame=render_start,
                render_duration_frames=render_frames,
                transparent=item.transparent,
            )
            self._add(motion)
            current = self._fit_visual_item(
                prefix, motion.id, item, profile, effect_time_offset, always=False
            )
            for effect in item.effects:
                if effect.enabled and effect.kind not in {
                    EffectKind.BLEND_MODE,
                    EffectKind.REFRAME,
                }:
                    current = self._lower_item_visual_effect(
                        sequence,
                        item,
                        matte_intersection,
                        profile,
                        matte_stack,
                        prefix,
                        current,
                        effect,
                        canvas=(profile.width, profile.height),
                        automation_offset=effect_time_offset,
                        frame_rate=profile.frame_rate,
                    )
            return current
        media = self._media_reference(item.media_reference_id)
        source = self._resolve_media(media)
        is_still = isinstance(item, StillImageClip)
        decode_id = self._decode_media(
            prefix=f"{prefix}-decode-video",
            media=media,
            source=source,
            artifact_type=ArtifactType.IMAGE if is_still else ArtifactType.VIDEO,
            still_image=is_still,
            video_stream_index=item.video_stream_index if isinstance(item, Clip) else 0,
        )
        source_range = source_range_override or TimeRange(
            start=RationalTime.zero(), duration=intersection.duration
        )
        if isinstance(item, Clip):
            if freeze is not None:
                _, freeze_parameters = freeze
                if freeze_parameters.source_range is not None:
                    source_range = freeze_parameters.source_range
                else:
                    frame_duration = sequence_frame_rate.frames_to_time(1)
                    freeze_timeline_range = TimeRange(
                        start=item.timeline_range.start + freeze_parameters.frame_time,
                        duration=frame_duration,
                    )
                    source_range = self._mapped_source_range(item, freeze_timeline_range)
            else:
                source_range = source_range_override or self._mapped_source_range(
                    item, intersection
                )
        trim = TrimNode(
            id=self._id(f"{prefix}-trim-video"),
            inputs=(decode_id,),
            artifact_type=ArtifactType.VIDEO,
            source_range=source_range,
        )
        self._add(trim)
        current = trim.id
        if isinstance(item, Clip):
            if freeze is not None:
                _, freeze_parameters = freeze
                reverse_source = (
                    freeze_parameters.source_reverse
                    if freeze_parameters.source_range is not None
                    else item.retime.reverse
                )
                if reverse_source:
                    reverse = ReverseNode(
                        id=self._id(f"{prefix}-retime-reverse"),
                        inputs=(current,),
                        artifact_type=ArtifactType.VIDEO,
                        reverse_video=True,
                        reverse_audio=False,
                    )
                    self._add(reverse)
                    current = reverse.id
            else:
                current = self._lower_retime(
                    prefix,
                    current,
                    item.retime,
                    ArtifactType.VIDEO,
                    timeline_offset=effect_time_offset,
                    timeline_duration=intersection.duration,
                    profile=profile,
                )
        conform = ConformNode(
            id=self._id(f"{prefix}-conform-video"),
            inputs=(current,),
            artifact_type=ArtifactType.VIDEO,
            frame_rate=profile.frame_rate,
            sample_rate=profile.audio_sample_rate,
        )
        self._add(conform)
        current = conform.id
        if freeze is not None:
            freeze_effect, _ = freeze
            freeze_node = FreezeNode(
                id=self._id(f"{prefix}-{freeze_effect.id}"),
                inputs=(current,),
                artifact_type=ArtifactType.VIDEO,
                frame_time=RationalTime.zero(),
                duration=intersection.duration,
                frame_rate=profile.frame_rate,
            )
            self._add(freeze_node)
            current = freeze_node.id
        stream_index = item.video_stream_index if isinstance(item, Clip) else 0
        current = self._lower_source_color(prefix, current, item, media, stream_index)
        if media.rotation_degrees:
            rotation = TransformNode(
                id=self._id(f"{prefix}-rotation"),
                inputs=(current,),
                artifact_type=ArtifactType.VIDEO,
                rotation_degrees=media.rotation_degrees,
            )
            self._add(rotation)
            current = rotation.id
        for effect in item.effects:
            if effect.enabled and effect.kind is EffectKind.CROP:
                crop = parse_visual_parameters(effect)
                assert isinstance(crop, CropParameters)
                if crop.space == "source":
                    current = self._lower_visual_effect(
                        prefix,
                        current,
                        effect,
                        automation_offset=effect_time_offset,
                        frame_rate=profile.frame_rate,
                    )
        current = self._fit_visual_item(
            prefix, current, item, profile, effect_time_offset, always=True
        )
        for effect in item.effects:
            if effect.enabled and effect.kind not in {
                EffectKind.BLEND_MODE,
                EffectKind.REFRAME,
                EffectKind.COLOR_INTERPRETATION,
                EffectKind.COLOR_NORMALIZATION,
                EffectKind.FREEZE,
            }:
                if effect.kind is EffectKind.CROP:
                    crop = parse_visual_parameters(effect)
                    assert isinstance(crop, CropParameters)
                    if crop.space == "source":
                        continue
                current = self._lower_item_visual_effect(
                    sequence,
                    item,
                    matte_intersection,
                    profile,
                    matte_stack,
                    prefix,
                    current,
                    effect,
                    canvas=(profile.width, profile.height),
                    automation_offset=effect_time_offset,
                    frame_rate=profile.frame_rate,
                )
        return current

    def _lower_source_color(
        self,
        prefix: str,
        current: str,
        item: Clip | StillImageClip,
        media: MediaReference,
        stream_index: int,
    ) -> str:
        interpretation = [
            effect
            for effect in item.effects
            if effect.enabled and effect.kind is EffectKind.COLOR_INTERPRETATION
        ]
        normalization = [
            effect
            for effect in item.effects
            if effect.enabled and effect.kind is EffectKind.COLOR_NORMALIZATION
        ]
        if len(interpretation) > 1 or len(normalization) > 1:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "a source item can have only one interpretation and normalization effect",
                context={"item_id": item.id},
            )
        for effect in [*interpretation, *normalization]:
            if effect.keyframes:
                raise EngineError(
                    ErrorCode.UNSUPPORTED_CAPABILITY,
                    "technical color stages cannot be keyframed",
                    context={"effect_id": effect.id},
                )
        input_space = self._source_color_space(media, stream_index)
        if interpretation:
            parsed_interpretation = parse_visual_parameters(interpretation[0])
            assert isinstance(parsed_interpretation, ColorInterpretationParameters)
            input_space = parsed_interpretation.input_space
        working_space = self._working_color_space
        tone_map: Literal["none", "hable", "mobius", "reinhard", "clip"] = (
            "hable"
            if input_space in {ColorSpace.HLG, ColorSpace.PQ}
            and working_space in {ColorSpace.REC709, ColorSpace.REC2020}
            else "none"
        )
        peak_nits = 1000.0 if input_space in {ColorSpace.HLG, ColorSpace.PQ} else 100.0
        if normalization:
            parsed_normalization = parse_visual_parameters(normalization[0])
            assert isinstance(parsed_normalization, ColorNormalizationParameters)
            tone_map = parsed_normalization.tone_map
            peak_nits = parsed_normalization.peak_nits
        if (
            input_space in {ColorSpace.HLG, ColorSpace.PQ}
            and working_space in {ColorSpace.REC709, ColorSpace.REC2020}
            and tone_map == "none"
        ):
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "HDR-to-SDR normalization requires an explicit tone-map operator",
                context={"item_id": item.id, "input_space": input_space.value},
            )
        if input_space is working_space and not normalization:
            return current
        conversion = ColorConversionNode(
            id=self._id(f"{prefix}-source-to-working-color"),
            inputs=(current,),
            artifact_type=ArtifactType.VIDEO,
            input_space=input_space,
            output_space=working_space,
            tone_map=tone_map,
            peak_nits=peak_nits,
        )
        self._add(conversion)
        return conversion.id

    def _fit_visual_item(
        self,
        prefix: str,
        current: str,
        item: Clip | StillImageClip | GeneratorClip | NestedSequenceClip,
        profile: DeliveryProfile,
        automation_offset: RationalTime,
        *,
        always: bool,
    ) -> str:
        effects = [
            effect
            for effect in item.effects
            if effect.enabled and effect.kind is EffectKind.REFRAME
        ]
        if len(effects) > 1:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "a visual item can have only one enabled reframe effect",
                context={"item_id": item.id},
            )
        if not effects and not always:
            return current
        fit = profile.fit
        focus_x = _extension_float(item.extensions.get("focus_x"), name="focus_x", default=0.5)
        focus_y = _extension_float(item.extensions.get("focus_y"), name="focus_y", default=0.5)
        zoom = 1.0
        target_width = profile.width
        target_height = profile.height
        automation: tuple[VisualAutomationPoint, ...] = ()
        if effects:
            expected_canvas = (
                effects[0].extensions.get("tracking_canvas_width"),
                effects[0].extensions.get("tracking_canvas_height"),
            )
            if expected_canvas[0] is not None and expected_canvas != (
                profile.width,
                profile.height,
            ):
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "tracking reframe geometry does not match the render canvas",
                    context={
                        "effect_id": effects[0].id,
                        "tracking_canvas": list(expected_canvas),
                        "render_canvas": [profile.width, profile.height],
                    },
                )
            parsed = parse_visual_parameters(effects[0])
            assert isinstance(parsed, ReframeParameters)
            fit = parsed.fit
            focus_x = parsed.focus_x
            focus_y = parsed.focus_y
            zoom = parsed.zoom
            target_width = parsed.target_width or profile.width
            target_height = parsed.target_height or profile.height
            automation = self._visual_automation(effects[0])
        scale = ScaleNode(
            id=self._id(f"{prefix}-fit"),
            inputs=(current,),
            artifact_type=ArtifactType.VIDEO,
            width=target_width,
            height=target_height,
            fit=fit,
            focus_x=focus_x,
            focus_y=focus_y,
            zoom=zoom,
            automation=automation,
            automation_offset=automation_offset,
        )
        self._add(scale)
        return scale.id

    def _compile_visual_transition(
        self,
        sequence: Sequence,
        transition: Transition,
        left: Clip | StillImageClip,
        right: Clip | StillImageClip,
        render_range: TimeRange,
        profile: DeliveryProfile,
        *,
        matte_stack: tuple[str, ...] = (),
    ) -> tuple[str, TimeRange] | None:
        before, after = self._transition_sides(transition, profile)
        cut = left.timeline_range.end
        window = TimeRange(start=cut - before, duration=transition.duration)
        visible = window.intersection(render_range)
        if visible is None:
            return None
        left_source = self._transition_source_range(left, before, after, side="left")
        right_source = self._transition_source_range(right, before, after, side="right")
        synthetic_range = TimeRange(start=RationalTime.zero(), duration=transition.duration)
        left_id = self._compile_visual_item(
            sequence,
            left,
            synthetic_range,
            profile,
            source_range_override=left_source,
            effect_time_offset_override=window.start - left.timeline_range.start,
            matte_intersection_override=window,
            matte_stack=matte_stack,
        )
        right_id = self._compile_visual_item(
            sequence,
            right,
            synthetic_range,
            profile,
            source_range_override=right_source,
            effect_time_offset_override=window.start - right.timeline_range.start,
            matte_intersection_override=window,
            matte_stack=matte_stack,
        )
        transition_node = TransitionNode(
            id=self._id(f"transition-{transition.id}"),
            inputs=(left_id, right_id),
            artifact_type=ArtifactType.VIDEO,
            transition=transition.kind,
            duration=transition.duration,
            offset=RationalTime.zero(),
            parameters=transition.parameters,
        )
        self._add(transition_node)
        current = transition_node.id
        if visible != window:
            trim = TrimNode(
                id=self._id(f"transition-{transition.id}-range"),
                inputs=(current,),
                artifact_type=ArtifactType.VIDEO,
                source_range=TimeRange(
                    start=visible.start - window.start,
                    duration=visible.duration,
                ),
                audio_fade_in=RationalTime.zero(),
                audio_fade_out=RationalTime.zero(),
            )
            self._add(trim)
            current = trim.id
        return current, TimeRange(
            start=visible.start - render_range.start,
            duration=visible.duration,
        )

    @staticmethod
    def _transition_sides(
        transition: Transition, profile: DeliveryProfile
    ) -> tuple[RationalTime, RationalTime]:
        try:
            frames = profile.frame_rate.time_to_frames(transition.duration, RoundingMode.EXACT)
        except ValueError as exc:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "transition duration is not aligned to the output frame grid",
                context={"transition_id": transition.id},
            ) from exc
        if transition.alignment == "start_at_cut":
            before_frames = 0
        elif transition.alignment == "end_at_cut":
            before_frames = frames
        else:
            before_frames = frames // 2
        before = profile.frame_rate.frames_to_time(before_frames)
        return before, transition.duration - before

    def _transition_source_range(
        self,
        item: Clip | StillImageClip,
        before: RationalTime,
        after: RationalTime,
        *,
        side: str,
    ) -> TimeRange:
        if isinstance(item, StillImageClip):
            return TimeRange(start=RationalTime.zero(), duration=before + after)
        if any(effect.enabled and effect.kind is EffectKind.FREEZE for effect in item.effects):
            return item.source_range
        timeline_start = item.timeline_range.duration - before if side == "left" else -before
        timeline_end = timeline_start + before + after
        source_offset_start = item.retime.source_offset_at(timeline_start)
        source_offset_end = item.retime.source_offset_at(timeline_end)
        if item.retime.reverse:
            source_start = item.source_range.end - source_offset_end
        else:
            source_start = item.source_range.start + source_offset_start
        source_range = TimeRange(
            start=source_start,
            duration=source_offset_end - source_offset_start,
        )
        available = self._media_reference(item.media_reference_id).available_range
        if source_range.start.value < 0 or (
            available is not None
            and (source_range.start < available.start or source_range.end > available.end)
        ):
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "transition exceeds available source handles",
                context={
                    "item_id": item.id,
                    "side": side,
                    "required_source_range": source_range.model_dump(mode="json"),
                },
            )
        return source_range

    def _lower_item_visual_effect(
        self,
        sequence: Sequence,
        item: Clip | StillImageClip | GeneratorClip | NestedSequenceClip,
        intersection: TimeRange,
        profile: DeliveryProfile,
        matte_stack: tuple[str, ...],
        prefix: str,
        current: str,
        effect: Effect,
        *,
        canvas: tuple[int, int] | None = None,
        automation_offset: RationalTime | None = None,
        enabled_range: TimeRange | None = None,
        frame_rate: FrameRate | None = None,
    ) -> str:
        matte_input: str | None = None
        if effect.kind is EffectKind.TRACK_MATTE:
            parsed = parse_visual_parameters(effect)
            assert isinstance(parsed, TrackMatteParameters)
            if parsed.path is None:
                matte_input = self._compile_matte_reference(
                    sequence,
                    item,
                    intersection,
                    profile,
                    parsed,
                    matte_stack,
                    effect.id,
                )
        return self._lower_visual_effect(
            prefix,
            current,
            effect,
            canvas=canvas,
            automation_offset=automation_offset,
            enabled_range=enabled_range,
            frame_rate=frame_rate,
            matte_input=matte_input,
        )

    def _compile_matte_reference(
        self,
        sequence: Sequence,
        owner: Clip | StillImageClip | GeneratorClip | NestedSequenceClip,
        intersection: TimeRange,
        profile: DeliveryProfile,
        parameters: TrackMatteParameters,
        matte_stack: tuple[str, ...],
        effect_id: str,
    ) -> str:
        visual_types = (Clip, GeneratorClip, NestedSequenceClip, StillImageClip)
        ancestry = (*matte_stack, owner.id)
        if parameters.item_id is not None:
            matches = [
                item
                for track in sequence.timeline.tracks
                for item in track.items
                if item.id == parameters.item_id
            ]
            if len(matches) != 1 or not isinstance(matches[0], visual_types):
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "track matte item reference did not resolve to one visual item",
                    context={"effect_id": effect_id, "item_id": parameters.item_id},
                )
            target_item = matches[0]
            if not target_item.enabled:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "track matte item reference is disabled",
                    context={"effect_id": effect_id, "item_id": target_item.id},
                )
            if target_item.id in ancestry:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "track matte dependencies contain a cycle",
                    context={"effect_id": effect_id, "cycle": [*ancestry, target_item.id]},
                )
            if target_item.timeline_range.intersection(intersection) != intersection:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "track matte item does not cover the compiled owner range",
                    context={
                        "effect_id": effect_id,
                        "item_id": target_item.id,
                        "required_range": intersection.model_dump(mode="json"),
                    },
                )
            return self._compile_visual_item(
                sequence,
                target_item,
                intersection,
                profile,
                matte_stack=ancestry,
            )

        assert parameters.track_id is not None
        tracks = [track for track in sequence.timeline.tracks if track.id == parameters.track_id]
        if len(tracks) != 1 or not isinstance(tracks[0], (VideoTrack, GraphicsTrack)):
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "track matte track reference did not resolve to one visual track",
                context={"effect_id": effect_id, "track_id": parameters.track_id},
            )
        layers: list[CompositeLayer] = []
        z_index = 0
        for track_item in tracks[0].items:
            if not isinstance(track_item, visual_types) or not track_item.enabled:
                continue
            target_intersection = track_item.timeline_range.intersection(intersection)
            if target_intersection is None:
                continue
            for boundary in (target_intersection.start, target_intersection.end):
                try:
                    profile.frame_rate.time_to_frames(boundary, RoundingMode.EXACT)
                except ValueError as exc:
                    raise EngineError(
                        ErrorCode.INVALID_TIMELINE,
                        "track matte item boundary is not aligned to the output frame grid",
                        context={
                            "effect_id": effect_id,
                            "item_id": track_item.id,
                            "time": boundary.model_dump(mode="json"),
                        },
                    ) from exc
            if track_item.id in ancestry:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "track matte dependencies contain a cycle",
                    context={"effect_id": effect_id, "cycle": [*ancestry, track_item.id]},
                )
            target_node = self._compile_visual_item(
                sequence,
                track_item,
                target_intersection,
                profile,
                matte_stack=ancestry,
            )
            for segment_index, (segment, opacity, blend_mode) in enumerate(
                self._visual_layer_segments(track_item, target_intersection)
            ):
                segment_node = target_node
                if segment != target_intersection:
                    trim = TrimNode(
                        id=self._id(
                            f"{owner.id}-{effect_id}-{track_item.id}-matte-segment-{segment_index}"
                        ),
                        inputs=(target_node,),
                        artifact_type=ArtifactType.VIDEO,
                        source_range=TimeRange(
                            start=segment.start - target_intersection.start,
                            duration=segment.duration,
                        ),
                    )
                    self._add(trim)
                    segment_node = trim.id
                layers.append(
                    CompositeLayer(
                        input_id=segment_node,
                        timeline_range=TimeRange(
                            start=segment.start - intersection.start,
                            duration=segment.duration,
                        ),
                        z_index=z_index,
                        opacity=opacity,
                        blend_mode=blend_mode,
                    )
                )
                z_index += 1
        item_by_id = {item.id: item for item in tracks[0].items}
        for transition in tracks[0].transitions:
            if transition.kind is TransitionKind.AUDIO_CROSSFADE:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "audio crossfade cannot be placed on a visual matte track",
                    context={"track_id": tracks[0].id, "transition_id": transition.id},
                )
            left = item_by_id[transition.from_item_id]
            right = item_by_id[transition.to_item_id]
            if not isinstance(left, (Clip, StillImageClip)) or not isinstance(
                right, (Clip, StillImageClip)
            ):
                raise EngineError(
                    ErrorCode.UNSUPPORTED_CAPABILITY,
                    "visual matte transitions currently require media or still endpoints",
                    context={"transition_id": transition.id},
                )
            transition_result = self._compile_visual_transition(
                sequence,
                transition,
                left,
                right,
                intersection,
                profile,
                matte_stack=ancestry,
            )
            if transition_result is not None:
                transition_node, layer_range = transition_result
                layers.append(
                    CompositeLayer(
                        input_id=transition_node,
                        timeline_range=layer_range,
                        z_index=z_index,
                    )
                )
                z_index += 1
        return self._bounded_composite(
            f"{owner.id}-{effect_id}-matte-track",
            layers,
            profile,
            intersection.duration,
            background_color="black@0",
        )

    def _lower_visual_effect(
        self,
        prefix: str,
        current: str,
        effect: Effect,
        *,
        canvas: tuple[int, int] | None = None,
        automation_offset: RationalTime | None = None,
        enabled_range: TimeRange | None = None,
        frame_rate: FrameRate | None = None,
        matte_input: str | None = None,
    ) -> str:
        automatable_kinds = {
            EffectKind.POSITION,
            EffectKind.SCALE,
            EffectKind.ROTATION,
            EffectKind.ANCHOR,
            EffectKind.OPACITY,
            EffectKind.CROP,
            EffectKind.CORNER_RADIUS,
            EffectKind.REFRAME,
            EffectKind.PERSPECTIVE,
            EffectKind.MASK,
            EffectKind.BACKGROUND_BLUR,
        }
        if effect.keyframes and effect.kind not in automatable_kinds:
            raise EngineError(
                ErrorCode.UNSUPPORTED_CAPABILITY,
                "this visual effect does not support keyframes",
                context={"effect_id": effect.id, "effect_kind": effect.kind.value},
            )
        if effect.keyframes and effect.kind is EffectKind.MASK:
            parsed_mask = parse_visual_parameters(effect)
            if isinstance(parsed_mask, MaskParameters) and parsed_mask.shape == "asset":
                raise EngineError(
                    ErrorCode.UNSUPPORTED_CAPABILITY,
                    "asset-backed masks do not support geometry keyframes",
                    context={"effect_id": effect.id},
                )
        if effect.keyframes and effect.kind is EffectKind.BACKGROUND_BLUR:
            parsed_blur = parse_visual_parameters(effect)
            if isinstance(parsed_blur, BlurParameters) and parsed_blur.region_shape == "full":
                raise EngineError(
                    ErrorCode.UNSUPPORTED_CAPABILITY,
                    "full-frame blur does not support region keyframes",
                    context={"effect_id": effect.id},
                )
        if canvas is not None and "tracking_canvas_width" in effect.extensions:
            expected = (
                effect.extensions.get("tracking_canvas_width"),
                effect.extensions.get("tracking_canvas_height"),
            )
            if expected != canvas:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "tracking effect geometry does not match the render canvas",
                    context={
                        "effect_id": effect.id,
                        "tracking_canvas": list(expected),
                        "render_canvas": list(canvas),
                    },
                )
        if effect.kind is EffectKind.BACKEND_OVERRIDE:
            if not self.config.allow_backend_overrides:
                raise EngineError(
                    ErrorCode.UNSUPPORTED_CAPABILITY,
                    "backend override effects are disabled",
                    context={"effect_id": effect.id},
                )
            raise EngineError(
                ErrorCode.UNSUPPORTED_CAPABILITY,
                "FFmpeg override extensions require an explicit lowering adapter",
                context={"effect_id": effect.id},
            )
        if effect.kind is EffectKind.REFRAME:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "reframe effects must be lowered by the item fit stage",
                context={"effect_id": effect.id},
            )
        parsed = parse_visual_parameters(effect)
        node: RenderNode
        node_id = self._id(f"{prefix}-{effect.id}")
        canvas_width = canvas[0] if canvas is not None else None
        canvas_height = canvas[1] if canvas is not None else None
        automation = self._visual_automation(effect)
        offset = automation_offset or RationalTime.zero()
        if isinstance(parsed, PositionParameters):
            node = TransformNode(
                id=node_id,
                inputs=(current,),
                artifact_type=ArtifactType.VIDEO,
                position_x=parsed.x,
                position_y=parsed.y,
                canvas_width=canvas_width,
                canvas_height=canvas_height,
                automation=automation,
                automation_offset=offset,
            )
        elif isinstance(parsed, ScaleParameters):
            node = TransformNode(
                id=node_id,
                inputs=(current,),
                artifact_type=ArtifactType.VIDEO,
                scale_x=parsed.x,
                scale_y=parsed.y,
                canvas_width=canvas_width,
                canvas_height=canvas_height,
                automation=automation,
                automation_offset=offset,
            )
        elif isinstance(parsed, RotationParameters):
            node = TransformNode(
                id=node_id,
                inputs=(current,),
                artifact_type=ArtifactType.VIDEO,
                rotation_degrees=parsed.degrees,
                canvas_width=canvas_width,
                canvas_height=canvas_height,
                automation=automation,
                automation_offset=offset,
            )
        elif isinstance(parsed, OpacityParameters):
            node = TransformNode(
                id=node_id,
                inputs=(current,),
                artifact_type=ArtifactType.VIDEO,
                opacity=parsed.value,
                canvas_width=canvas_width,
                canvas_height=canvas_height,
                automation=automation,
                automation_offset=offset,
            )
        elif isinstance(parsed, AnchorParameters):
            node = TransformNode(
                id=node_id,
                inputs=(current,),
                artifact_type=ArtifactType.VIDEO,
                anchor_x=parsed.x,
                anchor_y=parsed.y,
                canvas_width=canvas_width,
                canvas_height=canvas_height,
                automation=automation,
                automation_offset=offset,
            )
        elif isinstance(parsed, CropParameters):
            node = CropNode(
                id=node_id,
                inputs=(current,),
                artifact_type=ArtifactType.VIDEO,
                width=parsed.width,
                height=parsed.height,
                x=parsed.x,
                y=parsed.y,
                canvas_width=canvas_width,
                canvas_height=canvas_height,
                automation=automation,
                automation_offset=offset,
            )
        elif isinstance(parsed, CornerRadiusParameters):
            node = MaskNode(
                id=node_id,
                inputs=(current,),
                artifact_type=ArtifactType.VIDEO,
                mode="rounded_rectangle",
                corner_radius=parsed.radius,
                canvas_width=canvas_width,
                canvas_height=canvas_height,
                automation=automation,
                automation_offset=offset,
            )
        elif isinstance(parsed, BlurParameters):
            node = BlurNode(
                id=node_id,
                inputs=(current,),
                artifact_type=ArtifactType.VIDEO,
                sigma=parsed.sigma,
                steps=parsed.steps,
                region_shape=parsed.region_shape,
                region_policy=parsed.region_policy,
                x=parsed.x,
                y=parsed.y,
                width=parsed.width,
                height=parsed.height,
                feather=parsed.feather,
                canvas_width=canvas_width,
                canvas_height=canvas_height,
                automation=automation,
                automation_offset=offset,
            )
        elif isinstance(parsed, ShadowParameters):
            if canvas_width is None or canvas_height is None:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "drop shadow requires fixed canvas dimensions",
                    context={"effect_id": effect.id},
                )
            node = ShadowNode(
                id=node_id,
                inputs=(current,),
                artifact_type=ArtifactType.VIDEO,
                offset_x=parsed.offset_x,
                offset_y=parsed.offset_y,
                blur_sigma=parsed.blur_sigma,
                opacity=parsed.opacity,
                color=parsed.color,
                canvas_width=canvas_width,
                canvas_height=canvas_height,
            )
        elif isinstance(parsed, GlowParameters):
            node = GlowNode(
                id=node_id,
                inputs=(current,),
                artifact_type=ArtifactType.VIDEO,
                blur_sigma=parsed.blur_sigma,
                intensity=parsed.intensity,
                color=parsed.color,
            )
        elif isinstance(parsed, PerspectiveParameters):
            node = PerspectiveNode(
                id=node_id,
                inputs=(current,),
                artifact_type=ArtifactType.VIDEO,
                top_left_x=parsed.top_left_x,
                top_left_y=parsed.top_left_y,
                top_right_x=parsed.top_right_x,
                top_right_y=parsed.top_right_y,
                bottom_left_x=parsed.bottom_left_x,
                bottom_left_y=parsed.bottom_left_y,
                bottom_right_x=parsed.bottom_right_x,
                bottom_right_y=parsed.bottom_right_y,
                interpolation=parsed.interpolation,
                frame_rate=frame_rate or self.project.settings.frame_rate,
                automation=automation,
                automation_offset=offset,
            )
        elif isinstance(parsed, DistortionParameters):
            node = DistortionNode(
                id=node_id,
                inputs=(current,),
                artifact_type=ArtifactType.VIDEO,
                center_x=parsed.center_x,
                center_y=parsed.center_y,
                quadratic=parsed.quadratic,
                double_quadratic=parsed.double_quadratic,
                interpolation=parsed.interpolation,
            )
        elif isinstance(parsed, ChromaKeyParameters):
            node = MaskNode(
                id=node_id,
                inputs=(current,),
                artifact_type=ArtifactType.VIDEO,
                mode="chroma",
                key_color=parsed.key_color,
                similarity=parsed.similarity,
                blend=parsed.blend,
            )
        elif isinstance(parsed, LumaKeyParameters):
            node = MaskNode(
                id=node_id,
                inputs=(current,),
                artifact_type=ArtifactType.VIDEO,
                mode="luma_key",
                threshold=parsed.threshold,
                softness=parsed.softness,
                invert=parsed.invert,
            )
        elif isinstance(parsed, MaskParameters) and parsed.shape != "asset":
            node = MaskNode(
                id=node_id,
                inputs=(current,),
                artifact_type=ArtifactType.VIDEO,
                mode=parsed.shape,
                invert=parsed.invert,
                x=parsed.x,
                y=parsed.y,
                width=parsed.width,
                height=parsed.height,
                feather=parsed.feather,
                canvas_width=canvas_width,
                canvas_height=canvas_height,
                automation=automation,
                automation_offset=offset,
            )
        elif isinstance(parsed, (MaskParameters, TrackMatteParameters)):
            resolved_matte = matte_input
            if parsed.path is not None:
                matte_path = self._resolve_effect_asset(parsed.path, effect.id)
                decode = DecodeNode(
                    id=self._id(f"{prefix}-{effect.id}-matte-decode"),
                    artifact_type=ArtifactType.IMAGE,
                    source_uri=matte_path,
                    source_sha256=sha256_file(Path(matte_path)),
                    still_image=True,
                )
                self._add(decode)
                resolved_matte = decode.id
            if resolved_matte is None:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "track matte reference was not compiled",
                    context={"effect_id": effect.id},
                )
            mode: Literal["alpha_matte", "luma_matte"] = "alpha_matte"
            if isinstance(parsed, TrackMatteParameters) and parsed.channel == "luma":
                mode = "luma_matte"
            node = MaskNode(
                id=node_id,
                inputs=(current, resolved_matte),
                artifact_type=ArtifactType.VIDEO,
                mode=mode,
                invert=parsed.invert,
                canvas_width=canvas_width,
                canvas_height=canvas_height,
            )
        elif isinstance(parsed, FreezeParameters):
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "freeze must be lowered as an item-local temporal operation",
                context={"effect_id": effect.id},
            )
        elif isinstance(parsed, (ColorInterpretationParameters, ColorNormalizationParameters)):
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "technical color effects must be lowered before visual effects",
                context={"effect_id": effect.id},
            )
        elif isinstance(parsed, GradeParameters):
            lut_path = (
                self._resolve_effect_asset(parsed.lut_path, effect.id) if parsed.lut_path else None
            )
            node = GradeNode(
                id=node_id,
                inputs=(current,),
                artifact_type=ArtifactType.VIDEO,
                exposure_stops=parsed.exposure_stops,
                temperature=parsed.temperature,
                tint=parsed.tint,
                contrast=parsed.contrast,
                gamma=parsed.gamma,
                saturation=parsed.saturation,
                highlights=parsed.highlights,
                shadows=parsed.shadows,
                lut_path=lut_path,
                enabled_range=enabled_range,
            )
        elif isinstance(parsed, LutParameters):
            node = GradeNode(
                id=node_id,
                inputs=(current,),
                artifact_type=ArtifactType.VIDEO,
                lut_path=self._resolve_effect_asset(parsed.path, effect.id),
                enabled_range=enabled_range,
            )
        else:
            raise AssertionError("unreachable visual effect model")
        self._add(node)
        return node.id

    @staticmethod
    def _visual_automation(effect: Effect) -> tuple[VisualAutomationPoint, ...]:
        property_maps: dict[EffectKind, dict[str, str]] = {
            EffectKind.POSITION: {"x": "position_x", "y": "position_y"},
            EffectKind.SCALE: {"x": "scale_x", "y": "scale_y"},
            EffectKind.ROTATION: {"degrees": "rotation_degrees"},
            EffectKind.ANCHOR: {"x": "anchor_x", "y": "anchor_y"},
            EffectKind.OPACITY: {"value": "opacity"},
            EffectKind.CROP: {
                "width": "crop_width",
                "height": "crop_height",
                "x": "crop_x",
                "y": "crop_y",
            },
            EffectKind.CORNER_RADIUS: {"radius": "corner_radius"},
            EffectKind.REFRAME: {
                "focus_x": "focus_x",
                "focus_y": "focus_y",
                "zoom": "reframe_zoom",
            },
            EffectKind.PERSPECTIVE: {
                "top_left_x": "top_left_x",
                "top_left_y": "top_left_y",
                "top_right_x": "top_right_x",
                "top_right_y": "top_right_y",
                "bottom_left_x": "bottom_left_x",
                "bottom_left_y": "bottom_left_y",
                "bottom_right_x": "bottom_right_x",
                "bottom_right_y": "bottom_right_y",
            },
            EffectKind.MASK: {
                "x": "region_x",
                "y": "region_y",
                "width": "region_width",
                "height": "region_height",
            },
            EffectKind.BACKGROUND_BLUR: {
                "x": "region_x",
                "y": "region_y",
                "width": "region_width",
                "height": "region_height",
            },
        }
        mapping = property_maps.get(effect.kind, {})
        points: list[VisualAutomationPoint] = []
        for keyframe in sorted(effect.keyframes, key=lambda item: item.time):
            property_path = mapping.get(keyframe.property_path)
            if property_path is None:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "visual keyframe targets the wrong property",
                    context={
                        "effect_id": effect.id,
                        "property_path": keyframe.property_path,
                        "allowed": sorted(mapping),
                    },
                )
            value = keyframe.value
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "visual automation values must be numeric",
                    context={"effect_id": effect.id, "keyframe_id": keyframe.id},
                )
            numeric = float(value)
            if (
                property_path
                in {
                    "scale_x",
                    "scale_y",
                    "crop_width",
                    "crop_height",
                    "region_width",
                    "region_height",
                }
                and numeric <= 0
            ):
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "visual automation size values must be positive",
                    context={"effect_id": effect.id, "keyframe_id": keyframe.id},
                )
            if property_path in {"opacity", "anchor_x", "anchor_y"} and not 0 <= numeric <= 1:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "visual automation normalized values must be between zero and one",
                    context={"effect_id": effect.id, "keyframe_id": keyframe.id},
                )
            if (
                property_path
                in {
                    "region_x",
                    "region_y",
                    "region_width",
                    "region_height",
                }
                and not 0 <= numeric <= 1
            ):
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "animated region values must be normalized",
                    context={"effect_id": effect.id, "keyframe_id": keyframe.id},
                )
            if property_path in {"focus_x", "focus_y"} and not 0 <= numeric <= 1:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "reframe focus values must be between zero and one",
                    context={"effect_id": effect.id, "keyframe_id": keyframe.id},
                )
            if (
                property_path
                in {
                    "top_left_x",
                    "top_left_y",
                    "top_right_x",
                    "top_right_y",
                    "bottom_left_x",
                    "bottom_left_y",
                    "bottom_right_x",
                    "bottom_right_y",
                }
                and not 0 <= numeric <= 1
            ):
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "perspective coordinates must be between zero and one",
                    context={"effect_id": effect.id, "keyframe_id": keyframe.id},
                )
            if property_path == "reframe_zoom" and not 1 <= numeric <= 100:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "reframe zoom values must be between one and one hundred",
                    context={"effect_id": effect.id, "keyframe_id": keyframe.id},
                )
            if property_path in {"crop_x", "crop_y", "corner_radius"} and numeric < 0:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "animated crop positions must be nonnegative",
                    context={"effect_id": effect.id, "keyframe_id": keyframe.id},
                )
            points.append(
                VisualAutomationPoint.model_validate(
                    {
                        "property_path": property_path,
                        "time": keyframe.time,
                        "value": numeric,
                        "interpolation": keyframe.interpolation,
                        "in_tangent": keyframe.in_tangent,
                        "out_tangent": keyframe.out_tangent,
                    }
                )
            )
        if effect.kind in {EffectKind.MASK, EffectKind.BACKGROUND_BLUR} and points:
            region_points = [point for point in points if point.property_path.startswith("region_")]
            if any(point.interpolation is Interpolation.BEZIER for point in region_points):
                raise EngineError(
                    ErrorCode.UNSUPPORTED_CAPABILITY,
                    "Bezier region automation cannot guarantee normalized bounds",
                    context={"effect_id": effect.id},
                )
            parsed_region = parse_visual_parameters(effect)
            assert isinstance(parsed_region, (MaskParameters, BlurParameters))

            def maximum(property_path: str, base: float) -> float:
                return max(
                    [base]
                    + [
                        point.value
                        for point in region_points
                        if point.property_path == property_path
                    ]
                )

            if (
                maximum("region_x", parsed_region.x) + maximum("region_width", parsed_region.width)
                > 1
                or maximum("region_y", parsed_region.y)
                + maximum("region_height", parsed_region.height)
                > 1
            ):
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "animated region can extend outside the normalized canvas",
                    context={"effect_id": effect.id},
                )
        return tuple(points)

    @staticmethod
    def _mapped_source_range(
        item: Clip | AudioClip | NestedSequenceClip,
        timeline_range: TimeRange,
    ) -> TimeRange:
        relative_start = timeline_range.start - item.timeline_range.start
        source_offset_start = item.retime.source_offset_at(relative_start)
        source_offset_end = item.retime.source_offset_at(relative_start + timeline_range.duration)
        source_duration = source_offset_end - source_offset_start
        if item.retime.reverse:
            source_start = item.source_range.end - source_offset_end
        else:
            source_start = item.source_range.start + source_offset_start
        return TimeRange(start=source_start, duration=source_duration)

    @staticmethod
    def _freeze_effect(
        item: Clip | StillImageClip | GeneratorClip | NestedSequenceClip,
        frame_rate: FrameRate,
    ) -> tuple[Effect, FreezeParameters] | None:
        effects = [
            effect for effect in item.effects if effect.enabled and effect.kind is EffectKind.FREEZE
        ]
        if not effects:
            return None
        if len(effects) > 1:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "a visual item can have only one enabled freeze effect",
                context={"item_id": item.id},
            )
        effect = effects[0]
        if not isinstance(item, Clip):
            raise EngineError(
                ErrorCode.UNSUPPORTED_CAPABILITY,
                "freeze effects require source video clips",
                context={"item_id": item.id, "effect_id": effect.id},
            )
        if effect.keyframes:
            raise EngineError(
                ErrorCode.UNSUPPORTED_CAPABILITY,
                "freeze frame selection cannot be keyframed",
                context={"item_id": item.id, "effect_id": effect.id},
            )
        parsed = parse_visual_parameters(effect)
        assert isinstance(parsed, FreezeParameters)
        if parsed.duration != item.timeline_range.duration:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "freeze duration must equal the owning clip duration",
                context={"item_id": item.id, "effect_id": effect.id},
            )
        try:
            frame_rate.time_to_frames(parsed.frame_time, RoundingMode.EXACT)
            frame_rate.time_to_frames(parsed.duration, RoundingMode.EXACT)
        except ValueError as exc:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "freeze frame time and duration must align to the sequence frame grid",
                context={"item_id": item.id, "effect_id": effect.id},
            ) from exc
        frame_duration = frame_rate.frames_to_time(1)
        source_offset_end = item.retime.source_offset_at(parsed.frame_time + frame_duration)
        if parsed.source_range is None and source_offset_end > item.source_range.duration:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "freeze frame time lies outside the owning source context",
                context={"item_id": item.id, "effect_id": effect.id},
            )
        return effect, parsed

    def _lower_retime(
        self,
        prefix: str,
        current: str,
        retime: Retime,
        artifact_type: ArtifactType,
        *,
        timeline_offset: RationalTime,
        timeline_duration: RationalTime,
        profile: DeliveryProfile,
    ) -> str:
        if retime.reverse:
            reverse = ReverseNode(
                id=self._id(f"{prefix}-retime-reverse"),
                inputs=(current,),
                artifact_type=artifact_type,
                reverse_video=artifact_type is ArtifactType.VIDEO,
                reverse_audio=artifact_type is ArtifactType.AUDIO,
            )
            self._add(reverse)
            current = reverse.id
        if retime.speed_ramp:
            ramp = retime.window(timeline_offset, timeline_duration)
            speed_ramp = SpeedRampNode(
                id=self._id(f"{prefix}-retime-speed-ramp"),
                inputs=(current,),
                artifact_type=artifact_type,
                points=ramp.speed_ramp,
                duration=timeline_duration,
                frame_rate=profile.frame_rate,
                sample_rate=profile.audio_sample_rate,
            )
            self._add(speed_ramp)
            current = speed_ramp.id
        elif retime.rate.fraction != 1:
            speed = SpeedNode(
                id=self._id(f"{prefix}-retime-speed"),
                inputs=(current,),
                artifact_type=artifact_type,
                rate=retime.rate,
                duration=timeline_duration,
                frame_rate=profile.frame_rate,
                sample_rate=profile.audio_sample_rate,
            )
            self._add(speed)
            current = speed.id
        return current

    def _resolve_effect_asset(self, value: str, effect_id: str) -> str:
        path = Path(value)
        if not path.is_absolute():
            path = self.project_root / path
        path = path.resolve()
        if not path.is_file():
            raise EngineError(
                ErrorCode.MEDIA_NOT_FOUND,
                "visual effect asset is missing",
                context={"effect_id": effect_id, "path": str(path)},
            )
        return str(path)

    def _compile_captions(
        self,
        sequence: Sequence,
        timeline_range: TimeRange,
        profile: DeliveryProfile,
        visual_root: str,
        *,
        selected_track_ids: tuple[str, ...] | None = None,
        selected_languages: tuple[str, ...] | None = None,
        strict_selection: bool = False,
    ) -> str:
        cues: list[CaptionRenderCue] = []
        font_paths: set[str] = set()
        default_style_id = "default"
        caption_tracks = [
            track
            for track in sequence.timeline.tracks
            if isinstance(track, CaptionTrack) and track.enabled
        ]
        if selected_languages is not None:
            available_languages = {track.language for track in caption_tracks}
            missing_languages = set(selected_languages) - available_languages
            if strict_selection and missing_languages:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "caption language selection is unavailable",
                    context={"languages": sorted(missing_languages)},
                )
            caption_tracks = [
                track for track in caption_tracks if track.language in selected_languages
            ]
        if selected_track_ids is None and selected_languages is None:
            if len(caption_tracks) > 1:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "multiple enabled caption tracks require an explicit render selection",
                    context={"track_ids": [track.id for track in caption_tracks]},
                )
        elif selected_track_ids is not None:
            enabled_ids = {track.id for track in caption_tracks}
            missing = set(selected_track_ids) - enabled_ids
            if missing:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "caption render selection references missing or disabled tracks",
                    context={"track_ids": sorted(missing)},
                )
            caption_tracks = [
                track for track in caption_tracks if track.id in set(selected_track_ids)
            ]
        for track in caption_tracks:
            for region in track.collision_regions:
                expected_canvas = (
                    region.extensions.get("tracking_canvas_width"),
                    region.extensions.get("tracking_canvas_height"),
                )
                if expected_canvas[0] is not None and expected_canvas != (
                    profile.width,
                    profile.height,
                ):
                    raise EngineError(
                        ErrorCode.INVALID_TIMELINE,
                        "tracked caption exclusion geometry does not match the render canvas",
                        context={
                            "track_id": track.id,
                            "region_id": region.id,
                            "tracking_canvas": list(expected_canvas),
                            "render_canvas": [profile.width, profile.height],
                        },
                    )
            default_style_id = track.default_style_id
            visible_items = [
                item
                for item in track.items
                if not isinstance(item, CaptionCue) or item.timeline_range.overlaps(timeline_range)
            ]
            layout_track = track.model_copy(update={"items": visible_items})
            layout = validate_caption_layout(
                layout_track,
                self.project.caption_styles,
                width=profile.width,
                height=profile.height,
                config=self.config,
            )
            blocking_issues = [
                issue.model_dump(mode="json")
                for issue in layout.issues
                if issue.severity == "error"
            ]
            if blocking_issues:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "caption layout validation failed",
                    context={"track_id": track.id, "issues": blocking_issues},
                )
            font_paths.update(layout.resolved_fonts.values())
            for cue in track.items:
                if not isinstance(cue, CaptionCue) or not cue.enabled or cue.suppressed:
                    continue
                intersection = cue.timeline_range.intersection(timeline_range)
                if intersection is None:
                    continue
                cues.append(
                    CaptionRenderCue(
                        text=cue.text,
                        timeline_range=cue.timeline_range,
                        words=tuple(
                            CaptionRenderWord(
                                text=word.text,
                                timeline_range=word.range,
                                highlight=word.highlight,
                                style_id=word.style_id,
                            )
                            for word in cue.words
                        ),
                        style_id=cue.style_id or track.default_style_id,
                        position=cue.position,
                        speaker=cue.speaker,
                        language=(track.language if cue.language == "und" else cue.language),
                        position_x=cue.position_x,
                        position_y=cue.position_y,
                        style_overrides=cue.style_overrides.model_copy(
                            update={"font_size_px": layout.fitted_font_sizes.get(cue.id)}
                        ),
                    )
                )
        if not cues:
            return visual_root
        caption = CaptionNode(
            id=self._id("captions"),
            inputs=(visual_root,),
            artifact_type=ArtifactType.VIDEO,
            cues=tuple(cues),
            width=profile.width,
            height=profile.height,
            styles=tuple(self.project.caption_styles),
            default_style_id=default_style_id,
            timeline_offset=timeline_range.start,
            font_paths=tuple(sorted(font_paths)),
        )
        self._add(caption)
        return caption.id

    def _compile_audio(
        self,
        sequence: Sequence,
        timeline_range: TimeRange,
        profile: DeliveryProfile,
        embedded: list[tuple[Clip, TimeRange]],
        mode: RenderMode,
        *,
        apply_loudness: bool = True,
    ) -> str:
        bus_routes: dict[str, list[AudioMixInput]] = {
            bus.id: [] for bus in sequence.timeline.audio_buses
        }
        master_bus_id = sequence.timeline.master_bus_id
        buses = {bus.id: bus for bus in sequence.timeline.audio_buses}

        def route(
            node_id: str,
            bus_id: str,
            *,
            start: RationalTime,
            duration: RationalTime,
        ) -> None:
            bus_routes[bus_id].append(
                AudioMixInput(input_id=node_id, start=start, duration=duration)
            )

        replaced_embedded_items = {
            item.replaces_embedded_audio_item_id
            for track in sequence.timeline.tracks
            if isinstance(track, AudioTrack) and track.enabled
            for item in track.items
            if isinstance(item, AudioClip)
            and item.enabled
            and item.replaces_embedded_audio_item_id is not None
        }
        for clip, intersection in embedded:
            if clip.id in replaced_embedded_items:
                continue
            media = self._media_reference(clip.media_reference_id)
            if not self._media_has_audio(media):
                continue
            node_id = self._compile_audio_source(
                clip.id,
                clip.media_reference_id,
                self._mapped_source_range(clip, intersection),
                (),
                profile,
                retime=clip.retime,
                retime_range=TimeRange(
                    start=intersection.start - clip.timeline_range.start,
                    duration=intersection.duration,
                ),
                stream_index=clip.source_audio_stream_index,
                explicit_audio=False,
                fade_in=(intersection.start == clip.timeline_range.start),
                fade_out=(intersection.end == clip.timeline_range.end),
            )
            start = intersection.start - timeline_range.start
            AudioSampleTime.from_time(start, profile.audio_sample_rate, RoundingMode.NEAREST)
            route(
                node_id,
                master_bus_id,
                start=start,
                duration=intersection.duration,
            )
        for visual_track in sequence.timeline.tracks:
            if (
                not isinstance(visual_track, (VideoTrack, GraphicsTrack))
                or not visual_track.enabled
            ):
                continue
            for nested_item in visual_track.items:
                if not isinstance(nested_item, NestedSequenceClip) or not nested_item.enabled:
                    continue
                if not nested_item.source_audio_enabled:
                    continue
                nested_intersection = nested_item.timeline_range.intersection(timeline_range)
                if nested_intersection is None:
                    continue
                nested = self._sequence(nested_item.sequence_id, nested_item.sequence_version)
                nested_range = self._mapped_source_range(nested_item, nested_intersection)
                nested_profile = self._sequence_profile(nested, profile)
                nested_audio = self._compile_audio(
                    nested,
                    nested_range,
                    nested_profile,
                    self._embedded_audio(nested, nested_range),
                    mode,
                    apply_loudness=False,
                )
                if nested_profile.audio_sample_rate != profile.audio_sample_rate:
                    conform = ConformNode(
                        id=self._id(f"{nested_item.id}-nested-audio-conform"),
                        inputs=(nested_audio,),
                        artifact_type=ArtifactType.AUDIO,
                        frame_rate=profile.frame_rate,
                        sample_rate=profile.audio_sample_rate,
                    )
                    self._add(conform)
                    nested_audio = conform.id
                nested_audio = self._lower_retime(
                    _safe_id(nested_item.id),
                    nested_audio,
                    nested_item.retime,
                    ArtifactType.AUDIO,
                    timeline_offset=nested_intersection.start - nested_item.timeline_range.start,
                    timeline_duration=nested_intersection.duration,
                    profile=profile,
                )
                processors: list[AudioProcessor] = []
                if nested_item.audio_gain_db:
                    processors.append(
                        AudioProcessor(
                            kind="gain",
                            parameters={"db": nested_item.audio_gain_db},
                        )
                    )
                if nested_item.audio_pan:
                    processors.append(
                        AudioProcessor(kind="pan", parameters={"value": nested_item.audio_pan})
                    )
                if processors:
                    process = AudioProcessNode(
                        id=self._id(f"{nested_item.id}-nested-audio-process"),
                        inputs=(nested_audio,),
                        artifact_type=ArtifactType.AUDIO,
                        processors=tuple(processors),
                        sample_rate=profile.audio_sample_rate,
                        channel_layout=profile.audio_channel_layout,
                    )
                    self._add(process)
                    nested_audio = process.id
                start = nested_intersection.start - timeline_range.start
                AudioSampleTime.from_time(start, profile.audio_sample_rate, RoundingMode.NEAREST)
                route(
                    nested_audio,
                    nested_item.audio_bus_id or master_bus_id,
                    start=start,
                    duration=nested_intersection.duration,
                )
        for audio_track in sequence.timeline.tracks:
            if not isinstance(audio_track, AudioTrack) or not audio_track.enabled:
                continue
            grouped_inputs: dict[str, list[AudioMixInput]] = {}
            item_by_id = {
                item.id: item
                for item in audio_track.items
                if isinstance(item, AudioClip) and item.enabled
            }
            excluded_ranges: dict[str, list[TimeRange]] = {item_id: [] for item_id in item_by_id}
            transition_windows: list[
                tuple[Transition, AudioClip, AudioClip, TimeRange, RationalTime, RationalTime]
            ] = []
            for transition in audio_track.transitions:
                if transition.kind is not TransitionKind.AUDIO_CROSSFADE:
                    raise EngineError(
                        ErrorCode.INVALID_TIMELINE,
                        "visual transition cannot be placed on an audio track",
                        context={
                            "track_id": audio_track.id,
                            "transition_id": transition.id,
                        },
                    )
                left = item_by_id.get(transition.from_item_id)
                right = item_by_id.get(transition.to_item_id)
                if left is None or right is None:
                    continue
                left_bus = left.bus_id or audio_track.bus_id
                right_bus = right.bus_id or audio_track.bus_id
                if left_bus != right_bus:
                    raise EngineError(
                        ErrorCode.INVALID_TIMELINE,
                        "audio crossfade endpoints must route to the same bus",
                        context={"transition_id": transition.id},
                    )
                before, after = self._audio_transition_sides(transition, profile)
                window = TimeRange(
                    start=left.timeline_range.end - before,
                    duration=transition.duration,
                )
                excluded_ranges[left.id].append(TimeRange(start=window.start, duration=before))
                excluded_ranges[right.id].append(
                    TimeRange(start=right.timeline_range.start, duration=after)
                )
                transition_windows.append((transition, left, right, window, before, after))
            for audio_item in audio_track.items:
                if not isinstance(audio_item, AudioClip) or not audio_item.enabled:
                    continue
                audio_intersection = audio_item.timeline_range.intersection(timeline_range)
                if audio_intersection is None:
                    continue
                for segment in self._subtract_ranges(
                    audio_intersection, excluded_ranges[audio_item.id]
                ):
                    source_range = self._mapped_source_range(audio_item, segment)
                    node_id = self._compile_audio_source(
                        audio_item.id,
                        audio_item.media_reference_id,
                        source_range,
                        tuple(effect for effect in audio_item.effects if effect.enabled),
                        profile,
                        retime=audio_item.retime,
                        retime_range=TimeRange(
                            start=segment.start - audio_item.timeline_range.start,
                            duration=segment.duration,
                        ),
                        stream_index=audio_item.stream_index,
                        channel_map=audio_item.channel_map,
                        explicit_audio=True,
                        effect_time_offset=segment.start - audio_item.timeline_range.start,
                        fade_in=(segment.start == audio_item.timeline_range.start),
                        fade_out=(segment.end == audio_item.timeline_range.end),
                    )
                    start = segment.start - timeline_range.start
                    AudioSampleTime.from_time(start, profile.audio_sample_rate, RoundingMode.EXACT)
                    bus_id = audio_item.bus_id or audio_track.bus_id
                    grouped_inputs.setdefault(bus_id, []).append(
                        AudioMixInput(
                            input_id=node_id,
                            start=start,
                            duration=segment.duration,
                        )
                    )
            for transition, left, right, window, before, after in transition_windows:
                visible = window.intersection(timeline_range)
                if visible is None:
                    continue
                left_source = self._audio_transition_source_range(left, before, after, side="left")
                right_source = self._audio_transition_source_range(
                    right, before, after, side="right"
                )
                left_id = self._compile_audio_source(
                    f"transition-{transition.id}-left",
                    left.media_reference_id,
                    left_source,
                    tuple(effect for effect in left.effects if effect.enabled),
                    profile,
                    retime=left.retime,
                    retime_range=TimeRange(
                        start=left.timeline_range.duration - before,
                        duration=transition.duration,
                    ),
                    stream_index=left.stream_index,
                    channel_map=left.channel_map,
                    explicit_audio=True,
                    effect_time_offset=left.timeline_range.duration - before,
                )
                right_id = self._compile_audio_source(
                    f"transition-{transition.id}-right",
                    right.media_reference_id,
                    right_source,
                    tuple(effect for effect in right.effects if effect.enabled),
                    profile,
                    retime=right.retime,
                    retime_range=TimeRange(
                        start=-before,
                        duration=transition.duration,
                    ),
                    stream_index=right.stream_index,
                    channel_map=right.channel_map,
                    explicit_audio=True,
                    effect_time_offset=-before,
                )
                crossfade = TransitionNode(
                    id=self._id(f"transition-{transition.id}-audio"),
                    inputs=(left_id, right_id),
                    artifact_type=ArtifactType.AUDIO,
                    transition=TransitionKind.AUDIO_CROSSFADE,
                    duration=transition.duration,
                    offset=RationalTime.zero(),
                    audio_sample_rate=profile.audio_sample_rate,
                    parameters=transition.parameters,
                )
                self._add(crossfade)
                transition_root = crossfade.id
                if visible != window:
                    trim = TrimNode(
                        id=self._id(f"transition-{transition.id}-audio-range"),
                        inputs=(transition_root,),
                        artifact_type=ArtifactType.AUDIO,
                        source_range=TimeRange(
                            start=visible.start - window.start,
                            duration=visible.duration,
                        ),
                        audio_sample_rate=profile.audio_sample_rate,
                    )
                    self._add(trim)
                    transition_root = trim.id
                bus_id = left.bus_id or audio_track.bus_id
                grouped_inputs.setdefault(bus_id, []).append(
                    AudioMixInput(
                        input_id=transition_root,
                        start=visible.start - timeline_range.start,
                        duration=visible.duration,
                    )
                )
            for bus_id, inputs in grouped_inputs.items():
                track_root = self._bounded_audio_mix(
                    f"audio-track-{audio_track.id}-{bus_id}",
                    inputs,
                    timeline_range.duration,
                    profile,
                    buses[bus_id].channel_layout,
                )
                if audio_track.effects:
                    track_process = AudioProcessNode(
                        id=self._id(f"audio-track-{audio_track.id}-{bus_id}-process"),
                        inputs=(track_root,),
                        artifact_type=ArtifactType.AUDIO,
                        processors=tuple(
                            parse_audio_processor(effect, time_offset=timeline_range.start)
                            for effect in audio_track.effects
                            if effect.enabled
                        ),
                        sample_rate=profile.audio_sample_rate,
                        channel_layout=buses[bus_id].channel_layout,
                    )
                    self._add(track_process)
                    track_root = track_process.id
                route(
                    track_root,
                    bus_id,
                    start=RationalTime.zero(),
                    duration=timeline_range.duration,
                )

        children: dict[str, list[str]] = {bus_id: [] for bus_id in buses}
        for bus in buses.values():
            if bus.parent_bus_id is not None:
                children[bus.parent_bus_id].append(bus.id)
        compiled_buses: dict[str, str] = {}
        compiling_buses: set[str] = set()

        def compile_bus(bus_id: str) -> str:
            if bus_id in compiled_buses:
                return compiled_buses[bus_id]
            if bus_id in compiling_buses:
                raise EngineError(
                    ErrorCode.INVALID_TIMELINE,
                    "audio side-chain dependencies contain a cycle",
                    context={"bus_id": bus_id},
                )
            compiling_buses.add(bus_id)
            bus = buses[bus_id]
            inputs = list(bus_routes[bus_id]) if bus.enabled else []
            if bus.enabled:
                for child_id in children[bus_id]:
                    child_root = compile_bus(child_id)
                    inputs.append(
                        AudioMixInput(
                            input_id=child_root,
                            start=RationalTime.zero(),
                            duration=timeline_range.duration,
                        )
                    )
            output_layout = (
                profile.audio_channel_layout if bus_id == master_bus_id else bus.channel_layout
            )
            bus_root = self._bounded_audio_mix(
                "audio-master" if bus_id == master_bus_id else f"audio-bus-{bus_id}",
                inputs,
                timeline_range.duration,
                profile,
                output_layout,
            )
            processors = [
                parse_audio_processor(effect, time_offset=timeline_range.start)
                for effect in bus.effects
                if effect.enabled and effect.kind is not EffectKind.SIDECHAIN_DUCKING
            ]
            if bus.gain_db:
                processors.insert(
                    0,
                    AudioProcessor(kind="gain", parameters={"db": bus.gain_db}),
                )
            if bus.pan:
                processors.insert(
                    1 if bus.gain_db else 0,
                    AudioProcessor(kind="pan", parameters={"value": bus.pan}),
                )
            if processors:
                bus_process = AudioProcessNode(
                    id=self._id(f"audio-bus-{bus_id}-process"),
                    inputs=(bus_root,),
                    artifact_type=ArtifactType.AUDIO,
                    processors=tuple(processors),
                    sample_rate=profile.audio_sample_rate,
                    channel_layout=output_layout,
                )
                self._add(bus_process)
                bus_root = bus_process.id
            for effect in bus.effects:
                if not effect.enabled or effect.kind is not EffectKind.SIDECHAIN_DUCKING:
                    continue
                parameters = parse_sidechain_parameters(effect)
                if parameters.key_bus_id not in buses:
                    raise EngineError(
                        ErrorCode.INVALID_TIMELINE,
                        "side-chain effect references a missing key bus",
                        context={
                            "effect_id": effect.id,
                            "key_bus_id": parameters.key_bus_id,
                        },
                    )
                if parameters.key_bus_id == bus_id:
                    raise EngineError(
                        ErrorCode.INVALID_TIMELINE,
                        "audio bus cannot side-chain from itself",
                        context={"effect_id": effect.id, "bus_id": bus_id},
                    )
                key_root = compile_bus(parameters.key_bus_id)
                sidechain = AudioSidechainNode(
                    id=self._id(f"audio-bus-{bus_id}-{effect.id}-sidechain"),
                    inputs=(bus_root, key_root),
                    artifact_type=ArtifactType.AUDIO,
                    threshold_db=parameters.threshold_db,
                    ratio=parameters.ratio,
                    attack_ms=parameters.attack_ms,
                    release_ms=parameters.release_ms,
                    makeup_db=parameters.makeup_db,
                    mix=parameters.mix,
                    sample_rate=profile.audio_sample_rate,
                    channel_layout=output_layout,
                )
                self._add(sidechain)
                bus_root = sidechain.id
            compiled_buses[bus_id] = bus_root
            compiling_buses.remove(bus_id)
            return bus_root

        current = compile_bus(master_bus_id)
        if apply_loudness and profile.loudness is not None:
            loudness = LoudnessNode(
                id=self._id("audio-loudness"),
                inputs=(current,),
                artifact_type=ArtifactType.AUDIO,
                profile=profile.loudness,
                mode="two_pass" if mode is RenderMode.FINAL else "single_pass",
                sample_rate=profile.audio_sample_rate,
            )
            self._add(loudness)
            current = loudness.id
        return current

    def _bounded_audio_mix(
        self,
        prefix: str,
        inputs: list[AudioMixInput],
        duration: RationalTime,
        profile: DeliveryProfile,
        channel_layout: str,
    ) -> str:
        maximum = self.config.max_render_inputs
        current_inputs = inputs
        stage = 0
        while True:
            if len(current_inputs) <= maximum:
                mix = AudioMixNode(
                    id=self._id(f"{prefix}-mix" if stage == 0 else f"{prefix}-mix-{stage}"),
                    inputs=tuple(item.input_id for item in current_inputs),
                    artifact_type=ArtifactType.AUDIO,
                    mix_inputs=tuple(current_inputs),
                    duration=duration,
                    sample_rate=profile.audio_sample_rate,
                    channels=profile.audio_channels,
                    channel_layout=channel_layout,
                )
                self._add(mix)
                return mix.id
            grouped: list[AudioMixInput] = []
            for group_index in range(0, len(current_inputs), maximum):
                group = current_inputs[group_index : group_index + maximum]
                mix = AudioMixNode(
                    id=self._id(f"{prefix}-mix-{stage}-{group_index // maximum}"),
                    inputs=tuple(item.input_id for item in group),
                    artifact_type=ArtifactType.AUDIO,
                    mix_inputs=tuple(group),
                    duration=duration,
                    sample_rate=profile.audio_sample_rate,
                    channels=profile.audio_channels,
                    channel_layout=channel_layout,
                )
                self._add(mix)
                grouped.append(
                    AudioMixInput(
                        input_id=mix.id,
                        start=RationalTime.zero(),
                        duration=duration,
                    )
                )
            current_inputs = grouped
            stage += 1

    @staticmethod
    def _subtract_ranges(base: TimeRange, exclusions: list[TimeRange]) -> list[TimeRange]:
        segments = [base]
        for exclusion in sorted(exclusions, key=lambda item: item.start):
            updated: list[TimeRange] = []
            for segment in segments:
                overlap = segment.intersection(exclusion)
                if overlap is None:
                    updated.append(segment)
                    continue
                if segment.start < overlap.start:
                    updated.append(TimeRange.from_start_end(segment.start, overlap.start))
                if overlap.end < segment.end:
                    updated.append(TimeRange.from_start_end(overlap.end, segment.end))
            segments = updated
        return segments

    @staticmethod
    def _audio_transition_sides(
        transition: Transition, profile: DeliveryProfile
    ) -> tuple[RationalTime, RationalTime]:
        if transition.alignment == "start_at_cut":
            before = RationalTime.zero()
        elif transition.alignment == "end_at_cut":
            before = transition.duration
        else:
            before = transition.duration / 2
        after = transition.duration - before
        try:
            AudioSampleTime.from_time(before, profile.audio_sample_rate, RoundingMode.EXACT)
            AudioSampleTime.from_time(after, profile.audio_sample_rate, RoundingMode.EXACT)
        except ValueError as exc:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "audio transition is not aligned to the delivery sample grid",
                context={"transition_id": transition.id},
            ) from exc
        return before, after

    def _audio_transition_source_range(
        self,
        item: AudioClip,
        before: RationalTime,
        after: RationalTime,
        *,
        side: str,
    ) -> TimeRange:
        timeline_start = item.timeline_range.duration - before if side == "left" else -before
        timeline_end = timeline_start + before + after
        source_offset_start = item.retime.source_offset_at(timeline_start)
        source_offset_end = item.retime.source_offset_at(timeline_end)
        source_range = TimeRange(
            start=(
                item.source_range.end - source_offset_end
                if item.retime.reverse
                else item.source_range.start + source_offset_start
            ),
            duration=source_offset_end - source_offset_start,
        )
        available = self._media_reference(item.media_reference_id).available_range
        if source_range.start.value < 0 or (
            available is not None
            and (source_range.start < available.start or source_range.end > available.end)
        ):
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "audio crossfade exceeds available source handles",
                context={
                    "item_id": item.id,
                    "side": side,
                    "required_source_range": source_range.model_dump(mode="json"),
                },
            )
        return source_range

    @staticmethod
    def _embedded_audio(
        sequence: Sequence, timeline_range: TimeRange
    ) -> list[tuple[Clip, TimeRange]]:
        embedded: list[tuple[Clip, TimeRange]] = []
        for track in sequence.timeline.tracks:
            if not isinstance(track, (VideoTrack, GraphicsTrack)) or not track.enabled:
                continue
            for item in track.items:
                if not isinstance(item, Clip) or not item.enabled or not item.source_audio_enabled:
                    continue
                intersection = item.timeline_range.intersection(timeline_range)
                if intersection is not None:
                    embedded.append((item, intersection))
        return embedded

    def _compile_audio_source(
        self,
        item_id: str,
        media_reference_id: str,
        source_range: TimeRange,
        effects: tuple[Effect, ...],
        profile: DeliveryProfile,
        *,
        retime: Retime | None = None,
        stream_index: int = 0,
        channel_map: list[int] | None = None,
        explicit_audio: bool,
        effect_time_offset: RationalTime | None = None,
        retime_range: TimeRange | None = None,
        fade_in: bool = False,
        fade_out: bool = False,
    ) -> str:
        prefix = _safe_id(item_id)
        media = self._media_reference(media_reference_id)
        if not self._media_has_audio(media):
            if explicit_audio:
                raise EngineError(
                    ErrorCode.MEDIA_INVALID,
                    "explicit audio clip references media without an audio stream",
                    context={"item_id": item_id, "media_id": media.id},
                )
            raise EngineError(
                ErrorCode.MEDIA_INVALID,
                "embedded source audio stream is missing",
                context={"item_id": item_id, "media_id": media.id},
            )
        source = self._resolve_media(media)
        audio_streams = [stream for stream in media.streams if stream.codec_type == "audio"]
        if audio_streams and stream_index >= len(audio_streams):
            raise EngineError(
                ErrorCode.MEDIA_INVALID,
                "requested audio stream index is missing",
                context={
                    "item_id": item_id,
                    "media_id": media.id,
                    "stream_index": stream_index,
                },
            )
        source_sample_rate = audio_streams[stream_index].sample_rate if audio_streams else None
        decode_id = self._decode_media(
            prefix=f"{prefix}-decode-audio",
            media=media,
            source=source,
            artifact_type=ArtifactType.AUDIO,
            audio_stream_index=stream_index,
        )
        trim = TrimNode(
            id=self._id(f"{prefix}-trim-audio"),
            inputs=(decode_id,),
            artifact_type=ArtifactType.AUDIO,
            source_range=source_range,
            audio_fade_in=(
                self.project.settings.audio_boundary_fade if fade_in else RationalTime.zero()
            ),
            audio_fade_out=(
                self.project.settings.audio_boundary_fade if fade_out else RationalTime.zero()
            ),
            audio_sample_rate=source_sample_rate,
            audio_rounding=RoundingMode.NEAREST,
        )
        self._add(trim)
        conform = ConformNode(
            id=self._id(f"{prefix}-conform-audio"),
            inputs=(trim.id,),
            artifact_type=ArtifactType.AUDIO,
            frame_rate=profile.frame_rate,
            sample_rate=profile.audio_sample_rate,
        )
        self._add(conform)
        current = conform.id
        if retime is not None:
            if not retime.preserve_audio_pitch and (retime.rate.fraction != 1 or retime.speed_ramp):
                raise EngineError(
                    ErrorCode.UNSUPPORTED_CAPABILITY,
                    "pitch-shifting retime is not yet supported",
                    context={"item_id": item_id},
                )
            current = self._lower_retime(
                prefix,
                current,
                retime,
                ArtifactType.AUDIO,
                timeline_offset=(
                    retime_range.start if retime_range is not None else RationalTime.zero()
                ),
                timeline_duration=(
                    retime_range.duration
                    if retime_range is not None
                    else source_range.duration / retime.rate.fraction
                ),
                profile=profile,
            )
        processors = [
            parse_audio_processor(effect, time_offset=effect_time_offset) for effect in effects
        ]
        if channel_map is not None:
            processors.insert(
                0,
                AudioProcessor(kind="channel_map", parameters={"map": channel_map}),
            )
        if not processors:
            return current
        process = AudioProcessNode(
            id=self._id(f"{prefix}-audio-process"),
            inputs=(current,),
            artifact_type=ArtifactType.AUDIO,
            processors=tuple(processors),
            sample_rate=profile.audio_sample_rate,
            channel_layout=profile.audio_channel_layout,
        )
        self._add(process)
        return process.id

    @staticmethod
    def _media_has_audio(media: MediaReference) -> bool:
        return not media.streams or any(stream.codec_type == "audio" for stream in media.streams)

    @staticmethod
    def _source_color_space(media: MediaReference, stream_index: int) -> ColorSpace:
        streams = [stream for stream in media.streams if stream.codec_type == "video"]
        if stream_index < len(streams):
            stream = streams[stream_index]
            transfer = (stream.color_transfer or "").lower()
            primaries = (stream.color_primaries or "").lower()
            if transfer in {"arib-std-b67", "hlg"}:
                return ColorSpace.HLG
            if transfer in {"smpte2084", "pq"}:
                return ColorSpace.PQ
            if primaries in {"bt2020", "bt2020nc"}:
                return ColorSpace.REC2020
        if media.hdr:
            return RenderCompiler._hdr_space(media)
        return ColorSpace.REC709

    def _media_reference(self, media_id: str) -> MediaReference:
        try:
            return self._media[media_id]
        except KeyError as exc:
            raise EngineError(
                ErrorCode.MEDIA_NOT_FOUND,
                "timeline references missing media",
                context={"media_id": media_id},
            ) from exc

    def _resolve_media(self, media: MediaReference) -> Path:
        cached = self._resolved_media_paths.get(media.id)
        if cached is not None:
            return cached
        if media.offline:
            raise EngineError(
                ErrorCode.MEDIA_NOT_FOUND,
                "media is marked offline",
                context={"media_id": media.id},
            )
        path = Path(media.uri)
        if not path.is_absolute():
            path = self.project_root / path
        path = path.resolve()
        if not path.is_file():
            raise EngineError(
                ErrorCode.MEDIA_NOT_FOUND,
                "media source does not exist",
                context={"media_id": media.id, "path": str(path)},
            )
        if media.sha256:
            stat = path.stat()
            identity = (
                path,
                stat.st_size,
                stat.st_mtime_ns,
                stat.st_ctime_ns,
                stat.st_dev,
                stat.st_ino,
            )
            actual = self._source_hashes.get(identity)
            if actual is None:
                actual, _ = self._source_identity_store.verify(path)
                self._source_hashes[identity] = actual
            if actual != media.sha256:
                raise EngineError(
                    ErrorCode.MEDIA_INVALID,
                    "media source hash does not match the project reference",
                    context={"media_id": media.id, "path": str(path)},
                )
            snapshot = self._source_identity_store.materialize_verified(
                path,
                self.config.cache_dir
                / "source-snapshots"
                / media.sha256[:2]
                / f"{media.sha256}{path.suffix.lower()}",
                expected_sha256=media.sha256,
            )
        else:
            snapshot = path
        self._resolved_media_paths[media.id] = snapshot
        return snapshot

    def _decode_media(
        self,
        *,
        prefix: str,
        media: MediaReference,
        source: Path,
        artifact_type: ArtifactType,
        video_stream_index: int | None = None,
        audio_stream_index: int | None = None,
        still_image: bool = False,
    ) -> str:
        identity = (
            source,
            artifact_type,
            video_stream_index,
            audio_stream_index,
            still_image,
            media.sha256,
        )
        existing = self._decode_nodes.get(identity)
        if existing is not None:
            return existing
        original_source = Path(media.uri)
        if not original_source.is_absolute():
            original_source = self.project_root / original_source
        decode = DecodeNode(
            id=self._id(prefix),
            artifact_type=artifact_type,
            source_uri=str(original_source.resolve()),
            snapshot_uri=str(source),
            source_sha256=media.sha256,
            still_image=still_image,
            video_stream_index=video_stream_index,
            audio_stream_index=audio_stream_index,
            stream_metadata=self._declared_stream_metadata(
                media,
                artifact_type,
                video_stream_index=video_stream_index,
                audio_stream_index=audio_stream_index,
            ),
        )
        self._add(decode)
        self._decode_nodes[identity] = decode.id
        return decode.id

    @staticmethod
    def _declared_stream_metadata(
        media: MediaReference,
        artifact_type: ArtifactType,
        *,
        video_stream_index: int | None,
        audio_stream_index: int | None,
    ) -> dict[str, JsonValue]:
        is_video = artifact_type in {ArtifactType.VIDEO, ArtifactType.IMAGE}
        stream_kind = "video" if is_video else "audio"
        index = (video_stream_index if is_video else audio_stream_index) or 0
        streams = [stream for stream in media.streams if stream.codec_type == stream_kind]
        if index >= len(streams):
            return {}
        stream = streams[index]
        metadata: dict[str, JsonValue] = {"stream": f"{'v' if is_video else 'a'}:{index}"}
        if stream.sample_rate is not None:
            metadata["sample_rate"] = stream.sample_rate
        for key, value in {
            "pix_fmt": stream.pixel_format,
            "color_primaries": stream.color_primaries,
            "color_transfer": stream.color_transfer,
            "color_space": stream.color_space,
        }.items():
            if value is not None:
                metadata[key] = value
        return metadata

    @staticmethod
    def _hdr_space(media: MediaReference) -> ColorSpace:
        transfers = {stream.color_transfer for stream in media.streams}
        if "arib-std-b67" in transfers:
            return ColorSpace.HLG
        return ColorSpace.PQ

    def _id(self, base: str) -> str:
        candidate = _safe_id(base)
        if candidate not in self._ids:
            self._ids.add(candidate)
            return candidate
        index = 2
        while f"{candidate}-{index}" in self._ids:
            index += 1
        value = f"{candidate}-{index}"
        self._ids.add(value)
        return value

    def _add(self, node: RenderNode) -> None:
        self.nodes.append(node)
