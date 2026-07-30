"""Cross-model editorial integrity validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from editorial_brain.core.models import EditorialPlan, MediaUnderstandingIndex


class EditorialValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    message: str
    path: str
    blocking: bool = True


class EditorialValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    issues: list[EditorialValidationIssue] = Field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not any(issue.blocking for issue in self.issues)


def validate_plan_against_index(
    plan: EditorialPlan, index: MediaUnderstandingIndex
) -> EditorialValidationReport:
    issues: list[EditorialValidationIssue] = []
    media_hashes = index.media_hashes
    beat_ids = {beat.id for beat in plan.story.beats}
    select_ids = {
        segment.select_id
        for assembly in [plan.assembly, *plan.alternatives]
        for segment in assembly.segments
    }
    cut_ids = {cut.id for cut in plan.cut_candidates}
    point_ids = {point.id for point in plan.cut_points}
    for position, segment in enumerate(plan.assembly.segments):
        if segment.beat_id not in beat_ids:
            issues.append(
                EditorialValidationIssue(
                    code="missing_beat",
                    message=f"segment references missing beat {segment.beat_id!r}",
                    path=f"assembly.segments.{position}.beat_id",
                )
            )
        expected_hash = media_hashes.get(segment.media_id)
        if expected_hash is None:
            issues.append(
                EditorialValidationIssue(
                    code="missing_media",
                    message=f"segment references unanalyzed media {segment.media_id!r}",
                    path=f"assembly.segments.{position}.media_id",
                )
            )
        elif expected_hash != segment.media_sha256:
            issues.append(
                EditorialValidationIssue(
                    code="media_hash_mismatch",
                    message=f"segment media hash does not match analysis for {segment.media_id!r}",
                    path=f"assembly.segments.{position}.media_sha256",
                )
            )
    for position, decision in enumerate(plan.decisions):
        if (
            decision.selected_id
            and decision.kind == "select"
            and decision.selected_id not in select_ids
        ):
            issues.append(
                EditorialValidationIssue(
                    code="orphan_select_decision",
                    message=f"decision selects unknown assembly select {decision.selected_id!r}",
                    path=f"decisions.{position}.selected_id",
                )
            )
    missing_beats = {beat.id for beat in plan.story.beats if beat.mandatory} - set(
        plan.assembly.covered_beat_ids
    )
    for beat_id in sorted(missing_beats):
        issues.append(
            EditorialValidationIssue(
                code="missing_required_beat",
                message=f"assembly omits mandatory beat {beat_id!r}",
                path="assembly.covered_beat_ids",
            )
        )
    for position, cut_id in enumerate(plan.assembly.cut_ids):
        if cut_id not in cut_ids:
            issues.append(
                EditorialValidationIssue(
                    code="missing_cut_candidate",
                    message=f"assembly references unknown cut {cut_id!r}",
                    path=f"assembly.cut_ids.{position}",
                )
            )
    expected_cut_count = max(0, len(plan.assembly.segments) - 1)
    if len(plan.assembly.cut_ids) != expected_cut_count:
        issues.append(
            EditorialValidationIssue(
                code="cut_count_mismatch",
                message="assembly must contain one selected cut per adjacent segment boundary",
                path="assembly.cut_ids",
            )
        )
    for position, cut in enumerate(plan.cut_candidates):
        referenced = [cut.in_point_id, cut.out_point_id]
        if any(point_id is not None and point_id not in point_ids for point_id in referenced):
            issues.append(
                EditorialValidationIssue(
                    code="missing_cut_point",
                    message=f"cut {cut.id!r} references an unknown structural point",
                    path=f"cut_candidates.{position}",
                )
            )
    if plan.narration_media_id is not None and plan.narration_media_id not in media_hashes:
        issues.append(
            EditorialValidationIssue(
                code="missing_narration_analysis",
                message="narration media is absent from the evidence index",
                path="narration_media_id",
            )
        )
    return EditorialValidationReport(issues=issues)
