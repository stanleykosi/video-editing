"""Explicit do-not-cut reaction policy."""

from editorial_brain.core.models import Shot
from editorial_brain.understanding.reactions import protection_window
from video_engine.api import RationalTime


def reaction_cut_rejection(shot: Shot, cut_time: RationalTime) -> str | None:
    for reaction in shot.reactions:
        if reaction.salience >= 0.6 and protection_window(reaction).contains(cut_time):
            return "protected_reaction_window"
    return None
