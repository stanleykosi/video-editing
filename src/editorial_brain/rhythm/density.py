"""Information-density measurements."""

from editorial_brain.core.models import Shot, Transcript


def information_density(shot: Shot, transcripts: list[Transcript]) -> float:
    word_count = sum(
        shot.source_range.overlaps(word.source_range)
        for transcript in transcripts
        if transcript.media_id == shot.media_id
        for word in transcript.words
    )
    seconds = max(float(shot.source_range.duration.fraction), 0.001)
    speech_density = min(1, word_count / seconds / 4)
    semantic_density = min(1, len(shot.semantics.search_terms) / 8)
    return speech_density * 0.6 + semantic_density * 0.4
