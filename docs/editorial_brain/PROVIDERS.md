# Editorial Brain Providers

Provider protocols are transcription, diarization, vision, semantic, embedding,
and future editorial directives. Every request/result is strict and includes a
provider/model fingerprint, schema/prompt version, timeout/retry policy,
cache identity, usage/cost when reported, and structured availability/errors.

Baseline providers are deterministic and network-free. Cloud adapters are
optional: Deepgram is the preferred word-timed transcription path; OpenAI
Responses is the multimodal/semantic path. Provider outputs may rank or classify
known candidate IDs but cannot create source ranges.

Deepgram uses prerecorded `/v1/listen` with `nova-3`, word timing,
punctuation, utterances, optional fillers and diarization. Uploads stream in
bounded chunks; seconds convert immediately to microsecond-timescale rational
time. The diarization adapter returns typed `SpeakerSegment` values.

OpenAI uses the Responses API with strict `text.format` JSON Schema. Vision
requests validate local frame paths and SHA-256 and enforce a 20 MiB limit.
Responses must return exactly one judgment for every supplied candidate ID;
unknown, duplicate, omitted, or invented IDs fail closed.

`EditorialBrain.from_environment(project_root)` is the production provider
factory used by `video-brain`. It selects OpenAI when `OPENAI_API_KEY` exists;
otherwise it selects the authenticated local Codex CLI. Codex runs one fresh
ephemeral read-only sub-agent per batched semantic or vision request, from an
empty temporary directory, with verified images and a strict output schema.
Transcript/candidate content is treated as untrusted data. Direct
`EditorialBrain(project_root)` construction remains network-free unless callers
inject providers explicitly.

Secrets are read only at call time, never logged or cached. Providers resolve
the process environment first and then the project-root `.env` without copying
secrets into global process state. Missing keys produce
`provider_unavailable`; corrupt or schema-invalid responses fail closed.
Real smoke tests are marked `provider_smoke` and run only when explicitly
enabled with both credentials. Ordinary tests make no network calls.
