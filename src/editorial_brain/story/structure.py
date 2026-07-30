"""Story ordering, evidence-backed repetition refinement, and coverage."""

import re

from editorial_brain.core.models import StoryMap


def topological_beat_ids(story: StoryMap) -> list[str]:
    dependencies = {beat.id: set(beat.must_follow) for beat in story.beats}
    order: list[str] = []
    while dependencies:
        ready = sorted(beat_id for beat_id, required in dependencies.items() if not required)
        if not ready:
            raise ValueError("story beat dependencies contain a cycle")
        for beat_id in ready:
            order.append(beat_id)
            dependencies.pop(beat_id)
            for required in dependencies.values():
                required.discard(beat_id)
    return order


def missing_mandatory_beats(story: StoryMap, covered: set[str]) -> list[str]:
    return [beat.id for beat in story.beats if beat.mandatory and beat.id not in covered]


def refine_story_map(story: StoryMap) -> StoryMap:
    """Remove only optional, proven duplicate/false-start beats."""
    retained = []
    seen: set[str] = set()
    removed: set[str] = set()
    for beat in story.beats:
        normalized = re.sub(r"[^a-z0-9]+", " ", (beat.source_text or beat.purpose).lower()).strip()
        removable = beat.source_phrase_kind == "false_start" or (
            beat.source_phrase_kind == "repeated_attempt" and normalized in seen
        )
        if not beat.mandatory and removable:
            removed.add(beat.id)
            continue
        retained.append(beat)
        seen.add(normalized)
    if not removed:
        return story
    retained_ids = {beat.id for beat in retained}
    rewritten = []
    previous_id: str | None = None
    for beat in retained:
        dependencies = [item for item in beat.must_follow if item in retained_ids]
        if not dependencies and previous_id is not None:
            dependencies = [previous_id]
        rewritten.append(beat.model_copy(update={"must_follow": dependencies}, deep=True))
        previous_id = beat.id
    return story.model_copy(update={"beats": rewritten}, deep=True)
