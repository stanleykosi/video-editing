"""Brain-side source and engine compatibility gates."""

from pathlib import Path

from editorial_brain.core.models import EditorialPlan
from video_engine.api import Project, TimelinePatch, VideoEngine


def validate_plan_sources(project: Project, plan: EditorialPlan) -> None:
    media = {item.id: item for item in project.media}
    for segment in plan.assembly.segments:
        reference = media.get(segment.media_id)
        if reference is None:
            raise ValueError(f"plan references missing media {segment.media_id!r}")
        if reference.sha256 != segment.media_sha256:
            raise ValueError(f"plan media hash mismatch for {segment.media_id!r}")
        if reference.available_range is None:
            raise ValueError(f"media {segment.media_id!r} has no available source range")
        if (
            segment.source_range.start < reference.available_range.start
            or segment.source_range.end > reference.available_range.end
        ):
            raise ValueError(f"segment {segment.id!r} exceeds canonical source bounds")
    if plan.narration_media_id is not None:
        narration = media.get(plan.narration_media_id)
        if narration is None:
            raise ValueError("narration media is missing from the canonical project")
        if not any(stream.codec_type == "audio" for stream in narration.streams):
            raise ValueError("narration media has no canonical audio stream")
        if plan.narration_source_range is None or narration.available_range is None:
            raise ValueError("narration plan requires a verified source range")
        if (
            plan.narration_source_range.start < narration.available_range.start
            or plan.narration_source_range.end > narration.available_range.end
        ):
            raise ValueError("narration source range exceeds canonical media bounds")


def apply_and_validate(project_root: Path | str, project: Project, patch: TimelinePatch) -> Project:
    root = Path(project_root)
    engine = VideoEngine(root)
    editor = engine.editor(project)
    editor.apply_patch(patch)
    engine.validate_project(editor.project)
    return editor.project
