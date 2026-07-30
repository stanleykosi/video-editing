"""Provider-backed shot semantics constrained to verified frame IDs."""

from __future__ import annotations

from pathlib import Path

from editorial_brain.core.models import (
    Confidence,
    EvidenceKind,
    EvidenceRef,
    MediaUnderstandingIndex,
    ProviderEvidence,
    ShotSemantics,
)
from editorial_brain.providers.base import (
    FrameInput,
    ProviderStatus,
    VisionProvider,
    VisionRequest,
)
from editorial_brain.understanding.camera import camera_from_labels
from editorial_brain.understanding.reactions import reactions_from_labels
from editorial_brain.understanding.subjects import subjects_from_labels
from editorial_brain.understanding.visible_events import actions_from_labels


def enrich_shot_semantics(
    index: MediaUnderstandingIndex,
    provider: VisionProvider,
    *,
    instruction: str = (
        "Identify visible subjects, action, proof, reaction, cutaway value, shot scale, and "
        "camera motion. Encode observable subjects as subject:<generic label>, actions as "
        "action:<observable action>, and use only observable reaction cue labels."
    ),
) -> MediaUnderstandingIndex:
    frames = [
        FrameInput(
            candidate_id=frame.id,
            path=Path(frame.artifact_path),
            sha256=frame.sha256,
            caption=f"shot_id={shot.id}; frame_role={frame.role}",
        )
        for shot in index.shots
        for frame in shot.frames
        if frame.artifact_path is not None and frame.sha256 is not None
    ]
    if not frames:
        return index
    result = provider.inspect(
        VisionRequest(
            request_id=f"vision:{index.project_id}:{index.analysis_version}",
            task="shot_semantics",
            instruction=instruction,
            frames=frames,
        )
    )
    if result.status is ProviderStatus.UNAVAILABLE:
        current = index.extensions.get("editorial_brain:provider_unavailable", [])
        previous = [str(item) for item in current] if isinstance(current, list) else []
        unavailable = [
            *previous,
            f"{provider.provider_name}:{result.error_code or 'unavailable'}",
        ]
        return index.model_copy(
            update={
                "extensions": {
                    **index.extensions,
                    "editorial_brain:provider_unavailable": unavailable,
                }
            },
            deep=True,
        )
    if (
        result.status is not ProviderStatus.SUCCESS
        or result.output is None
        or result.evidence is None
    ):
        raise RuntimeError(result.error_message or "vision provider failed")
    by_frame = {judgment.candidate_id: judgment for judgment in result.output.judgments}
    enriched = []
    new_evidence: list[EvidenceRef] = []
    for shot in index.shots:
        judgments = [by_frame[frame.id] for frame in shot.frames if frame.id in by_frame]
        if not judgments:
            enriched.append(shot)
            continue
        labels = sorted({label for judgment in judgments for label in judgment.labels})
        summaries = [judgment.summary for judgment in judgments]
        score = sum(judgment.score for judgment in judgments) / len(judgments)
        confidence = Confidence(
            score=min(judgment.confidence.score for judgment in judgments),
            basis=EvidenceKind.MODEL_INFERRED,
            calibration="minimum_frame_judgment",
            sample_size=len(judgments),
        )
        ref = EvidenceRef(
            id=f"evidence:{shot.id}:semantics:{provider.fingerprint[:12]}",
            kind=EvidenceKind.MODEL_INFERRED,
            media_id=shot.media_id,
            media_sha256=shot.media_sha256,
            source_range=shot.source_range,
            shot_id=shot.id,
            provider_evidence=result.evidence,
            analysis_version=index.analysis_version,
            confidence=confidence,
            summary="; ".join(summaries)[:500],
        )
        semantics = ShotSemantics(
            summary="; ".join(summaries),
            search_terms=labels,
            establishing_value=_label_score(labels, {"wide", "location", "establishing"}, score),
            reaction_value=_label_score(labels, {"reaction", "smiles", "laughs", "gesture"}, score),
            evidence_value=_label_score(
                labels, {"proof", "detail", "product", "ui", "text"}, score
            ),
            cutaway_value=_label_score(labels, {"cutaway", "detail", "context", "action"}, score),
            atmosphere_value=_label_score(labels, {"atmosphere", "location", "ambient"}, score),
            text_present=bool({"text", "ui", "graphic"} & set(labels)),
            confidence=confidence,
        )
        semantic_shot = shot.model_copy(
            update={"semantics": semantics, "evidence": [*shot.evidence, ref]},
            deep=True,
        )
        enriched.append(
            semantic_shot.model_copy(
                update={
                    "subjects": subjects_from_labels(semantic_shot),
                    "actions": actions_from_labels(semantic_shot),
                    "reactions": reactions_from_labels(semantic_shot),
                    "camera": camera_from_labels(semantic_shot),
                },
                deep=True,
            )
        )
        new_evidence.append(ref)
    provider_items: list[ProviderEvidence] = [*index.provider_evidence, result.evidence]
    return index.model_copy(
        update={
            "shots": enriched,
            "evidence": index.evidence.model_copy(
                update={"refs": [*index.evidence.refs, *new_evidence]}
            ),
            "provider_evidence": provider_items,
        }
    )


def _label_score(labels: list[str], desired: set[str], fallback: float) -> float:
    normalized = {label.lower().replace(" ", "_") for label in labels}
    return fallback if normalized & desired else 0
