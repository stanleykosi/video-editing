"""Brief normalization without inventing creative requirements."""

from editorial_brain.core.models import EditorialBrief


def normalize_brief(brief: EditorialBrief) -> EditorialBrief:
    objective = " ".join(brief.objective.split())
    audience = " ".join(brief.audience.split())
    if not objective:
        raise ValueError("editorial objective cannot be blank")
    return brief.model_copy(update={"objective": objective, "audience": audience})
