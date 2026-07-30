"""Action-boundary cut preference."""

from editorial_brain.core.models import CutPointCandidate


def action_cut_bonus(point: CutPointCandidate) -> float:
    return point.strength if point.kind in {"motion_start", "motion_end", "action_peak"} else 0
