# Editorial Brain Current State

Baseline recorded on 2026-07-29 at commit
`54c6dcd1b29be4f6bf653a4ee0ef2691d5400b11`; the worktree was clean before
implementation. The canonical engine schema is `1.2.0`, project revisions are
optimistically checked, and all authoritative time is `RationalTime`/
`TimeRange`.

The engine already provides strict projects, media SHA-256 identity, media
probing and derivatives, exact inspection artifacts, transactional operations,
J/L-cut and audio-extension operations, rendering, and technical QC. It does
not provide source understanding, semantic indexing, editorial selection,
continuity judgment, pacing, or sequence optimization. Those belong exclusively
in `editorial_brain`.

The unmodified engine baseline completed with 329 passed and 10 skipped tests;
compact immutable evidence remains in `testdata/engine/baseline.tar.gz`.
Existing helper transcription is Deepgram `nova-3` with words/diarization. The
Brain wraps it with strict requests, immediate rational-time conversion,
provider fingerprints, retry/error semantics and source-hash cache identity.

No existing engine backend or helper-owned timeline is used by the Brain. The
only engine addition is the general-purpose `AddTrackOperation`, proven
necessary for projects without suitable video/audio lanes. It has no editorial
policy.
