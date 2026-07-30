"""Revision-checked TimelinePatch compiler."""

from __future__ import annotations

from editorial_brain.compile.operations import operation_payloads
from editorial_brain.compile.tracks import editorial_track_ids, new_tracks
from editorial_brain.core.models import EditorialPlan
from video_engine.api import Project, TimelinePatch


def compile_patch(
    project: Project, plan: EditorialPlan
) -> tuple[TimelinePatch, dict[str, list[int]]]:
    if plan.project_id != project.id:
        raise ValueError("editorial plan targets a different engine project")
    if plan.project_revision != project.revision:
        raise ValueError(
            "editorial plan revision conflict: "
            f"expected {plan.project_revision}, actual {project.revision}"
        )
    video_id, audio_id = editorial_track_ids(project, plan.id)
    video_track, audio_track = new_tracks(video_id, audio_id, plan.id)
    payloads, decision_map = operation_payloads(project, plan, video_id, audio_id)
    operations: list[dict[str, object]] = [
        {"operation": "add_track", "track": video_track},
    ]
    if any(stream.codec_type == "audio" for media in project.media for stream in media.streams):
        operations.append({"operation": "add_track", "track": audio_track})
    offset = len(operations)
    operations.extend(payloads)
    adjusted = {
        decision_id: [index + offset for index in indexes]
        for decision_id, indexes in decision_map.items()
    }
    patch = TimelinePatch.model_validate(
        {
            "patch_id": f"editorial-brain-{plan.id}",
            "sequence_id": project.active_sequence_id,
            "expected_project_revision": project.revision,
            "operations": operations,
            "metadata": {
                "editorial_brain:plan_id": plan.id,
                "editorial_brain:fingerprint": plan.deterministic_fingerprint,
                "editorial_brain:policy_id": plan.policy_id,
            },
        }
    )
    return patch, adjusted
