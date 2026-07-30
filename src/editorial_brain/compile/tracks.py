"""Deterministic canonical track allocation."""

from typing import Any

from video_engine.api import AudioTrack, Project, VideoTrack


def editorial_track_ids(project: Project, plan_id: str) -> tuple[str, str]:
    existing = {track.id for track in project.sequence(project.active_sequence_id).timeline.tracks}
    suffix = plan_id.replace(":", "-").replace("/", "-")[-32:]
    video_id = _unique(f"editorial-brain-video-{suffix}", existing)
    existing.add(video_id)
    audio_id = _unique(f"editorial-brain-audio-{suffix}", existing)
    return video_id, audio_id


def new_tracks(video_id: str, audio_id: str, plan_id: str) -> tuple[VideoTrack, AudioTrack]:
    metadata: dict[str, Any] = {
        "editorial_brain:plan_id": plan_id,
        "editorial_brain:role": "compiled_edit",
    }
    return (
        VideoTrack(id=video_id, name="Editorial Brain Picture", extensions=metadata),
        AudioTrack(id=audio_id, name="Editorial Brain Source Audio", extensions=metadata),
    )


def _unique(base: str, existing: set[str]) -> str:
    if base not in existing:
        return base
    index = 2
    while f"{base}-{index}" in existing:
        index += 1
    return f"{base}-{index}"
