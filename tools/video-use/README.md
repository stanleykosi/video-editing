<p align="center">
  <img src="docs/assets/video-use-banner.png" alt="video-use" width="100%">
</p>

# video-use

**video-use** is the agent workflow layer around the canonical
`video_engine` package. It works with Codex, Claude Code, and other agents that
can read the skill and invoke local tools.

Drop raw footage in a folder, direct your coding agent, and get `final.mp4` back.
The workflow supports talking heads, montages, tutorials, travel, and interviews
without requiring a separate editing UI.

## What it does

- **Cuts out filler words** (`umm`, `uh`, false starts) and dead space between takes
- **Applies typed color pipelines** per segment, including measured correction, named legacy-preset translations, and LUTs
- **30ms audio fades** at every cut so you never hear a pop
- **Burns subtitles** in your style — 2-word UPPERCASE chunks by default, fully customizable
- **Generates animation overlays** via [HyperFrames](https://github.com/heygen-com/hyperframes), [Remotion](https://www.remotion.dev/), or [Manim](https://www.manim.community/); Pillow is reserved for diagnostics, masks, placeholders, and test utilities
- **Self-evaluates the rendered output** at every cut boundary before showing you anything
- **Persists session memory** in `project.md` so next week's session picks up where you left off

## Setup prompt

Paste into Claude Code, Codex, Hermes, Openclaw, or any agent with shell access:

```text
Set up https://github.com/stanleykosi/video-editing for me.

Read install.md first to install this repo, wire up ffmpeg, and register the
skill with whichever agent you're running under. Set up a Deepgram key only when
the requested workflow needs hosted transcription or voiceover. Then read
SKILL.md for daily usage and use the canonical `video-engine` CLI for project
migration, rendering, inspection, and QC. Preparation helpers remain available
only for the tasks named in SKILL.md. After install, do not transcribe anything
on your own; report readiness and wait for footage or a project brief.
```

The agent handles the clone, dependencies, and skill registration. Deepgram is
the preferred hosted speech provider; the older ElevenLabs Scribe helper remains
available only for compatibility.

Then point your agent at a folder of raw takes:

```bash
cd /path/to/your/videos
claude    # or codex, hermes, etc.
```

And in the session:

> edit these into a launch video

It inventories the sources, proposes a strategy, waits for your OK, then produces `edit/final.mp4` next to your sources. All outputs live in `<videos_dir>/edit/` — the skill directory stays clean.

## Manual install

If you'd rather do it by hand:

```bash
# 1. Clone and symlink into your agent's skills directory
git clone https://github.com/stanleykosi/video-editing ~/Developer/video-editing
ln -sfn ~/Developer/video-editing/tools/video-use ~/.claude/skills/video-use
# ln -sfn ~/Developer/video-editing/tools/video-use ~/.codex/skills/video-use

# 2. Install deps
cd ~/Developer/video-editing
uv sync --frozen --extra legacy --extra interchange --group dev
npm ci --ignore-scripts
npm run remotion:browser
brew install ffmpeg             # required
brew install yt-dlp             # optional, for downloading online sources

# 3. Add optional hosted speech credentials when needed
cp .env.example .env
$EDITOR .env                    # DEEPGRAM_API_KEY=...
```

The repository-root `pyproject.toml`, `uv.lock`, `package.json`, and
`package-lock.json` are the only dependency authorities. `tools/video-use/` is
a skill/workflow directory, not a separately installed package.

## How it works

The LLM never watches the video. It **reads** it — through two layers that together give it everything it needs to cut with word-boundary precision.

<p align="center">
  <img src="docs/assets/timeline-view.svg" alt="timeline_view composite — filmstrip + speaker track + waveform + word labels + silence-gap cut candidates" width="100%">
</p>

**Layer 1 — Audio transcript (always loaded).** Deepgram produces word-level
timestamps and speaker diarization; the compatibility Scribe helper can produce
the same packed input shape. All takes pack into a compact `takes_packed.md`,
the agent's primary reading view.

```
## C0103  (duration: 43.0s, 8 phrases)
  [002.52-005.36] S0 Ninety percent of what a web agent does is completely wasted.
  [006.08-006.74] S0 We fixed this.
```

**Layer 2 — Visual composite (on demand).** Canonical `video-engine inspect`
produces hashed filmstrip, waveform, contact-sheet, and JSON/Markdown evidence.
The historical `timeline_view.py` command is a thin compatibility delegate to
that service. Use it only at decision points such as ambiguous pauses, retake
comparisons, and cut-point checks.

> Naive approach: 30,000 frames × 1,500 tokens = **45M tokens of noise**.
> Video Use: **12KB text + a handful of PNGs**.

Same idea as browser-use giving an LLM a structured DOM instead of a screenshot — but for video.

## Pipeline

```
Transcribe ──> Pack ──> LLM Reasons ──> EDL ──> Render ──> Self-Eval
                                                              │
                                                              └─ issue? fix + re-render (max 3)
```

The self-eval loop runs `timeline_view` on the _rendered output_ at every cut boundary — catches visual jumps, audio pops, hidden subtitles. You see the preview only after it passes.

## Design principles

1. **Text + on-demand visuals.** No frame-dumping. The transcript is the surface.
2. **Audio is primary, visuals follow.** Cuts come from speech boundaries and silence gaps.
3. **Ask → confirm → execute → self-eval → persist.** Never touch the cut without strategy approval.
4. **Zero assumptions about content type.** Look, ask, then edit.
5. **Hard correctness rules, artistic freedom elsewhere.** Production correctness is non-negotiable. Taste is not.

See [`SKILL.md`](./SKILL.md) for the full production rules and editing craft.
