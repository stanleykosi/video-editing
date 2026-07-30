# Editorial Brain Benchmarks

Reports separate technical correctness, expected editorial behavior, and
subjective review areas. Required technical metrics include invalid ranges,
cuts inside words, missing beats, duration error, duplicate usage, continuity,
visual requirement match, reaction preservation, AV alignment, must-use/
must-exclude coverage, patch validation, engine compile success and deterministic
repeatability.

`video-brain benchmark` runs every scenario through actual selects, structural
cut generation, multi-variant planning, a second identical planning run,
transactional patch compilation, project validation and render-DAG
compilation. It does not merely validate fixture descriptions.

Annotated goldens additionally report select top-K recall, cut-window accuracy,
candidate rank, expected J/L choice and expected reaction hold. Synthetic scores
are not described as human-level editing performance.

Each scenario also emits named behavior gates for cadence/reaction coverage,
narration reveal timing, recap order/selective fragments, product proof,
non-mechanical music structure, measured multicamera sync, documentary
breathing room, intentional no-cut holds, and reference-prior application. The
multicamera fixture contains two synchronized media references; the
reference-led fixture supplies a separate measured grammar profile.

The final ten-scenario run passed every technical and expected-behavior gate
with deterministic fingerprint
`ab5598dd00db633b9a4dea0bd6d07234fbe8f95cdbd495b90970f5d41e729914`.
On the final validation run, the four-hour transcript index completed in
1.48s, hundreds-of-beats beam search in 3.02s, the thousand-document
index/search fixture in 0.11s, and 1,000 checksum-validated cache reuses in
0.79s. These are synthetic scaling measurements, not claims about human
editorial quality or cloud-provider latency.

Knowledge-enabled runs additionally require at least 380 accepted inputs, at
least 70% principle reduction and 45% total-construct reduction,
scenario-relevant TasteProfiles, zero
unresolved conflicts, and source-neutral taste identity in plans. The current
catalog contains 385 accepted items and zero rejected files; all ten scenarios
pass these gates.
