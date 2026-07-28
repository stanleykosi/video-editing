"""Canonical timeline, range, cut, audio, and caption inspection service."""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
import uuid
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from video_engine.captions.layout import validate_caption_layout
from video_engine.config import EngineConfig
from video_engine.core.schema import CaptionCue, CaptionTrack, Project, Sequence
from video_engine.core.time import RationalTime, RoundingMode, TimeRange
from video_engine.errors import EngineError, ErrorCode
from video_engine.media.probe import probe_media
from video_engine.process import CommandRunner
from video_engine.render.cache import sha256_file

from .models import (
    InspectionArtifact,
    InspectionKind,
    InspectionRequest,
    InspectionResult,
    InspectionSample,
    InspectionStatus,
)


class InspectionService:
    def __init__(
        self,
        project: Project,
        project_root: Path,
        config: EngineConfig,
        runner: CommandRunner | None = None,
    ) -> None:
        self.project = project.model_copy(deep=True)
        self.project_root = project_root.resolve()
        self.config = config.materialize(self.project_root)
        self.runner = runner or CommandRunner()

    def inspect(self, request: InspectionRequest) -> InspectionResult:
        inspection_id = f"inspection-{uuid.uuid4().hex}"
        try:
            sequence = self.project.sequence(request.sequence_id)
        except StopIteration as exc:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "inspection sequence was not found",
                context={"sequence_id": request.sequence_id},
            ) from exc
        output_dir = (
            request.output_dir.resolve()
            if request.output_dir is not None
            else self.project_root / "reports" / "inspection" / inspection_id
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        report_json = output_dir / "inspection.json"
        report_markdown = output_dir / "inspection.md"
        selected_range = self._selected_range(request, sequence)
        self._validate_range(selected_range, sequence)
        artifacts: list[InspectionArtifact] = []
        warnings: list[str] = []
        if request.media_path is not None:
            media_probe = probe_media(
                self._media(request.media_path), self.config, self.runner, deep_vfr=False
            )
            if not media_probe.audio_streams:
                warnings.append("inspection media has no audio stream; waveform is flat")
        summary: dict[str, Any] = {
            "timeline_range": selected_range.model_dump(mode="json"),
            "track_count": len(sequence.timeline.tracks),
        }
        if request.kind is InspectionKind.TIMELINE:
            artifacts.extend(
                self._timeline_artifacts(sequence, selected_range, output_dir, request)
            )
        elif request.kind is InspectionKind.RANGE:
            assert request.media_path is not None
            artifacts.extend(
                self._range_artifacts(
                    sequence,
                    selected_range,
                    self._media(request.media_path),
                    output_dir,
                    request,
                )
            )
        elif request.kind is InspectionKind.CUT:
            assert request.media_path is not None and request.cut_time is not None
            artifacts.extend(
                self._cut_artifacts(
                    sequence,
                    selected_range,
                    request.cut_time,
                    self._media(request.media_path),
                    output_dir,
                    request,
                )
            )
            summary["cut_time"] = request.cut_time.model_dump(mode="json")
        elif request.kind is InspectionKind.AUDIO:
            assert request.media_path is not None
            artifacts.extend(
                self._audio_artifacts(
                    self._media(request.media_path), selected_range, output_dir, request
                )
            )
        elif request.kind is InspectionKind.CAPTIONS:
            artifacts.extend(self._caption_artifacts(sequence, selected_range, output_dir))
        result = InspectionResult(
            inspection_id=inspection_id,
            kind=request.kind,
            project_id=self.project.id,
            project_revision=self.project.revision,
            sequence_id=sequence.id,
            status=(InspectionStatus.PARTIAL if warnings else InspectionStatus.COMPLETE),
            output_dir=output_dir,
            report_json=report_json.resolve(),
            report_markdown=report_markdown.resolve(),
            artifacts=tuple(artifacts),
            summary=summary,
            warnings=tuple(warnings),
        )
        self._write_json(report_json, result.model_dump(mode="json"))
        self._write_markdown(report_markdown, result)
        return result

    def _selected_range(self, request: InspectionRequest, sequence: Sequence) -> TimeRange:
        if request.kind is InspectionKind.CUT:
            assert request.cut_time is not None
            half = request.cut_window / 2
            start = max(RationalTime.zero(), request.cut_time - half)
            end = min(sequence.timeline.duration, request.cut_time + half)
            return TimeRange(start=start, duration=end - start)
        return request.timeline_range or TimeRange(
            start=RationalTime.zero(), duration=sequence.timeline.duration
        )

    @staticmethod
    def _validate_range(selected: TimeRange, sequence: Sequence) -> None:
        if selected.duration.value <= 0:
            raise EngineError(ErrorCode.INVALID_TIMELINE, "inspection range must be positive")
        if selected.start.value < 0 or selected.end > sequence.timeline.duration:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "inspection range lies outside the sequence",
                context={
                    "range": selected.model_dump(mode="json"),
                    "sequence_duration": sequence.timeline.duration.model_dump(mode="json"),
                },
            )

    def _timeline_artifacts(
        self,
        sequence: Sequence,
        selected: TimeRange,
        output_dir: Path,
        request: InspectionRequest,
    ) -> list[InspectionArtifact]:
        payload = self._timeline_payload(sequence, selected)
        metadata_path = output_dir / "timeline.json"
        page_ranges: list[TimeRange] = []
        cursor = selected.start
        while cursor < selected.end:
            duration = min(request.timeline_page_duration, selected.end - cursor)
            page_ranges.append(TimeRange(start=cursor, duration=duration))
            cursor = cursor + duration
        lane_pages = [
            sequence.timeline.tracks[index : index + request.max_lanes_per_page]
            for index in range(0, len(sequence.timeline.tracks), request.max_lanes_per_page)
        ] or [[]]
        payload["pages"] = [
            {
                "time_page": time_index,
                "lane_page": lane_index,
                "range": page_range.model_dump(mode="json"),
                "track_ids": [track.id for track in tracks],
            }
            for time_index, page_range in enumerate(page_ranges, start=1)
            for lane_index, tracks in enumerate(lane_pages, start=1)
        ]
        self._write_json(metadata_path, payload)
        artifacts = [
            self._artifact("timeline-data", "timeline_data", metadata_path, "application/json")
        ]
        for time_index, page_range in enumerate(page_ranges, start=1):
            for lane_index, tracks in enumerate(lane_pages, start=1):
                image_path = output_dir / (
                    f"timeline-time-{time_index:03d}-lanes-{lane_index:03d}.png"
                )
                self._draw_timeline(sequence, page_range, image_path, tracks)
                artifacts.append(
                    self._artifact(
                        f"timeline-map-{time_index}-{lane_index}",
                        "timeline_map",
                        image_path,
                        "image/png",
                    )
                )
        return artifacts

    def _range_artifacts(
        self,
        sequence: Sequence,
        selected: TimeRange,
        media: Path,
        output_dir: Path,
        request: InspectionRequest,
    ) -> list[InspectionArtifact]:
        samples = self._frame_samples(media, selected, request.frame_count)
        payload_path = output_dir / "range.json"
        payload = self._timeline_payload(
            sequence, selected, [sample.timeline_time for sample in samples]
        )
        payload["frame_samples"] = [sample.model_dump(mode="json") for sample in samples]
        self._write_json(payload_path, payload)
        artifacts = [self._artifact("range-data", "range_data", payload_path, "application/json")]
        filmstrip = self._filmstrip(media, output_dir, samples)
        audio_artifacts = self._audio_artifacts(media, selected, output_dir, request)
        artifacts.append(filmstrip)
        artifacts.extend(audio_artifacts)
        waveform = next(artifact for artifact in audio_artifacts if artifact.kind == "waveform")
        artifacts.append(
            self._inspection_contact_sheet(
                sequence,
                selected,
                output_dir,
                filmstrip,
                waveform,
                samples,
            )
        )
        return artifacts

    def _cut_artifacts(
        self,
        sequence: Sequence,
        selected: TimeRange,
        cut_time: RationalTime,
        media: Path,
        output_dir: Path,
        request: InspectionRequest,
    ) -> list[InspectionArtifact]:
        samples = self._cut_frame_samples(media, selected, cut_time, request.frame_count)
        payload = self._timeline_payload(
            sequence, selected, [sample.timeline_time for sample in samples]
        )
        payload["cut_time"] = cut_time.model_dump(mode="json")
        payload["frame_samples"] = [sample.model_dump(mode="json") for sample in samples]
        payload["adjacent_items"] = [
            {
                "track_id": track.id,
                "items": [
                    item.id
                    for item in track.items
                    if item.timeline_range.start <= cut_time <= item.timeline_range.end
                    or item.timeline_range.end == cut_time
                    or item.timeline_range.start == cut_time
                ],
            }
            for track in sequence.timeline.tracks
        ]
        path = output_dir / "cut.json"
        self._write_json(path, payload)
        artifacts = [self._artifact("cut-data", "cut_data", path, "application/json")]
        filmstrip = self._filmstrip(media, output_dir, samples)
        audio_artifacts = self._audio_artifacts(media, selected, output_dir, request)
        artifacts.append(filmstrip)
        artifacts.extend(audio_artifacts)
        waveform = next(artifact for artifact in audio_artifacts if artifact.kind == "waveform")
        artifacts.append(
            self._inspection_contact_sheet(
                sequence,
                selected,
                output_dir,
                filmstrip,
                waveform,
                samples,
            )
        )
        return artifacts

    def _audio_artifacts(
        self,
        media: Path,
        selected: TimeRange,
        output_dir: Path,
        request: InspectionRequest,
    ) -> list[InspectionArtifact]:
        media_probe = probe_media(media, self.config, self.runner, deep_vfr=False)
        if not media_probe.audio_streams:
            image_path = output_dir / "waveform.png"
            image = Image.new("RGB", (request.waveform_width, request.waveform_height), "#141518")
            draw = ImageDraw.Draw(image)
            draw.line(
                (
                    0,
                    request.waveform_height // 2,
                    request.waveform_width,
                    request.waveform_height // 2,
                ),
                fill="#FFFFFF",
            )
            image.save(image_path, "PNG", optimize=True)
            peaks_path = output_dir / "audio-peaks.json"
            self._write_json(
                peaks_path,
                {
                    "sample_rate": None,
                    "channels": 0,
                    "sample_count": 0,
                    "range": selected.model_dump(mode="json"),
                    "silence_intervals": [selected.model_dump(mode="json")],
                    "buckets": [],
                },
            )
            return [
                self._artifact("waveform", "waveform", image_path, "image/png"),
                self._artifact("audio-peaks", "audio_peaks", peaks_path, "application/json"),
            ]
        image_path = output_dir / "waveform.png"
        self.runner.run(
            [
                self.config.ffmpeg_path,
                "-v",
                "error",
                "-y",
                "-ss",
                f"{float(selected.start.fraction):.9f}",
                "-i",
                media,
                "-t",
                f"{float(selected.duration.fraction):.9f}",
                "-filter_complex",
                (
                    "aformat=channel_layouts=mono,"
                    f"showwavespic=s={request.waveform_width}x{request.waveform_height}:"
                    "colors=white:scale=sqrt"
                ),
                "-frames:v",
                "1",
                image_path,
            ]
        )
        peaks_path = output_dir / "audio-peaks.json"
        self._write_json(
            peaks_path,
            self._audio_peaks(
                media,
                selected,
                media_probe.audio_streams[0].channels or 1,
                output_dir,
                request,
            ),
        )
        return [
            self._artifact("waveform", "waveform", image_path, "image/png"),
            self._artifact("audio-peaks", "audio_peaks", peaks_path, "application/json"),
        ]

    def _audio_peaks(
        self,
        media: Path,
        selected: TimeRange,
        channels: int,
        output_dir: Path,
        request: InspectionRequest,
    ) -> dict[str, Any]:
        sample_rate = 48_000
        raw_path = output_dir / ".inspection-audio.f32le"
        result = self.runner.run(
            [
                self.config.ffmpeg_path,
                "-v",
                "error",
                "-y",
                "-ss",
                f"{float(selected.start.fraction):.9f}",
                "-i",
                media,
                "-t",
                f"{float(selected.duration.fraction):.9f}",
                "-map",
                "0:a:0",
                "-ac",
                str(channels),
                "-ar",
                str(sample_rate),
                "-c:a",
                "pcm_f32le",
                "-f",
                "f32le",
                raw_path,
            ],
            check=False,
        )
        if result.return_code != 0 or not raw_path.is_file():
            raise EngineError(
                ErrorCode.EXTERNAL_TOOL,
                "FFmpeg failed to decode inspection audio",
                context={"stderr_tail": result.stderr[-2000:]},
            )
        samples = np.fromfile(raw_path, dtype="<f4")
        raw_path.unlink(missing_ok=True)
        frames = samples[: samples.size - samples.size % channels].reshape(-1, channels)
        bucket_size = max(1, math.ceil(len(frames) / request.peak_buckets))
        buckets: list[dict[str, Any]] = []
        for index, offset in enumerate(range(0, len(frames), bucket_size)):
            chunk = frames[offset : offset + bucket_size]
            buckets.append(
                {
                    "index": index,
                    "start_sample": offset,
                    "peak": np.max(np.abs(chunk), axis=0).round(7).tolist(),
                    "rms": np.sqrt(np.mean(np.square(chunk), axis=0)).round(7).tolist(),
                }
            )
        silence_result = self.runner.run(
            [
                self.config.ffmpeg_path,
                "-hide_banner",
                "-nostats",
                "-ss",
                f"{float(selected.start.fraction):.9f}",
                "-i",
                media,
                "-t",
                f"{float(selected.duration.fraction):.9f}",
                "-map",
                "0:a:0",
                "-af",
                (
                    f"silencedetect=noise={request.silence_noise_db}dB:"
                    f"d={float(request.silence_min_duration.fraction):.9f}"
                ),
                "-vn",
                "-f",
                "null",
                "-",
            ],
            check=False,
        )
        silence_starts = [
            float(value)
            for value in re.findall(r"silence_start:\s*([0-9.]+)", silence_result.stderr)
        ]
        silence_ends = [
            float(value) for value in re.findall(r"silence_end:\s*([0-9.]+)", silence_result.stderr)
        ]
        return {
            "sample_rate": sample_rate,
            "channels": channels,
            "sample_count": len(frames),
            "range": selected.model_dump(mode="json"),
            "absolute_peak": (
                np.max(np.abs(frames), axis=0).round(7).tolist() if len(frames) else []
            ),
            "rms": (
                np.sqrt(np.mean(np.square(frames), axis=0)).round(7).tolist() if len(frames) else []
            ),
            "silence_intervals": [
                {
                    "start": start_value,
                    "end": end_value,
                    "duration": end_value - start_value,
                }
                for start_value, end_value in zip(silence_starts, silence_ends, strict=False)
            ],
            "buckets": buckets,
        }

    def _caption_artifacts(
        self, sequence: Sequence, selected: TimeRange, output_dir: Path
    ) -> list[InspectionArtifact]:
        width = sequence.settings_override.width or self.project.settings.width
        height = sequence.settings_override.height or self.project.settings.height
        tracks = [
            track
            for track in sequence.timeline.tracks
            if isinstance(track, CaptionTrack) and track.enabled
        ]
        cues = [
            {"track_id": track.id, **cue.model_dump(mode="json")}
            for track in tracks
            for cue in track.items
            if isinstance(cue, CaptionCue)
            and cue.enabled
            and not cue.suppressed
            and cue.timeline_range.overlaps(selected)
        ]
        data_path = output_dir / "captions.json"
        image_path = output_dir / "caption-map.png"
        self._write_json(
            data_path,
            {
                "range": selected.model_dump(mode="json"),
                "cue_count": len(cues),
                "cues": cues,
                "tracks": [
                    {
                        "id": track.id,
                        "name": track.name,
                        "language": track.language,
                        "default_style_id": track.default_style_id,
                        "collision_regions": [
                            region.model_dump(mode="json")
                            for region in track.collision_regions
                            if region.timeline_range.overlaps(selected)
                        ],
                        "layout": validate_caption_layout(
                            track,
                            self.project.caption_styles,
                            width=width,
                            height=height,
                            config=self.config,
                        ).model_dump(mode="json"),
                    }
                    for track in tracks
                ],
            },
        )
        self._draw_caption_map(cues, selected, image_path)
        return [
            self._artifact("caption-data", "caption_data", data_path, "application/json"),
            self._artifact("caption-map", "caption_map", image_path, "image/png"),
        ]

    def _filmstrip(
        self,
        media: Path,
        output_dir: Path,
        samples: list[InspectionSample],
    ) -> InspectionArtifact:
        columns = min(4, len(samples))
        rows = math.ceil(len(samples) / columns)
        path = output_dir / "filmstrip.png"
        expression = "+".join(f"eq(n\\,{sample.frame_index})" for sample in samples)
        result = self.runner.run(
            [
                self.config.ffmpeg_path,
                "-v",
                "error",
                "-y",
                "-i",
                media,
                "-vf",
                (
                    f"select='{expression}',"
                    "scale=320:-2,"
                    f"tile={columns}x{rows}:padding=4:margin=4:color=black"
                ),
                "-frames:v",
                "1",
                path,
            ],
            check=False,
        )
        if result.return_code != 0 or not path.is_file():
            raise EngineError(
                ErrorCode.EXTERNAL_TOOL,
                "FFmpeg failed to generate inspection filmstrip",
                context={"stderr_tail": result.stderr[-2000:]},
            )
        return self._artifact("filmstrip", "filmstrip", path, "image/png")

    def _inspection_contact_sheet(
        self,
        sequence: Sequence,
        selected: TimeRange,
        output_dir: Path,
        filmstrip: InspectionArtifact,
        waveform: InspectionArtifact,
        samples: list[InspectionSample],
    ) -> InspectionArtifact:
        filmstrip_image = Image.open(filmstrip.path).convert("RGB")
        waveform_image = Image.open(waveform.path).convert("RGB")
        cues = [
            (track.id, cue)
            for track in sequence.timeline.tracks
            if isinstance(track, CaptionTrack) and track.enabled
            for cue in track.items
            if isinstance(cue, CaptionCue)
            and cue.enabled
            and not cue.suppressed
            and cue.timeline_range.overlaps(selected)
        ]
        displayed_cues = cues[:12]
        width = max(filmstrip_image.width, waveform_image.width, 960)
        header_height = 72
        gap = 12
        caption_height = 24 + len(displayed_cues) * 18 if displayed_cues else 0
        height = (
            header_height
            + filmstrip_image.height
            + gap
            + waveform_image.height
            + caption_height
            + 20
        )
        image = Image.new("RGB", (width, height), "#141518")
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()
        draw.text((16, 14), f"{sequence.name} inspection", fill="#FFFFFF", font=font)
        sample_labels = ", ".join(
            f"{float(sample.timeline_time.fraction):.3f}s" for sample in samples
        )
        draw.text(
            (16, 34),
            (
                f"{float(selected.start.fraction):.3f}s to "
                f"{float(selected.end.fraction):.3f}s | frames: {sample_labels}"
            ),
            fill="#AAB0B8",
            font=font,
        )
        filmstrip_x = (width - filmstrip_image.width) // 2
        image.paste(filmstrip_image, (filmstrip_x, header_height))
        waveform_y = header_height + filmstrip_image.height + gap
        waveform_x = (width - waveform_image.width) // 2
        image.paste(waveform_image, (waveform_x, waveform_y))
        if displayed_cues:
            text_y = waveform_y + waveform_image.height + 12
            draw.text((16, text_y), "Caption cues", fill="#D6A53A", font=font)
            for index, (track_id, cue) in enumerate(displayed_cues, start=1):
                cue_start = float(cue.timeline_range.start.fraction)
                cue_end = float(cue.timeline_range.end.fraction)
                label = f"{cue_start:.3f}-{cue_end:.3f}s [{track_id}] {cue.text}"
                draw.text((16, text_y + index * 18), label, fill="#FFFFFF", font=font)
        path = output_dir / "inspection-contact-sheet.png"
        image.save(path, "PNG", optimize=True)
        return self._artifact(
            "inspection-contact-sheet",
            "inspection_contact_sheet",
            path,
            "image/png",
        )

    def _frame_samples(
        self, media: Path, selected: TimeRange, requested: int
    ) -> list[InspectionSample]:
        media_probe = probe_media(media, self.config, self.runner, deep_vfr=False)
        if not media_probe.video_streams:
            raise EngineError(
                ErrorCode.MEDIA_INVALID,
                "filmstrip inspection requires a video stream",
                context={"path": str(media)},
            )
        rate = media_probe.video_streams[0].average_frame_rate
        if rate is None:
            raise EngineError(
                ErrorCode.MEDIA_INVALID,
                "video frame rate is unavailable for exact inspection sampling",
                context={"path": str(media)},
            )
        first = rate.time_to_frames(selected.start, RoundingMode.CEIL)
        end_exclusive = rate.time_to_frames(selected.end, RoundingMode.CEIL)
        available = end_exclusive - first
        if available <= 0:
            raise EngineError(
                ErrorCode.INVALID_TIMELINE,
                "inspection range contains no video frames",
            )
        count = min(requested, available)
        if count == 1:
            indices = [first + available // 2]
        else:
            indices = [first + (index * available) // count for index in range(count)]
        return [
            InspectionSample(
                frame_index=frame_index,
                timeline_time=rate.frames_to_time(frame_index),
            )
            for frame_index in indices
        ]

    def _cut_frame_samples(
        self,
        media: Path,
        selected: TimeRange,
        cut_time: RationalTime,
        requested: int,
    ) -> list[InspectionSample]:
        samples = self._frame_samples(media, selected, requested)
        media_probe = probe_media(media, self.config, self.runner, deep_vfr=False)
        rate = media_probe.video_streams[0].average_frame_rate
        assert rate is not None
        cut_frame = rate.time_to_frames(cut_time, RoundingMode.CEIL)
        exact = [
            InspectionSample(
                frame_index=frame_index,
                timeline_time=rate.frames_to_time(frame_index),
            )
            for frame_index in range(max(0, cut_frame - 2), cut_frame + 2)
            if selected.contains(rate.frames_to_time(frame_index))
        ]
        return sorted(
            {sample.frame_index: sample for sample in [*samples, *exact]}.values(),
            key=lambda sample: sample.frame_index,
        )

    def _timeline_payload(
        self,
        sequence: Sequence,
        selected: TimeRange,
        sample_times: list[RationalTime] | None = None,
    ) -> dict[str, Any]:
        tracks: list[dict[str, Any]] = []
        for track in sequence.timeline.tracks:
            item_by_id = {item.id: item for item in track.items}
            transitions: list[dict[str, Any]] = []
            for transition in getattr(track, "transitions", []):
                left = item_by_id.get(transition.from_item_id)
                if left is None:
                    continue
                cut = left.timeline_range.end
                if transition.alignment == "start_at_cut":
                    start = cut
                elif transition.alignment == "end_at_cut":
                    start = cut - transition.duration
                else:
                    start = cut - transition.duration / 2
                window = TimeRange(start=start, duration=transition.duration)
                transitions.append(
                    {
                        **transition.model_dump(mode="json"),
                        "cut_time": cut.model_dump(mode="json"),
                        "timeline_range": window.model_dump(mode="json"),
                    }
                )
            transitions = [
                transition
                for transition in transitions
                if TimeRange.model_validate(transition["timeline_range"]).overlaps(selected)
            ]
            tracks.append(
                {
                    "id": track.id,
                    "name": track.name,
                    "track_type": track.track_type,
                    "enabled": track.enabled,
                    "locked": track.locked,
                    "items": [
                        self._item_payload(item, sample_times or [])
                        for item in track.items
                        if item.timeline_range.overlaps(selected)
                    ],
                    "transitions": transitions,
                }
            )
        return {
            "sequence_id": sequence.id,
            "sequence_revision": sequence.revision,
            "range": selected.model_dump(mode="json"),
            "tracks": tracks,
            "markers": [
                marker.model_dump(mode="json")
                for marker in sequence.timeline.markers
                if selected.contains(marker.time)
            ],
            "link_groups": [
                group.model_dump(mode="json") for group in sequence.timeline.link_groups
            ],
            "audio_buses": [bus.model_dump(mode="json") for bus in sequence.timeline.audio_buses],
        }

    @staticmethod
    def _item_payload(item: Any, sample_times: list[RationalTime]) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": item.id,
            "name": item.name,
            "item_type": item.item_type,
            "enabled": item.enabled,
            "timeline_range": item.timeline_range.model_dump(mode="json"),
            "canonical": item.model_dump(mode="json"),
        }
        if not hasattr(item, "source_range") or not hasattr(item, "retime"):
            payload["source_mappings"] = []
            return payload
        mappings: list[dict[str, Any]] = []
        for timeline_time in sample_times:
            if not item.timeline_range.contains(timeline_time):
                continue
            offset = (timeline_time - item.timeline_range.start) * item.retime.rate.fraction
            source_time = (
                item.source_range.end - offset
                if item.retime.reverse
                else item.source_range.start + offset
            )
            mappings.append(
                {
                    "timeline_time": timeline_time.model_dump(mode="json"),
                    "source_time": source_time.model_dump(mode="json"),
                }
            )
        payload["source_mappings"] = mappings
        return payload

    def _draw_timeline(
        self,
        sequence: Sequence,
        selected: TimeRange,
        path: Path,
        tracks: list[Any] | None = None,
    ) -> None:
        visible_tracks = tracks if tracks is not None else list(sequence.timeline.tracks)
        label_width = 220
        plot_width = 1380
        lane_height = 64
        header = 72
        height = header + max(1, len(visible_tracks)) * lane_height + 36
        image = Image.new("RGB", (label_width + plot_width + 24, height), "#141518")
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()
        draw.text(
            (16, 16),
            f"{sequence.name}  revision {sequence.revision}",
            fill="#FFFFFF",
            font=font,
        )
        draw.text(
            (16, 36),
            f"{float(selected.start.fraction):.3f}s to {float(selected.end.fraction):.3f}s",
            fill="#AAB0B8",
            font=font,
        )
        colors = {
            "video": "#3A78C2",
            "audio": "#2F9D68",
            "caption": "#D6A53A",
            "graphics": "#A85DB5",
            "adjustment": "#68727F",
        }
        duration = float(selected.duration.fraction)
        for index, track in enumerate(visible_tracks):
            y = header + index * lane_height
            draw.rectangle((8, y, label_width + plot_width, y + lane_height - 4), fill="#202228")
            draw.text((16, y + 12), track.name, fill="#FFFFFF", font=font)
            draw.text((16, y + 30), f"{track.track_type}  {track.id}", fill="#9EA6B0", font=font)
            for item in track.items:
                visible = item.timeline_range.intersection(selected)
                if visible is None:
                    continue
                x0 = label_width + round(
                    float((visible.start - selected.start).fraction) / duration * plot_width
                )
                x1 = label_width + round(
                    float((visible.end - selected.start).fraction) / duration * plot_width
                )
                fill = colors.get(str(track.track_type), "#5E6773")
                draw.rectangle((x0, y + 8, max(x0 + 2, x1), y + lane_height - 12), fill=fill)
                draw.text((x0 + 4, y + 20), item.id[:24], fill="#FFFFFF", font=font)
        for marker in sequence.timeline.markers:
            if selected.start <= marker.time <= selected.end:
                x = label_width + round(
                    float((marker.time - selected.start).fraction) / duration * plot_width
                )
                draw.line((x, header - 8, x, height - 20), fill="#F15B5B", width=2)
                draw.text((x + 3, header - 20), marker.name or marker.id, fill="#F15B5B", font=font)
        image.save(path, "PNG", optimize=True)

    def _draw_caption_map(
        self, cues: list[dict[str, Any]], selected: TimeRange, path: Path
    ) -> None:
        width = 1600
        row_height = 48
        height = 80 + max(1, len(cues)) * row_height
        image = Image.new("RGB", (width, height), "#141518")
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()
        draw.text((16, 16), "Caption cue map", fill="#FFFFFF", font=font)
        duration = float(selected.duration.fraction)
        for index, cue in enumerate(cues):
            timeline_range = TimeRange.model_validate(cue["timeline_range"])
            visible = timeline_range.intersection(selected)
            if visible is None:
                continue
            y = 60 + index * row_height
            x0 = 180 + round(float((visible.start - selected.start).fraction) / duration * 1380)
            x1 = 180 + round(float((visible.end - selected.start).fraction) / duration * 1380)
            draw.text((12, y + 12), str(cue["track_id"])[:22], fill="#AAB0B8", font=font)
            draw.rectangle((x0, y + 6, max(x0 + 2, x1), y + 38), fill="#D6A53A")
            draw.text((x0 + 4, y + 15), str(cue["text"])[:80], fill="#111111", font=font)
        image.save(path, "PNG", optimize=True)

    def _media(self, path: Path) -> Path:
        resolved = path.resolve()
        if not resolved.is_file():
            raise EngineError(
                ErrorCode.MEDIA_NOT_FOUND,
                "inspection media does not exist",
                context={"path": str(resolved)},
            )
        return resolved

    @staticmethod
    def _write_json(path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(path)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise EngineError(
                ErrorCode.STORAGE,
                "failed to write inspection artifact",
                context={"path": str(path), "detail": str(exc)},
            ) from exc

    @staticmethod
    def _write_markdown(path: Path, result: InspectionResult) -> None:
        lines = [
            "# Inspection Report",
            "",
            f"- Inspection: `{result.inspection_id}`",
            f"- Kind: `{result.kind.value}`",
            f"- Status: `{result.status.value}`",
            f"- Project: `{result.project_id}` revision {result.project_revision}",
            f"- Sequence: `{result.sequence_id}`",
            "",
            "## Artifacts",
            "",
        ]
        lines.extend(
            f"- `{artifact.kind}`: `{artifact.path}` (sha256 `{artifact.sha256}`)"
            for artifact in result.artifacts
        )
        if result.warnings:
            lines.extend(["", "## Warnings", ""])
            lines.extend(f"- {warning}" for warning in result.warnings)
        lines.append("")
        InspectionService._atomic_text(path, "\n".join(lines))

    @staticmethod
    def _atomic_text(path: Path, content: str) -> None:
        descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(path)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise EngineError(
                ErrorCode.STORAGE,
                "failed to write inspection report",
                context={"path": str(path), "detail": str(exc)},
            ) from exc

    @staticmethod
    def _artifact(artifact_id: str, kind: str, path: Path, media_type: str) -> InspectionArtifact:
        return InspectionArtifact(
            id=artifact_id,
            kind=kind,
            path=path.resolve(),
            sha256=sha256_file(path),
            size_bytes=path.stat().st_size,
            media_type=media_type,
        )
