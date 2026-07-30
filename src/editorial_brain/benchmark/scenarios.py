"""Ten explicit golden editorial scenario specifications."""

from pydantic import Field

from editorial_brain.core.models import BrainModel, EditorialProfile, WorkflowModifier


class GoldenScenario(BrainModel):
    id: str
    title: str
    profile: EditorialProfile
    modifiers: list[WorkflowModifier] = Field(default_factory=list)
    expected_behaviors: list[str] = Field(min_length=1)


SCENARIOS = [
    GoldenScenario(
        id="interview",
        title="Interview",
        profile=EditorialProfile.DIALOGUE,
        modifiers=[WorkflowModifier.INTERVIEW],
        expected_behaviors=[
            "dead_space_tightened",
            "reaction_preserved",
            "no_cut_inside_word",
            "natural_cadence",
        ],
    ),
    GoldenScenario(
        id="podcast_clip",
        title="Podcast Clip",
        profile=EditorialProfile.DIALOGUE,
        modifiers=[WorkflowModifier.PODCAST_CLIP],
        expected_behaviors=["coherent_context", "dialogue_cover", "motivated_j_l_cut"],
    ),
    GoldenScenario(
        id="narration_animal",
        title="Narration-Driven Animal Video",
        profile=EditorialProfile.NARRATION,
        modifiers=[WorkflowModifier.FACELESS_NARRATION],
        expected_behaviors=["named_subject_match", "minimum_reveal_hold", "no_repetition"],
    ),
    GoldenScenario(
        id="recap",
        title="Recap",
        profile=EditorialProfile.NARRATION,
        modifiers=[WorkflowModifier.RECAP],
        expected_behaviors=["event_scene_match", "story_order", "selective_fragments"],
    ),
    GoldenScenario(
        id="product_advertisement",
        title="Product Advertisement",
        profile=EditorialProfile.NARRATION,
        modifiers=[WorkflowModifier.ADVERTISEMENT, WorkflowModifier.PRODUCT_VIDEO],
        expected_behaviors=["benefit_proof", "detail_closeup", "product_visibility"],
    ),
    GoldenScenario(
        id="music_montage",
        title="Music Montage",
        profile=EditorialProfile.MONTAGE,
        expected_behaviors=["musical_structure", "non_mechanical_beats", "visual_progression"],
    ),
    GoldenScenario(
        id="multicam_conversation",
        title="Multi-Camera Conversation",
        profile=EditorialProfile.DIALOGUE,
        expected_behaviors=["measured_sync", "speaker_reaction_choice", "non_mechanical_switching"],
    ),
    GoldenScenario(
        id="long_form_documentary",
        title="Long-Form Documentary",
        profile=EditorialProfile.NEUTRAL,
        modifiers=[WorkflowModifier.DOCUMENTARY, WorkflowModifier.LONG_FORM],
        expected_behaviors=["beat_structure", "long_range_continuity", "slower_sections"],
    ),
    GoldenScenario(
        id="intentional_long_hold",
        title="Intentional Long Hold",
        profile=EditorialProfile.NEUTRAL,
        expected_behaviors=["do_not_cut", "protected_hold", "no_fast_bias"],
    ),
    GoldenScenario(
        id="reference_led",
        title="Reference-Led Edit",
        profile=EditorialProfile.NEUTRAL,
        expected_behaviors=["measured_reference_grammar", "pacing_prior", "no_sequence_copy"],
    ),
]
