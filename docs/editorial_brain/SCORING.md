# Editorial Brain Scoring

Hard constraints run first: valid media/ranges, word-safe edges, handles,
locks, required/excluded material, ordering, and engine feasibility.

Accepted cuts retain individual dimensions for semantic completeness, story,
visual relevance, visual/action/screen/scale/composition/motion continuity,
audio/speech integrity, reaction/emotion preservation, rhythm, density,
novelty, quality, handles, profile fit, and feasibility. A typed policy owns
weights and thresholds. Measured, derived, and provider scores remain separate
inputs to the aggregate.

Assembly scoring adds beat coverage, duration error, diversity, repetition,
pacing-curve fit, audio relationships and mandatory constraints. Deterministic
tie-breaking uses stable candidate ID order.

Select scoring exposes semantic relevance, clarity, action completion,
quality, reaction, proof, novelty and repetition. Cut scoring normalizes the
twenty documented dimensions through `CutScoringPolicy`; hard rejection forces
the aggregate to zero. Model judgments and deterministic measurements remain
separate fields.

Beam search uses memoized pair continuity and merged rational source intervals.
Full assembly weights are coverage (0.27), selects (0.20), continuity (0.13),
pacing (0.13), duration (0.12), diversity (0.10), and AV relationship (0.05),
with explicit repetition and constraint deductions. Variants are re-ranked
after fine-cut, AV, picture-role, transition, and rhythm passes.
